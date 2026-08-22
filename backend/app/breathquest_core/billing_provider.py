"""
breathquest_core/billing_provider.py — payment-provider abstraction stub.

routers/breathquest/billing.py referenced `core.billing_provider` (wrong
module path entirely -- that package doesn't exist in this codebase) and,
even at the right path, no such module existed anywhere: no Razorpay/
Stripe integration has been picked yet. This is a minimal stand-in so
billing.py's checkout/webhook endpoints have a real dependency to resolve
against and return honest 501s instead of failing to import at all.

Swap get_billing_provider's return value for a real
RazorpayProvider/StripeProvider once a provider is chosen -- nothing else
in billing.py needs to change, since it only depends on this interface.
"""

from fastapi import HTTPException
from uuid import UUID


class BillingProvider:
    async def create_checkout_session(
        self, customer_email: str, plan_type: str, owner_id: UUID, owner_kind: str,
    ) -> str:
        raise NotImplementedError

    async def verify_and_parse_webhook(self, payload: bytes, headers: dict) -> dict:
        raise NotImplementedError


class StubBillingProvider(BillingProvider):
    """No payment provider is wired up yet. Explicit 501s, matching
    billing.py's own docstring ("no fake success responses, no silent
    no-ops") rather than pretending a checkout session was created."""

    async def create_checkout_session(
        self, customer_email: str, plan_type: str, owner_id: UUID, owner_kind: str,
    ) -> str:
        raise HTTPException(
            status_code=501,
            detail="Billing is not set up yet -- no payment provider is configured.",
        )

    async def verify_and_parse_webhook(self, payload: bytes, headers: dict) -> dict:
        raise HTTPException(
            status_code=501,
            detail="Billing is not set up yet -- no payment provider is configured.",
        )


def get_billing_provider() -> BillingProvider:
    return StubBillingProvider()
