"""
breathquest_core/parental_consent.py — COPPA gate for the self-serve kid
signup path.

POST /auth/kid-register is the only account-creation route with no adult
already in the loop: kid-pin-setup and the assessment-linked flow both
require a therapist or parent to have created the record first. This
module answers "has a parent verified this email recently enough to
consent to creating this child's account" for that one route.

We reuse the existing email-OTP infrastructure (EmailVerification /
POST /verify/request + /verify/confirm) rather than building a second
verification system -- a confirmed code already proves control of the
inbox, which is the verifiable part of "verifiable parental consent".
What this module adds on top is the *recency* requirement: a code
confirmed once, days ago, shouldn't be replayable forever to gate
new signups, so a verification only counts within CONSENT_WINDOW_MINUTES
of when it was confirmed. In practice this means the parent verifies
their email and the account is created in the same sitting, which also
matches the actual UX (Play.jsx sends them straight from confirming the
code into finishing registration).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import EmailVerification

CONSENT_WINDOW_MINUTES = 30


@dataclass
class ConsentStatus:
    granted: bool
    reason: str  # "granted" | "not_verified" | "expired"
    verified_at: Optional[datetime] = None


async def check_parental_consent(email: str, db: AsyncSession) -> ConsentStatus:
    """Most recent verified EmailVerification for this email, checked
    against the recency window. Case-sensitivity matches EmailVerification's
    own storage -- it's written and looked up as given, same as
    verify.py's own queries."""
    result = await db.execute(
        select(EmailVerification)
        .where(
            EmailVerification.email == email,
            EmailVerification.verified == True,  # noqa: E712
        )
        .order_by(EmailVerification.verified_at.desc())
        .limit(1)
    )
    record = result.scalars().first()

    if record is None or record.verified_at is None:
        return ConsentStatus(granted=False, reason="not_verified")

    elapsed_minutes = (datetime.now(timezone.utc) - record.verified_at).total_seconds() / 60
    if elapsed_minutes > CONSENT_WINDOW_MINUTES:
        return ConsentStatus(granted=False, reason="expired", verified_at=record.verified_at)

    return ConsentStatus(granted=True, reason="granted", verified_at=record.verified_at)
