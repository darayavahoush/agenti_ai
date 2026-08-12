"""
breathquest_core/parental_consent.py — COPPA gate for the self-serve kid
signup path.

POST /auth/kid-register is the only account-creation route with no adult
already in the loop: kid-pin-setup and the assessment-linked flow both
require a therapist or parent to have created the record first. This
module answers "has a parent verified enough to consent to creating this
child's account" for that one route.

We reuse the existing OTP infrastructure (EmailVerification/PhoneVerification
via POST /verify/request + /verify/confirm, and their phone equivalents)
rather than building a second verification system -- a confirmed code
already proves control of the inbox/phone, which is the verifiable part
of "verifiable parental consent". What this module adds on top is the
*recency* requirement: a code confirmed once, days ago, shouldn't be
replayable forever to gate new signups, so a verification only counts
within CONSENT_WINDOW_MINUTES of when it was confirmed. In practice this
means the parent verifies both email and phone and the account is
created in the same sitting, which also matches the actual UX (Play.jsx
sends them straight from confirming each code into finishing
registration).

Both factors are required, not alternatives -- check_parental_consent
only grants once both check_email_consent and check_phone_consent do.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import EmailVerification, PhoneVerification

CONSENT_WINDOW_MINUTES = 30


@dataclass
class ConsentStatus:
    granted: bool
    reason: str  # "granted" | "not_verified" | "expired" | "email_not_verified" | "phone_not_verified" | "email_expired" | "phone_expired"
    verified_at: Optional[datetime] = None


async def _check_factor_consent(model, field_name: str, value: str, db: AsyncSession) -> ConsentStatus:
    """Shared recency-window check, parameterized over EmailVerification
    (field_name="email") and PhoneVerification (field_name="phone") --
    the two models are identical in shape, so this avoids duplicating the
    query/window logic twice."""
    result = await db.execute(
        select(model)
        .where(
            getattr(model, field_name) == value,
            model.verified == True,  # noqa: E712
        )
        .order_by(model.verified_at.desc())
        .limit(1)
    )
    record = result.scalars().first()

    if record is None or record.verified_at is None:
        return ConsentStatus(granted=False, reason="not_verified")

    elapsed_minutes = (datetime.now(timezone.utc) - record.verified_at).total_seconds() / 60
    if elapsed_minutes > CONSENT_WINDOW_MINUTES:
        return ConsentStatus(granted=False, reason="expired", verified_at=record.verified_at)

    return ConsentStatus(granted=True, reason="granted", verified_at=record.verified_at)


async def check_email_consent(email: str, db: AsyncSession) -> ConsentStatus:
    return await _check_factor_consent(EmailVerification, "email", email, db)


async def check_phone_consent(phone: str, db: AsyncSession) -> ConsentStatus:
    return await _check_factor_consent(PhoneVerification, "phone", phone, db)


@dataclass
class DualConsentStatus:
    granted: bool
    reason: str  # "granted" | "email_not_verified" | "email_expired" | "phone_not_verified" | "phone_expired"
    email_verified_at: Optional[datetime] = None
    phone_verified_at: Optional[datetime] = None


async def check_parental_consent(email: str, phone: str, db: AsyncSession) -> DualConsentStatus:
    """Both email and phone must be independently, recently verified --
    this is a hard AND, not either-or. Checks email first so the more
    common failure (email never sent/confirmed) surfaces first; if email
    passes but phone doesn't, the phone-specific reason is returned."""
    email_status = await check_email_consent(email, db)
    if not email_status.granted:
        return DualConsentStatus(
            granted=False,
            reason=f"email_{email_status.reason}" if email_status.reason != "not_verified" else "email_not_verified",
        )

    phone_status = await check_phone_consent(phone, db)
    if not phone_status.granted:
        return DualConsentStatus(
            granted=False,
            reason=f"phone_{phone_status.reason}" if phone_status.reason != "not_verified" else "phone_not_verified",
            email_verified_at=email_status.verified_at,
        )

    return DualConsentStatus(
        granted=True,
        reason="granted",
        email_verified_at=email_status.verified_at,
        phone_verified_at=phone_status.verified_at,
    )
