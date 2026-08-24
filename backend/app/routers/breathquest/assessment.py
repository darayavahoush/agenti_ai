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

from datetime import datetime, timedelta, timezone

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

RETAKE_COOLDOWN_DAYS = 30


def _retake_available_at(patient: BreathQuestPatient) -> datetime | None:
    """None if this kid has never completed an assessment. Otherwise the
    timestamp their retake cooldown lifts -- assessment_completed_at (set
    by /assessment/complete) plus RETAKE_COOLDOWN_DAYS. Legacy rows
    completed before assessment_completed_at existed have no value to
    compute from; treat those as eligible immediately (datetime.min)
    rather than blocking a retake on data we simply don't have."""
    if not patient.assessment_completed:
        return None
    if patient.assessment_completed_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return patient.assessment_completed_at + timedelta(days=RETAKE_COOLDOWN_DAYS)


@router.post("/start", response_model=AssessmentStartOut)
async def start_assessment(
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Auto-links or creates the Assessment-side Patient row for the
    logged-in kid, and returns what AssessmentGate.jsx needs to render
    Assessment.jsx in authed mode.

    already_completed here means "still on cooldown", not just "has ever
    completed one" -- a kid past their cooldown gets already_completed=
    False so AssessmentGate.jsx renders Assessment.jsx fresh, same as a
    first-timer. assessment_completed itself never resets; only the
    computed cooldown gates a retake."""
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

    retake_at = _retake_available_at(patient)
    still_on_cooldown = retake_at is not None and retake_at > datetime.now(timezone.utc)

    return AssessmentStartOut(
        assessment_patient_id=str(main_patient.id),
        first_name=patient.first_name,
        already_completed=still_on_cooldown,
        retake_available_at=retake_at if still_on_cooldown else None,
    )


@router.post("/complete", status_code=204)
async def complete_assessment(
    data: AssessmentCompleteRequest,
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Marks the logged-in kid's assessment_completed flag and stores a
    lightweight summary (word count + severity read) for
    AssessmentReport.jsx's free teaser. Also stamps
    assessment_completed_at -- every completion (first time or a later
    retake) restarts the RETAKE_COOLDOWN_DAYS clock from here."""
    from sqlalchemy import select

    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == patient.id))
    row = result.scalar_one()
    row.assessment_completed = True
    row.assessment_completed_at = datetime.now(timezone.utc)
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
    dashboard.py already uses, just exposed to the kid themselves. Also
    carries retake_available_at so the report page can show a retake
    button (or a "come back on <date>" note) without a second request."""
    if not patient.assessment_patient_id:
        return None
    result = await asyncio.to_thread(get_latest_assessment, str(patient.assessment_patient_id))
    if result is None:
        return None
    retake_at = _retake_available_at(patient)
    still_on_cooldown = retake_at is not None and retake_at > datetime.now(timezone.utc)
    result["retake_available_at"] = retake_at.isoformat() if still_on_cooldown else None
    return result
