"""
routers/kid_progress.py — What the child themself can see about their own
progress. Deliberately minimal: no raw scores, no per-level breakdown, no
clinical language — just concrete, encouraging counts a kid can read
themself. Full session/level detail stays therapist/parent-only.
"""

from datetime import datetime, timezone, timedelta
import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db, SessionLocal
from app.models.patient import Patient
from app.models.breathquest_models import GameSession
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.retraining import data_store as chime_data_store
from app.models.vaakmirror_models import VaakMirrorSession
from app.models.flashcards_models import FlashcardAttempt
from app.models.session import Session as AssessmentSession
from app.schemas.breathquest_schemas import KidProgressOut, KidHistoryEntry, BreathQuestLevelScore
from app.breathquest_core.deps import get_current_patient
from app.routers.breathquest.dashboard import LEVEL_NAMES as BQ_LEVEL_NAMES
from app.models.vaakmirror_models import GameName as VMGameName

router = APIRouter(prefix="/me", tags=["kid-progress"])

CHIME_DB_PATH = chime_data_store.DEFAULT_DB_PATH
LEVELS_PER_STAR_CAP = 6  # matches len(dashboard.LEVEL_NAMES) — max_possible_stars basis

VM_GAME_LABELS = {
    VMGameName.mirror_mirror.value: "Mirror, Mirror",
    VMGameName.tongue_tamer.value: "Tongue Tamer",
    VMGameName.lip_sync_hero.value: "Lip Sync Hero",
}


