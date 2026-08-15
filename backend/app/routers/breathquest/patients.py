"""
routers/patients.py — Patient management (therapist-only), BreathQuest side.

Fixed 2026-08-11: was pointing at app.models.patient.Patient (Assessment's
patient-intake record) and app.models.session.Session (Assessment's manual
acoustic-session log) instead of the correct BreathQuestPatient/GameSession
models in app.models.breathquest_models — see main.py's original 2026-08-06
disable comment, which flagged this exact bug as the reason this router was
turned off.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.breathquest_models import BreathQuestPatient, GameSession
from app.models.patient import Patient
from app.schemas.breathquest_schemas import (
    PatientCreate, PatientUpdate, PatientOut, PatientDetailOut, KidTokenResponse,
)
from app.breathquest_core.deps import get_current_therapist
from app.breathquest_core.security import hash_pin, create_kid_token

router = APIRouter(prefix="/patients", tags=["patients"])

def _player_code(patient_id) -> str:
    return f"P{str(patient_id).replace('-', '')[:9].upper()}"

@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreate,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    """Creates BOTH the BreathQuestPatient (game-side identity, PIN login)
    and its linked Assessment-side Patient row, in one transaction --
    fixing the gap identified 2026-08-13: previously, assessment_patient_id
    only ever got set via the kid self-login path (breathquest/assessment.py's
    /start), so a therapist-created patient had no game<->assessment link at
    all until the kid happened to self-start an assessment. A therapist
    launching Assessment/Live Therapy for a patient they just created
    (see start-session below) needs that link to exist immediately.

    Single flush at the end, no intermediate commit -- both rows are
    created atomically or neither is, since Patient's own creation has no
    meaningful existence without a BreathQuestPatient to hand it back to."""
    assessment_patient = Patient(
        name=data.first_name,
        age=data.age,
        diagnosis=data.diagnosis_notes,
        registered_therapist_id=therapist.id,
    )
    db.add(assessment_patient)
    await db.flush()  # populate assessment_patient.id before referencing it below

    patient = BreathQuestPatient(
        therapist_id=therapist.id,
        first_name=data.first_name,
        avatar=data.avatar,
        pin_hash=hash_pin(data.pin),
        player_code="",  # set below once we have the generated id
        age=data.age,
        diagnosis_notes=data.diagnosis_notes,
        assessment_patient_id=assessment_patient.id,
    )
    db.add(patient)
    await db.flush()
    patient.player_code = _player_code(patient.id)
    await db.flush()
    return PatientOut(
        id=str(patient.id), first_name=patient.first_name, avatar=patient.avatar,
        age=patient.age, is_active=patient.is_active, created_at=patient.created_at,
    )

@router.post("/{patient_id}/start-session", response_model=KidTokenResponse)
async def start_session(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    """The therapist-launched entry point into Assessment/Live Therapy
    (2026-08-13): mints a real kid token for a chosen patient without
    requiring the kid's PIN, so a therapist can launch a session directly
    from PatientDetail.jsx instead of the kid having to self-login first.
    Frontend stashes its own session and adopts this token as a
    supervised session (see AuthContext.jsx's startSupervisedSession),
    then restores the therapist session on exit.

    Also backfills assessment_patient_id for patients created before the
    linking fix above (only correctly linked patients have GameSession/
    diagnostic-context lookups actually work) -- this endpoint is the
    only reachable path some pre-fix patients have, so it doubles as the
    backstop rather than leaving them permanently unlinked."""
    result = await db.execute(
        select(BreathQuestPatient).where(
            BreathQuestPatient.id == patient_id,
            BreathQuestPatient.therapist_id == therapist.id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not patient.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    if patient.assessment_patient_id is None:
        assessment_patient = Patient(
            name=patient.first_name,
            age=patient.age,
            diagnosis=patient.diagnosis_notes,
            registered_therapist_id=therapist.id,
        )
        db.add(assessment_patient)
        await db.flush()
        patient.assessment_patient_id = assessment_patient.id
        await db.flush()

    token = create_kid_token(patient.id)
    return KidTokenResponse(
        access_token=token,
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        player_code=patient.player_code,
        assessment_completed=patient.assessment_completed,
    )


@router.get("", response_model=list[PatientDetailOut])
async def list_patients(
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BreathQuestPatient)
        .where(BreathQuestPatient.therapist_id == therapist.id)
        .order_by(BreathQuestPatient.created_at.desc())
    )
    patients = result.scalars().all()

    out = []
    for p in patients:
        stats = await db.execute(
            select(
                func.count(GameSession.id).label("total"),
                func.sum(GameSession.stars_earned).label("stars"),
                func.max(GameSession.started_at).label("last"),
            ).where(GameSession.patient_id == p.id)
        )
        row = stats.one()
        out.append(PatientDetailOut(
            id=str(p.id), first_name=p.first_name, avatar=p.avatar, age=p.age,
            is_active=p.is_active, created_at=p.created_at,
            diagnosis_notes=p.diagnosis_notes,
            total_sessions=row.total or 0, total_stars=int(row.stars or 0),
            last_session_at=row.last,
        ))
    return out

@router.get("/{patient_id}", response_model=PatientDetailOut)
async def get_patient(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BreathQuestPatient).where(
            BreathQuestPatient.id == patient_id,
            BreathQuestPatient.therapist_id == therapist.id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    stats = await db.execute(
        select(
            func.count(GameSession.id).label("total"),
            func.sum(GameSession.stars_earned).label("stars"),
            func.max(GameSession.started_at).label("last"),
        ).where(GameSession.patient_id == patient.id)
    )
    row = stats.one()
    return PatientDetailOut(
        id=str(patient.id), first_name=patient.first_name, avatar=patient.avatar,
        age=patient.age, is_active=patient.is_active, created_at=patient.created_at,
        diagnosis_notes=patient.diagnosis_notes,
        total_sessions=row.total or 0, total_stars=int(row.stars or 0),
        last_session_at=row.last,
    )

@router.patch("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BreathQuestPatient).where(
            BreathQuestPatient.id == patient_id,
            BreathQuestPatient.therapist_id == therapist.id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(patient, field, value)

    return PatientOut(
        id=str(patient.id), first_name=patient.first_name, avatar=patient.avatar,
        age=patient.age, is_active=patient.is_active, created_at=patient.created_at,
    )

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BreathQuestPatient).where(
            BreathQuestPatient.id == patient_id,
            BreathQuestPatient.therapist_id == therapist.id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    await db.delete(patient)


# ------------------------------------------------------------------ #
#  Kid self-service profile edit -- separate from PATCH /{patient_id}
#  above, which is therapist-only and scoped by therapist_id. This lets
#  a logged-in kid change their own display name and avatar, nothing
#  else (no therapist_id, is_active, etc. exposed here).
# ------------------------------------------------------------------ #
from pydantic import BaseModel, Field
from app.breathquest_core.deps import get_current_patient

VALID_AVATARS = {"chick", "dragon", "bunny", "fox", "rocket", "fish"}


class MyProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar: str | None = None


@router.patch("/me/profile", response_model=PatientOut)
async def update_my_profile(
    data: MyProfileUpdate,
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    if data.avatar is not None and data.avatar not in VALID_AVATARS:
        raise HTTPException(status_code=400, detail="Invalid avatar choice")

    if data.first_name is not None:
        patient.first_name = data.first_name.strip()
    if data.avatar is not None:
        patient.avatar = data.avatar

    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    return PatientOut(
        id=str(patient.id), first_name=patient.first_name, avatar=patient.avatar,
        age=patient.age, is_active=patient.is_active, created_at=patient.created_at,
    )
