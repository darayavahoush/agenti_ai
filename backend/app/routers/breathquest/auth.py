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
from datetime import datetime, timezone

from app.database import get_db, SessionLocal
from app.models.breathquest_models import BreathQuestPatient, Parent
from app.models.patient import Patient
from app.schemas.breathquest_schemas import (
    KidLoginRequest, KidTokenResponse, KidRegisterRequest, KidPinSetupRequest,
    ParentRegisterRequest, ParentLoginRequest, ParentTokenResponse,
)
from app.breathquest_core.security import (
    hash_pin, verify_pin, create_kid_token, generate_unique_player_code,
    hash_password, verify_password, create_parent_token,
)
from app.breathquest_core.login_throttle import check_throttle, record_failure, record_success
from app.breathquest_core.parental_consent import check_parental_consent

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
    POST /auth/kid-pin-setup instead.

    COPPA: this is the only kid-account path with no adult already in the
    loop, so it's gated on a recently-verified parent email AND phone
    (both required, see breathquest_core/parental_consent.py) before it
    will touch the DB at all."""
    consent = await check_parental_consent(data.parent_email, data.parent_phone, db)
    if not consent.granted:
        detail_by_reason = {
            "email_not_verified": "A parent needs to verify their email before creating this account",
            "email_expired": "Please verify the parent's email again before creating the account",
            "phone_not_verified": "A parent needs to verify their phone number before creating this account",
            "phone_expired": "Please verify the parent's phone number again before creating the account",
        }
        detail = detail_by_reason.get(consent.reason, "A parent needs to verify their email and phone before creating this account")
        raise HTTPException(status_code=403, detail=detail)

    player_code = await generate_unique_player_code(db, data.avatar)
    patient = BreathQuestPatient(
        therapist_id=None,
        first_name=data.first_name,
        avatar=data.avatar,
        pin_hash=hash_pin(data.pin),
        player_code=player_code,
        parent_email=data.parent_email,
        parent_consent_verified_at=consent.email_verified_at,
        parent_phone=data.parent_phone,
        parent_phone_consent_verified_at=consent.phone_verified_at,
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


# ------------------------------------------------------------------ #
#  Parent auth                                                         #
# ------------------------------------------------------------------ #
# Added 2026-08-13: frontend/src/context/AuthContext.jsx's registerParent()
# and loginParent() (used by pages/parent/ParentAuth.jsx) have called
# authAPI.parentRegister()/parentLogin() -- POST /auth/parent-register and
# POST /auth/parent-login -- since they were written, but no route ever
# served either path; every call 404'd. The Parent model, hash_password/
# verify_password, and create_parent_token/decode_parent_token all already
# existed (see breathquest_core/security.py and breathquest_core/deps.py's
# get_current_parent), so this was purely a missing router, not missing
# infrastructure.
#
# invite_code is accepted by the schema (ParentAuth.jsx already has a UI
# toggle for it) but there's no invite-code generation/storage anywhere in
# the backend yet -- that's a separate, larger feature (a code needs to be
# generated by a therapist, stored, and redeemed exactly once). Rather than
# silently no-op or pretend it works, an invite_code attempt gets a clear
# 501 for now; player_code (fully real -- BreathQuestPatient.player_code)
# is the only working path today.

def _make_parent_token_response(parent: Parent, child_first_name: str) -> ParentTokenResponse:
    token = create_parent_token(str(parent.id))
    return ParentTokenResponse(
        access_token=token,
        parent_id=str(parent.id),
        patient_id=str(parent.patient_id),
        child_first_name=child_first_name,
    )


@router.post("/parent-register", response_model=ParentTokenResponse, status_code=201)
async def register_parent(data: ParentRegisterRequest, db: AsyncSession = Depends(get_db)):
    if not data.player_code and not data.invite_code:
        raise HTTPException(status_code=400, detail="A player code or invite code is required")
    if data.invite_code:
        raise HTTPException(status_code=501, detail="Invite codes aren't available yet — use your child's player code instead")

    result = await db.execute(
        select(BreathQuestPatient).where(BreathQuestPatient.player_code == data.player_code.strip().upper())
    )
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="No child found with that player code")

    existing_email = await db.execute(select(Parent).where(Parent.email == data.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_link = await db.execute(select(Parent).where(Parent.patient_id == child.id))
    if existing_link.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This child already has a linked parent account")

    parent = Parent(
        patient_id=child.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
    )
    db.add(parent)
    await db.commit()
    await db.refresh(parent)
    return _make_parent_token_response(parent, child.first_name)


@router.post("/parent-login", response_model=ParentTokenResponse)
async def login_parent(data: ParentLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parent).where(Parent.email == data.email))
    parent = result.scalar_one_or_none()
    if not parent or not verify_password(data.password, parent.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not parent.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    child_result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == parent.patient_id))
    child = child_result.scalar_one_or_none()

    parent.last_login = datetime.now(timezone.utc)
    await db.commit()
    return _make_parent_token_response(parent, child.first_name if child else "")
