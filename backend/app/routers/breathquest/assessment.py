"""
routers/breathquest/assessment.py — kid-authenticated wrapper around the
Assessment flow (frontend/src/assessment/Assessment.jsx).

Assessment.jsx normally gates itself behind its own name+DOB
login/patient-details screens (POST /patients/, POST /patients/login) --
that made sense when it was a standalone tool, but a kid who already has a
BreathQuest account (JWT via get_current_patient) shouldn't have to enter
their name and birthdate a second time. These two endpoints let
pages/kid/AssessmentGate.jsx bootstrap that same underlying Assessment
`Patient` row using the kid's own identity, then pass the result straight
into Assessment.jsx as authedPatientId/authedPatientName props.

Deliberately sync (SessionLocal, not AsyncSession) for the Patient-table
work, matching assessment_lookup.py's own note on why the Assessment side
of this codebase stays sync.
"""

from fastapi import APIRouter, Depends

from app.database import get_db, SessionLocal
from app.models.breathquest_models import BreathQuestPatient
from app.models.patient import Patient
from app.breathquest_core.deps import get_current_patient
from app.schemas.breathquest_schemas import AssessmentStartOut, AssessmentCompleteRequest
from app.routers.breathquest.assessment_lookup import get_latest_assessment
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

router = APIRouter(prefix="/assessment", tags=["assessment"])


@router.post("/start", response_model=AssessmentStartOut)
async def start_assessment(
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Auto-links or creates the Assessment-side Patient row for the
    logged-in kid, and returns what AssessmentGate.jsx needs to render
    Assessment.jsx in authed mode."""
    sync_db = SessionLocal()
    try:
        main_patient = None
        if patient.assessment_patient_id:
            main_patient = sync_db.get(Patient, patient.assessment_patient_id)

        if not main_patient or not main_patient.is_active:
            main_patient = Patient(name=patient.first_name)
            sync_db.add(main_patient)
            sync_db.commit()
            sync_db.refresh(main_patient)
    finally:
        sync_db.close()

    if patient.assessment_patient_id != main_patient.id:
        # Newly created (or re-linked) -- persist the link on the async
        # session get_current_patient already resolved `patient` through.
        patient.assessment_patient_id = main_patient.id
        db.add(patient)
        await db.commit()

    return AssessmentStartOut(
        assessment_patient_id=str(main_patient.id),
        first_name=patient.first_name,
        already_completed=patient.assessment_completed,
    )


@router.post("/complete", status_code=204)
async def complete_assessment(
    data: AssessmentCompleteRequest,
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Marks the logged-in kid's assessment_completed flag and stores a
    lightweight summary (word count + severity read) for
    AssessmentReport.jsx's free teaser."""
    from sqlalchemy import select

    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == patient.id))
    row = result.scalar_one()
    row.assessment_completed = True
    row.assessment_summary = {
        "words_attempted": data.words_attempted,
        "severity_classification": data.severity_classification,
    }
    await db.commit()


@router.get("/me/latest")
async def get_my_latest_assessment(
    patient: BreathQuestPatient = Depends(get_current_patient),
):
    """Kid-authenticated 'my latest results' lookup, for
    pages/kid/AssessmentReport.jsx when revisited later (not just right
    after finishing an assessment via router state). Same in-process query
    dashboard.py already uses, just exposed to the kid themselves."""
    if not patient.assessment_patient_id:
        return None
    return await asyncio.to_thread(get_latest_assessment, str(patient.assessment_patient_id))
