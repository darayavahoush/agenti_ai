from pydantic import BaseModel
from typing import Optional
from uuid import UUID

# Manual acoustic session
class SessionCreate(BaseModel):
    patient_id: UUID

    f0_mean: float
    mpt: float
    jitter: float
    shimmer: float
    hnr: float

    trs_score: int


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
    feedback: Optional[str] = None
    stars: Optional[int] = None

    class Config:
        from_attributes = True