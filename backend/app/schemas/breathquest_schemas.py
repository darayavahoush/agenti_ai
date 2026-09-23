"""
schemas/breathquest_schemas.py — Pydantic v1 request/response models for BreathQuest.
"""

from datetime import datetime, date
from enum import Enum
from typing import Annotated, Any, Literal, Optional, List
from uuid import UUID
from pydantic import BaseModel, BeforeValidator, EmailStr, validator
import re


def _id_to_str(v):
    """UUID (and str-less Enum) values from ORM rows -> plain str.

    Pydantic v2 refuses to coerce a uuid.UUID into a `str` field, so any
    endpoint that returned a raw ORM row through an `*Out` schema declaring
    `id: str` failed response validation -- a 500 that the browser reports
    as a CORS error, because errors raised outside CORSMiddleware carry no
    Access-Control-Allow-Origin header. Notes dodged it by hand-building
    NoteOut with str(...); Assignments/Goals/Messages/HomePractice returned
    the row directly and broke on every create (and on every list once a
    row existed).
    """
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, Enum) and not isinstance(v, str):
        return str(v.value)
    return v


StrId = Annotated[str, BeforeValidator(_id_to_str)]


def _normalize_email(v):
    """strip + lowercase so `Jane@Gmail.com` and `jane@gmail.com` are
    treated as the same account everywhere -- register, login, reset
    and the verify/consent layer all go through this now instead of
    only the reset/forgot paths."""
    return v.strip().lower() if isinstance(v, str) else v


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

    parent_phone: collected but not verified. Was a second required
    consent factor alongside email (via POST /verify/phone/confirm) until
    2026-08-29, when phone consent was removed (no real SMS provider was
    ever wired up -- see breathquest_core/parental_consent.py). Same
    "collected, not verified" shape as Parent.phone/Therapist.phone
    elsewhere."""
    first_name: str
    avatar: str = "chick"
    pin: str
    parent_email: EmailStr
    parent_phone: Optional[str] = None

    @validator("parent_email")
    def normalize_parent_email(cls, v):
        return _normalize_email(v)

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
        valid = {"chick", "dragon", "bunny", "fox", "rocket", "fish"}
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
        valid = {"chick", "dragon", "bunny", "fox", "rocket", "fish"}
        if v not in valid:
            raise ValueError(f"Avatar must be one of {valid}")
        return v


class KidLoginRequest(BaseModel):
    # This field remains named player_code for API compatibility. The login
    # endpoint also accepts the child's registered first name, or the
    # parent's email on file, as its value -- see kid_login's docstring.
    player_code: str
    pin: str

    @validator("player_code")
    def login_identifier_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter your name, email, or player code")
        return v

    @validator("pin")
    def pin_format(cls, v):
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class KidTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    patient_id: str
    first_name: str
    avatar: str
    avatar_photo_url: str | None = None
    player_code: str
    assessment_completed: bool = False
    # None until the kid picks one -- the frontend shows the first-login
    # username picker whenever this comes back null.
    username: str | None = None


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
    # Set only when already_completed is True -- when the cooldown (see
    # assessment.py's RETAKE_COOLDOWN_DAYS) is still active, this is the
    # timestamp it lifts. None either means never completed, or completed
    # but already eligible to retake right now.
    retake_available_at: Optional[datetime] = None


class AssessmentCompleteRequest(BaseModel):
    words_attempted: int = 0
    severity_classification: Optional[str] = None
    # Per-word breakdown from this run (Assessment.jsx's accumulated
    # wordResults) -- stored so AssessmentReport.jsx's unlocked "detailed
    # results" view has real content on revisit too, not just right after
    # finishing (when it's available via router state instead). Untyped
    # passthrough on purpose: this mirrors /assessment/analyze's response
    # shape (target_word/spoken_word/accuracy/phoneme_matches/etc.), which
    # already lives on the Assessment side and isn't worth re-declaring
    # field-for-field here.
    word_results: list[dict] = []


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
    allow_duplicate: bool = False  # set true to add a second same-named patient under one therapist

    @validator("pin")
    def pin_format(cls, v):
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @validator("avatar")
    def avatar_valid(cls, v):
        valid = {"chick", "dragon", "bunny", "fox", "rocket", "fish"}
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
    username: Optional[str] = None
    age: Optional[int]
    is_active: bool
    created_at: datetime
    assessment_patient_id: Optional[str] = None
    archived_at: Optional[datetime] = None
    # Note: diagnosis_notes and pin_hash are NOT exposed here (therapist-only)


class LinkPatientRequest(BaseModel):
    """Therapist-initiated: attach the calling therapist to an EXISTING
    kid account (one that registered itself, or was created by a parent)
    by @username or player_code -- same dual lookup kid_login already
    supports, just from the therapist side. Renamed from a player_code-
    only field: most kids never share their player code with anyone but
    a parent, but @username is the thing they'd actually hand a
    therapist. Sets BreathQuestPatient.therapist_id; does not touch
    anything on the Assessment/Patient side."""
    identifier: str

    @validator("identifier")
    def identifier_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter the child's username or player code")
        return v


class TransferPatientRequest(BaseModel):
    """Therapist-to-therapist reassignment -- a single FK update, no
    cascade concerns (unlike parent-to-parent, which goes through
    ParentChild and is a separate, already-solved multi-child flow)."""
    new_therapist_id: UUID


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
    # True when last_seen_at (bumped on every authenticated kid request --
    # see breathquest_core/deps.py) is within PRESENCE_UPDATE_INTERVAL.
    # Distinct from is_active (account enabled/disabled) -- this is "playing
    # right now", not "allowed to play" (#69).
    is_logged_in: bool = False


class PatientExportOut(BaseModel):
    """One-shot compliance/records snapshot -- everything that hangs off
    patient_id, assembled and returned as a single JSON document rather
    than a file, so the caller (therapist-facing UI) decides whether to
    display it, download it, or hand it to a parent."""
    # Moved below PatientDetailOut (was defined above it, unquoted -- a
    # genuine pre-existing NameError on import, not something introduced
    # by this change; confirmed by reproducing it against the pinned
    # pydantic==2.13.4 + email-validator environment before touching it.
    patient: PatientDetailOut
    sessions: list["SessionOut"]
    notes: list["NoteOut"]
    assignments: list["AssignmentOut"]
    goals: list["GoalOut"]
    messages: list["MessageOut"]
    home_practice_logs: list["HomePracticeLogOut"]
    companion_unlocks: list[dict]
    exported_at: datetime


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

    id: UUID
    patient_id: UUID
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
    # "up" / "down" / "flat", or None with fewer than 2 dated data points
    # (a brand-new category shouldn't render a flat arrow).
    trend: Optional[str] = None


class HistoryEntry(BaseModel):
    """One row in a category's expanded history -- both the log line and
    the chart point come from the same entry, value is always 0-100 (or
    0-3 for BreathQuest stars) so the frontend can plot it without
    per-category special-casing."""
    date: datetime
    label: str
    value: float
    detail: Optional[str] = None


class CategoryHistoryOut(BaseModel):
    category_name: str
    entries: List[HistoryEntry]


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
    # Surfaces the account-recovery code so a therapist can read it back to
    # a parent/kid on request instead of pointing them at the pre-login
    # forgot-player-code email flow for something they could just be told.
    player_code: Optional[str] = None
    # The kid's own chosen handle (see UsernameGate/username_routes.py) --
    # the dashboard header should show this once set instead of the
    # player_code, which is really just a recovery code, not an identity.
    username: Optional[str] = None


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

    Reuses kid-register's COPPA gate: email must already be recently
    verified via POST /verify/confirm (see check_email_consent) before
    this will touch the DB. The parent's email here IS their login
    credential AND the consent-check subject -- unlike kid-register
    where parent_email is only used for consent and no Parent account
    gets created. phone is collected but not verified (see
    KidRegisterRequest.parent_phone's comment)."""
    # -- kid fields --
    first_name: str
    avatar: str = "chick"
    pin: str
    # -- parent fields --
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: str

    @validator("email")
    def normalize_email(cls, v):
        return _normalize_email(v)

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
        valid = {"chick", "dragon", "bunny", "fox", "rocket", "fish"}
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

    @validator("email")
    def normalize_email(cls, v):
        return _normalize_email(v)


