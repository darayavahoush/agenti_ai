"""
routers/verify.py — email OTP gate in front of the public landing page's
"Start Assessment"/"Start Trial" buttons. See app.models.breathquest_models.
EmailVerification for why this is deliberately separate from the real
Patient/Therapist account systems.

Import paths fixed 2026-08-12 to match the merged app's layout (was still
quest-games' standalone-backend imports -- database, models.models,
schemas.schemas, core.email -- which is why this router was never actually
mounted in main.py; importing it as-is would throw ModuleNotFoundError,
same class of bug already fixed for chime.py/voicehurdlerace.py).
"""

import hashlib
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.breathquest_models import EmailVerification
from app.schemas.breathquest_schemas import VerifyRequestIn, VerifyConfirmIn, VerifyConfirmOut
from app.services.email import send_otp_email

router = APIRouter(prefix="/verify", tags=["verify"])

OTP_EXPIRY_MINUTES = 10
MAX_ATTEMPTS = 5


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


RESEND_COOLDOWN_SECONDS = 60

@router.post("/request")
async def request_verification(data: VerifyRequestIn, db: AsyncSession = Depends(get_db)):
    # Throttle: block a new code if this email has one issued in the
    # last RESEND_COOLDOWN_SECONDS, so the endpoint can't be hammered to
    # spam an inbox or used to brute-force-enumerate emails via timing.
    recent_result = await db.execute(
        select(EmailVerification)
        .where(EmailVerification.email == data.email)
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )
    recent = recent_result.scalars().first()
    if recent is not None:
        elapsed = (datetime.now(timezone.utc) - recent.created_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait}s before requesting another code",
            )

    code = f"{random.randint(0, 999999):06d}"
    record = EmailVerification(
        email=data.email,
        otp_code_hash=_hash_code(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(record)
    await db.flush()

    send_otp_email(data.email, code)

    return {"message": f"Verification code sent to {data.email}"}


@router.post("/confirm", response_model=VerifyConfirmOut)
async def confirm_verification(data: VerifyConfirmIn, db: AsyncSession = Depends(get_db)):
    # Most recent unverified, unexpired attempt for this email.
    result = await db.execute(
        select(EmailVerification)
        .where(
            EmailVerification.email == data.email,
            EmailVerification.verified == False,  # noqa: E712
        )
        .order_by(EmailVerification.created_at.desc())
    )
    record = result.scalars().first()

    if record is None:
        raise HTTPException(status_code=400, detail="No pending verification for this email — request a new code")

    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Code expired — request a new one")

    if record.attempts >= MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts — request a new code")

    if _hash_code(data.code) != record.otp_code_hash:
        record.attempts += 1
        raise HTTPException(status_code=400, detail="Incorrect code")

    # Check BEFORE marking this record verified, or this email would
    # always look "verified before" on its own new record.
    prior_result = await db.execute(
        select(EmailVerification.id)
        .where(EmailVerification.email == data.email, EmailVerification.verified == True)  # noqa: E712
        .limit(1)
    )
    first_time = prior_result.scalar_one_or_none() is None

    record.verified = True
    record.verified_at = datetime.now(timezone.utc)

    return VerifyConfirmOut(verified=True, first_time=first_time)
