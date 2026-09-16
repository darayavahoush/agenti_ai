"""
services/weekly_target.py — This week's practice calendar for the kid-facing
My Progress page, plus an auto-derived weekly target.

No new DB column: the target is computed from the kid's own recent habit
(average number of practice-days per week over the last 4 *complete* weeks,
clamped to 1--7, defaulting to 3 with no history) rather than being set by a
therapist. That keeps this purely additive — no migration, nothing for a
therapist to maintain — and keeps the bar personal: a kid who practices twice
a week is nudged toward three, not toward someone else's seven.

"Practiced" means at least one session/event on that calendar day from ANY of
the five surfaces a kid can play (BreathQuest, VoiceHurdleRace, VaakMirror /
Orpheus, Chime flashcard attempts, Chime RL events) — same union
/me/progress's own weekly count uses. Days are bucketed in UTC, matching how
every one of those tables stores its timestamps; sub-day precision isn't
meaningful here anyway.
"""

import asyncio
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import GameSession
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.vaakmirror_models import VaakMirrorSession
from app.models.flashcards_models import FlashcardAttempt
from app.retraining import data_store as chime_data_store

WEEKS_OF_HISTORY = 4          # complete weeks averaged for the target
DEFAULT_TARGET_DAYS = 3       # used when there's no history to average
MIN_TARGET_DAYS = 1
MAX_TARGET_DAYS = 7

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _week_start(d: date) -> date:
    """Monday of the week containing `d`."""
    return d - timedelta(days=d.weekday())


def _as_date(value) -> date | None:
    """Normalise whatever a given table handed back into a UTC calendar date.

    The five sources here are not consistent: the ORM tables return aware
    datetimes, `func.date(...)` returns a date on some drivers and a plain
    string on others (SQLite), and data_store rows can carry naive
    timestamps. Funnel all of it through one place rather than guessing at
    the call site.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:19]).date()
    except (ValueError, TypeError):
        return None


async def _practice_dates_since(patient_id, since: datetime, db: AsyncSession) -> set[date]:
    """Every calendar day on or after `since` with at least one bit of
    practice on it, across all five surfaces."""
    dates: set[date] = set()

    bq = (await db.execute(
        select(GameSession.started_at).where(
            GameSession.patient_id == patient_id,
            GameSession.started_at >= since,
        )
    )).scalars().all()

    vhr = (await db.execute(
        select(VoiceHurdleRaceSession.created_at).where(
            VoiceHurdleRaceSession.patient_id == patient_id,
            VoiceHurdleRaceSession.created_at >= since,
        )
    )).scalars().all()

    # VaakMirrorSession.patient_id is a plain String column, not a UUID FK --
    # str() it explicitly, same as kid_progress.py's own queries do.
    vm = (await db.execute(
        select(VaakMirrorSession.started_at).where(
            VaakMirrorSession.patient_id == str(patient_id),
            VaakMirrorSession.started_at >= since,
        )
    )).scalars().all()

    fc = (await db.execute(
        select(FlashcardAttempt.created_at).where(
            FlashcardAttempt.patient_id == patient_id,
            FlashcardAttempt.created_at >= since,
        )
    )).scalars().all()

    for value in (*bq, *vhr, *vm, *fc):
        d = _as_date(value)
        if d:
            dates.add(d)

    # chime_data_store is synchronous I/O -- thread it off rather than
    # blocking the event loop, same rule the rest of kid_progress.py follows.
    events = await asyncio.to_thread(chime_data_store.get_events, patient_id)
    since_date = _as_date(since)
    for event in events or []:
        d = _as_date(event.get("timestamp"))
        if d and (since_date is None or d >= since_date):
            dates.add(d)

    return dates


def _auto_weekly_target(practice_dates: set[date], this_week_start: date) -> int:
    """Average practice-days/week over the last WEEKS_OF_HISTORY *complete*
    weeks (this week is excluded — it's still in progress, so counting it
    would drag the target down every Monday). Weeks before the kid's first
    ever practice day are skipped rather than counted as zeros, so a brand
    new kid isn't handed a target of 1."""
    if not practice_dates:
        return DEFAULT_TARGET_DAYS

    first_practice_week = _week_start(min(practice_dates))
    counts: list[int] = []
    for i in range(1, WEEKS_OF_HISTORY + 1):
        start = this_week_start - timedelta(weeks=i)
        if start < first_practice_week:
            continue
        end = start + timedelta(days=7)
        counts.append(sum(1 for d in practice_dates if start <= d < end))

    if not counts:
        return DEFAULT_TARGET_DAYS

    avg = sum(counts) / len(counts)
    # Round up: the target should be a small stretch on the recent habit,
    # not a restatement of it.
    target = int(avg + 0.5) or 1
    return max(MIN_TARGET_DAYS, min(MAX_TARGET_DAYS, target))


async def get_weekly_calendar(patient_id, db: AsyncSession) -> dict:
    """This week Mon--Sun, one entry per day, plus the auto target and the
    kid's current position against it."""
    today = datetime.now(timezone.utc).date()
    this_week_start = _week_start(today)
    history_start = this_week_start - timedelta(weeks=WEEKS_OF_HISTORY)

    practice_dates = await _practice_dates_since(
        patient_id,
        datetime.combine(history_start, datetime.min.time(), tzinfo=timezone.utc),
        db,
    )

    days = []
    for i in range(7):
        d = this_week_start + timedelta(days=i)
        days.append({
            "date": d,
            "label": DAY_LABELS[i],
            "practiced": d in practice_dates,
            "is_today": d == today,
            "is_future": d > today,
        })

    target = _auto_weekly_target(practice_dates, this_week_start)
    days_practiced = sum(1 for day in days if day["practiced"])
    days_left = sum(1 for day in days if day["is_future"])

    return {
        "week_start": this_week_start,
        "days": days,
        "days_practiced": days_practiced,
        "target_days": target,
        "target_met": days_practiced >= target,
        "days_left": days_left,
        "message": _calendar_message(days_practiced, target, days_left),
    }


def _calendar_message(done: int, target: int, days_left: int) -> str:
    """One short, concrete line a kid can read themself. Never scolding --
    a missed week reads as an open invitation, not a failure."""
    remaining = max(0, target - done)
    if done >= target:
        return "You hit your goal for this week! 🎉"
    if remaining > days_left:
        return "Every day you practice counts — let's get one in today! 💪"
    if remaining == 1:
        return "Just one more practice day this week! ⭐️"
    return f"{remaining} more practice days to hit your goal this week! 🚀"
