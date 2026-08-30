"""
routers/therapist_auth.py -- Register/login for Assessment-native therapist
accounts. See app/models/therapist.py's docstring for why this is separate
from the retiring breathquest_therapists table.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.therapist import Therapist
from app.models.breathquest_models import BreathQuestPatient, Subscription, TherapistNote
from app.models.patient import Patient
from app.schemas.therapist_auth import TherapistRegister, TherapistLogin, TherapistTokenResponse, GoogleAuthRequest, TherapistResetPasswordRequest, TherapistDeleteAccountRequest
from app.breathquest_core.security import hash_password, verify_password, create_access_token
from app.breathquest_core.google_oauth import verify_google_id_token
from datetime import datetime, timezone
from app.breathquest_core.parental_consent import check_email_consent
from app.breathquest_core.deps import get_current_therapist
# Same throttle module kid-login uses (see login_throttle.py's docstring) --
# it's identifier-agnostic (just a string key), so it works equally well
# keyed on a therapist's email as on a kid's name/player_code. Therapist
# accounts guard real patient clinical data behind a real password, and
# had no brute-force protection at all before this -- unlike kid-login's
# 4-digit PIN, which was the threat this module was originally written for.
from app.breathquest_core.login_throttle import check_throttle, record_failure, record_success
from app.breathquest_core.rate_limit import check_ip_rate_limit
from app.breathquest_core.security import create_refresh_token
from sqlalchemy import delete as sa_delete, update as sa_update

router = APIRouter(prefix="/auth", tags=["therapist-auth"])


@router.post("/register", response_model=TherapistTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_therapist(request: Request, data: TherapistRegister, db: AsyncSession = Depends(get_db)):
    check_ip_rate_limit(request)
    # Same recently-verified-email gate as kid-register (see
    # parental_consent.py) -- a therapist signing up standalone has no
    # adult/org already vouching for them, same "no one else in the loop"
    # situation kid-register was built for. AUTO_VERIFY_CONSENT currently
    # makes this auto-grant once an email is provided (no live OTP
    # provider wired up yet) -- see that flag's docstring.
    consent = await check_email_consent(data.email, db)
    if not consent.granted:
        detail_by_reason = {
            "not_verified": "Please verify your email before registering",
            "expired": "Please verify your email again before registering",
        }
        detail = detail_by_reason.get(consent.reason, "Please verify your email before registering")
        raise HTTPException(status_code=403, detail=detail)

    existing = await db.execute(select(Therapist).where(Therapist.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    therapist = Therapist(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        clinic_name=data.clinic_name,
        phone=data.phone,
    )
    db.add(therapist)
    await db.flush()

    token = create_access_token(str(therapist.id))
    refresh_token = await create_refresh_token(db, "therapist", str(therapist.id))
    await db.commit()
    return TherapistTokenResponse(
        access_token=token, refresh_token=refresh_token, therapist_id=str(therapist.id),
        full_name=therapist.full_name, email=therapist.email,
        phone=therapist.phone,
    )


@router.post("/login", response_model=TherapistTokenResponse)
async def login_therapist(data: TherapistLogin, db: AsyncSession = Depends(get_db)):
    # Throttle check happens before touching hashed_password at all -- a
    # locked-out email gets 429 regardless of whether the password sent is
    # even close, matching kid-login's same reasoning: a locked-out
    # attacker learns nothing from further guesses.
    throttle = await check_throttle(data.email, db)
    if throttle.locked:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(throttle.retry_after_seconds)},
        )

    result = await db.execute(select(Therapist).where(Therapist.email == data.email))
    therapist = result.scalar_one_or_none()

    if not therapist or not verify_password(data.password, therapist.hashed_password):
        await record_failure(data.email, db)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not therapist.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    await record_success(data.email, db)
    token = create_access_token(str(therapist.id))
    refresh_token = await create_refresh_token(db, "therapist", str(therapist.id))
    await db.commit()
    return TherapistTokenResponse(
        access_token=token, refresh_token=refresh_token, therapist_id=str(therapist.id),
        full_name=therapist.full_name, email=therapist.email,
        phone=therapist.phone,
    )


@router.post("/reset-password", status_code=200)
async def reset_therapist_password(request: Request, data: TherapistResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Password reset for a therapist who's locked out. Gated on the same
    recently-verified email consent register_therapist itself requires.
    Returns the same generic response whether or not the email has an
    account -- matches parent-reset-password's anti-enumeration shape,
    so this can't be used to check which emails have therapist accounts."""
    check_ip_rate_limit(request)
    email = data.email.strip().lower()

    consent = await check_email_consent(email, db)
    if not consent.granted:
        detail_by_reason = {
            "not_verified": "Please verify this email before resetting the password",
            "expired": "Please verify this email again before resetting the password",
        }
        detail = detail_by_reason.get(consent.reason, "Please verify this email before resetting the password")
        raise HTTPException(status_code=403, detail=detail)

    result = await db.execute(select(Therapist).where(Therapist.email == email))
    therapist = result.scalar_one_or_none()
    if therapist:
        therapist.hashed_password = hash_password(data.new_password)
        await db.commit()
    return {"message": "If that email has an account, its password has been reset."}


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_therapist_account(
    data: TherapistDeleteAccountRequest,
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    """Deletes the therapist's own account -- an irreversible action, so
    requires re-entering the current password first (skipped only for
    Google-only accounts with no password ever set). Previously this was
    a bare authenticated DELETE with no re-auth at all: anyone with a
    few seconds of unattended access to a logged-in session could wipe
    the account.

    Does NOT cascade-delete their
    patients -- a therapist leaving shouldn't destroy a kid's account or
    progress. Nullable FKs (BreathQuestPatient.therapist_id,
    Subscription.owner_therapist_id, Patient.registered_therapist_id) are
    detached instead. TherapistNote.therapist_id is NOT nullable (notes
    are authored content, not a loose reference), so those rows are
    deleted outright rather than left dangling.

    2026-08-30: this used to skip the TherapistNote cleanup and the
    Patient.registered_therapist_id detachment -- both only existed in a
    dead, unreachable duplicate of this same route in breathquest/auth.py
    (shadowed because therapist_auth_router mounts first in main.py). Any
    therapist who'd ever written a note would hit a DB IntegrityError
    trying to delete their own account, since TherapistNote.therapist_id
    has no ON DELETE CASCADE. Merged the duplicate's cleanup logic in
    here (the live route) and removed the dead copy."""
    if therapist.hashed_password:
        if not data.current_password or not verify_password(data.current_password, therapist.hashed_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

    await db.execute(sa_delete(TherapistNote).where(TherapistNote.therapist_id == therapist.id))
    await db.execute(
        sa_update(BreathQuestPatient).where(BreathQuestPatient.therapist_id == therapist.id).values(therapist_id=None)
    )
    await db.execute(sa_delete(Subscription).where(Subscription.owner_therapist_id == therapist.id))
    await db.execute(
        sa_update(Patient).where(Patient.registered_therapist_id == therapist.id).values(registered_therapist_id=None)
    )
    await db.execute(sa_delete(Therapist).where(Therapist.id == therapist.id))
    await db.commit()


@router.post("/google", response_model=TherapistTokenResponse)
async def google_login_or_register_therapist(
    request: Request, data: GoogleAuthRequest, db: AsyncSession = Depends(get_db)
):
    """Combined login-or-register, unlike the password flow's separate
    /register and /login -- a therapist account has no other required
    field (unlike Parent, which needs a linked child, see
    breathquest/auth.py's parent-google-* split), so there's nothing
    register would need that we don't already have from the verified
    Google token.

    Three cases, in order:
    1. google_sub already on file -> this is a returning Google user, log in.
    2. No google_sub match, but email matches an existing (password)
       account -> first time this therapist has used Google; link it,
       so they can use either method from now on. Requires
       email_verified from Google, since linking on email alone would
       let anyone claim an existing account just by controlling an
       unverified address at signup time.
    3. Neither matches -> brand new therapist, auto-register.
    """
    check_ip_rate_limit(request)
    google_user = verify_google_id_token(data.id_token)

    result = await db.execute(select(Therapist).where(Therapist.google_sub == google_user.sub))
    therapist = result.scalar_one_or_none()

    if therapist is None and google_user.email:
        result = await db.execute(select(Therapist).where(Therapist.email == google_user.email))
        existing = result.scalar_one_or_none()
        if existing is not None:
            if not google_user.email_verified:
                raise HTTPException(
                    status_code=403,
                    detail="Google account email isn't verified -- can't link to an existing account",
                )
            existing.google_sub = google_user.sub
            therapist = existing

    if therapist is None:
        if not google_user.email_verified:
            raise HTTPException(status_code=403, detail="Google account email isn't verified")
        therapist = Therapist(
            email=google_user.email,
            hashed_password=None,
            full_name=google_user.name or google_user.email.split("@")[0],
            google_sub=google_user.sub,
        )
        db.add(therapist)
        await db.flush()

    if not therapist.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    therapist.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    token = create_access_token(str(therapist.id))
    refresh_token = await create_refresh_token(db, "therapist", str(therapist.id))
    await db.commit()
    return TherapistTokenResponse(
        access_token=token, refresh_token=refresh_token, therapist_id=str(therapist.id),
        full_name=therapist.full_name, email=therapist.email,
        phone=therapist.phone,
    )
