"""
routers/auth.py — Authentication for therapists (JWT) and kids (PIN).
"""

import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
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

@router.get("/therapist-candidates")
def therapist_candidates():
    """Return unique therapist names already recorded during Assessment."""
    sync_db = SessionLocal()
    try:
        names = (
            sync_db.query(Patient.therapist_name)
            .filter(Patient.therapist_name.isnot(None), func.trim(Patient.therapist_name) != "")
            .distinct()
            .order_by(Patient.therapist_name)
            .all()
        )
        return [name for (name,) in names]
    finally:
        sync_db.close()

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

@router.get("/kid-candidates")
def kid_candidates():
    """Return children already created through Assessment for PIN setup."""
    sync_db = SessionLocal()
    try:
        patients = sync_db.query(Patient).filter(Patient.is_active.is_(True)).order_by(Patient.name).all()
        return [{"id": str(patient.id), "name": patient.name} for patient in patients]
    finally:
        sync_db.close()

@router.post("/kid-register", response_model=KidTokenResponse, status_code=201)
async def kid_register(data: KidRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Set or reset a BreathQuest PIN for a child created in Assessment."""
    sync_db = SessionLocal()
    try:
        main_patient = sync_db.get(Patient, data.patient_id)
    finally:
        sync_db.close()

    if not main_patient or not main_patient.is_active:
        raise HTTPException(status_code=404, detail="Registered child not found")

    player_code = f"P{str(main_patient.id).replace('-', '')[:9].upper()}"
    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.player_code == player_code))
    patient = result.scalar_one_or_none()

    if patient:
        patient.first_name = main_patient.name
        patient.avatar = data.avatar
        patient.pin_hash = hash_pin(data.pin)
        patient.is_active = True
    else:
        patient = BreathQuestPatient(
            therapist_id=None,
            first_name=main_patient.name,
            avatar=data.avatar,
            pin_hash=hash_pin(data.pin),
            player_code=player_code,
            assessment_patient_id=main_patient.id,
        )
        db.add(patient)

    await db.commit()
    await db.refresh(patient)
    token = create_kid_token(patient.id)
    return KidTokenResponse(
        access_token=token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        player_code=patient.player_code,
    )

@router.post("/kid-login", response_model=KidTokenResponse)
async def kid_login(data: KidLoginRequest, db: AsyncSession = Depends(get_db)):
    # Player codes remain supported for children who already have one. Names
    # are matched without regard to case so children can use their registered
    # name together with their PIN.
    identifier = data.player_code.strip()
    result = await db.execute(
        select(BreathQuestPatient).where(
            (BreathQuestPatient.player_code == identifier.upper())
            | (func.lower(BreathQuestPatient.first_name) == identifier.lower())
        )
    )
    patients = result.scalars().all()

    # More than one child can have the same name. The PIN identifies the
    # matching account; their player code remains a fallback for a collision.
    matching_patients = [patient for patient in patients if verify_pin(data.pin, patient.pin_hash)]
    if not matching_patients:
        raise HTTPException(status_code=401, detail="Incorrect name, player code, or PIN")
    if len(matching_patients) > 1:
        raise HTTPException(status_code=409, detail="More than one player matches. Please use your player code.")

    patient = matching_patients[0]

    if not patient.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_kid_token(patient.id)
    await db.commit()
    return KidTokenResponse(
        access_token=token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        player_code=patient.player_code,
    )
