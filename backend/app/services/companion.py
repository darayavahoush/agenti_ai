"""
services/companion.py — Cosmetic companion accessories a kid earns by
hitting practice-streak milestones, layered on the existing illustrated
Creature avatar (frontend/src/components/ui/Creatures.jsx) rather than
adding a new art system. The static avatar picker becomes something that
visibly grows with the kid instead of a one-time choice.

Unlocks are permanent once earned (see models.breathquest_models
.CompanionUnlock's docstring) -- granting is idempotent and safe to call on
every /me/progress request, the same on-read-rather-than-webhook pattern
weekly_target.py and kid_goal.py already use for their own computed state.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import CompanionUnlock

# Ordered by streak_days ascending -- the frontend also relies on this order
# to decide which single accessory is "equipped" (the highest one earned).
UNLOCK_TIERS = [
    {"item_id": "sparkle_trail", "streak_days": 3,  "label": "Sparkle Trail",  "description": "3-day practice streak"},
    {"item_id": "party_hat",     "streak_days": 7,  "label": "Party Hat",      "description": "7-day practice streak"},
    {"item_id": "golden_crown",  "streak_days": 14, "label": "Golden Crown",   "description": "14-day practice streak"},
]


async def grant_earned_unlocks(patient_id, current_streak_days: int, db: AsyncSession) -> None:
    """Insert any tier this streak now qualifies for that isn't already
    owned. ON CONFLICT DO NOTHING makes this safe to call unconditionally
    on every progress fetch without a SELECT-then-INSERT race or duplicate
    rows -- two concurrent requests granting the same tier is a no-op, not
    an IntegrityError."""
    newly_earned = [t["item_id"] for t in UNLOCK_TIERS if current_streak_days >= t["streak_days"]]
    if not newly_earned:
        return

    stmt = pg_insert(CompanionUnlock).values([
        {"patient_id": patient_id, "item_id": item_id} for item_id in newly_earned
    ]).on_conflict_do_nothing(constraint="uq_companion_unlock_patient_item")
    await db.execute(stmt)
    await db.commit()


async def get_companion_state(patient_id, db: AsyncSession) -> dict:
    """Every accessory this kid has ever earned, plus which one is
    'equipped' (highest tier owned) for the avatar to actually render."""
    owned_result = await db.execute(
        select(CompanionUnlock.item_id).where(CompanionUnlock.patient_id == patient_id)
    )
    owned = set(owned_result.scalars().all())

    equipped = None
    for tier in UNLOCK_TIERS:  # ascending order -- last match wins
        if tier["item_id"] in owned:
            equipped = tier["item_id"]

    return {
        "equipped": equipped,
        "unlocked": [t["item_id"] for t in UNLOCK_TIERS if t["item_id"] in owned],
        "next": next((t for t in UNLOCK_TIERS if t["item_id"] not in owned), None),
    }
