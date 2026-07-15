from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

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
# Dashboard Summary
# -----------------------------------
@router.get("/dashboard/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db)
):
    patients = db.query(Patient).all()
    patient_ids = [p.id for p in patients]
    
    # Get overall sessions and accuracy
    overall_stats = db.query(
        func.count(SessionModel.id).label("total_sessions"),
        func.avg(SessionModel.accuracy).label("avg_accuracy"),
        func.avg(SessionModel.stars).label("avg_stars"),
    ).filter(
        SessionModel.patient_id.in_(patient_ids)
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
        
        patient_details.append({
            "id": str(p.id),
            "name": p.name,
            "age": p.age,
            "is_active": p.is_active,
            "created_at": p.created_at,
            "diagnosis": p.diagnosis,
            "total_sessions": stats.total or 0,
            "total_stars": int(stats.stars or 0),
            "last_session_at": stats.last,
            "avg_accuracy": float(stats.avg_accuracy) if stats.avg_accuracy else None
        })
    
    return {
        "total_patients": len(patients),
        "total_sessions": overall_stats.total_sessions or 0,
        "avg_accuracy": round(float(overall_stats.avg_accuracy), 2) if overall_stats.avg_accuracy else None,
        "avg_stars": round(float(overall_stats.avg_stars), 2) if overall_stats.avg_stars else None,
        "patients": patient_details
    }

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