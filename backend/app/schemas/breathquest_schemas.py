"""
schemas/breathquest_schemas.py — Pydantic v1 request/response models for BreathQuest.
"""

from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID
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
    """Self-serve signup — a brand-new kid with no prior Assessment record.
    Repurposed 2026-08-12: this used to require patient_id (an existing
    Assessment patient to link), but frontend/src/context/AuthContext.jsx's
    registerKid() has only ever sent {first_name, avatar, pin} — patient_id
    was never in that payload, so every call here 422'd. That
    link-an-existing-patient shape moved to KidPinSetupRequest below,
    matching what the frontend's separate setupKidPin() actually sends.

    parent_email added 2026-08-12 for COPPA -- this is the only kid-account
    creation path with no adult already in the loop, so it's the one that
    needs verifiable parental consent (see breathquest_core/parental_consent.py).
    The email must already have a recently-confirmed code from POST
    /verify/confirm before this endpoint will accept it.

    parent_phone added 2026-08-12: phone is a second required factor
    alongside email (not an alternative -- both must be independently
    verified), same recently-confirmed-code requirement via
    POST /verify/phone/confirm."""
    first_name: str
    avatar: str = "chick"
    pin: str
    parent_email: EmailStr
    parent_phone: str

    @validator("parent_phone")
    def parent_phone_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter a parent's phone number")
        return v

    @validator("first_name")
    def first_name_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter a name")
        return v

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


class KidPinSetupRequest(BaseModel):
    """Link a BreathQuest PIN to a child already created in Assessment
    (via POST /patients/). This is the old KidRegisterRequest shape --
    kept as its own class since kid-pin-setup and kid-register are now
    two genuinely different flows, not one dual-purpose endpoint."""
    patient_id: UUID
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
    avatar_photo_url: str | None = None
    player_code: str
    assessment_completed: bool = False


# ------------------------------------------------------------------ #
#  Assessment (kid-authenticated wrapper)                             #
# ------------------------------------------------------------------ #

class AssessmentStartOut(BaseModel):
    """What AssessmentGate.jsx needs to render Assessment.jsx in authed
    mode: the Assessment-side patient id/name to pass down as
    authedPatientId/authedPatientName, skipping Assessment.jsx's own
    name+DOB gate entirely."""
    assessment_patient_id: str
    first_name: str
    already_completed: bool


class AssessmentCompleteRequest(BaseModel):
    words_attempted: int = 0
    severity_classification: Optional[str] = None


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
    avatar_photo_url: Optional[str] = None
    player_code: str
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
    # True when this patient has a linked Assessment intake record
    # (assessment_patient_id is set -- see routers/breathquest/patients.py's
    # atomic create) but total_sessions across every BreathQuest surface
    # (Chime, VoiceHurdleRace, VaakMirror, GameSession) is still zero.
    # Distinct from the `alerts` endpoint's flags: those describe a patient
    # who's playing but showing concerning signals; this describes a
    # patient who was assessed and is ready to start but just hasn't yet --
    # an opportunity to follow up on, not a red flag.
    needs_first_session: bool = False


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


class CategoryProgress(BaseModel):
    """Normalized per-game progress row. Unlike LevelProgress (BreathQuest-
    only, stars-based), this covers all five games uniformly: category_name
    is level_name for BreathQuest/VoiceHurdleRace, sub-game for VaakMirror,
    phoneme for Flashcards. accuracy_pct meaning varies by game (see
    parent.py's get_parent_progress for the per-game formula) but is always
    0-100. stars is None for games with no stars concept (VaakMirror,
    Flashcards)."""
    category_name: str
    attempts: int
    accuracy_pct: float
    last_played: datetime | None
    stars: Optional[int] = None


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
    # Added for the quest-games dashboard merge (2026-08-12): surfaces the
    # Assessment-side diagnosis and the RL agent's current game-difficulty
    # recommendation alongside session stats. Both Optional/default-None so
    # existing callers of this schema that don't set them keep working.
    latest_assessment: Optional[dict] = None
    recommended_action: Optional[str] = None
    recommendation_message: Optional[str] = None
    recommendation_policy: Optional[str] = None


