"""
routers/auth.py — Kid PIN auth for BreathQuest, plus candidate lookups
against Assessment's patient/therapist records.

Therapist register/login live at app/routers/therapist_auth.py instead
(mounted at the same /api/v1/auth/register and /api/v1/auth/login paths
this router used to define) -- that one is backed by the canonical
`therapists` table; this router's old register/login used the retiring
`breathquest_therapists` table and were removed 2026-08-12 to avoid a
silent route collision if both were ever mounted together, and because
get_current_therapist (gating patients.py/dashboard.py/chime.py) already
only recognizes the canonical table's tokens -- the old endpoints here
issued tokens those routes could never actually accept.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.database import get_db, SessionLocal
from app.models.breathquest_models import BreathQuestPatient
from app.models.patient import Patient
from app.schemas.breathquest_schemas import (
    KidLoginRequest, KidTokenResponse, KidRegisterRequest, KidPinSetupRequest,
)
from app.breathquest_core.security import (
    hash_pin, verify_pin, create_kid_token, generate_unique_player_code,
)
from app.breathquest_core.login_throttle import check_throttle, record_failure, record_success

router = APIRouter(prefix="/auth", tags=["auth"])


# ------------------------------------------------------------------ #
#  Therapist candidate lookup (Assessment cross-reference)              #
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
    """Brand-new self-serve kid signup — no prior Assessment record
    required. This is what frontend/src/context/AuthContext.jsx's
    registerKid() (used by pages/kid/Play.jsx's signup form) actually
    calls; it only ever sends {first_name, avatar, pin}. The old
    patient_id-required version of this endpoint made every one of those
    calls 422. That link-an-existing-Assessment-patient flow now lives at
    POST /auth/kid-pin-setup instead."""
    player_code = await generate_unique_player_code(db, data.avatar)
    patient = BreathQuestPatient(
        therapist_id=None,
        first_name=data.first_name,
        avatar=data.avatar,
        pin_hash=hash_pin(data.pin),
        player_code=player_code,
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
        assessment_completed=patient.assessment_completed,
    )


@router.post("/kid-pin-setup", response_model=KidTokenResponse, status_code=201)
async def kid_pin_setup(data: KidPinSetupRequest, db: AsyncSession = Depends(get_db)):
    """Set or reset a BreathQuest PIN for a child already created in
    Assessment (via POST /patients/). This is the endpoint
    AuthContext.jsx's setupKidPin() calls -- it used to point at a route
    that didn't exist at all (404 on every call), since this logic
    previously lived under /auth/kid-register instead."""
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
            assessment_completed=True,  # they already have an Assessment record
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
        assessment_completed=patient.assessment_completed,
    )

@router.post("/kid-login", response_model=KidTokenResponse)
async def kid_login(data: KidLoginRequest, db: AsyncSession = Depends(get_db)):
    # Player codes remain supported for children who already have one. Names
    # are matched without regard to case so children can use their registered
    # name together with their PIN.
    identifier = data.player_code.strip()

    # Throttle check happens before touching pin_hash at all -- a locked-out
    # identifier gets 429 regardless of whether the PIN they sent is even
    # close, so a locked-out attacker learns nothing from further guesses.
    throttle = await check_throttle(identifier, db)
    if throttle.locked:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(throttle.retry_after_seconds)},
        )

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
        await record_failure(identifier, db)
        await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect name, player code, or PIN")
    if len(matching_patients) > 1:
        raise HTTPException(status_code=409, detail="More than one player matches. Please use your player code.")

    patient = matching_patients[0]

    if not patient.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_kid_token(patient.id)
    await record_success(identifier, db)
    await db.commit()
    return KidTokenResponse(
        access_token=token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        player_code=patient.player_code,
        assessment_completed=patient.assessment_completed,
    )
