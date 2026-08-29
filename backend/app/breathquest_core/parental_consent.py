"""
breathquest_core/parental_consent.py — COPPA gate for the self-serve kid
signup path.

POST /auth/kid-register is the only account-creation route with no adult
already in the loop: kid-pin-setup and the assessment-linked flow both
require a therapist or parent to have created the record first. This
module answers "has a parent verified enough to consent to creating this
child's account" for that one route.

We reuse the existing OTP infrastructure (EmailVerification via
POST /verify/request + /verify/confirm) rather than building a second
verification system -- a confirmed code already proves control of the
inbox, which is the verifiable part of "verifiable parental consent".
What this module adds on top is the *recency* requirement: a code
confirmed once, days ago, shouldn't be replayable forever to gate new
signups, so a verification only counts within CONSENT_WINDOW_MINUTES of
when it was confirmed. In practice this means the parent verifies their
email and the account is created in the same sitting, which also matches
the actual UX (Play.jsx sends them straight from confirming the code into
finishing registration).

2026-08-29: phone was previously a second required consent factor
alongside email (check_parental_consent / check_phone_consent /
DualConsentStatus). Removed -- no real SMS provider was ever wired up
(ACS doesn't support Indian numbers, no alternative provider configured),
so it only ever worked via the AUTO_VERIFY_CONSENT stub below, never a
real OTP round-trip. Email-only consent is now the single, permanent gate
for this route. The /verify/phone/* endpoints, PhoneVerification model,
and phone_provider.py were removed alongside this.

TEMPORARY 2026-08-12: AUTO_VERIFY_CONSENT below bypasses the real OTP
check entirely. No live email provider is wired up yet (send_otp_email
is a stub), so there's no way for a parent to actually receive and
confirm a code right now. With the flag on, check_email_consent grants
immediately once an email is *provided* -- not verified.
Flip AUTO_VERIFY_CONSENT to False (or delete the branch below it) once
a real email provider exists -- the recency-window logic and the
/verify/* endpoints are all still here and unchanged, ready to go the
moment that flag comes off.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import EmailVerification

CONSENT_WINDOW_MINUTES = 30
AUTO_VERIFY_CONSENT = False


@dataclass
class ConsentStatus:
    granted: bool
    reason: str  # "granted" | "not_verified" | "expired"
    verified_at: Optional[datetime] = None


async def _check_factor_consent(model, field_name: str, value: str, db: AsyncSession) -> ConsentStatus:
    """Shared recency-window check. Originally parameterized over
    EmailVerification and PhoneVerification (identical shape); phone was
    removed 2026-08-29, but this stays generic in case another factor is
    ever added the same way.

    AUTO_VERIFY_CONSENT bypass lives here (not just in callers) so every
    caller gets the same "no OTP round-trip needed yet" behavior,
    instead of enforcing a real EmailVerification row that nothing in
    this environment can create yet."""
    if AUTO_VERIFY_CONSENT:
        if not value or not value.strip():
            return ConsentStatus(granted=False, reason="not_verified")
        now = datetime.now(timezone.utc)
        return ConsentStatus(granted=True, reason="granted_auto_verify_stub", verified_at=now)

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