class DashboardSummary(BaseModel):
    total_patients: int
    active_patients: int
    sessions_this_week: int
    avg_stars_this_week: Optional[float]
    most_improved_patient: Optional[str]
    patients: List[PatientDetailOut]


# ------------------------------------------------------------------ #
#  Assessment-linked kid setup                                        #
# ------------------------------------------------------------------ #

class AssessmentPinSetupRequest(BaseModel):
    # id of the Assessment-side Patient record (not a BreathQuest patient_id)
    patient_id: str
    avatar: str = "chick"
    pin: str

    @validator("pin")
    def pin_format(cls, v):
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


# ------------------------------------------------------------------ #
#  Parent auth                                                         #
# ------------------------------------------------------------------ #

class ParentKidRegisterRequest(BaseModel):
    """Combined signup: a parent creates their own account AND their
    child's account in one step, with no therapist involved (therapist_id
    stays None on the resulting BreathQuestPatient, same as kid-register).
    Distinct from the existing two-step dance (kid-register, then a
    separate parent-register using the resulting player_code) -- this is
    for the parent-initiated case where they're doing both at once.

    Reuses kid-register's COPPA gate: email/phone must already be
    recently verified via POST /verify/confirm + /verify/phone/confirm
    (see check_parental_consent) before this will touch the DB. The
    parent's email/phone here ARE their login credentials AND the
    consent-check subject -- unlike kid-register where parent_email is
    only used for consent and no Parent account gets created."""
    # -- kid fields --
    first_name: str
    avatar: str = "chick"
    pin: str
    # -- parent fields --
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: str

    @validator("first_name")
    def first_name_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter your child's name")
        return v

    @validator("phone")
    def phone_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter your phone number")
        return v

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


class ParentRegisterRequest(BaseModel):
    # Exactly one of these must be provided — validated in the endpoint,
    # not here, since it needs a DB lookup either way.
    player_code: Optional[str] = None
    invite_code: Optional[str] = None
    email: str
    password: str
    full_name: Optional[str] = None
    # Collected, not verified -- see Parent.phone's comment.
    phone: Optional[str] = None


class ParentLoginRequest(BaseModel):
    email: str
    password: str


class ParentTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    parent_id: str
    patient_id: str
    child_first_name: str
    email: str
    phone: str | None = None


class ParentInviteCodeOut(BaseModel):
    invite_code: str


# ------------------------------------------------------------------ #
#  Weekly summary / sound progress (rule-based, no LLM calls)          #
# ------------------------------------------------------------------ #

class WeeklySummaryOut(BaseModel):
    patient_id: str
    week_start: datetime
    week_end: datetime
    narrative: str            # dense multi-sentence paragraph
    highlights: List[str]     # short chip-style facts for the UI
    stats: dict                # raw numbers backing the narrative, for charts


class SoundWeekPoint(BaseModel):
    week: str          # ISO week label, e.g. "2026-W28"
    week_start: datetime
    accuracy: float     # 0-1
    attempts: int


class SoundProgressOut(BaseModel):
    patient_id: str
    sounds: dict
    practiced_sound_count: int   # distinct sounds attempted at least once, all-time


class HomePracticeIdeaOut(BaseModel):
    id: int
    title: str
    description: str
    conditions: List[str]
    goals: List[str]


class GuidedActivityOut(BaseModel):
    idea: HomePracticeIdeaOut
    reason: str   # plain-language "why this one" for the parent


class ParentProgressOut(BaseModel):
    """Parent view: more than the kid sees, but no clinical notes and no
    raw per-attempt data — trend-level, not session-by-session."""
    child_first_name: str
    avatar: str
    total_sessions: int
    total_stars: int
    max_possible_stars: int
    completion_rate: float
    improvement_trend: Optional[float]
    level_progress: List[LevelProgress]   # kept for backward compat (report_pdf.py etc. — BreathQuest only)
    categories: dict[str, List[CategoryProgress]]  # {"breathquest": [...], "voicehurdlerace": [...], "vaakmirror": [...], "flashcards": [...]}
    weekly_summary: WeeklySummaryOut
    # Added to surface two things parents couldn't see before: the same
    # adaptive-difficulty "today's recommendation" therapists already get
    # (PatientProgress.recommended_action, same chime_data_store source),
    # and a breath-consistency trend (session-level only until now, never
    # aggregated for the parent view).
    recommended_action: Optional[str] = None
    recommendation_message: Optional[str] = None
    avg_breath_consistency: Optional[float] = None


