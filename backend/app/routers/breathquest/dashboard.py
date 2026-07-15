"""
routers/dashboard.py — Therapist dashboard: analytics, progress, notes.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.database import SessionLocal
from app.models.patient import Patient
from app.models.session import Session as SessionModel
from app.schemas.breathquest_schemas import (
    PatientProgress, LevelProgress, DashboardSummary,
    PatientDetailOut, PatientOut, SessionOut,
    NoteCreate, NoteUpdate, NoteOut,
)
from app.breathquest_core.deps import get_current_therapist

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

LEVEL_NAMES = {
    "pinwheel":    "Pinwheel Spin",
    "float_rider": "Float Rider",
    "candle":      "Candle Gauntlet",
    "balloon":     "Balloon Pop",
    "dandelion":   "Dandelion Storm",
    "dragon":      "Dragon Fire",
}


# ------------------------------------------------------------------ #
#  Summary                                                             #
# ------------------------------------------------------------------ #

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    # All patients (using old Patient table)
    patients = db.query(Patient).all()
    patient_ids = [p.id for p in patients]

    active_count = sum(1 for p in patients if p.is_active)

    # Sessions this week (using old Session table)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    week_sessions = db.query(
        func.count(SessionModel.id).label("count"),
        func.avg(SessionModel.accuracy).label("avg_accuracy"),
        func.avg(SessionModel.stars).label("avg_stars"),
    ).filter(
        SessionModel.patient_id.in_(patient_ids),
        SessionModel.created_at >= week_ago,
    ).first()

    # Build patient detail list
    patient_details = []
    for p in patients:
        stats = db.query(
            func.count(SessionModel.id).label("total"),
            func.sum(SessionModel.stars).label("stars"),
            func.avg(SessionModel.accuracy).label("avg_accuracy"),
            func.max(SessionModel.created_at).label("last"),
        ).filter(SessionModel.patient_id == p.id).first()
        
        # Map old patient fields to expected schema
        patient_details.append(PatientDetailOut(
            id=str(p.id),
            first_name=p.name,
            avatar="chick",  # Default avatar
            age=p.age,
            is_active=p.is_active,
            created_at=p.created_at,
            diagnosis_notes=p.diagnosis,
            total_sessions=stats.total or 0,
            total_stars=int(stats.stars or 0),
            last_session_at=stats.last,
        ))

    return DashboardSummary(
        total_patients=len(patients),
        active_patients=active_count,
        sessions_this_week=week_sessions.count or 0,
        avg_stars_this_week=round(float(week_sessions.avg_stars), 2) if week_sessions.avg_stars else None,
        avg_accuracy_this_week=round(float(week_sessions.avg_accuracy), 2) if week_sessions.avg_accuracy else None,
        most_improved_patient=None,
        patients=patient_details,
    )


# ------------------------------------------------------------------ #
#  Patient progress                                                    #
# ------------------------------------------------------------------ #

@router.get("/patients/{patient_id}/progress", response_model=PatientProgress)
def get_patient_progress(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    # Get patient from old table
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get all sessions from old table
    sessions = db.query(SessionModel).filter(
        SessionModel.patient_id == patient_id
    ).order_by(SessionModel.created_at.desc()).all()

    total_stars = sum(s.stars or 0 for s in sessions)
    total_accuracy = sum(s.accuracy or 0 for s in sessions) if sessions else 0
    avg_accuracy = round(total_accuracy / len(sessions), 2) if sessions else 0

    # Per-level breakdown (simplified for old data)
    level_progress = []
    for level_id, level_name in LEVEL_NAMES.items():
        level_sessions = [s for s in sessions if s.session_type == level_id]
        if level_sessions:
            best_stars = max(s.stars or 0 for s in level_sessions)
            avg_stars = sum(s.stars or 0 for s in level_sessions) / len(level_sessions)
            accuracy_vals = [s.accuracy for s in level_sessions if s.accuracy]
            avg_accuracy_level = sum(accuracy_vals) / len(accuracy_vals) if accuracy_vals else None
            last_played = max(s.created_at for s in level_sessions)
        else:
            best_stars = 0
            avg_stars = 0.0
            avg_accuracy_level = None
            last_played = None

        level_progress.append(LevelProgress(
            level_id=level_id,
            level_name=level_name,
            attempts=len(level_sessions),
            best_stars=best_stars,
            avg_stars=round(avg_stars, 2),
            avg_breath_strength=round(avg_accuracy_level, 2) if avg_accuracy_level else None,
            last_played=last_played,
        ))

    # Improvement trend (compare last 5 vs previous 5 sessions)
    trend = None
    if len(sessions) >= 6:
        recent = [s.accuracy or 0 for s in sessions[:5]]
        older  = [s.accuracy or 0 for s in sessions[5:10]]
        trend = round((sum(recent) / len(recent)) - (sum(older) / len(older)), 2)

    return PatientProgress(
        patient_id=str(patient.id),
        first_name=patient.name,
        avatar="chick",
        total_sessions=len(sessions),
        total_stars=total_stars,
        max_possible_stars=len(LEVEL_NAMES) * 3,
        completion_rate=1.0,  # All sessions are considered complete in old system
        avg_breath_strength=avg_accuracy,
        improvement_trend=trend,
        level_progress=level_progress,
        recent_sessions=[SessionOut(
            id=str(s.id),
            patient_id=str(s.patient_id),
            level_id=s.session_type or "pinwheel",
            started_at=s.created_at,
            ended_at=s.created_at,
            duration_seconds=s.mpt or 30.0,
            status="completed",
            stars_earned=s.stars or 0,
            completed=True,
            avg_breath_strength=s.accuracy or 0,
            max_breath_strength=s.accuracy or 0,
            breath_consistency=s.hnr or 0.8,
            total_puffs=1,
            lives_lost=0
        ) for s in sessions[:10]],
    )


# ------------------------------------------------------------------ #
#  Notes                                                               #
# ------------------------------------------------------------------ #

@router.post("/patients/{patient_id}/notes", response_model=NoteOut, status_code=201)
def create_note(
    patient_id: str,
    data: NoteCreate,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Notes not implemented in old system, return placeholder
    return NoteOut(
        id="placeholder",
        patient_id=patient_id,
        therapist_id="placeholder",
        content=data.content,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@router.get("/patients/{patient_id}/notes", response_model=list[NoteOut])
def list_notes(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Notes not implemented in old system, return empty list
    return []


@router.patch("/notes/{note_id}", response_model=NoteOut)
def update_note(
    note_id: str,
    data: NoteUpdate,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    raise HTTPException(status_code=501, detail="Notes not implemented in old system")


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    raise HTTPException(status_code=501, detail="Notes not implemented in old system")
