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
from app.schemas.therapist_auth import TherapistRegister, TherapistLogin, TherapistTokenResponse
from app.breathquest_core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["therapist-auth"])


@router.post("/register", response_model=TherapistTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_therapist(data: TherapistRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Therapist).where(Therapist.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    therapist = Therapist(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        clinic_name=data.clinic_name,
    )
    db.add(therapist)
    await db.flush()

    token = create_access_token(str(therapist.id))
    return TherapistTokenResponse(
        access_token=token, therapist_id=str(therapist.id),
        full_name=therapist.full_name, email=therapist.email,
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
    )