class KidProgressOut(BaseModel):
    """What the child sees about themself — no scores, no clinical
    language, just concrete, encouraging counts."""
    first_name: str
    avatar: str
    total_stars: int
    max_possible_stars: int
    games_played_this_week: int
    current_streak_days: int


# ------------------------------------------------------------------ #
#  Email verification                                                  #
# ------------------------------------------------------------------ #

class VerifyRequestIn(BaseModel):
    email: EmailStr


class VerifyConfirmIn(BaseModel):
    email: EmailStr
    code: str


class VerifyConfirmOut(BaseModel):
    verified: bool
    first_time: bool


class PhoneVerifyRequestIn(BaseModel):
    phone: str

    @validator("phone")
    def phone_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter a phone number")
        return v


class PhoneVerifyConfirmIn(BaseModel):
    phone: str
    code: str


# ------------------------------------------------------------------ #
#  Assignments ("homework")                                            #
# ------------------------------------------------------------------ #

class AssignmentCreate(BaseModel):
    game: str
    level_id: Optional[str] = None
    title: str
    instructions: Optional[str] = None
    due_at: Optional[datetime] = None


class AssignmentUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    due_at: Optional[datetime] = None


class AssignmentOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    patient_id: str
    assigned_by: str
    game: str
    level_id: Optional[str]
    title: str
    instructions: Optional[str]
    status: str
    created_at: datetime
    due_at: Optional[datetime]
    completed_at: Optional[datetime]


# ------------------------------------------------------------------ #
#  Goals                                                               #
# ------------------------------------------------------------------ #

class GoalCreate(BaseModel):
    target_metric: str
    target_value: float
    baseline_value: Optional[float] = None
    target_date: Optional[datetime] = None


class GoalUpdate(BaseModel):
    target_value: Optional[float] = None
    target_date: Optional[datetime] = None
    achieved: Optional[bool] = None


class GoalOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    patient_id: str
    created_by: str
    target_metric: str
    target_value: float
    baseline_value: Optional[float]
    target_date: Optional[datetime]
    achieved: bool
    achieved_at: Optional[datetime]
    created_at: datetime
    current_value: Optional[float] = None   # populated at read time, not stored


# ------------------------------------------------------------------ #
#  Messages                                                            #
# ------------------------------------------------------------------ #

class MessageCreate(BaseModel):
    body: str
    sender_role: str = "therapist"  # therapist or parent


class MessageOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    patient_id: str
    sender_role: str
    sender_id: Optional[str]
    body: str
    created_at: datetime
    read_at: Optional[datetime]


# ------------------------------------------------------------------ #
#  Home practice log                                                   #
# ------------------------------------------------------------------ #

class HomePracticeLogCreate(BaseModel):
    practiced_on: datetime
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None


class HomePracticeLogOut(BaseModel):
    class Config:
        from_attributes = True

    id: str
    patient_id: str
    logged_at: datetime
    practiced_on: datetime
    duration_minutes: Optional[int]
    notes: Optional[str]


# ------------------------------------------------------------------ #
#  Multi-child alert view                                              #
# ------------------------------------------------------------------ #

class PatientAlert(BaseModel):
    patient_id: str
    first_name: str
    days_since_last_session: Optional[int]   # None = never played
    overdue_assignments: int
    flag: str   # "plateau" | "frustration_rising" | "inactive" | "overdue_assignment" | "ok"


# ------------------------------------------------------------------ #
#  Billing / subscription                                              #
# ------------------------------------------------------------------ #

class SubscriptionOut(BaseModel):
    plan_type: str
    status: str
    trial_ends_at: datetime
    current_period_end: Optional[datetime]
