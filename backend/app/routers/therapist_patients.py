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

dashboard_summary/list_my_sessions added 2026-08-13: main.py's
/patients/dashboard/summary and /patients/sessions/all were retired
2026-08-07 (unauthenticated) with no live replacement mounted at the
/api/v1 prefix Dashboard.jsx/Progress.jsx actually call -- a real 404,
not just the intentional 410 those retired stubs raise at their own
unprefixed path. There was also an orphaned, never-mounted
app/routes/patient.py with the same routes; its dashboard_summary
returned hardcoded fake numbers (total_patients: 11, etc.), not a real
query, so it wasn't a usable reference either. These versions are real
queries, scoped to the calling therapist's own patients only.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.patient import Patient
from app.models.therapist import Therapist
from app.models.session import Session as SessionModel
from app.deps.therapist_auth_deps import get_current_therapist

from app.schemas.patient import PatientCreate, PatientOut
from app.schemas.session import SessionOut

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/dashboard/summary")
async def dashboard_summary(
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    patient_ids_result = await db.execute(
        select(Patient.id).where(Patient.registered_therapist_id == therapist.id)
    )
    patient_ids = [row[0] for row in patient_ids_result.all()]

    if not patient_ids:
        return {"total_patients": 0, "total_sessions": 0, "avg_accuracy": None}

    total_sessions = (
        await db.execute(
            select(func.count(SessionModel.id)).where(SessionModel.patient_id.in_(patient_ids))
        )
    ).scalar() or 0

    avg_accuracy = (
        await db.execute(
            select(func.avg(SessionModel.accuracy)).where(SessionModel.patient_id.in_(patient_ids))
        )
    ).scalar()

    return {
        "total_patients": len(patient_ids),
        "total_sessions": total_sessions,
        "avg_accuracy": round(float(avg_accuracy), 2) if avg_accuracy is not None else None,
    }


@router.get("/sessions/all", response_model=list[SessionOut])
async def list_my_sessions(
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    patient_ids_result = await db.execute(
        select(Patient.id).where(Patient.registered_therapist_id == therapist.id)
    )
    patient_ids = [row[0] for row in patient_ids_result.all()]
    if not patient_ids:
        return []

    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.patient_id.in_(patient_ids))
        .order_by(SessionModel.created_at.desc())
    )
    return result.scalars().all()


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
