"""
services/kid_goal.py — The kid-facing view of their own newest therapist-set
goal.

Same underlying Goal row and same rolling-5-session current_value the Care
tab shows a therapist (dashboard.py:_compute_goal_current_value), but
re-framed for a child: a friendly name instead of `breath_consistency`, a
0--100 progress number instead of a float, and never the raw metric value
itself. That matches the rule the rest of the /me surface already follows --
a kid sees what they've done and what's next, not their clinical numbers.

Returns None when there's no goal, or when the goal's metric isn't one we can
compute a current value for yet; the frontend then shows no card at all
rather than an empty or fake-progress one.
"""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import Goal, GameSession

# Mirrors dashboard.py's _GOAL_METRIC_FIELDS -- kept as its own copy here
# rather than imported so this service doesn't pull in the whole
# therapist-facing dashboard router (and its auth deps) just for a dict.
# If a metric is added there, add it here too.
_GOAL_METRIC_FIELDS = {
    "breath_consistency": GameSession.breath_consistency,
    "avg_breath_strength": GameSession.avg_breath_strength,
}

# Kid-readable names for the same metrics. Anything unmapped falls back to a
# de-underscored version of the raw metric name.
_FRIENDLY_METRIC_NAMES = {
    "breath_consistency": "Steady Breathing",
    "avg_breath_strength": "Strong Breaths",
}

_FRIENDLY_METRIC_BLURBS = {
    "breath_consistency": "Keeping your breath smooth and even while you play",
    "avg_breath_strength": "Blowing with big, strong breaths",
}


async def _current_value(goal: Goal, db: AsyncSession) -> float | None:
    """Rolling average of the last 5 BreathQuest sessions with a value for
    this metric -- identical to the therapist-side computation so a kid and
    their therapist never see two different numbers for the same goal."""
    field = _GOAL_METRIC_FIELDS.get(goal.target_metric)
    if field is None:
        return None
    recent = (
        select(field)
        .where(GameSession.patient_id == goal.patient_id, field.is_not(None))
        .order_by(GameSession.started_at.desc())
        .limit(5)
        .subquery()
    )
    avg = (await db.execute(select(func.avg(recent.c[field.key])))).scalar()
    return float(avg) if avg is not None else None


def _progress_pct(current: float | None, goal: Goal) -> int:
    """How far along the kid is, 0--100.

    Measured from the baseline where there is one, so progress reflects the
    distance actually travelled rather than crediting the kid for wherever
    they happened to start. Falls back to a plain fraction of the target when
    no baseline was recorded, and to 0 when there's nothing to measure yet.
    """
    if current is None:
        return 0
    baseline = goal.baseline_value
    if baseline is not None and goal.target_value != baseline:
        pct = (current - baseline) / (goal.target_value - baseline) * 100
    elif goal.target_value:
        pct = current / goal.target_value * 100
    else:
        return 0
    return max(0, min(100, int(round(pct))))


def _encouragement(pct: int, achieved: bool) -> str:
    if achieved or pct >= 100:
        return "You did it! Your therapist is going to be so proud. 🏆"
    if pct >= 75:
        return "So close! You're nearly there. Keep going! 🔥"
    if pct >= 40:
        return "You're over halfway there — great work! 💪"
    if pct > 0:
        return "You've started! Every practice moves you closer. 🌱"
    return "A brand new goal to chase. Let's go! 🚀"


def _looking_forward(pct: int, achieved: bool, days_left: int | None) -> str:
    """The 'what to look forward to' line -- one concrete near thing, not a
    vague cheer."""
    if achieved or pct >= 100:
        return "Next up: your therapist will set you a brand new goal to try!"
    if days_left is not None and days_left >= 0:
        if days_left == 0:
            return "Today's the last day for this goal — give it your best shot!"
        if days_left == 1:
            return "1 day left to reach this goal!"
        return f"{days_left} days left to reach this goal!"
    remaining = 100 - pct
    if remaining <= 25:
        return "Just a little more practice and this goal is yours!"
    return "Keep playing your games — every round pushes this bar along."


async def get_latest_goal_for_kid(patient_id, db: AsyncSession) -> dict | None:
    goal = (await db.execute(
        select(Goal)
        .where(Goal.patient_id == patient_id)
        .order_by(Goal.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if goal is None:
        return None

    current = await _current_value(goal, db)
    # A goal on a metric we can't compute yet (e.g. a Chime target) has no
    # honest progress number to show a kid -- better no card than a bar
    # frozen at zero that never moves no matter how much they practice.
    if current is None and not goal.achieved:
        return None

    pct = 100 if goal.achieved else _progress_pct(current, goal)

    days_left = None
    if goal.target_date and not goal.achieved:
        target_date = goal.target_date
        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=timezone.utc)
        days_left = (target_date.date() - datetime.now(timezone.utc).date()).days
        if days_left < 0:
            days_left = None   # past due: drop the countdown rather than show a negative

    metric = goal.target_metric
    return {
        "id": str(goal.id),
        "title": _FRIENDLY_METRIC_NAMES.get(metric, metric.replace("_", " ").title()),
        "blurb": _FRIENDLY_METRIC_BLURBS.get(metric, "A goal your therapist picked just for you"),
        "progress_pct": pct,
        "achieved": bool(goal.achieved),
        "days_left": days_left,
        "encouragement": _encouragement(pct, bool(goal.achieved)),
        "looking_forward": _looking_forward(pct, bool(goal.achieved), days_left),
    }