@router.get("/progress", response_model=KidProgressOut)
async def get_my_progress(
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    stars_result = await db.execute(
        select(func.sum(GameSession.stars_earned)).where(
            GameSession.patient_id == patient.id, GameSession.completed == True
        )
    )
    total_stars = int(stars_result.scalar() or 0)

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    bq_week = (await db.execute(
        select(func.count(GameSession.id)).where(
            and_(GameSession.patient_id == patient.id, GameSession.started_at >= week_ago)
        )
    )).scalar() or 0
    vhr_week = (await db.execute(
        select(func.count(VoiceHurdleRaceSession.id)).where(
            and_(VoiceHurdleRaceSession.patient_id == patient.id, VoiceHurdleRaceSession.created_at >= week_ago)
        )
    )).scalar() or 0
    # patient_id here is a plain String column (VaakMirrorSession rows are
    # written via a str(patient.id) elsewhere -- see
    # routers/vaakmirror/sessions.py's create_session), not a UUID column
    # like the other three tables queried on this page. Comparing it
    # directly against patient.id (a UUID object) either mismatches
    # silently or errors depending on the driver's type coercion --
    # str() it explicitly rather than relying on that.
    vm_week = (await db.execute(
        select(func.count(VaakMirrorSession.id)).where(
            and_(VaakMirrorSession.patient_id == str(patient.id), VaakMirrorSession.started_at >= week_ago)
        )
    )).scalar() or 0
    # chime_data_store.* is synchronous SQLite I/O — thread it off since
    # this route is `async def` (same class of bug fixed across
    # dashboard.py/parent.py/chime.py's get_patient_events in this pass:
    # a direct call here would block the whole app's event loop for
    # every other concurrent request while this query runs).
    chime_week = await asyncio.to_thread(
        chime_data_store.count_events_since, [patient.id], week_ago.isoformat(), db_path=CHIME_DB_PATH,
    )

    games_played_this_week = bq_week + vhr_week + vm_week + chime_week

    # Simple streak: count consecutive days (including today) with at least
    # one session/event, walking backward from today. Cheap enough at kid
    # data volumes to compute on read rather than maintaining a counter.
    last_played = await asyncio.to_thread(chime_data_store.last_event_time, child_id=patient.id, db_path=CHIME_DB_PATH)
    bq_dates_result = await db.execute(
        select(func.date(GameSession.started_at)).where(GameSession.patient_id == patient.id).distinct()
    )
    played_dates = {row[0] for row in bq_dates_result.all()}

    streak = 0
    cursor = datetime.now(timezone.utc).date()
    while cursor.isoformat() in {str(d) for d in played_dates}:
        streak += 1
        cursor = cursor - timedelta(days=1)

    return KidProgressOut(
        first_name=patient.first_name,
        avatar=patient.avatar,
        total_stars=total_stars,
        max_possible_stars=LEVELS_PER_STAR_CAP * 3,
        games_played_this_week=games_played_this_week,
        current_streak_days=streak,
    )


@router.get("/breathquest/level-scores", response_model=dict[str, BreathQuestLevelScore])
async def get_my_breathquest_level_scores(
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Per-level best stars + play count, keyed by level_id -- the server-side
    source of truth for the level-unlock/best-star state that
    game/scoring/index.js previously only kept in localStorage. That cache
    silently reset on a new device, a cleared browser, or private/incognito
    mode even though every completed GameSession was already recorded here;
    this lets the frontend hydrate from the real history instead of trusting
    whatever (if anything) survived in this browser."""
    rows = (await db.execute(
        select(
            GameSession.level_id,
            func.max(GameSession.stars_earned).label("best_stars"),
            func.count(GameSession.id).label("plays"),
            func.max(GameSession.started_at).label("last_played"),
        )
        .where(GameSession.patient_id == patient.id, GameSession.completed == True)
        .group_by(GameSession.level_id)
    )).all()

    return {
        (row.level_id.value if hasattr(row.level_id, "value") else row.level_id): BreathQuestLevelScore(
            stars=int(row.best_stars or 0),
            plays=int(row.plays or 0),
            last_played=row.last_played,
        )
        for row in rows
    }


@router.get("/history", response_model=list[KidHistoryEntry])
async def get_my_history(
    patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Combined, chronological (newest first) list of every assessment
    and every game session this kid has, across all four games plus the
    Assessment flow -- for pages/kid/AccountHistory.jsx, linked from
    MyAccount.jsx. Same no-raw-scores framing as /me/progress; game
    entries say what was played and when, not the underlying accuracy
    numbers, and assessment entries say one happened, not its
    severity_classification/diagnostic findings (therapist/parent-only,
    same as the rest of this app)."""
    entries: list[KidHistoryEntry] = []

    # --- Assessments (Assessment side's `sessions` table, session_type
    # "word_practice" -- see assessment_lookup.py's own note on why this
    # table/query shape). Sync SessionLocal to match that file's pattern.
    if patient.assessment_patient_id:
        def _fetch_assessments():
            sync_db = SessionLocal()
            try:
                return (
                    sync_db.query(AssessmentSession)
                    .filter(
                        AssessmentSession.patient_id == patient.assessment_patient_id,
                        AssessmentSession.session_type == "word_practice",
                    )
                    .order_by(AssessmentSession.created_at.desc())
                    .all()
                )
            finally:
                sync_db.close()

        for s in await asyncio.to_thread(_fetch_assessments):
            entries.append(KidHistoryEntry(
                kind="assessment",
                title="Pronunciation Assessment",
                detail="Completed",
                date=s.created_at,
            ))

    # --- BreathQuest
    bq_rows = (await db.execute(
        select(GameSession).where(GameSession.patient_id == patient.id)
    )).scalars().all()
    for g in bq_rows:
        level_name = BQ_LEVEL_NAMES.get(g.level_id, g.level_id)
        detail = f"{g.stars_earned} star{'s' if g.stars_earned != 1 else ''}" if g.completed else "Not completed"
        entries.append(KidHistoryEntry(
            kind="game", game="BreathQuest",
            title=f"BreathQuest — {level_name}",
            detail=detail,
            date=g.started_at,
        ))

    # --- VoiceHurdleRace
    vhr_rows = (await db.execute(
        select(VoiceHurdleRaceSession).where(VoiceHurdleRaceSession.patient_id == patient.id)
    )).scalars().all()
    for v in vhr_rows:
        entries.append(KidHistoryEntry(
            kind="game", game="VoiceHurdleRace",
            title=f"VoiceHurdleRace — {v.level_name}",
            detail=f"{v.stars} star{'s' if v.stars != 1 else ''}",
            date=v.created_at,
        ))

    # --- VaakMirror. patient_id is a plain String column here (see the
    # str(patient.id) note on /progress's own VaakMirror query above).
    vm_rows = (await db.execute(
        select(VaakMirrorSession).where(VaakMirrorSession.patient_id == str(patient.id))
    )).scalars().all()
    for m in vm_rows:
        game_label = VM_GAME_LABELS.get(m.game.value if hasattr(m.game, "value") else m.game, str(m.game))
        entries.append(KidHistoryEntry(
            kind="game", game="VaakMirror",
            title=f"VaakMirror — {game_label}",
            detail="Completed" if m.ended_at else "In progress",
            date=m.started_at,
        ))

    # --- Chime/Flashcards. One row per attempted word -- grouped by
    # session_id into one history entry per playthrough, same as a kid
    # would think of "a round" rather than seeing one line per word.
    chime_rows = (await db.execute(
        select(
            FlashcardAttempt.session_id,
            func.min(FlashcardAttempt.created_at).label("started_at"),
            func.max(FlashcardAttempt.theme_id).label("theme_id"),
            func.count(FlashcardAttempt.id).label("word_count"),
        )
        .where(FlashcardAttempt.patient_id == patient.id)
        .group_by(FlashcardAttempt.session_id)
    )).all()
    for session_id, started_at, theme_id, word_count in chime_rows:
        entries.append(KidHistoryEntry(
            kind="game", game="Chime",
            title=f"Chime — {theme_id or 'Practice'}",
            detail=f"{word_count} word{'s' if word_count != 1 else ''} practiced",
            date=started_at,
        ))

    def _sort_key(entry: KidHistoryEntry):
        # Mixed sources here: the Assessment side's `sessions` table uses
        # a naive TIMESTAMP (app/models/session.py), while the four game
        # tables use timezone-aware DateTime -- sorting a naive/aware mix
        # directly raises TypeError. Strip tzinfo for the sort key only;
        # the actual `date` field returned to the client keeps whatever
        # the DB gave it.
        if entry.date is None:
            return datetime.min
        return entry.date.replace(tzinfo=None) if entry.date.tzinfo else entry.date

    entries.sort(key=_sort_key, reverse=True)
    return entries
