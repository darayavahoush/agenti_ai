"""
breathquest_core/entitlements.py — shared "does this kid's account have an
active subscription behind it" check.

A BreathQuestPatient doesn't hold billing status directly -- it's owned
(at most) by one of:
  - a Parent row (Parent.patient_id -> BreathQuestPatient.id), whose own
    Subscription lives at Subscription.owner_parent_id, or
  - a therapist (BreathQuestPatient.therapist_id), whose Subscription
    lives at Subscription.owner_therapist_id.
A self-serve kid with neither has no subscription to check and is
unentitled by default -- that's the expected state right after
kid-register, before any grown-up has signed up.

"Active" means status == "active", OR status == "trialing" with
trial_ends_at still in the future -- an expired trial that hasn't been
marked past_due/canceled yet by a webhook shouldn't still count as access.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import BreathQuestPatient, Parent, Subscription

# TEMPORARY 2026-08-30: no payment provider (Stripe or otherwise) is wired
# up yet, so no Subscription row is ever created for a real user -- which
# means _evaluate()'s documented "self-serve kid with neither [parent nor
# therapist subscription] is unentitled by default" isn't a trial/pre-signup
# state as originally intended, it's the permanent, only state every real
# kid account reaches. GET /me/access (routers/breathquest/access.py) and
# AssessmentReport.jsx's "unlocks with a parent or therapist plan" lock
# screen were therefore blocking 100% of real signups, not gating a small
# minority who haven't paid -- confirmed via a parent report of being stuck
# behind a "plan required" wall with no way to actually purchase one.
#
# With the flag off, get_patient_entitlement short-circuits to
# has_access=True before touching Parent/Subscription at all -- the real
# lookup/trial-expiry logic below is untouched and ready to go the moment
# a real billing integration exists to actually create Subscription rows.
# Flip REQUIRE_SUBSCRIPTION back to True once that's live.
REQUIRE_SUBSCRIPTION = False


@dataclass
class EntitlementStatus:
    has_access: bool
    reason: str  # "active" | "trialing" | "trial_expired" | "past_due" | "canceled" | "no_subscription"
    trial_ends_at: Optional[datetime] = None
    plan_type: Optional[str] = None


def _evaluate(sub: Subscription | None) -> EntitlementStatus:
    if sub is None:
        return EntitlementStatus(has_access=False, reason="no_subscription")

    if sub.status == "active":
        return EntitlementStatus(has_access=True, reason="active", plan_type=sub.plan_type)

    if sub.status == "trialing":
        still_trialing = sub.trial_ends_at is not None and sub.trial_ends_at > datetime.now(timezone.utc)
        return EntitlementStatus(
            has_access=still_trialing,
            reason="trialing" if still_trialing else "trial_expired",
            trial_ends_at=sub.trial_ends_at,
            plan_type=sub.plan_type,
        )

    # past_due, canceled, or any other terminal status
    return EntitlementStatus(has_access=False, reason=sub.status, plan_type=sub.plan_type)


async def get_patient_entitlement(patient: BreathQuestPatient, db: AsyncSession) -> EntitlementStatus:
    """Resolves whichever owner (parent, then therapist) this kid's
    account is linked to and evaluates their Subscription. Parent takes
    priority since a parent-managed account is the more specific link --
    a therapist-created patient with no parent yet falls through to the
    therapist's own subscription.

    See the REQUIRE_SUBSCRIPTION note above this module's top -- while
    it's off, every patient gets has_access=True unconditionally, no
    Parent/Subscription lookup happens at all."""
    if not REQUIRE_SUBSCRIPTION:
        return EntitlementStatus(has_access=True, reason="no_paywall_yet")

    parent_result = await db.execute(select(Parent).where(Parent.patient_id == patient.id))
    parent = parent_result.scalar_one_or_none()
    if parent is not None:
        sub_result = await db.execute(select(Subscription).where(Subscription.owner_parent_id == parent.id))
        return _evaluate(sub_result.scalar_one_or_none())

    if patient.therapist_id is not None:
        sub_result = await db.execute(
            select(Subscription).where(Subscription.owner_therapist_id == patient.therapist_id)
        )
        return _evaluate(sub_result.scalar_one_or_none())

    return EntitlementStatus(has_access=False, reason="no_subscription")
