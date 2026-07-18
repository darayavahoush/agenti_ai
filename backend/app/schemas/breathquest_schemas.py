"""
schemas/breathquest_schemas.py — Pydantic v1 request/response models for BreathQuest.
"""

from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, EmailStr, validator
import re


# ------------------------------------------------------------------ #
#  Auth                                                                #
# ------------------------------------------------------------------ #

class TherapistRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    clinic_name: Optional[str] = None

    @validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TherapistLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    therapist_id: str
    full_name: str


class KidRegisterRequest(BaseModel):
    first_name: str
    avatar: str = "chick"
    pin: str

    @validator("pin")
    def pin_format(cls, v):
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @validator("avatar")
    def avatar_valid(cls, v):
        valid = {"chick", "dragon", "cloud", "star", "rocket", "fish"}
        if v not in valid:
            raise ValueError(f"Avatar must be one of {valid}")
        return v


class KidLoginRequest(BaseModel):
    # This field remains named player_code for API compatibility. The login
    # endpoint also accepts the child's registered first name as its value.
    player_code: str
    pin: str

    @validator("player_code")
    def login_identifier_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter your name or player code")
        return v

    @validator("pin")
    def pin_format(cls, v):
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class KidTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    patient_id: str
    first_name: str
    avatar: str
    player_code: str


# ------------------------------------------------------------------ #
#  Therapist                                                           #
# ------------------------------------------------------------------ #

class TherapistOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    email: str
    full_name: str
    clinic_name: Optional[str]
    is_active: bool
    created_at: datetime


# ------------------------------------------------------------------ #
#  Patient                                                             #
# ------------------------------------------------------------------ #

class PatientCreate(BaseModel):
    first_name: str
    avatar: str = "chick"
    pin: str
    age: Optional[int] = None
    diagnosis_notes: Optional[str] = None

    @validator("pin")
    def pin_format(cls, v):
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @validator("avatar")
    def avatar_valid(cls, v):
        valid = {"chick", "dragon", "cloud", "star", "rocket", "fish"}
        if v not in valid:
            raise ValueError(f"Avatar must be one of {valid}")
        return v


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    avatar: Optional[str] = None
    age: Optional[int] = None
    diagnosis_notes: Optional[str] = None
    is_active: Optional[bool] = None


class PatientOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    first_name: str
    avatar: str
    age: Optional[int]
    is_active: bool
    created_at: datetime
    # Note: diagnosis_notes and pin_hash are NOT exposed here (therapist-only)


class PatientDetailOut(PatientOut):
    """Extended view for therapist dashboard."""
    diagnosis_notes: Optional[str]
    total_sessions: int = 0
    total_stars: int = 0
    last_session_at: Optional[datetime] = None


# ------------------------------------------------------------------ #
#  Session                                                             #
# ------------------------------------------------------------------ #

class SessionStart(BaseModel):
    level_id: str

    @validator("level_id")
    def valid_level(cls, v):
        valid = {"pinwheel", "float_rider", "candle", "balloon", "dandelion", "dragon"}
        if v not in valid:
            raise ValueError(f"Invalid level_id. Must be one of {valid}")
        return v


class SessionEnd(BaseModel):
    stars_earned: int
    completed: bool
    completion_message: Optional[str] = None
    avg_breath_strength: Optional[float] = None
    max_breath_strength: Optional[float] = None
    breath_consistency: Optional[float] = None
    total_puffs: Optional[int] = None
    lives_lost: Optional[int] = None


class SessionEventCreate(BaseModel):
    event_type: str
    breath_value: Optional[float] = None
    event_data: Optional[dict[str, Any]] = None


class SessionEventBatch(BaseModel):
    """Send multiple events at once to reduce API calls during gameplay."""
    events: List[SessionEventCreate]


class SessionOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    patient_id: str
    level_id: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: Optional[float]
    status: str
    stars_earned: Optional[int]
    completed: bool
    avg_breath_strength: Optional[float]
    max_breath_strength: Optional[float]
    breath_consistency: Optional[float]
    total_puffs: Optional[int]
    lives_lost: Optional[int]


# ------------------------------------------------------------------ #
#  Notes                                                               #
# ------------------------------------------------------------------ #

class NoteCreate(BaseModel):
    content: str
    session_id: Optional[str] = None
    tags: Optional[List[str]] = None


class NoteUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class NoteOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    patient_id: str
    therapist_id: str
    session_id: Optional[str]
    content: str
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------ #
#  Dashboard / Analytics                                               #
# ------------------------------------------------------------------ #

class LevelProgress(BaseModel):
    level_id: str
    level_name: str
    attempts: int
    best_stars: int
    avg_stars: float
    avg_breath_strength: Optional[float]
    last_played: datetime | None


class PatientProgress(BaseModel):
    patient_id: str
    first_name: str
    avatar: str
    total_sessions: int
    total_stars: int
    max_possible_stars: int
    completion_rate: float           # 0-1
    avg_breath_strength: Optional[float]
    improvement_trend: Optional[float]  # positive = improving
    level_progress: List[LevelProgress]
    recent_sessions: List[SessionOut]


class DashboardSummary(BaseModel):
    total_patients: int
    active_patients: int
    sessions_this_week: int
    avg_stars_this_week: Optional[float]
    most_improved_patient: Optional[str]
    patients: List[PatientDetailOut]
