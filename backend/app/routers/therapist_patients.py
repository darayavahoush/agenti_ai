"""
routers/therapist_patients.py -- Therapist-scoped patient CRUD: the one
real patient-creation entry point (2026-08-10), replacing the retired,
unauthenticated /patients/ routes in main.py (see its 2026-08-07 disable
comments). POST sets registered_therapist_id from the authenticated
therapist directly. Deliberately does NOT touch GET /assessment/patients
(service-key protected, for service-to-service calls, not browser JS).

This patient_id is meant to be the one true origin, flowing into
BreathQuest via the existing kid-pin-setup linking flow rather than
AddPatientModal.jsx creating a second, disconnected patient there.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.patient import Patient
from app.models.therapist import Therapist
from app.deps.therapist_auth_deps import get_current_therapist

from app.schemas.patient import PatientCreate, PatientOut

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientOut, status_code=201)
async def create_patient(
    data: PatientCreate,
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    """The one real patient-creation entry point (see the 2026-08-10 branch
    note): sets registered_therapist_id from the authenticated therapist
    directly, rather than relying on the free-text therapist_name field or
    a downstream fix. This patient_id is meant to flow into BreathQuest via
    the existing kid-pin-setup linking flow, not get duplicated there."""
    patient = Patient(
        name=data.name, age=data.age, date_of_birth=data.date_of_birth,
        language=data.language, gender=data.gender, diagnosis=data.diagnosis,
        therapist_name=data.therapist_name, parent_name=data.parent_name,
        parent_contact=data.parent_contact, email=data.email,
        registered_therapist_id=therapist.id,
    )
    db.add(patient)
    await db.flush()
    return patient


@router.get("", response_model=list[PatientOut])
async def list_my_patients(
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Patient).where(Patient.registered_therapist_id == therapist.id)
    )
    return result.scalars().all()


@router.get("/{patient_id}", response_model=PatientOut)
async def get_my_patient(
    patient_id: str,
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    """Scoped GET for Assessment.jsx's loadPatientDetails() -- distinct from
    the service-key-protected GET /assessment/patients/{id} in routes/
    assessment.py, which is for service-to-service calls, not browser JS."""
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, Patient.registered_therapist_id == therapist.id
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
