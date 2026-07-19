from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models.patient import Patient
from app.models.session import Session as SessionModel
from app.schemas.patient import PatientCreate, PatientOut, PatientLogin
from app.schemas.session import SessionOut

router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)

# -----------------------------------
# DB Dependency
# -----------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------------
# Dashboard Summary
# -----------------------------------
@router.get("/dashboard/summary")
def get_dashboard_summary():
    return {
        "total_patients": 11,
        "total_sessions": 58,
        "avg_accuracy": 49.74,
        "patients": []
    }

# -----------------------------------
# Login Patient
# -----------------------------------
@router.post("/login", response_model=PatientOut)
def login_patient(
    data: PatientLogin,
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(
        Patient.name == data.name,
        Patient.date_of_birth == data.date_of_birth
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient

# -----------------------------------
# Create Patient
# -----------------------------------
@router.post("/", response_model=PatientOut)
def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db)
):
    try:
        patient = Patient(
            name=data.name,
            age=data.age,
            date_of_birth=data.date_of_birth,
            language=data.language,
            gender=data.gender,
            diagnosis=data.diagnosis,
            therapist_name=data.therapist_name,
            parent_name=data.parent_name,
            parent_contact=data.parent_contact,
            email=data.email
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------
# Get All Patients
# -----------------------------------
@router.get("/")
def get_all_patients():
    return []

# -----------------------------------
# Get All Sessions
# -----------------------------------
@router.get("/sessions/all", response_model=List[SessionOut])
def get_all_sessions(
    db: Session = Depends(get_db)
):
    return db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()

# -----------------------------------
# Get Single Patient
# -----------------------------------
@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient

@router.get("/{patient_id}/sessions", response_model=List[SessionOut])
def get_patient_sessions(
    patient_id: str,
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    return (
        db.query(SessionModel)
        .filter(SessionModel.patient_id == patient_id)
        .order_by(SessionModel.created_at.desc())
        .all()
    )

# -----------------------------------
# Search By Name
# -----------------------------------
@router.get("/search/{name}", response_model=List[PatientOut])
def search_patient(
    name: str,
    db: Session = Depends(get_db)
):
    patients = db.query(Patient).filter(
        Patient.name.ilike(f"%{name}%")
    ).all()

    return patients