"""
routers/auth.py — Authentication for therapists (JWT) and kids (PIN).
"""

import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.breathquest_models import Therapist, BreathQuestPatient
from app.models.patient import Patient
from app.schemas.breathquest_schemas import (
    TherapistRegister, TherapistLogin, TokenResponse,
    KidLoginRequest, KidTokenResponse, KidRegisterRequest,
)
from app.breathquest_core.security import (
    hash_password, verify_password,
    create_access_token,
    hash_pin, verify_pin, create_kid_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ------------------------------------------------------------------ #
#  Therapist auth                                                      #
# ------------------------------------------------------------------ #

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_therapist(data: TherapistRegister, db: AsyncSession = Depends(get_db)):
    therapist = Therapist(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        clinic_name=data.clinic_name,
    )
    db.add(therapist)
    await db.commit()
    await db.refresh(therapist)

    token = create_access_token(therapist.id)
    return TokenResponse(
        access_token=token,
        therapist_id=str(therapist.id),
        full_name=therapist.full_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login_therapist(data: TherapistLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Therapist).where(Therapist.email == data.email))
    therapist = result.scalar_one_or_none()

    if not therapist or not verify_password(data.password, therapist.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not therapist.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    therapist.last_login = datetime.now(timezone.utc)

    token = create_access_token(therapist.id)
    return TokenResponse(
        access_token=token,
        therapist_id=str(therapist.id),
        full_name=therapist.full_name,
    )


# ------------------------------------------------------------------ #
#  Kid self-registration                                               #
# ------------------------------------------------------------------ #

@router.post("/kid-register", response_model=KidTokenResponse, status_code=201)
async def kid_register(data: KidRegisterRequest, db: AsyncSession = Depends(get_db)):
    # Generate short unique player code e.g. CHICK42
    while True:
        code = data.avatar.upper()[:5] + str(random.randint(10, 99))
        exists = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.player_code == code))
        if not exists.scalar_one_or_none():
            break

    patient = BreathQuestPatient(
        therapist_id=None,
        first_name=data.first_name,
        avatar=data.avatar,
        pin_hash=hash_pin(data.pin),
        player_code=code,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    # Also create a record in the main Patient table for dashboard visibility
    try:
        sync_db = SessionLocal()
        main_patient = Patient(
            name=data.first_name,
            age=data.age if hasattr(data, 'age') else None,
            language="en",
            gender="other",
            diagnosis="General Speech",
            is_active=True
        )
        sync_db.add(main_patient)
        sync_db.commit()
        sync_db.close()
    except Exception as e:
        # Log error but don't fail the registration
        print(f"Failed to create main Patient record: {e}")

    token = create_kid_token(patient.id)
    return KidTokenResponse(
        access_token=token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        player_code=code,
    )


# ------------------------------------------------------------------ #
#  Kid PIN login (using player_code + PIN)                            #
# ------------------------------------------------------------------ #

@router.post("/kid-login", response_model=KidTokenResponse)
async def kid_login(data: KidLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BreathQuestPatient).where(BreathQuestPatient.player_code == data.player_code.upper())
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Player code not found")

    if not patient.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    if not verify_pin(data.pin, patient.pin_hash):
        raise HTTPException(status_code=401, detail="Incorrect PIN")

    token = create_kid_token(patient.id)
    await db.commit()
    return KidTokenResponse(
        access_token=token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        player_code=patient.player_code,
    )
