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
from app.models import breathquest_models
from app.models import retraining_models  # noqa: F401 -- import registers RLTrainingEvent/RetrainCheckpoint with Base before create_all
from app.models import vaakmirror_models
from app.models import therapist as therapist_model  # noqa: F401 -- import registers Therapist with Base before create_all
from app.routers.therapist_auth import router as therapist_auth_router
from app.routers.therapist_patients import router as therapist_patients_router
from app.routes.assessment import router as assessment_router
from app.routers.breathquest import auth as breathquest_auth_router
from app.routers.breathquest import patients as breathquest_patients_router
from app.routers.breathquest import sessions as breathquest_sessions_router
from app.routers.breathquest import dashboard as breathquest_dashboard_router
from app.routers.breathquest import breath_agent as breathquest_breath_agent_router
from app.routers.breathquest import chime as breathquest_chime_router
from app.routers.breathquest import voicehurdlerace as breathquest_voicehurdlerace_router
from app.routers.vaakmirror.sessions import router as vaakmirror_sessions_router
from app.routers.vaakmirror.dashboard import router as vaakmirror_dashboard_router
from app.routers.vaakmirror.exercises import router as vaakmirror_exercises_router

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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include assessment router for speech analysis
app.include_router(assessment_router, prefix="/assessment", tags=["Assessment"])
app.include_router(therapist_auth_router, prefix="/api/v1")
app.include_router(therapist_patients_router, prefix="/api/v1")
# Re-enabled 2026-08-12: the standalone backend (port 8001) this was
# deferring to is no longer running (confirmed via `ps`/`lsof` -- nothing
# listens on 8001), so /auth/kid-register and /auth/kid-login had no live
# implementation anywhere. Trimmed down first: this router used to also
# define /auth/register and /auth/login against the retiring
# breathquest_therapists table, which would have silently collided with
# therapist_auth_router's identical paths below (the canonical `therapists`
# table) and issued tokens get_current_therapist could never resolve.
# Only the kid-specific + Assessment-candidate endpoints remain.
app.include_router(breathquest_auth_router.router, prefix="/api/v1")
# Re-enabled 2026-08-11: rewritten against BreathQuestPatient/GameSession
# (the 2026-08-06 disable reason -- wrong model imports -- is fixed).
# get_current_therapist uses real JWT auth; the "DummyTherapist stub" note
# above was stale.
app.include_router(breathquest_patients_router.router, prefix="/api/v1/breathquest")
# Re-enabled 2026-08-12: same situation as breathquest_auth above -- was
# deferring to the standalone backend on port 8001, which isn't running.
# get_current_patient uses real JWT auth, not a stub.
app.include_router(breathquest_sessions_router.router, prefix="/api/v1")
# Re-enabled 2026-08-11: rewritten against BreathQuestPatient/GameSession/
# TherapistNote. Also fixed two scoping bugs found during rewrite:
# get_dashboard_summary queried all patients with no therapist filter, and
# get_patient_progress had no ownership check.
app.include_router(breathquest_dashboard_router.router, prefix="/api/v1")
# Added 2026-08-11: ported from quest-games as part of the backend-merge
# reversal (agenti_ai/backend absorbing quest-games's routers going
# forward). Required adding breathquest_patients.assessment_patient_id
# (see backend/app/models/breathquest_models.py) since this router's
# get_diagnostic_context() call needed a real link that didn't exist yet.
app.include_router(breathquest_breath_agent_router.router, prefix="/api/v1")
# Swapped 2026-08-12: was app.routers.voiceHurdleRace (top-level, capital
# H) -- a stale, unauthenticated implementation still requiring patient_id
# in the request body and missing GET /sessions ("my sessions") entirely,
# which the current frontend (voiceHurdleRaceApi.ts, rewritten to send the
# bearer token instead of patient_id) can't work with at all. This is the
# breathquest-native version instead: token-authenticated via
# get_current_patient, built on BreathQuestPatient/GameSession like every
# other game router here, and has the /agent/decide endpoint the old one
# never had. Its imports needed the same app.* rewrite chime.py got.
app.include_router(breathquest_voicehurdlerace_router.router, prefix="/api/v1", tags=["VoiceHurdleRace"])

# Added 2026-08-12: chime.py's imports were still the standalone quest-games
# layout (bare `database`/`models.models`/`core.deps` instead of `app.*`)
# and would have raised ModuleNotFoundError on import -- never actually
# mountable before now. Rewritten to match sessions.py/patients.py's pattern
# (BreathQuestPatient instead of the wrong Patient model) and mounted here
# for the first time.
app.include_router(breathquest_chime_router.router, prefix="/api/v1")

# Include VaakMirror routers
app.include_router(vaakmirror_sessions_router, prefix="/api/v1/vaakmirror")
app.include_router(vaakmirror_dashboard_router, prefix="/api/v1/vaakmirror")
app.include_router(vaakmirror_exercises_router, prefix="/api/v1/vaakmirror")

# Ensure assets/audio directory exists
AUDIO_DIR = Path("assets/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

# No Alembic in this project yet — create_all() only creates missing
# tables, it does NOT alter existing ones. This is a stopgap: safe,
# idempotent ADD COLUMN IF NOT EXISTS for columns added after the
# sessions table already existed in a deployed DB. A real migration
# tool (Alembic) is the correct long-term fix, not a replacement for
# this pattern scaling indefinitely.
def _ensure_patient_therapist_link_column():
    """One-time ADD COLUMN for registered_therapist_id -- patients table
    already existed before this column was added to the model (0 rows as
    of this migration, so purely additive, no backfill needed)."""
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE patients ADD COLUMN IF NOT EXISTS registered_therapist_id UUID"
        ))

_ensure_patient_therapist_link_column()

def _ensure_therapist_last_login_column():
    """One-time ADD COLUMN for last_login -- added 2026-08-11 as part of
    collapsing quest-games' separate Therapist table into this one,
    canonical Assessment-native Therapist (see models/therapist.py)."""
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE therapists ADD COLUMN IF NOT EXISTS last_login TIMESTAMP"
        ))

_ensure_therapist_last_login_column()

def _ensure_session_diagnostic_columns():
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS severity_classification VARCHAR"
        ))
        conn.execute(text(
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS error_patterns JSONB"
        ))
        conn.execute(text(
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS targeted_quests JSONB"
        ))
        conn.execute(text(
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS diagnostic_report VARCHAR"
        ))

_ensure_session_diagnostic_columns()

@app.get("/")
def home():
    return {"message": "VaakSuddhi V1 Running"}

@app.get("/patients/dashboard/summary")
def dashboard_summary():
    raise HTTPException(status_code=410, detail="Retired 2026-08-07: unauthenticated, superseded by standalone breathquest backend (port 8001) / assessment.py. See merge notes.")
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
    raise HTTPException(status_code=410, detail="Retired 2026-08-07: unauthenticated, superseded by standalone breathquest backend (port 8001) / assessment.py. See merge notes.")
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
    raise HTTPException(status_code=410, detail="Retired 2026-08-07: unauthenticated, superseded by standalone breathquest backend (port 8001) / assessment.py. See merge notes.")
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
    raise HTTPException(status_code=410, detail="Retired 2026-08-07: unauthenticated, superseded by standalone breathquest backend (port 8001) / assessment.py. See merge notes.")
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
    raise HTTPException(status_code=410, detail="Retired 2026-08-07: unauthenticated, superseded by standalone breathquest backend (port 8001) / assessment.py. See merge notes.")
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
