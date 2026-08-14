"""
routers/breathquest/patients.py — Patient management (therapist-only).

Fixed 2026-08-14: was pointing at app.models.patient.Patient (Assessment's
patient-intake record) and app.models.session.Session (Assessment's manual
acoustic-session log) instead of the correct BreathQuestPatient/GameSession
models in app.models.breathquest_models, and get_current_therapist was a
hardcoded dummy rather than real auth. Both fixed here.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.breathquest_models import BreathQuestPatient, GameSession
from app.schemas.breathquest_schemas import PatientCreate, PatientUpdate, PatientOut, PatientDetailOut
from app.breathquest_core.deps import get_current_therapist
from app.breathquest_core.security import hash_pin

router = APIRouter(prefix="/patients", tags=["patients"])


def _player_code(patient_id) -> str:
    return f"P{str(patient_id).replace('-', '')[:9].upper()}"


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreate,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    patient = BreathQuestPatient(
        therapist_id=therapist.id,
        first_name=data.first_name,
        avatar=data.avatar,
        pin_hash=hash_pin(data.pin),
        player_code="",  # set below once we have the generated id
        age=data.age,
        diagnosis_notes=data.diagnosis_notes,
    )
    db.add(patient)
    await db.flush()
    patient.player_code = _player_code(patient.id)
    await db.flush()

    return PatientOut(
        id=str(patient.id), first_name=patient.first_name, avatar=patient.avatar,
        player_code=patient.player_code, age=patient.age, is_active=patient.is_active,
        created_at=patient.created_at,
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
            id=str(p.id), first_name=p.first_name, avatar=p.avatar,
            player_code=p.player_code, age=p.age, is_active=p.is_active,
            created_at=p.created_at, diagnosis_notes=p.diagnosis_notes,
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
        player_code=patient.player_code, age=patient.age, is_active=patient.is_active,
        created_at=patient.created_at, diagnosis_notes=patient.diagnosis_notes,
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
        player_code=patient.player_code, age=patient.age, is_active=patient.is_active,
        created_at=patient.created_at,
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
