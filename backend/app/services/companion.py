"""
services/companion.py — Cosmetic companion accessories and avatar species
a kid earns by hitting practice-streak milestones, layered on the existing
illustrated Creature avatar (frontend/src/components/ui/Creatures.jsx)
rather than adding a new art system.

Unlocks are permanent once earned (see models.breathquest_models
.CompanionUnlock's docstring) -- granting is idempotent and safe to call on
every /me/progress request, the same on-read-rather-than-webhook pattern
weekly_target.py and kid_goal.py already use for their own computed state.

A single equipped_companion_item column on BreathQuestPatient stores the
kid's actual choice -- unified pool, one slot, whether it's an avatar
species swap or an accessory. Falls back to highest-tier-owned only if
nothing's been explicitly equipped yet.
"""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import CompanionUnlock, BreathQuestPatient

# Ordered by streak_days ascending. 'kind' tells the frontend which Avatar
# prop to set when equipped -- unlock/equip logic itself doesn't care.
UNLOCK_TIERS = [
    {"item_id": "sparkle_trail", "streak_days": 3,  "kind": "accessory", "label": "Sparkle Trail"},
    {"item_id": "fox",           "streak_days": 5,  "kind": "avatar",    "label": "Fox"},
    {"item_id": "party_hat",     "streak_days": 7,  "kind": "accessory", "label": "Party Hat"},
    {"item_id": "owl",           "streak_days": 10, "kind": "avatar",    "label": "Owl"},
    {"item_id": "golden_crown",  "streak_days": 14, "kind": "accessory", "label": "Golden Crown"},
    {"item_id": "bunny",         "streak_days": 18, "kind": "avatar",    "label": "Bunny"},
]


async def grant_earned_unlocks(patient_id, current_streak_days: int, db: AsyncSession) -> None:
    """Insert any tier this streak now qualifies for that isn't already
    owned. ON CONFLICT DO NOTHING makes this safe to call unconditionally
    on every progress fetch without a race or duplicate rows."""
    newly_earned = [t["item_id"] for t in UNLOCK_TIERS if current_streak_days >= t["streak_days"]]
    if not newly_earned:
        return

    stmt = pg_insert(CompanionUnlock).values([
        {"patient_id": patient_id, "item_id": item_id} for item_id in newly_earned
    ]).on_conflict_do_nothing(constraint="uq_companion_unlock_patient_item")
    await db.execute(stmt)
    await db.commit()


async def get_companion_state(patient_id, db: AsyncSession) -> dict:
    """Every accessory/avatar this kid has ever earned, plus which one is
    actually equipped -- the kid's stored choice if it's still owned,
    otherwise falls back to highest-tier-owned (e.g. before they've ever
    picked one)."""
    owned_result = await db.execute(
        select(CompanionUnlock.item_id).where(CompanionUnlock.patient_id == patient_id)
    )
    owned = set(owned_result.scalars().all())

    patient = await db.get(BreathQuestPatient, patient_id)
    equipped_id = patient.equipped_companion_item
    if equipped_id not in owned:
        equipped_id = None
        for tier in UNLOCK_TIERS:  # ascending order -- last match wins
            if tier["item_id"] in owned:
                equipped_id = tier["item_id"]

    equipped = next((t for t in UNLOCK_TIERS if t["item_id"] == equipped_id), None)

    return {
        "equipped": equipped,
        "unlocked": [t for t in UNLOCK_TIERS if t["item_id"] in owned],
        "next": next((t for t in UNLOCK_TIERS if t["item_id"] not in owned), None),
    }


async def equip_item(patient_id, item_id: str, db: AsyncSession) -> dict:
    """Kid picks any accessory or avatar they've already unlocked. Rejects
    anything not owned -- no equipping items you haven't earned."""
    owned_result = await db.execute(
        select(CompanionUnlock.item_id).where(CompanionUnlock.patient_id == patient_id)
    )
    owned = set(owned_result.scalars().all())
    if item_id not in owned:
        raise ValueError(f"item '{item_id}' not unlocked for this patient")

    patient = await db.get(BreathQuestPatient, patient_id)
    patient.equipped_companion_item = item_id
    await db.commit()
    return await get_companion_state(patient_id, db)
