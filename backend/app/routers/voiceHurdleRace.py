from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models.patient import Patient
from app.models.session import Session as SessionModel

router = APIRouter()

class VoiceHurdleRaceSessionCreate(BaseModel):
    patient_id: str
    level_id: int
    level_name: str
    score: int
    time_remaining: float
    pitch_accuracy: float
    loudness_accuracy: float
    stars: int

class VoiceHurdleRaceSessionResponse(BaseModel):
    id: str
    patient_id: str
    target_word: str
    spoken_word: str
    accuracy: int
    stars: int
    pitch: float
    loudness: float
    duration: float
    session_type: str
    created_at: str

def resolve_patient_id(patient_id: str, db: Session) -> Optional[Patient]:
    """
    Checks if patient_id belongs to a BreathQuestPatient.
    If so, resolves the corresponding Patient in the main table by matching player_code or name.
    If not, queries the Patient table directly.
    """
    from app.models.breathquest_models import BreathQuestPatient
    from sqlalchemy import func
    
    # Try finding in BreathQuestPatient table
    bq_patient = db.query(BreathQuestPatient).filter(BreathQuestPatient.id == patient_id).first()
    if bq_patient:
        # Loop through active patients to find one matching the generated player_code
        for p in db.query(Patient).filter(Patient.is_active == True).all():
            p_code = f"P{str(p.id).replace('-', '')[:9].upper()}"
            if p_code == bq_patient.player_code:
                return p
        # Fallback to name match
        return db.query(Patient).filter(
            func.lower(Patient.name) == func.lower(bq_patient.first_name)
        ).first()
        
    return db.query(Patient).filter(Patient.id == patient_id).first()

@router.post("/voicehurdlerace/sessions", response_model=VoiceHurdleRaceSessionResponse)
def create_voice_hurdle_race_session(
    session_data: VoiceHurdleRaceSessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new VoiceHurdleRace game session"""
    # Verify patient exists (resolving BreathQuestPatient ID if needed)
    patient = resolve_patient_id(session_data.patient_id, db)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Calculate overall accuracy
    overall_accuracy = int((session_data.pitch_accuracy + session_data.loudness_accuracy) / 2)
    
    # Calculate duration (total time - remaining time)
    duration = 45.0 - session_data.time_remaining
    
    # Create session with main Patient ID
    session = SessionModel(
        patient_id=str(patient.id),
        target_word=session_data.level_name,
        spoken_word=f"Level {session_data.level_id}",
        accuracy=overall_accuracy,
        stars=session_data.stars,
        pitch=session_data.pitch_accuracy,
        loudness=session_data.loudness_accuracy,
        duration=duration,
        session_type="voice_hurdle_race"
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return VoiceHurdleRaceSessionResponse(
        id=str(session.id),
        patient_id=str(session.patient_id),
        target_word=session.target_word,
        spoken_word=session.spoken_word,
        accuracy=session.accuracy,
        stars=session.stars,
        pitch=session.pitch,
        loudness=session.loudness,
        duration=session.duration,
        session_type=session.session_type,
        created_at=session.created_at.isoformat()
    )

@router.get("/voicehurdlerace/patients/{patient_id}/sessions")
def get_voice_hurdle_race_sessions(patient_id: str, db: Session = Depends(get_db)):
    """Get all VoiceHurdleRace sessions for a patient"""
    # Verify patient exists (resolving BreathQuestPatient ID if needed)
    patient = resolve_patient_id(patient_id, db)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    sessions = db.query(SessionModel).filter(
        SessionModel.patient_id == str(patient.id),
        SessionModel.session_type == "voice_hurdle_race"
    ).order_by(SessionModel.created_at.desc()).all()
    
    return [
        {
            "id": str(s.id),
            "patient_id": str(s.patient_id),
            "target_word": s.target_word,
            "spoken_word": s.spoken_word,
            "accuracy": s.accuracy,
            "stars": s.stars,
            "pitch": s.pitch,
            "loudness": s.loudness,
            "duration": s.duration,
            "session_type": s.session_type,
            "created_at": s.created_at.isoformat()
        }
        for s in sessions
    ]

@router.get("/voicehurdlerace/leaderboard")
def get_voice_hurdle_race_leaderboard(db: Session = Depends(get_db)):
    """Get leaderboard for VoiceHurdleRace"""
    sessions = db.query(SessionModel).filter(
        SessionModel.session_type == "voice_hurdle_race"
    ).order_by(SessionModel.stars.desc(), SessionModel.accuracy.desc()).limit(10).all()
    
    # Get patient names
    result = []
    for session in sessions:
        patient = db.query(Patient).filter(Patient.id == session.patient_id).first()
        result.append({
            "session_id": str(session.id),
            "patient_name": patient.name if patient else "Unknown",
            "target_word": session.target_word,
            "stars": session.stars,
            "accuracy": session.accuracy,
            "created_at": session.created_at.isoformat()
        })
    
    return result