class ParentLoginRequest(BaseModel):
    email: str
    password: str

    @validator("email")
    def normalize_email(cls, v):
        return _normalize_email(v)


class ParentGoogleLoginRequest(BaseModel):
    """For an already-existing Parent account (password or previously-
    linked Google) signing in with Google. See ParentGoogleRegisterRequest
    for the brand-new-account case -- split the same way parent-login/
    parent-register already are, since (unlike therapist-google) a new
    Parent can't be created from the Google token alone: it always needs
    a child to link to."""
    id_token: str


class ParentGoogleRegisterRequest(BaseModel):
    """Google equivalent of ParentRegisterRequest -- links a new parent
    account (identified by the Google token, not a password) to an
    existing child via player_code/invite_code. Deliberately does NOT
    cover ParentKidRegisterRequest's "new child, no therapist" combined
    flow, which doesn't yet have a Google-auth equivalent designed --
    follow-up, not in scope here.
    """
    player_code: Optional[str] = None
    invite_code: Optional[str] = None
    id_token: str
    # Collected, not verified -- see Parent.phone's comment.
    phone: Optional[str] = None


class ChildSummary(BaseModel):
    """One entry in a parent's child-switcher. Mirrors the handful of
    BreathQuestPatient fields the switcher UI actually needs to render an
    avatar tile -- deliberately not the full patient record (diagnosis
    notes, assessment summary, etc. have no business leaving the active
    child's own dashboard queries)."""
    patient_id: str
    first_name: str
    avatar: str
    avatar_photo_url: str | None = None
    player_code: str
    is_active: bool
    is_primary: bool
    username: str | None = None


class ParentTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    parent_id: str
    patient_id: str
    child_first_name: str
    email: str
    phone: str | None = None
    # Added 2026-09-10 for multi-child support: the full set of children
    # this parent can switch between (patient_id/child_first_name above
    # stay the CURRENTLY ACTIVE one for backward compatibility with every
    # existing caller). See ChildSummary above.
    children: list[ChildSummary] = []
    username: str | None = None


class ParentChildrenResponse(BaseModel):
    children: list[ChildSummary]


class AddChildRequest(BaseModel):
    """Creates a brand-new child profile under the already-authenticated
    parent -- the "add another child" path, as opposed to LinkChildRequest
    below (an existing child created elsewhere, e.g. by a therapist).
    Deliberately a much smaller field set than ParentKidRegisterRequest:
    the parent's own email/password/consent are already established by
    the fact they're calling this authenticated, so only the new child's
    own fields are needed."""
    first_name: str
    avatar: str = "chick"
    pin: str

    @validator("first_name")
    def first_name_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter your child's name")
        return v

    @validator("pin")
    def pin_format(cls, v):
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @validator("avatar")
    def avatar_valid(cls, v):
        valid = {"chick", "dragon", "bunny", "fox", "rocket", "fish"}
        if v not in valid:
            raise ValueError(f"Avatar must be one of {valid}")
        return v


class UpdateChildRequest(BaseModel):
    """Lets the parent change their own child's avatar after creation --
    the parent-side counterpart to PatientUpdate (therapist) and
    UpdateMyProfileRequest (kid). Avatar-only for now, since that's the
    one thing #68 flagged as missing; not first_name/PIN, which have
    their own dedicated flows (kid-account settings) already."""
    avatar: str


class LinkChildRequest(BaseModel):
    """Adds an EXISTING child (already created via kid-register, a
    therapist, or another parent's AddChildRequest) to this parent's
    switcher, by the same player_code ParentRegisterRequest already uses
    to link a first child -- this is that same lookup, just callable
    again post-login for a second/third child instead of only at
    registration time."""
    player_code: str


