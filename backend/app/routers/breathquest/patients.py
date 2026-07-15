"""
routers/patients.py — Patient management (therapist-only).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models.patient import Patient
from app.models.session import Session as SessionModel
from app.schemas.breathquest_schemas import PatientCreate, PatientUpdate, PatientOut, PatientDetailOut
from app.breathquest_core.deps import get_current_therapist

router = APIRouter(prefix="/patients", tags=["patients"])

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    data: PatientCreate,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    patient = Patient(
        name=data.first_name,
        age=data.age,
        language="en",
        gender="other",
        diagnosis=data.diagnosis_notes,
        therapist_name="Therapist",
        parent_contact="",
        is_active=True
    )
    db.add(patient)
    db.flush()
    
    return PatientOut(
        id=str(patient.id),
        first_name=patient.name,
        avatar=data.avatar,
        age=patient.age,
        is_active=patient.is_active,
        created_at=patient.created_at
    )


@router.get("", response_model=list[PatientDetailOut])
def list_patients(
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()

    out = []
    for p in patients:
        # Get session stats
        stats = db.query(
            func.count(SessionModel.id).label("total"),
            func.sum(SessionModel.stars).label("stars"),
            func.avg(SessionModel.accuracy).label("avg_accuracy"),
            func.max(SessionModel.created_at).label("last"),
        ).filter(SessionModel.patient_id == p.id).first()
        out.append(PatientDetailOut(
            id=str(p.id),
            first_name=p.name,
            avatar="chick",
            age=p.age,
            is_active=p.is_active,
            created_at=p.created_at,
            diagnosis_notes=p.diagnosis,
            total_sessions=stats.total or 0,
            total_stars=int(stats.stars or 0),
            last_session_at=stats.last,
        ))
    return out


@router.get("/{patient_id}", response_model=PatientDetailOut)
def get_patient(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    stats = db.query(
        func.count(SessionModel.id).label("total"),
        func.sum(SessionModel.stars).label("stars"),
        func.avg(SessionModel.accuracy).label("avg_accuracy"),
        func.max(SessionModel.created_at).label("last"),
    ).filter(SessionModel.patient_id == patient.id).first()
    return PatientDetailOut(
        id=str(patient.id),
        first_name=patient.name,
        avatar="chick",
        age=patient.age,
        is_active=patient.is_active,
        created_at=patient.created_at,
        diagnosis_notes=patient.diagnosis,
        total_sessions=stats.total or 0,
        total_stars=int(stats.stars or 0),
        last_session_at=stats.last,
    )


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: str,
    data: PatientUpdate,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Map schema fields to model fields
    if data.first_name:
        patient.name = data.first_name
    if data.age is not None:
        patient.age = data.age
    if data.diagnosis_notes is not None:
        patient.diagnosis = data.diagnosis_notes
    if data.is_active is not None:
        patient.is_active = data.is_active

    return PatientOut(
        id=str(patient.id),
        first_name=patient.name,
        avatar="chick",
        age=patient.age,
        is_active=patient.is_active,
        created_at=patient.created_at
    )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: Session = Depends(get_sync_db),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
