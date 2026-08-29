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

TEMPORARY 2026-08-12: AUTO_VERIFY_CONSENT below bypasses the real OTP
check entirely. No live email/SMS provider is wired up yet (send_otp_email
is a stub; phone_provider.py's StubPhoneProvider 501s), so there's no way
for a parent to actually receive and confirm a code right now. With the
flag on, check_parental_consent grants immediately once an email and
phone are *provided* -- not verified -- and Play.jsx's frontend matches
this by skipping the OTP-entry screens and registering right after the
single contact-info form.
Flip AUTO_VERIFY_CONSENT to False (or delete the branch below it) once
real email/SMS providers exist -- the recency-window logic, the
dual-factor requirement, and the /verify/* endpoints are all still here
and unchanged, ready to go the moment that flag comes off.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import EmailVerification, PhoneVerification

CONSENT_WINDOW_MINUTES = 30
AUTO_VERIFY_CONSENT = False


@dataclass
class ConsentStatus:
    granted: bool
    reason: str  # "granted" | "not_verified" | "expired" | "email_not_verified" | "phone_not_verified" | "email_expired" | "phone_expired"
    verified_at: Optional[datetime] = None


async def _check_factor_consent(model, field_name: str, value: str, db: AsyncSession) -> ConsentStatus:
    """Shared recency-window check, parameterized over EmailVerification
    (field_name="email") and PhoneVerification (field_name="phone") --
    the two models are identical in shape, so this avoids duplicating the
    query/window logic twice.

    AUTO_VERIFY_CONSENT bypass lives here (not just in
    check_parental_consent) so single-factor callers -- check_email_consent
    on its own, e.g. therapist registration -- get the same "no OTP
    round-trip needed yet" behavior as the dual-factor kid/parent flows,
    instead of being the one path that actually enforces a real
    EmailVerification row that nothing in this environment can create yet."""
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
    passes but phone doesn't, the phone-specific reason is returned.

    See the AUTO_VERIFY_CONSENT note at the top of this file -- while
    it's on, this skips the EmailVerification/PhoneVerification lookups
    entirely and grants based on the values being present and non-empty.
    kid_register's own schema validators already reject blank/missing
    email or phone, so this isn't a "no consent needed at all" bypass,
    just a "no OTP round-trip needed yet" one."""
    if AUTO_VERIFY_CONSENT:
        now = datetime.now(timezone.utc)
        return DualConsentStatus(
            granted=True,
            reason="granted_auto_verify_stub",
            email_verified_at=now,
            phone_verified_at=now,
        )

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
