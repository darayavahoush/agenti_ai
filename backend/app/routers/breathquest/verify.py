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
import smtplib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from app.database import get_db
from app.breathquest_core.rate_limit import check_ip_rate_limit
from app.models.breathquest_models import BreathQuestPatient, EmailVerification
from app.models.therapist import Therapist
from app.schemas.breathquest_schemas import (
    VerifyRequestIn, VerifyConfirmIn, VerifyConfirmOut,
)
from app.config import settings
from app.services.email import send_otp_email

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/verify", tags=["verify"])

OTP_EXPIRY_MINUTES = 10
MAX_ATTEMPTS = 5


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


RESEND_COOLDOWN_SECONDS = 60


async def _refuse_if_account_exists(data: VerifyRequestIn, db: AsyncSession) -> None:
    """Registration screens only (see VerifyRequestIn.purpose): tell the
    person now that the account exists, rather than after they've fetched
    and typed a code. Runs before anything is created or emailed, so it
    neither burns the resend cooldown nor sends a pointless code."""
    email = data.email.strip().lower()

    if data.purpose == "register_therapist":
        found = (await db.execute(
            select(Therapist.id).where(func.lower(Therapist.email) == email).limit(1)
        )).scalar_one_or_none()
        if found is not None:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please sign in instead.",
            )

    elif data.purpose == "register_kid" and data.first_name and data.first_name.strip():
        # Same rule kid-register applies after verification (a kid with this
        # first name already registered under this parent email).
        kid = (await db.execute(
            select(BreathQuestPatient)
            .where(
                BreathQuestPatient.is_active.is_(True),
                func.lower(BreathQuestPatient.first_name) == data.first_name.strip().lower(),
                func.lower(BreathQuestPatient.parent_email) == email,
            )
            .limit(1)
        )).scalars().first()
        if kid is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"An account for {kid.first_name} already exists for this email. "
                    "Tap \u201cI have a code\u201d to log in. If the player code is lost, "
                    "enter the parent's email there and we'll email it."
                ),
            )


@router.post("/request")
async def request_verification(request: Request, data: VerifyRequestIn, db: AsyncSession = Depends(get_db)):
    if data.purpose is not None:
        # This path reveals whether an account exists, so throttle it like
        # the other auth endpoints (20 requests/min/IP) to make bulk
        # probing impractical.
        check_ip_rate_limit(request)
        await _refuse_if_account_exists(data, db)

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

    # send_otp_email does a blocking smtplib call with no timeout/retry of
    # its own -- if Gmail rejects auth, drops the connection, or is just
    # slow, this used to propagate as a raw unhandled 500 with no logged
    # detail beyond the traceback. Catching it here does two things: logs
    # the *actual* SMTP exception server-side (so "did it really send"
    # stops being a guessing game), and returns a clean, expected error to
    # the frontend, which already renders `error` via getErrorMessage --
    # see handleSendParentContact/handleResendEmailCode in Play.jsx.
    try:
        send_otp_email(data.email, code)
    except smtplib.SMTPAuthenticationError:
        # Not a transient blip -- retrying will never work until the
        # credentials are fixed, so make that obvious in the log.
        logger.exception(
            "OTP email FAILED: SMTP login was rejected for %s. Check the "
            "SMTP_USER / SMTP_PASSWORD secrets (Gmail needs a 16-character "
            "app password generated for that exact account; a truncated or "
            "revoked one gives this error).", settings.SMTP_USER,
        )
        raise HTTPException(
            status_code=502,
            detail="We couldn't send the verification email. Please try again in a few minutes, or contact support if it keeps happening.",
        )
    except Exception:
        logger.exception(f"Failed to send OTP email to {data.email}")
        raise HTTPException(
            status_code=502,
            detail="We couldn't send the verification email. Please try again in a few minutes, or contact support if it keeps happening.",
        )

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
