"""
routers/parent.py — Parent-facing views. Deliberately separate from
dashboard.py (therapist-only) so clinical notes and the ICF PDF report can
never be reachable via a parent token, even by accident.
"""

from datetime import datetime, timezone, timedelta
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.breathquest_models import Parent, GameSession, BreathQuestPatient, Message, SenderRole, Goal, Assignment
from app.schemas.breathquest_schemas import ParentProgressOut, WeeklySummaryOut, GuidedActivityOut, HomePracticeIdeaOut, CategoryProgress, LevelProgress, MessageCreate, MessageOut, GoalOut, AssignmentOut
from app.breathquest_core.deps import get_current_parent
from app.services.weekly_summary import generate_weekly_summary
from app.services.home_practice_ideas import IDEAS, filter_ideas
from app.retraining import data_store as chime_data_store
from app.routers.breathquest.dashboard import LEVEL_NAMES, CHIME_DB_PATH, _compute_goal_current_value
# vaakmirror lives outside this backend's Python path in some deploy
# configs -- degrade to None rather than crashing app startup, same
# pattern as kid_progress.py's own VaakMirrorSession handling.
from collections import defaultdict
from app.models.vaakmirror_models import (
    VaakMirrorSession, Attempt, AttemptOutcome,
)
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.flashcards_models import PhonemeMastery, FlashcardAttempt
from app.schemas.breathquest_schemas import HistoryEntry, CategoryHistoryOut, ChimeWeeklyBreakdownOut, ChimeSoundBreakdown, EmailPreferencesOut, CrossGamePhonemeSummaryOut
from app.services.weekly_summary import _week_chime_events
from app.services.phoneme_summary import get_cross_game_phoneme_summary
from sqlalchemy import func

_VM_SUCCESS_OUTCOMES = (AttemptOutcome.passed, AttemptOutcome.caught)  # matches weekly_summary.py's definition


def _trend_from_dated(rows, date_fn, value_fn):
    """Compares the two most recent entries' values by date_fn. None with
    fewer than 2 rows -- a brand-new category shouldn't show a flat arrow,
    it should show nothing."""
    if len(rows) < 2:
        return None
    ordered = sorted(rows, key=date_fn)
    prev, latest = value_fn(ordered[-2]), value_fn(ordered[-1])
    if latest > prev:
        return "up"
    if latest < prev:
        return "down"
    return "flat"


# raise = engine made it harder going into this attempt, lower = easier,
# hold = unchanged. "level_complete" is a client-set sentinel on the
# final event of a level and never appears in recommended_action (that's
# a server-set field, this games's client sends `action` for that instead
# -- two different columns), so it's deliberately absent here.
_CHIME_DIFFICULTY_LABELS = {"raise": "harder", "lower": "easier", "hold": "same"}


def _chime_ts(ev):
    ts = datetime.fromisoformat(ev["timestamp"])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


router = APIRouter(prefix="/parent", tags=["parent"])


async def _get_linked_patient(parent: Parent, db: AsyncSession) -> BreathQuestPatient:
    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == parent.patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Linked child account no longer exists")
    return patient


async def _get_linked_patient_with_therapist(parent: Parent, db: AsyncSession) -> BreathQuestPatient:
    """Same as _get_linked_patient, but for the messaging routes only --
    messaging a therapist requires an actual therapist to be on the other
    end. Without this check, a self-registered family (no therapist_id)
    could send messages into a conversation nobody ever reads, with no
    error surfaced anywhere -- silently broken rather than absent."""
    patient = await _get_linked_patient(parent, db)
    if not patient.therapist_id:
        raise HTTPException(
            status_code=403,
            detail="Messaging is available once your child is connected with a therapist",
        )
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
            trend=_trend_from_dated(level_sessions, lambda s: s.started_at, lambda s: s.stars_earned or 0),
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
            trend=_trend_from_dated(rows, lambda r: r.created_at, lambda r: (r.pitch_accuracy + r.loudness_accuracy) / 2),
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
            trend=_trend_from_dated(rows, lambda r: r.created_at, lambda r: 100.0 if r.outcome in _VM_SUCCESS_OUTCOMES else 0.0),
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
            # PhonemeMastery is a rolling aggregate, not a dated attempt
            # list -- no "last two" to compare without an extra query.
            trend=None,
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
            trend=_trend_from_dated(evs, _chime_ts, lambda e: 100.0 if e.get("is_valid_attempt") else 0.0),
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

    # Actual goal/assignment content -- weekly_summary above only ever
    # carried counts (goals_open, assignments_completed). Reuses the same
    # rolling-5-session _compute_goal_current_value the therapist Care tab
    # uses so a goal never shows a different number to the two of them.
    goals_result = await db.execute(
        select(Goal).where(Goal.patient_id == patient.id).order_by(Goal.created_at.desc())
    )
    goals_out = []
    for g in goals_result.scalars().all():
        item = GoalOut.model_validate(g)
        item.current_value = await _compute_goal_current_value(g, db)
        goals_out.append(item)

    assignments_result = await db.execute(
        select(Assignment).where(Assignment.patient_id == patient.id).order_by(Assignment.created_at.desc())
    )
    assignments_out = [AssignmentOut.model_validate(a) for a in assignments_result.scalars().all()]

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
        has_therapist=bool(patient.therapist_id),
        goals=goals_out,
        assignments=assignments_out,
        player_code=patient.player_code,
    )


