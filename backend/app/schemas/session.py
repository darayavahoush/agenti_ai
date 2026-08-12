from pydantic import BaseModel
from typing import Optional
from uuid import UUID

# Manual acoustic session
class SessionCreate(BaseModel):
    patient_id: UUID
    target_word: str
    spoken_word: Optional[str] = None
    accuracy: Optional[int] = None
    phoneme_accuracy: Optional[float] = None
    feedback: Optional[str] = None
    stars: Optional[int] = None
    duration: Optional[float] = None
    loudness: Optional[float] = None
    pitch: Optional[float] = None
    session_type: Optional[str] = "word_practice"


# AI Speech Therapy Request
class SpeechTherapyCreate(BaseModel):
    patient_id: Optional[UUID] = None
    target_word: str


# Session Output
class SessionOut(BaseModel):
    id: UUID
    patient_id: UUID
    target_word: Optional[str] = None
    spoken_word: Optional[str] = None
    accuracy: Optional[int] = None
    phoneme_accuracy: Optional[float] = None
    feedback: Optional[str] = None
    stars: Optional[int] = None
    duration: Optional[float] = None
    loudness: Optional[float] = None
    pitch: Optional[float] = None
    session_type: Optional[str] = None

    class Config:
        from_attributes = True