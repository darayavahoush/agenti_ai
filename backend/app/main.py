from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import os
from pathlib import Path

from app.database import Base, engine, SessionLocal
from app.models.patient import Patient
from app.models.session import Session as SessionModel
from app.models.assessment_word import AssessmentWord
from app.routes.assessment import router as assessment_router

class PatientCreate(BaseModel):
    name: str
    age: Optional[int] = None
    date_of_birth: Optional[str] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    therapist_name: Optional[str] = None
    parent_name: Optional[str] = None
    parent_contact: Optional[str] = None
    email: Optional[str] = None

class PatientLogin(BaseModel):
    name: str
    date_of_birth: str

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include assessment router for speech analysis
app.include_router(assessment_router, prefix="/assessment", tags=["Assessment"])

# Ensure assets/audio directory exists
AUDIO_DIR = Path("assets/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "VaakSuddhi V1 Running"}

@app.get("/patients/dashboard/summary")
def dashboard_summary():
    db = SessionLocal()
    try:
        patients = db.query(Patient).all()
        total_patients = len(patients)
        total_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
        avg_accuracy = db.query(func.avg(SessionModel.accuracy)).scalar()
        
        return {
            "total_patients": total_patients,
            "total_sessions": total_sessions,
            "avg_accuracy": round(float(avg_accuracy), 2) if avg_accuracy else None,
            "patients": []
        }
    finally:
        db.close()

@app.get("/patients/")
def get_all_patients():
    db = SessionLocal()
    try:
        patients = db.query(Patient).all()
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "age": p.age,
                "date_of_birth": p.date_of_birth,
                "language": p.language,
                "gender": p.gender,
                "diagnosis": p.diagnosis,
                "therapist_name": p.therapist_name,
                "parent_name": p.parent_name,
                "parent_contact": p.parent_contact,
                "email": p.email,
                "is_active": p.is_active,
                "created_at": p.created_at,
            }
            for p in patients
        ]
    finally:
        db.close()

@app.post("/patients/")
def create_patient(data: PatientCreate):
    db = SessionLocal()
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
        return {
            "id": str(patient.id),
            "name": patient.name,
            "age": patient.age,
            "date_of_birth": patient.date_of_birth,
            "language": patient.language,
            "gender": patient.gender,
            "diagnosis": patient.diagnosis,
            "therapist_name": patient.therapist_name,
            "parent_contact": patient.parent_contact,
            "email": patient.email,
            "is_active": patient.is_active,
            "created_at": patient.created_at
        }
    finally:
        db.close()

@app.post("/patients/login")
def login_patient(data: PatientLogin):
    db = SessionLocal()
    try:
        # Search for patient by name and date of birth
        patient = db.query(Patient).filter(
            Patient.name == data.name,
            Patient.date_of_birth == data.date_of_birth
        ).first()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        return {
            "id": str(patient.id),
            "name": patient.name,
            "age": patient.age,
            "date_of_birth": patient.date_of_birth,
            "language": patient.language,
            "gender": patient.gender,
            "diagnosis": patient.diagnosis,
            "therapist_name": patient.therapist_name,
            "parent_name": patient.parent_name,
            "parent_contact": patient.parent_contact,
            "email": patient.email,
            "is_active": patient.is_active,
            "created_at": patient.created_at
        }
    finally:
        db.close()

@app.get("/patients/sessions/all")
def get_all_sessions():
    db = SessionLocal()
    try:
        sessions = db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
        return [
            {
                "id": str(s.id),
                "patient_id": str(s.patient_id),
                "target_word": s.target_word,
                "spoken_word": s.spoken_word,
                "accuracy": s.accuracy,
                "feedback": s.feedback,
                "stars": s.stars,
                "pitch": s.pitch,
                "loudness": s.loudness,
                "duration": s.duration,
                "created_at": s.created_at
            }
            for s in sessions
        ]
    finally:
        db.close()

# -----------------------------------
# Assessment Endpoints (Minimal)
# -----------------------------------
def serialize_word(item: AssessmentWord) -> dict:
    return {
        "id": item.id,
        "word": item.word,
        "image_prompt": item.image_prompt,
        "image_url": f"/assessment/words/image/{item.word}",
        "translations": {
            "english": item.english,
            "telugu": item.telugu,
            "hindi": item.hindi,
            "tamil": item.tamil,
            "kannada": item.kannada,
            "malayalam": item.malayalam,
            "bengali": item.bengali,
            "marathi": item.marathi,
        }
    }

@app.get("/assessment/words/random")
def random_word():
    db = SessionLocal()
    try:
        item = (
            db.query(AssessmentWord)
            .filter(AssessmentWord.is_active.is_(True))
            .order_by(func.random())
            .first()
        )
        if not item:
            return {"error": "No words available"}
        return serialize_word(item)
    finally:
        db.close()

@app.get("/assessment/words/image/{word}")
def get_word_image(word: str):
    # Simple fallback - check data/images directory
    data_dir = Path(__file__).parent.parent.parent / "data" / "images"
    image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
    
    for ext in image_extensions:
        image_path = data_dir / f"{word}{ext}"
        if image_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(image_path)
    
    # Try with different casing
    for ext in image_extensions:
        image_path = data_dir / f"{word.lower()}{ext}"
        if image_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(image_path)
    
    return {"error": "Image not found"}

@app.get("/assessment/audio/{word_key}/{language}/exists")
def check_audio_exists(word_key: str, language: str):
    audio_path = AUDIO_DIR / f"{word_key}_{language}.wav"
    return {"exists": audio_path.exists()}

@app.post("/assessment/audio/{word_key}/{language}/upload")
def upload_audio(word_key: str, language: str, file: UploadFile):
    audio_path = AUDIO_DIR / f"{word_key}_{language}.wav"
    try:
        with open(audio_path, "wb") as buffer:
            buffer.write(file.file.read())
        return {"success": True, "path": str(audio_path)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/assessment/audio/{word_key}/{language}")
def get_audio(word_key: str, language: str):
    audio_path = AUDIO_DIR / f"{word_key}_{language}.wav"
    if audio_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(audio_path, media_type="audio/wav")
    else:
        return {"error": "Audio not found"}