@router.get("/history/{category}/{item}", response_model=CategoryHistoryOut)
async def get_category_history(
    category: str,
    item: str,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    """Per-attempt history for a single category/item pair from the
    /progress summary above -- e.g. category='flashcards', item='EH'.
    Kept as its own endpoint rather than inflating /progress, since most
    of the time a parent never expands a row and doesn't need this."""
    patient = await _get_linked_patient(parent, db)
    pid_str = str(patient.id)
    entries: list[HistoryEntry] = []

    if category == "breathquest":
        level_id = {v: k for k, v in LEVEL_NAMES.items()}.get(item)
        if level_id:
            rows = (await db.execute(
                select(GameSession)
                .where(GameSession.patient_id == patient.id, GameSession.level_id == level_id)
                .order_by(GameSession.started_at.asc())
            )).scalars().all()
            entries = [
                HistoryEntry(
                    date=s.started_at,
                    label=f"{s.stars_earned or 0}★" + ("" if s.completed else " · not completed"),
                    value=float(s.stars_earned or 0),
                ) for s in rows
            ]

    elif category == "voicehurdlerace":
        rows = (await db.execute(
            select(VoiceHurdleRaceSession)
            .where(VoiceHurdleRaceSession.patient_id == patient.id, VoiceHurdleRaceSession.level_name == item)
            .order_by(VoiceHurdleRaceSession.created_at.asc())
        )).scalars().all()
        entries = [
            HistoryEntry(
                date=s.created_at,
                label=f"{s.stars}★ · pitch {round(s.pitch_accuracy)}% · loudness {round(s.loudness_accuracy)}%",
                value=round((s.pitch_accuracy + s.loudness_accuracy) / 2, 1),
            ) for s in rows
        ]

    elif category == "vaakmirror":
        rows = (await db.execute(
            select(Attempt)
            .join(VaakMirrorSession, Attempt.session_id == VaakMirrorSession.id)
            .where(VaakMirrorSession.patient_id == pid_str, VaakMirrorSession.game == item)
            .order_by(Attempt.created_at.asc())
        )).scalars().all()
        entries = [
            HistoryEntry(
                date=r.created_at,
                label=(r.outcome.value if hasattr(r.outcome, "value") else str(r.outcome)) + (f" · {r.sound_id}" if r.sound_id else ""),
                value=100.0 if r.outcome in _VM_SUCCESS_OUTCOMES else 0.0,
            ) for r in rows
        ]

    elif category == "flashcards":
        phoneme = item.upper()
        rows = (await db.execute(
            select(FlashcardAttempt)
            .where(FlashcardAttempt.patient_id == patient.id)
            .order_by(FlashcardAttempt.created_at.asc())
        )).scalars().all()
        for a in rows:
            matches = [m for m in (a.phoneme_matches or []) if (m.get("expected") or "").upper() == phoneme]
            if not matches:
                continue
            correct = any(m.get("correct") for m in matches)
            entries.append(HistoryEntry(
                date=a.created_at,
                label=f"'{a.target_word}' · {'correct' if correct else 'needs work'}",
                value=100.0 if correct else 0.0,
                detail=a.transcript,
            ))

    elif category == "chime":
        chime_events = await asyncio.to_thread(
            chime_data_store.get_events, child_id=pid_str, db_path=chime_data_store.DEFAULT_DB_PATH
        )
        for ev in chime_events:
            if ev.get("level_id") != item:
                continue
            try:
                ts = datetime.fromisoformat(ev["timestamp"])
            except (KeyError, ValueError, TypeError):
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            label = "valid attempt" if ev.get("is_valid_attempt") else "attempt"
            # recommended_action is written server-side from the shared
            # adaptive engine's last decision at the moment this event was
            # logged -- since the game client calls logEvent() BEFORE its
            # next getAgentDecision() call (confirmed in SubmarineDive.jsx),
            # that stored decision is the one made after the *previous*
            # attempt, i.e. it's the difficulty adjustment actually in
            # effect for THIS attempt, not a forward-looking suggestion.
            difficulty_label = _CHIME_DIFFICULTY_LABELS.get(ev.get("recommended_action"))
            if difficulty_label:
                label += f" · {difficulty_label}"
            entries.append(HistoryEntry(
                date=ts,
                label=label,
                value=100.0 if ev.get("is_valid_attempt") else 0.0,
            ))
        entries.sort(key=lambda e: e.date)

    else:
        raise HTTPException(status_code=404, detail=f"Unknown category '{category}'")

    return CategoryHistoryOut(category_name=item, entries=entries[-100:])


@router.get("/weekly-breakdown/chime", response_model=ChimeWeeklyBreakdownOut)
async def get_chime_weekly_breakdown(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    """Per-sound split behind the 'Chime attempts' number in the weekly
    summary grid -- this week only, same week boundary as get_parent_progress
    (Monday 00:00 UTC), reusing weekly_summary.py's own week-filter helper
    so the two numbers can never silently drift apart."""
    patient = await _get_linked_patient(parent, db)
    pid_str = str(patient.id)
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    chime_events = await asyncio.to_thread(
        _week_chime_events, pid_str, week_start, week_end, chime_data_store.DEFAULT_DB_PATH
    )
    by_sound = defaultdict(list)
    for ev in chime_events:
        level_id = ev.get("level_id")
        if level_id:
            by_sound[level_id].append(ev)

    items = [
        ChimeSoundBreakdown(
            sound_id=sound_id,
            attempts=len(evs),
            valid_attempts=len([e for e in evs if e.get("is_valid_attempt")]),
        ) for sound_id, evs in sorted(by_sound.items(), key=lambda kv: -len(kv[1]))
    ]
    return ChimeWeeklyBreakdownOut(items=items)


@router.get("/phoneme-summary", response_model=CrossGamePhonemeSummaryOut)
async def get_parent_phoneme_summary(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    """Parent-facing cross-game phoneme summary -- same merge the
    therapist's Phoneme Command Center and the ICF PDF report use
    (services/phoneme_summary.get_cross_game_phoneme_summary), just scoped
    to the parent's own linked child instead of a therapist-supplied
    patient_id. Returned as-is (accuracy percentages are already shown to
    parents elsewhere on this page, e.g. per-game CategoryProgress rows) --
    the frontend is responsible for the friendlier framing (no raw IPA,
    "sounds to celebrate"/"sounds to practice" instead of
    strongest/weakest)."""
    patient = await _get_linked_patient(parent, db)
    result = await get_cross_game_phoneme_summary(db, str(patient.id), chime_db_path=CHIME_DB_PATH)
    return CrossGamePhonemeSummaryOut(**result)


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


# ------------------------------------------------------------------ #
#  Messages (parent's side of the therapist <-> parent log)            #
# ------------------------------------------------------------------ #
# Same `Message` table dashboard.py's therapist-side endpoints write to
# -- this is the other half of that same conversation, not a separate
# inbox. Every route here goes through _get_linked_patient, which reads
# parent.patient_id off the authenticated token rather than trusting a
# patient_id in the URL/body, so a parent can never address another
# family's messages by guessing/supplying an id.

@router.get("/messages", response_model=list[MessageOut])
async def list_messages(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    # Unlike sending (below), listing is safe even with no therapist yet --
    # an empty conversation is a perfectly normal state the frontend already
    # renders gracefully ("your child isn't connected with a therapist
    # yet"), so this uses the plain lookup instead of the therapist-required
    # one and just returns [] rather than 403ing on a page load.
    patient = await _get_linked_patient(parent, db)
    if not patient.therapist_id:
        return []
    result = await db.execute(
        select(Message).where(Message.patient_id == patient.id).order_by(Message.created_at.asc())
    )
    return result.scalars().all()


@router.post("/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def create_message(
    data: MessageCreate,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    patient = await _get_linked_patient_with_therapist(parent, db)
    message = Message(
        patient_id=patient.id,
        sender_role=SenderRole.parent,  # never trust data.sender_role here -- this endpoint only ever sends as this parent
        sender_id=parent.id,
        body=data.body,
    )
    db.add(message)
    await db.flush()
    return message


@router.post("/messages/{message_id}/read", response_model=MessageOut)
async def mark_message_read(
    message_id: str,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    patient = await _get_linked_patient(parent, db)
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.patient_id == patient.id)
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.read_at is None:
        message.read_at = datetime.now(timezone.utc)
    return message


@router.get("/email-preferences", response_model=EmailPreferencesOut)
async def get_email_preferences(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    patient = await _get_linked_patient(parent, db)
    return EmailPreferencesOut(weekly_email_opt_out=patient.weekly_email_opt_out)


@router.put("/email-preferences", response_model=EmailPreferencesOut)
async def update_email_preferences(
    data: EmailPreferencesOut,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    """Settings-page mirror of the unsubscribe/resubscribe email links
    (see routers/breathquest/email_prefs.py) -- same underlying flag,
    just reachable from inside the app instead of an old email."""
    patient = await _get_linked_patient(parent, db)
    patient.weekly_email_opt_out = data.weekly_email_opt_out
    await db.commit()
    return EmailPreferencesOut(weekly_email_opt_out=patient.weekly_email_opt_out)

# Editable @username (GET / check / suggestions / PATCH) -- see routers/username_routes.py.
from app.routers.username_routes import make_username_router  # noqa: E402
router.include_router(
    make_username_router(get_current_parent, "parent"),
    prefix="/username",
)
