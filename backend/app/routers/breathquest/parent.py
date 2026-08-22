"""
routers/parent.py — Parent-facing views. Deliberately separate from
dashboard.py (therapist-only) so clinical notes and the ICF PDF report can
never be reachable via a parent token, even by accident.
"""

from datetime import datetime, timezone, timedelta
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.breathquest_models import Parent, GameSession, BreathQuestPatient
from app.schemas.breathquest_schemas import ParentProgressOut, WeeklySummaryOut, GuidedActivityOut, HomePracticeIdeaOut, CategoryProgress, LevelProgress
from app.breathquest_core.deps import get_current_parent
from app.services.weekly_summary import generate_weekly_summary
from app.services.home_practice_ideas import IDEAS, filter_ideas
from app.retraining import data_store as chime_data_store
from app.routers.breathquest.dashboard import LEVEL_NAMES, CHIME_DB_PATH
# vaakmirror lives outside this backend's Python path in some deploy
# configs -- degrade to None rather than crashing app startup, same
# pattern as kid_progress.py's own VaakMirrorSession handling.
from collections import defaultdict
from app.models.vaakmirror_models import (
    VaakMirrorSession, Attempt, AttemptOutcome,
)
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.flashcards_models import PhonemeMastery
from sqlalchemy import func

_VM_SUCCESS_OUTCOMES = (AttemptOutcome.passed, AttemptOutcome.caught)  # matches weekly_summary.py's definition

router = APIRouter(prefix="/parent", tags=["parent"])


async def _get_linked_patient(parent: Parent, db: AsyncSession) -> BreathQuestPatient:
    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == parent.patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Linked child account no longer exists")
    return patient


