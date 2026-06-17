from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.patient import Patient
from app.models.session import Session as SessionModel
from app.schemas.patient import PatientCreate, PatientOut
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
# Create Patient
# -----------------------------------
@router.post("/", response_model=PatientOut)
def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db)
):
    patient = Patient(
        name=data.name,
        age=data.age,
        language=data.language,
        gender=data.gender,
        diagnosis=data.diagnosis,
        therapist_name=data.therapist_name,
        parent_contact=data.parent_contact
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient

# -----------------------------------
# Get All Patients
# -----------------------------------
@router.get("/", response_model=List[PatientOut])
def get_all_patients(
    db: Session = Depends(get_db)
):
    return db.query(Patient).order_by(Patient.created_at.desc()).all()

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