class LinkTherapistRequest(BaseModel):
    """Parent-initiated: attach an EXISTING therapist account to the
    parent's currently-active child, by the therapist's login identifier
    (their email, or their @username if they've set one -- see
    breathquest_core/username.py). This is the reverse of
    POST /breathquest/patients/link below (which a therapist uses to
    attach themselves to an existing, self/parent-registered kid) -- one
    endpoint per direction, same underlying effect: setting
    BreathQuestPatient.therapist_id."""
    therapist_code: str

    @validator("therapist_code")
    def therapist_code_present(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Enter your therapist's email or @username")
        return v.lstrip("@")


class LinkTherapistResponse(BaseModel):
    patient_id: str
    child_first_name: str
    therapist_id: str
    therapist_name: str
    clinic_name: str | None = None


class SwitchChildRequest(BaseModel):
    patient_id: str


class SwitchChildResponse(BaseModel):
    """Deliberately does NOT include a new access/refresh token pair --
    switching which child is active doesn't change the parent's own
    identity (the JWT's `sub` is parent_id, never patient_id), so nothing
    about the existing token is invalidated or needs rotating. The caller
    already holds a valid token; this just tells it what patient_id to
    treat as active from now on."""
    patient_id: str
    child_first_name: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


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


class ChimeSoundBreakdown(BaseModel):
    sound_id: str
    attempts: int
    valid_attempts: int


class ChimeWeeklyBreakdownOut(BaseModel):
    """Per-sound split of this week's Chime attempts -- the number behind
    the 'Chime attempts' stat in the weekly summary grid, broken open."""
    items: List[ChimeSoundBreakdown]


class SoundWeekPoint(BaseModel):
    week: str          # ISO week label, e.g. "2026-W28"
    week_start: datetime
    accuracy: float     # 0-1
    attempts: int


class SoundProgressOut(BaseModel):
    patient_id: str
    sounds: dict
    practiced_sound_count: int   # distinct sounds attempted at least once, all-time


class PhonemeMasteryOut(BaseModel):
    phoneme: str
    attempts: int
    correct_count: int
    accuracy: float
    last_word: Optional[str] = None
    last_practiced_at: Optional[datetime] = None
    trend: Optional[str] = None  # "up" / "down" / "flat" / None


class FlashcardsProgressOut(BaseModel):
    patient_id: str
    total_attempts: int
    distinct_phonemes_practiced: int
    overall_accuracy: float
    strongest: List[PhonemeMasteryOut]   # top 3 by accuracy (min attempts threshold)
    weakest: List[PhonemeMasteryOut]     # bottom 3 by accuracy (min attempts threshold)
    mastery: List[PhonemeMasteryOut]     # full list, sorted by accuracy asc (weakest-first)
    recent_words: List[str]              # last ~10 distinct target_words attempted, most recent first


class PhonemeGameBreakdownOut(BaseModel):
    game: str            # "flashcards" | "vaakmirror" | "chime"
    attempts: int
    correct: int
    accuracy: float      # 0-1


class CrossGamePhonemeOut(BaseModel):
    phoneme: str
    ipa: Optional[str] = None
    example_word: Optional[str] = None
    category: Optional[str] = None       # PHONEME_DATA's "category" (stop/fricative/vowel/...)
    attempts: int
    correct: int
    accuracy: float                      # 0-1, across all games combined
    by_game: List[PhonemeGameBreakdownOut]
    last_practiced_at: Optional[datetime] = None


class CategoryRollupOut(BaseModel):
    category: str
    attempts: int
    correct: int
    accuracy: float       # 0-1


class CrossGamePhonemeSummaryOut(BaseModel):
    patient_id: str
    phonemes: List[CrossGamePhonemeOut]              # every phoneme practiced in any game
    by_category: List[CategoryRollupOut]              # rolled up by articulatory category
    game_totals: List[PhonemeGameBreakdownOut]        # rolled up by game, independent of phoneme -- the "at a glance" strip
    weakest: List[CrossGamePhonemeOut]                # min 3 attempts, worst accuracy first
    total_attempts: int
    overall_accuracy: float                           # 0-1


class HomePracticeIdeaOut(BaseModel):
    id: int
    title: str
    description: str
    conditions: List[str]
    goals: List[str]


class GuidedActivityOut(BaseModel):
    idea: HomePracticeIdeaOut
    reason: str   # plain-language "why this one" for the parent


class KidProgressOut(BaseModel):
    """What the child sees about themself — no scores, no clinical
    language, just concrete, encouraging counts."""
    first_name: str
    avatar: str
    total_stars: int
    max_possible_stars: int
    games_played_this_week: int
    current_streak_days: int


class BreathQuestLevelScore(BaseModel):
    """One level's best result for GET /me/breathquest/level-scores. Mirrors
    the shape the frontend already keeps in localStorage (game/scoring/index.js's
    `{stars, plays, lastPlayed}` per level) so the two can be merged directly --
    this is the durable, cross-device source of truth that cache is meant to
    mirror, not a competing shape."""
    stars: int
    plays: int
    last_played: datetime | None = None


class GameSummary(BaseModel):
    """One world's at-a-glance summary for GET /me/games-summary, keyed by
    the same app ids GamePicker.jsx already uses ('breathquest',
    'vaakmirror', 'chime', 'voice-hurdle-race', 'flashcards'). stars/max_stars
    are omitted (None) for games without a per-level star concept -- the
    frontend falls back to showing just a play count for those."""
    last_played: datetime | None = None
    stars: int | None = None
    max_stars: int | None = None
    plays: int = 0


class KidHistoryEntry(BaseModel):
    """One row in the kid's own combined assessment+game timeline
    (GET /me/history). Same no-scores, no-clinical-language ethos as
    KidProgressOut: an assessment entry says an assessment happened and
    when, not its severity_classification/diagnostic findings -- those
    stay therapist/parent-only, same as everywhere else in this app."""
    kind: str            # "assessment" | "game"
    game: str | None = None   # None for assessment entries
    title: str
    detail: str | None = None
    date: datetime | None = None


# ------------------------------------------------------------------ #
#  Email verification                                                  #
# ------------------------------------------------------------------ #

class ParentResetPasswordRequest(BaseModel):
    """Password reset for parents, gated the same way ForgotPinRequest
    gates a kid's PIN reset -- a recently-verified OTP on the account
    email (see check_email_consent), not a mailed reset link/token,
    since the OTP infra already exists and a link would need a second
    new mechanism (signed tokens, expiry, a reset-confirmation page)
    for no real benefit over what's already here."""
    email: EmailStr
    new_password: str

    @validator("email")
    def normalize_email(cls, v):
        return _normalize_email(v)

    @validator("new_password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ParentDeleteAccountRequest(BaseModel):
    """Re-auth for the irreversible delete-account action. current_password
    is required unless the account is Google-only (no password ever set --
    see Parent.hashed_password's comment), in which case it's omitted
    entirely rather than asking for a password that was never created.
    Same reasoning as TherapistDeleteAccountRequest."""
    current_password: Optional[str] = None


class KidDeleteAccountRequest(BaseModel):
    """Re-auth for the irreversible delete-account action -- PIN instead
    of password, matching how kids authenticate everywhere else."""
    current_pin: str


class ForgotEmailRequest(BaseModel):
    player_code: str


class ForgotPlayerCodeRequest(BaseModel):
    email: EmailStr

    @validator("email")
    def normalize_email(cls, v):
        return _normalize_email(v)


class ForgotPinRequest(BaseModel):
    """Self-registered kids (POST /auth/kid-register) have no Patient row
    to key a reset off of -- only a BreathQuestPatient with a parent_email
    column set directly at signup -- so this checks player_code +
    parent_email against that column, not a therapist-side lookup like
    kid-pin-setup's patient_id does."""
    player_code: str
    parent_email: EmailStr
    new_pin: str

    @validator("parent_email")
    def normalize_parent_email(cls, v):
        return _normalize_email(v)

    @validator("new_pin")
    def pin_format(cls, v):
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 digits")
        return v


class VerifyRequestIn(BaseModel):
    """Ask for a 6-digit code by email.

    `purpose` is set only by the three REGISTRATION screens, so the server
    can say "that account already exists" up front instead of mailing a
    code that leads nowhere. It is deliberately absent from forgot-password
    / forgot-PIN, which must keep sending codes to existing accounts.
    Accepted trade-off: because of this, a registration screen can be used
    to check whether an email (or a kid's name + parent email) has an
    account -- mitigated by the per-IP auth rate limit."""
    email: EmailStr
    purpose: Literal["register_therapist", "register_kid", "register_parent"] | None = None
    first_name: str | None = None  # register_kid only

    @validator("email")
    def normalize_email(cls, v):
        return _normalize_email(v)


class VerifyConfirmIn(BaseModel):
    email: EmailStr
    code: str

    @validator("email")
    def normalize_email(cls, v):
        return _normalize_email(v)


class VerifyConfirmOut(BaseModel):
    verified: bool
    first_time: bool


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

    id: StrId
    patient_id: StrId
    assigned_by: StrId
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

    id: StrId
    patient_id: StrId
    created_by: StrId
    target_metric: str
    target_value: float
    baseline_value: Optional[float]
    target_date: Optional[datetime]
    achieved: bool
    achieved_at: Optional[datetime]
    created_at: datetime
    current_value: Optional[float] = None   # populated at read time, not stored


class ParentProgressOut(BaseModel):
    """Parent view: more than the kid sees, but no clinical notes and no
    raw per-attempt data — trend-level, not session-by-session.

    Relocated below GoalOut/AssignmentOut (this file has no forward-ref
    support) since goals/assignments now carry the actual goal/assignment
    content, not just counts -- see weekly_summary's goals_open/
    assignments_completed for the counts-only view this supplements."""
    child_first_name: str
    avatar: str
    # Uploaded profile photo (overrides the creature art wherever set), same
    # field the therapist views already return -- the parent dashboard header
    # used to get only `avatar`, so a photo the kid uploaded never showed here.
    avatar_photo_url: Optional[str] = None
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
    # Lets the frontend show/hide therapist-dependent UI (messaging) honestly
    # instead of a message box that silently 403s or accepts messages nobody
    # reads. Boolean only -- parents don't need the therapist's actual id.
    has_therapist: bool = False
    # The actual goal/assignment content -- weekly_summary only ever had
    # counts (goals_open, assignments_completed), never what those goals
    # or assignments *are*. Reuses the therapist-facing GoalOut/AssignmentOut
    # shapes as-is rather than a parent-specific subset, since nothing in
    # them is clinician-only (that's clinical *notes*, which live elsewhere).
    goals: List[GoalOut] = []
    assignments: List[AssignmentOut] = []
    player_code: Optional[str] = None
    # See PatientProgress.username above -- same reasoning for the parent
    # dashboard header.
    username: Optional[str] = None


# ------------------------------------------------------------------ #
#  Messages                                                            #
# ------------------------------------------------------------------ #

class MessageCreate(BaseModel):
    body: str
    sender_role: str = "therapist"  # therapist or parent


class MessageOut(BaseModel):
    class Config:
        from_attributes = True

    id: StrId
    patient_id: StrId
    sender_role: str
    sender_id: Optional[StrId]
    body: str
    created_at: datetime
    read_at: Optional[datetime]


class EmailPreferencesOut(BaseModel):
    """Logged-in-parent-facing mirror of the same weekly_email_opt_out
    flag the unsubscribe email link sets -- lets a parent change their
    mind from Settings without having to dig up an old email."""
    weekly_email_opt_out: bool


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

    id: StrId
    patient_id: StrId
    logged_at: datetime
    practiced_on: datetime
    duration_minutes: Optional[int]
    notes: Optional[str]


# ------------------------------------------------------------------ #
#  Kid-facing practice calendar + goal (services/weekly_target.py,     #
#  services/kid_goal.py)                                               #
# ------------------------------------------------------------------ #

class CalendarDay(BaseModel):
    date: date
    label: str          # "Mon" .. "Sun"
    practiced: bool
    is_today: bool
    is_future: bool


class WeeklyCalendarOut(BaseModel):
    week_start: date
    days: List[CalendarDay]
    days_practiced: int
    target_days: int    # auto-computed from the kid's own recent habit
    target_met: bool
    days_left: int
    message: str


class KidGoalOut(BaseModel):
    id: str
    title: str          # friendly name, never the raw target_metric
    blurb: str
    progress_pct: int   # 0..100
    achieved: bool
    days_left: Optional[int] = None
    encouragement: str
    looking_forward: str


class WeeklyQuestOut(BaseModel):
    id: str
    title: str
    description: str
    progress: int
    target: int
    complete: bool


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


# ------------------------------------------------------------------ #
#  Usernames (kid / parent / therapist -- see breathquest_core/username.py)
# ------------------------------------------------------------------ #

class UsernameSetRequest(BaseModel):
    username: str


class UsernameOut(BaseModel):
    """Current handle for the signed-in account; null until they pick one."""
    username: str | None = None


class UsernameCheckOut(BaseModel):
    """Result of the live availability check. `username` is the normalized
    form (lower-cased, '@' stripped) so the UI can show exactly what would
    be saved. `reason` is a short, kid-readable sentence whenever
    available is false."""
    username: str
    available: bool
    reason: str | None = None


class UsernameSuggestionsOut(BaseModel):
    suggestions: list[str]
