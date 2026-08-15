from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class PhonemeMatch(BaseModel):
    expected: str
    detected: Optional[str]
    correct: bool

class AcousticMetrics(BaseModel):
    loudness_rms: float
    loudness_db: float
    loudness_in_range: bool
    loudness_score: float
    pitch_mean_hz: float
    pitch_std_hz: float
    pitch_variation: str
    pitch_score: float
    speaking_rate: float
    speaking_rate_rating: str
    rate_score: float
    jitter_percent: float
    shimmer_percent: float
    hnr_db: float
    voice_quality_score: float
    f1_hz: Optional[float]
    f2_hz: Optional[float]

class PhonemeScores(BaseModel):
    matches: List[PhonemeMatch]
    accuracy: float
    error_types: List[str]

class AttemptResult(BaseModel):
    attempt_id: str = str(uuid.uuid4())
    session_id: str
    child_id: Optional[str]
    timestamp: datetime = datetime.now()
    target_word: str
    target_phonemes: List[str]
    transcript: str
    detected_phonemes: List[str]
    phoneme_scores: PhonemeScores
    acoustic: AcousticMetrics
    composite_score: float
    repeat_needed: bool
    attempt_number: int
    feedback: str
    condition: str = "autism"
