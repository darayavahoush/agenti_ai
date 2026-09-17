"""
services/weekly_quest.py — Two lightweight, auto-generated quests layered
on top of weekly_target.py's day-count practice calendar.

weekly_target.py answers "did you practice enough days this week". These
quests answer a different question: "did you practice in a way that's
actually useful" -- a kid who plays one BreathQuest level five times a day
hits weekly_target's number but never touches variety or their actual goal.

Both quests reset every Monday with the same calendar week weekly_target.py
uses, are computed fresh on every request, and need no new DB table --
nothing for a therapist to configure or maintain.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import GameSession, Goal
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.vaakmirror_models import VaakMirrorSession
from app.models.flashcards_models import FlashcardAttempt
from app.retraining import data_store as chime_data_store
from .weekly_target import _week_start, _as_date
from .kid_goal import _FRIENDLY_METRIC_NAMES

VARIETY_TARGET_GAMES = 2
GOAL_STREAK_TARGET_DAYS = 3


async def _surfaces_played_this_week(patient_id, week_start, db: AsyncSession) -> dict[str, set]:
    """{'breathquest': {dates...}, 'voicehurdlerace': {...}, 'vaakmirror': {...},
    'chime': {...}, 'flashcards': {...}} -- this week only (Mon so far),
    not the 4-week history window weekly_target.py pulls for its average."""
    since = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)
    result: dict[str, set] = {
        "breathquest": set(), "voicehurdlerace": set(), "vaakmirror": set(),
        "chime": set(), "flashcards": set(),
    }

    bq = (await db.execute(
        select(GameSession.started_at).where(
            GameSession.patient_id == patient_id, GameSession.started_at >= since
        )
    )).scalars().all()
    for v in bq:
        d = _as_date(v)
        if d:
            result["breathquest"].add(d)

    vhr = (await db.execute(
        select(VoiceHurdleRaceSession.created_at).where(
            VoiceHurdleRaceSession.patient_id == patient_id, VoiceHurdleRaceSession.created_at >= since
        )
    )).scalars().all()
    for v in vhr:
        d = _as_date(v)
        if d:
            result["voicehurdlerace"].add(d)

    # VaakMirrorSession.patient_id is a plain String column, not a UUID FK --
    # str() it, same as weekly_target.py and kid_progress.py's own queries do.
    vm = (await db.execute(
        select(VaakMirrorSession.started_at).where(
            VaakMirrorSession.patient_id == str(patient_id), VaakMirrorSession.started_at >= since
        )
    )).scalars().all()
    for v in vm:
        d = _as_date(v)
        if d:
            result["vaakmirror"].add(d)

    fc = (await db.execute(
        select(FlashcardAttempt.created_at).where(
            FlashcardAttempt.patient_id == patient_id, FlashcardAttempt.created_at >= since
        )
    )).scalars().all()
    for v in fc:
        d = _as_date(v)
        if d:
            result["flashcards"].add(d)

    # chime_data_store is synchronous SQLite I/O -- thread it off, same rule
    # weekly_target.py's own chime query follows.
    events = await asyncio.to_thread(chime_data_store.get_events, patient_id)
    for event in events or []:
        d = _as_date(event.get("timestamp"))
        if d and d >= week_start:
            result["chime"].add(d)

    return result


async def get_weekly_quests(patient_id, db: AsyncSession) -> list[dict]:
    """Always returns the variety quest. Also returns a goal-streak quest,
    but only when the kid has an active (unachieved) therapist goal to
    build toward -- a quest tied to a goal that doesn't exist would just
    be confusing, not motivating."""
    today = datetime.now(timezone.utc).date()
    week_start = _week_start(today)
    surfaces = await _surfaces_played_this_week(patient_id, week_start, db)

    games_played = sum(1 for dates in surfaces.values() if dates)
    quests = [{
        "id": "variety",
        "title": "Game Explorer",
        "description": f"Try {VARIETY_TARGET_GAMES} different games this week",
        "progress": min(games_played, VARIETY_TARGET_GAMES),
        "target": VARIETY_TARGET_GAMES,
        "complete": games_played >= VARIETY_TARGET_GAMES,
    }]

    goal_result = await db.execute(
        select(Goal)
        .where(Goal.patient_id == patient_id, Goal.achieved.is_(False))
        .order_by(Goal.created_at.desc())
    )
    goal = goal_result.scalars().first()
    if goal is not None:
        # Both current goal metrics (breath_consistency, avg_breath_strength)
        # are computed from GameSession rows -- see kid_goal.py's
        # _GOAL_METRIC_FIELDS -- so "days played toward this goal" means
        # days with a BreathQuest session, not any of the other 4 surfaces.
        friendly = _FRIENDLY_METRIC_NAMES.get(goal.target_metric, goal.target_metric.replace("_", " "))
        bq_days = len(surfaces["breathquest"])
        quests.append({
            "id": "goal_streak",
            "title": f"{friendly} Streak",
            "description": f"Play BreathQuest on {GOAL_STREAK_TARGET_DAYS} days this week to build toward your goal",
            "progress": min(bq_days, GOAL_STREAK_TARGET_DAYS),
            "target": GOAL_STREAK_TARGET_DAYS,
            "complete": bq_days >= GOAL_STREAK_TARGET_DAYS,
        })

    return quests
