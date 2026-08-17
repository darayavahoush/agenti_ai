"""
routers/therapist_auth.py -- Register/login for Assessment-native therapist
accounts. See app/models/therapist.py's docstring for why this is separate
from the retiring breathquest_therapists table.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.therapist import Therapist
from app.models.breathquest_models import BreathQuestPatient, Subscription
from app.schemas.therapist_auth import TherapistRegister, TherapistLogin, TherapistTokenResponse
from app.breathquest_core.security import hash_password, verify_password, create_access_token
from app.breathquest_core.parental_consent import check_email_consent
from app.breathquest_core.deps import get_current_therapist
from sqlalchemy import delete as sa_delete, update as sa_update

router = APIRouter(prefix="/auth", tags=["therapist-auth"])


@router.post("/register", response_model=TherapistTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_therapist(data: TherapistRegister, db: AsyncSession = Depends(get_db)):
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
    return TherapistTokenResponse(
        access_token=token, therapist_id=str(therapist.id),
        full_name=therapist.full_name, email=therapist.email,
        phone=therapist.phone,
    )


@router.post("/login", response_model=TherapistTokenResponse)
async def login_therapist(data: TherapistLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Therapist).where(Therapist.email == data.email))
    therapist = result.scalar_one_or_none()

    if not therapist or not verify_password(data.password, therapist.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not therapist.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token(str(therapist.id))
    return TherapistTokenResponse(
        access_token=token, therapist_id=str(therapist.id),
        full_name=therapist.full_name, email=therapist.email,
        phone=therapist.phone,
    )


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_therapist_account(
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    """Deletes the therapist's own account. Does NOT cascade to their
    patients -- BreathQuestPatient.therapist_id is nullable, so patients
    just become unassigned (therapist_id=None) rather than being deleted,
    matching how kid-register already creates patients with no therapist."""
    await db.execute(
        sa_update(BreathQuestPatient).where(BreathQuestPatient.therapist_id == therapist.id).values(therapist_id=None)
    )
    await db.execute(sa_delete(Subscription).where(Subscription.owner_therapist_id == therapist.id))
    await db.execute(sa_delete(Therapist).where(Therapist.id == therapist.id))
    await db.commit()
