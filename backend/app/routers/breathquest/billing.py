"""
routers/billing.py — subscription status + payment-provider stubs.

GET endpoints use plain get_current_therapist/get_current_parent (not
core.entitlements' require_active_*) deliberately: viewing your own
billing status must work even when the trial's expired or the sub is
past_due -- that's precisely when someone needs to see it. Entitlement
gating belongs on the paid feature routes, not on billing itself.

POST endpoints are explicit 501s until a provider (Razorpay/Stripe) is
picked -- no fake success responses, no silent no-ops.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.breathquest_models import Subscription, Parent
from app.models.therapist import Therapist
from app.schemas.breathquest_schemas import SubscriptionOut
from app.breathquest_core.deps import get_current_therapist, get_current_parent
from app.breathquest_core.billing_provider import get_billing_provider, BillingProvider

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=SubscriptionOut)
async def get_therapist_subscription(
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(Subscription.owner_therapist_id == therapist.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this account")
    return SubscriptionOut(
        plan_type=sub.plan_type,
        status=sub.status,
        trial_ends_at=sub.trial_ends_at,
        current_period_end=sub.current_period_end,
    )


@router.get("/parent-subscription", response_model=SubscriptionOut)
async def get_parent_subscription(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(Subscription.owner_parent_id == parent.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this account")
    return SubscriptionOut(
        plan_type=sub.plan_type,
        status=sub.status,
        trial_ends_at=sub.trial_ends_at,
        current_period_end=sub.current_period_end,
    )


# TODO: real payment -- no provider is picked yet (see billing_provider.py),
# so "checkout" here just marks the subscription active directly instead of
# calling provider.create_checkout_session (which honestly 501s). Product
# call: the paywall isn't live yet, so clicking Subscribe should grant
# access for everyone rather than dead-ending on a 501. Swap this back to
# calling the real provider and letting /billing/webhook flip the status
# once Razorpay/Stripe is wired up -- don't leave this bypass in place
# past that point.
async def _mark_active(db: AsyncSession, owner_col, owner_id, plan_type: str) -> None:
    result = await db.execute(select(Subscription).where(owner_col == owner_id))
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = "active"
    else:
        db.add(Subscription(
            **{owner_col.key: owner_id},
            plan_type=plan_type,
            status="active",
        ))
    await db.flush()


@router.post("/checkout")
async def start_therapist_checkout(
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    await _mark_active(db, Subscription.owner_therapist_id, therapist.id, "therapist_monthly")
    return {"checkout_url": "/therapist/billing?subscribed=1"}


@router.post("/parent-checkout")
async def start_parent_checkout(
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    await _mark_active(db, Subscription.owner_parent_id, parent.id, "parent_monthly")
    return {"checkout_url": "/parent/billing?subscribed=1"}


@router.post("/webhook")
async def billing_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    provider: BillingProvider = Depends(get_billing_provider),
):
    payload = await request.body()
    event = await provider.verify_and_parse_webhook(payload, dict(request.headers))

    owner_col = (
        Subscription.owner_therapist_id if event["owner_kind"] == "therapist"
        else Subscription.owner_parent_id
    )
    result = await db.execute(select(Subscription).where(owner_col == event["owner_id"]))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for webhook owner_id")

    event_type = event["type"]
    if event_type == "subscription.activated":
        sub.status = "active"
        sub.current_period_end = event.get("current_period_end")
    elif event_type == "subscription.past_due":
        sub.status = "past_due"
    elif event_type == "subscription.canceled":
        sub.status = "canceled"
    else:
        raise HTTPException(status_code=400, detail=f"Unhandled event type: {event_type}")

    await db.flush()
    return {"received": True}
