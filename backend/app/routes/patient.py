from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.patient import Patient
from app.models.session import Session as TherapySession
from app.schemas.patient import PatientCreate

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
@router.post("/")
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
@router.get("/")
def get_all_patients(
    db: Session = Depends(get_db)
):
    return db.query(Patient).all()


@router.get("/summary")
def get_patient_summary(
    db: Session = Depends(get_db)
):
    rows = db.query(
        Patient,
        func.count(TherapySession.id).label("session_count"),
        func.avg(TherapySession.accuracy).label("average_accuracy"),
        func.max(TherapySession.created_at).label("last_session_at")
    ).outerjoin(TherapySession).group_by(Patient.id).order_by(Patient.created_at.desc()).all()

    return [
        {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "language": patient.language,
            "session_count": session_count,
            "average_accuracy": round(float(average_accuracy or 0), 1),
            "last_session_at": last_session_at,
        }
        for patient, session_count, average_accuracy, last_session_at in rows
    ]


@router.get("/stats")
def get_patient_stats(
    db: Session = Depends(get_db)
):
    patient_count = db.query(func.count(Patient.id)).scalar() or 0
    session_count = db.query(func.count(TherapySession.id)).scalar() or 0
    average_accuracy = db.query(func.avg(TherapySession.accuracy)).scalar() or 0

    return {
        "patients": patient_count,
        "sessions": session_count,
        "accuracy": round(float(average_accuracy), 1),
    }


@router.get("/progress")
def get_progress(
    db: Session = Depends(get_db)
):
    rows = db.query(
        TherapySession,
        Patient.name,
        Patient.age
    ).join(Patient).order_by(TherapySession.created_at.desc()).all()

    return [
        {
            "id": session.id,
            "patient_id": session.patient_id,
            "child_name": name,
            "child_age": age,
            "target_word": session.target_word,
            "spoken_word": session.spoken_word,
            "accuracy": session.accuracy,
            "feedback": session.feedback,
            "stars": session.stars,
            "session_type": session.session_type,
            "created_at": session.created_at,
        }
        for session, name, age in rows
    ]

# -----------------------------------
# Get Single Patient
# -----------------------------------
@router.get("/{patient_id}")
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

# -----------------------------------
# Search By Name
# -----------------------------------
@router.get("/search/{name}")
def search_patient(
    name: str,
    db: Session = Depends(get_db)
):
    patients = db.query(Patient).filter(
        Patient.name.ilike(f"%{name}%")
    ).all()

    return patients