@router.get("/progress", response_model=ParentProgressOut)
async def get_parent_progress(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    patient = await _get_linked_patient(parent, db)

    pid_str = str(patient.id)

    # --- BreathQuest ---
    sessions_result = await db.execute(
        select(GameSession)
        .where(GameSession.patient_id == patient.id)
        .order_by(GameSession.started_at.desc())
    )
    sessions = sessions_result.scalars().all()
    completed = [s for s in sessions if s.completed]

    total_stars = sum(s.stars_earned or 0 for s in completed)
    max_possible = len(LEVEL_NAMES) * 3

    level_progress = []
    bq_categories = []
    for level_id, level_name in LEVEL_NAMES.items():
        level_sessions = [s for s in completed if s.level_id == level_id]
        all_level_sessions = [s for s in sessions if s.level_id == level_id]
        best_stars = max((s.stars_earned or 0 for s in level_sessions), default=0)
        avg_stars = (sum(s.stars_earned or 0 for s in level_sessions) / len(level_sessions)) if level_sessions else 0.0
        last_played = max((s.started_at for s in level_sessions), default=None)
        level_progress.append(LevelProgress(
            level_id=level_id,
            level_name=level_name,
            attempts=len(all_level_sessions),
            best_stars=best_stars,
            avg_stars=round(avg_stars, 2),
            # Deliberately omitted for parents — avg_breath_strength is a
            # clinical/raw measurement, not something a parent needs to see
            # a number for; the trend is conveyed via weekly_summary's text.
            avg_breath_strength=None,
            last_played=last_played,
        ))
        bq_categories.append(CategoryProgress(
            category_name=level_name,
            attempts=len(all_level_sessions),
            accuracy_pct=round(100 * len(level_sessions) / len(all_level_sessions), 1) if all_level_sessions else 0.0,
            last_played=last_played,
            stars=best_stars,
        ))

    # --- VoiceHurdleRace ---
    vhr_sessions = (await db.execute(
        select(VoiceHurdleRaceSession).where(VoiceHurdleRaceSession.patient_id == patient.id)
    )).scalars().all()
    vhr_by_level = defaultdict(list)
    for s in vhr_sessions:
        vhr_by_level[s.level_name].append(s)
    vhr_categories = [
        CategoryProgress(
            category_name=name,
            attempts=len(rows),
            accuracy_pct=round(sum((r.pitch_accuracy + r.loudness_accuracy) / 2 for r in rows) / len(rows), 1),
            last_played=max(r.created_at for r in rows),
            stars=max(r.stars for r in rows),
        ) for name, rows in vhr_by_level.items()
    ]
    vhr_total_stars = sum(s.stars for s in vhr_sessions)

    # --- VaakMirror (patient_id is a loose String column, not a real FK —
    # join Attempt -> VaakMirrorSession on session_id, filter session's
    # patient_id as a string compare, same pattern as weekly_summary.py) ---
    vm_attempts = (await db.execute(
        select(Attempt, VaakMirrorSession.game)
        .join(VaakMirrorSession, Attempt.session_id == VaakMirrorSession.id)
        .where(VaakMirrorSession.patient_id == pid_str)
    )).all()
    vm_by_game = defaultdict(list)
    for attempt, game in vm_attempts:
        vm_by_game[game.value].append(attempt)
    vm_categories = [
        CategoryProgress(
            category_name=game,
            attempts=len(rows),
            accuracy_pct=round(100 * len([r for r in rows if r.outcome in _VM_SUCCESS_OUTCOMES]) / len(rows), 1),
            last_played=max(r.created_at for r in rows),
            stars=None,
        ) for game, rows in vm_by_game.items()
    ]

    # --- Flashcards ---
    fc_mastery = (await db.execute(
        select(PhonemeMastery).where(PhonemeMastery.patient_id == patient.id)
    )).scalars().all()
    fc_categories = [
        CategoryProgress(
            category_name=m.phoneme,
            attempts=m.attempts_count,
            accuracy_pct=round(m.accuracy, 1),
            last_played=m.last_practiced_at,
            stars=None,
        ) for m in fc_mastery
    ]

    # --- Chime -- Postgres-backed RLTrainingEvent rows, grouped by level_id.
    # level_id here is actually a sound/phoneme id (same key dashboard.py's
    # weekly-trend buckets already group VaakMirror + Chime together on),
    # not a BreathQuest level number -- so no LEVEL_NAMES lookup, mirror
    # Flashcards' bare-id-as-category_name treatment instead. No stars
    # concept, same as VaakMirror/Flashcards.
    chime_events = await asyncio.to_thread(
        chime_data_store.get_events, child_id=pid_str, db_path=chime_data_store.DEFAULT_DB_PATH
    )
    chime_by_sound = defaultdict(list)
    for ev in chime_events:
        level_id = ev.get("level_id")
        if not level_id:
            continue
        chime_by_sound[level_id].append(ev)
    chime_categories = [
        CategoryProgress(
            category_name=sound_id,
            attempts=len(evs),
            accuracy_pct=round(100 * len([e for e in evs if e.get("is_valid_attempt")]) / len(evs), 1),
            last_played=max(e["timestamp"] for e in evs),
            stars=None,
        ) for sound_id, evs in chime_by_sound.items()
    ]

    trend = None
    if len(completed) >= 6:
        recent = [s.stars_earned or 0 for s in completed[:5]]
        older = [s.stars_earned or 0 for s in completed[5:10]]
        trend = round((sum(recent) / len(recent)) - (sum(older) / len(older)), 2)

    now = datetime.now(timezone.utc)
    this_monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    weekly_data = await generate_weekly_summary(db, patient, this_monday, chime_data_store.DEFAULT_DB_PATH)

    # Same adaptive-difficulty recommendation therapists already see on
    # PatientProgress (dashboard.py) -- reusing the identical source
    # rather than a second, possibly-divergent computation.
    latest_decision = await asyncio.to_thread(chime_data_store.get_latest_decision, str(patient.id))
    recommended_action = latest_decision["recommended_action"] if latest_decision else None
    recommendation_message = latest_decision["recommendation_message"] if latest_decision else None

    breath_consistency_vals = [s.breath_consistency for s in completed if s.breath_consistency is not None]
    avg_breath_consistency = (
        round(sum(breath_consistency_vals) / len(breath_consistency_vals), 3)
        if breath_consistency_vals else None
    )

    return ParentProgressOut(
        child_first_name=patient.first_name,
        avatar=patient.avatar,
        total_sessions=len(sessions),
        total_stars=total_stars + vhr_total_stars,
        max_possible_stars=max_possible + len(vhr_by_level) * 3,
        completion_rate=round(len(completed) / len(sessions), 2) if sessions else 0.0,
        improvement_trend=trend,
        level_progress=level_progress,
        categories={
            "breathquest": bq_categories,
            "voicehurdlerace": vhr_categories,
            "vaakmirror": vm_categories,
            "flashcards": fc_categories,
            "chime": chime_categories,
        },
        weekly_summary=WeeklySummaryOut(**weekly_data),
        recommended_action=recommended_action,
        recommendation_message=recommendation_message,
        avg_breath_consistency=avg_breath_consistency,
    )


# Sound ids used in VaakMirror/Chime don't always match a home-practice-idea
# goal tag directly (e.g. "th-voiced" vs "th", or a CV syllable like "ta"
# instead of the base sound "t") — this normalizes the common cases down to
# the tags home_practice_ideas.py actually uses.
def _normalize_goal_tag(sound_id: str) -> str:
    s = sound_id.lower()
    if s.startswith("th"):
        return "th"
    for base in ("sh", "ch", "ng", "wh", "qu"):
        if s.startswith(base):
            return base
    if s and s[0] in "szldrtkgnwyh":
        return s[0]
    return s


@router.get("/guided-activity", response_model=GuidedActivityOut)
async def get_guided_activity(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    """'Try this activity with your child' — picks one idea from the 50-item
    library, targeted at whichever sound has the lowest recent accuracy if
    we have enough data, otherwise a stable pick-of-the-day so it's not a
    different random suggestion on every refresh."""
    patient = await _get_linked_patient(parent, db)
    since = datetime.now(timezone.utc) - timedelta(days=30)

    accuracy_by_sound: dict[str, list[int]] = {}  # sound -> [correct, total]

    vm_result = await db.execute(
        select(Attempt.sound_id, Attempt.outcome)
        .join(VaakMirrorSession, Attempt.session_id == VaakMirrorSession.id)
        .where(
            # VaakMirrorSession.patient_id is a loose String column, not a
            # real FK -- must compare as str(patient.id), same pattern as
            # get_parent_progress's pid_str and weekly_summary.py.
            VaakMirrorSession.patient_id == str(patient.id),
            Attempt.created_at >= since,
            Attempt.sound_id.isnot(None),
        )
    )
    for sound_id, outcome in vm_result.all():
        tag = _normalize_goal_tag(sound_id)
        entry = accuracy_by_sound.setdefault(tag, [0, 0])
        entry[1] += 1
        if outcome in ("passed", "caught"):
            entry[0] += 1

    # chime_data_store.get_events is synchronous SQLite I/O — thread it off
    # since this route is `async def` (same fix applied across
    # dashboard.py/kid_progress.py/chime.py's get_patient_events).
    chime_events = await asyncio.to_thread(chime_data_store.get_events, child_id=patient.id, db_path=CHIME_DB_PATH)
    for ev in chime_events:
        if not ev.get("level_id"):
            continue
        try:
            ts = datetime.fromisoformat(ev["timestamp"])
        except (KeyError, ValueError, TypeError):
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < since:
            continue
        tag = _normalize_goal_tag(ev["level_id"])
        entry = accuracy_by_sound.setdefault(tag, [0, 0])
        entry[1] += 1
        if ev.get("is_valid_attempt"):
            entry[0] += 1

    weakest_tag = None
    weakest_rate = None
    for tag, (correct, total) in accuracy_by_sound.items():
        if total < 2:
            continue
        rate = correct / total
        if weakest_rate is None or rate < weakest_rate:
            weakest_rate, weakest_tag = rate, tag

    pool = filter_ideas(goal=weakest_tag) if weakest_tag else IDEAS
    if not pool:
        pool = IDEAS

    # Stable per-day pick so the suggestion doesn't change on every refresh.
    pick_index = (hash(str(patient.id) + datetime.now(timezone.utc).strftime("%Y-%m-%d"))) % len(pool)
    idea = pool[pick_index]

    if weakest_tag:
        reason = f"{patient.first_name} has been finding the '{weakest_tag}' sound tricky recently — this activity gives some low-pressure extra practice with it."
    else:
        reason = f"A good all-around activity to try with {patient.first_name} today."

    return GuidedActivityOut(idea=HomePracticeIdeaOut(**idea), reason=reason)
