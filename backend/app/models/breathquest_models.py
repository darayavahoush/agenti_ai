"""
models/breathquest_models.py — All database models for BreathQuest.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)

def new_uuid():
    return uuid.uuid4()


class LevelID(str, enum.Enum):
    pinwheel    = "pinwheel"
    float_rider = "float_rider"
    candle      = "candle"
    balloon     = "balloon"
    dandelion   = "dandelion"
    dragon      = "dragon"


class SessionStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed   = "completed"
    abandoned   = "abandoned"


class Therapist(Base):
    __tablename__ = "breathquest_therapists"

    id:               Mapped[uuid.UUID]    = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    email:            Mapped[str]           = mapped_column(String(255), nullable=False, index=True)
    hashed_password:  Mapped[str]           = mapped_column(String(255), nullable=False)
    full_name:        Mapped[str]           = mapped_column(String(255), nullable=False)
    clinic_name:      Mapped[str | None]    = mapped_column(String(255))
    is_active:        Mapped[bool]          = mapped_column(Boolean, default=True)
    created_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True))

    # back_populates relationship to BreathQuestPatient removed 2026-08-12 --
    # this class (breathquest_therapists) is retiring; nothing creates rows
    # here anymore (see app.models.therapist.Therapist, the real one
    # get_current_therapist resolves against). Every FK that used to point
    # at this table has been repointed to therapists.id. Keeping this class
    # only because breathquest_models.Therapist is still imported by name
    # in a couple of unported routers (chime.py/voicehurdlerace.py) --
    # remove entirely once those are fixed.


class BreathQuestPatient(Base):
    __tablename__ = "breathquest_patients"

    id:               Mapped[uuid.UUID]    = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    # Repointed 2026-08-12: was FK'd to breathquest_therapists.id (the
    # retiring class above), but every therapist created through the
    # canonical /api/v1/auth/register path lives in therapists.id (see
    # app/models/therapist.py). That mismatch made every therapist-created
    # patient fail with an FK integrity error -- confirmed via a real
    # Internal Server Error on POST /api/v1/breathquest/patients. Both
    # tables were empty at the time of this fix, so this is a clean swap,
    # not a data migration (see main.py's _ensure_breathquest_therapist_fks
    # stopgap for the matching DB-side ALTER).
    therapist_id:     Mapped[uuid.UUID | None] = mapped_column(ForeignKey("therapists.id"), nullable=True, index=True)
    first_name:       Mapped[str]           = mapped_column(String(100), nullable=False)
    avatar:           Mapped[str]           = mapped_column(String(50), default="chick")
    pin_hash:         Mapped[str]           = mapped_column(String(64), nullable=False)
    player_code:      Mapped[str]           = mapped_column(String(10), unique=True, nullable=False, index=True)
    age:              Mapped[int | None]    = mapped_column(Integer)
    diagnosis_notes:  Mapped[str | None]   = mapped_column(Text)
    is_active:        Mapped[bool]          = mapped_column(Boolean, default=True)
    # Links to Assessment's patients.id -- added 2026-08-11 so breath_agent.py's
    # diagnostic-context lookup (get_diagnostic_context(patient.assessment_patient_id))
    # has something real to read. Nullable: not every BreathQuestPatient originates
    # from a kid_register(data.patient_id) call yet (see patients.py's therapist-created
    # path, which doesn't set this).
    assessment_patient_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True)
    # Added 2026-08-12 to gate the kid onto /assessment on first login until
    # they've completed it (see routers/breathquest/assessment.py). Nullable
    # JSON summary intentionally kept lightweight -- just what
    # AssessmentReport.jsx's free teaser needs (word count, severity read),
    # not the full diagnostic report (that stays on the Assessment side's
    # own Session rows, looked up via assessment_patient_id).
    assessment_completed: Mapped[bool]       = mapped_column(Boolean, default=False)
    assessment_summary:   Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Added 2026-08-12 for COPPA: POST /auth/kid-register (the only path with
    # no adult already in the loop -- see breathquest_core/parental_consent.py)
    # now requires a recently-verified parent email before it will create an
    # account at all, and records that email + when consent was verified on
    # the resulting row. Nullable because kid-pin-setup and the
    # assessment-linked flow both already require a therapist/parent to have
    # created the record first, so this doesn't apply to them.
    parent_email:                Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_consent_verified_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Added 2026-08-12: phone verification is now required alongside email
    # (not an alternative -- both must be verified) for kid-register. Same
    # nullable reasoning as parent_email above.
    parent_phone:                     Mapped[str | None] = mapped_column(String(32), nullable=True)
    parent_phone_consent_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)

    # `therapist` relationship removed 2026-08-12 alongside the FK repoint
    # above -- it was wired via back_populates to breathquest_models.Therapist
    # specifically (the retiring class), which is now the wrong target for
    # what therapist_id actually references (therapists.id). No router
    # actually used patient.therapist (confirmed by search), so this is a
    # pure removal, not a repoint -- if ORM-level access to the owning
    # therapist is needed later, query app.models.therapist.Therapist by
    # therapist_id directly rather than re-adding a relationship here.
    sessions:  Mapped[list["GameSession"]]  = relationship(back_populates="patient", cascade="all, delete-orphan")
    notes:     Mapped[list["TherapistNote"]]= relationship(back_populates="patient", cascade="all, delete-orphan")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    goals:       Mapped[list["Goal"]]       = relationship(back_populates="patient", cascade="all, delete-orphan")
    messages:    Mapped[list["Message"]]    = relationship(back_populates="patient", cascade="all, delete-orphan")
    home_practice_logs: Mapped[list["HomePracticeLog"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    parent: Mapped["Parent | None"] = relationship(back_populates="patient", uselist=False, cascade="all, delete-orphan")


class GameSession(Base):
    __tablename__ = "breathquest_game_sessions"

    id:                   Mapped[uuid.UUID]   = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:           Mapped[uuid.UUID]   = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    level_id:             Mapped[str]          = mapped_column(SAEnum(LevelID), nullable=False)
    started_at:           Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at:             Mapped[datetime|None]= mapped_column(DateTime(timezone=True))
    duration_seconds:     Mapped[float|None]   = mapped_column(Float)
    status:               Mapped[str]          = mapped_column(SAEnum(SessionStatus), default=SessionStatus.in_progress)
    stars_earned:         Mapped[int|None]     = mapped_column(Integer)
    completed:            Mapped[bool]         = mapped_column(Boolean, default=False)
    completion_message:   Mapped[str|None]     = mapped_column(String(255))
    avg_breath_strength:  Mapped[float|None]   = mapped_column(Float)
    max_breath_strength:  Mapped[float|None]   = mapped_column(Float)
    breath_consistency:   Mapped[float|None]   = mapped_column(Float)
    total_puffs:          Mapped[int|None]     = mapped_column(Integer)
    lives_lost:           Mapped[int|None]     = mapped_column(Integer)

    patient: Mapped["BreathQuestPatient"]              = relationship(back_populates="sessions")
    events:  Mapped[list["SessionEvent"]]   = relationship(back_populates="session", cascade="all, delete-orphan")


class SessionEvent(Base):
    __tablename__ = "breathquest_session_events"

    id:           Mapped[uuid.UUID]   = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id:   Mapped[uuid.UUID]   = mapped_column(ForeignKey("breathquest_game_sessions.id"), nullable=False, index=True)
    timestamp:    Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow)
    event_type:   Mapped[str]          = mapped_column(String(50))
    breath_value: Mapped[float|None]   = mapped_column(Float)
    event_data:   Mapped[dict|None]    = mapped_column(JSON)

    session: Mapped["GameSession"] = relationship(back_populates="events")


class TherapistNote(Base):
    __tablename__ = "breathquest_therapist_notes"

    id:           Mapped[uuid.UUID]   = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:   Mapped[uuid.UUID]   = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    # Repointed 2026-08-12, same root cause as BreathQuestPatient.therapist_id
    # above -- see that field's comment.
    therapist_id: Mapped[uuid.UUID]   = mapped_column(ForeignKey("therapists.id"), nullable=False)
    created_at:   Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:   Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow)
    session_id:   Mapped[uuid.UUID|None] = mapped_column(ForeignKey("breathquest_game_sessions.id"))
    content:      Mapped[str]          = mapped_column(Text, nullable=False)
    tags:         Mapped[list|None]    = mapped_column(JSON)

    patient: Mapped["BreathQuestPatient"] = relationship(back_populates="notes")


class EmailVerification(Base):
    """OTP-gate in front of both the Assessment and BreathQuest entry points.
    Deliberately NOT tied to Therapist/BreathQuestPatient -- just answers
    "have we verified this email before" for the public landing flow."""
    __tablename__ = "breathquest_email_verifications"

    id:               Mapped[uuid.UUID]    = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    email:            Mapped[str]           = mapped_column(String(255), nullable=False, index=True)
    otp_code_hash:    Mapped[str]           = mapped_column(String(64), nullable=False)
    expires_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    attempts:         Mapped[int]           = mapped_column(Integer, default=0)
    verified:         Mapped[bool]          = mapped_column(Boolean, default=False)
    # Added 2026-08-12 for COPPA parental consent (see breathquest_core/
    # parental_consent.py): kid-register needs to know *when* an email was
    # verified, not just whether it ever was, so a code confirmed weeks ago
    # can't be replayed indefinitely to gate a new signup.
    verified_at:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)


class PhoneVerification(Base):
    """OTP-gate for parent phone numbers, mirroring EmailVerification
    exactly. Added 2026-08-12 alongside making phone verification a second
    required consent factor on kid-register (see breathquest_core/
    parental_consent.py) -- deliberately its own table rather than adding
    a phone column to EmailVerification, same reasoning EmailVerification
    itself gives for staying separate from Therapist/BreathQuestPatient."""
    __tablename__ = "breathquest_phone_verifications"

    id:               Mapped[uuid.UUID]    = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    phone:            Mapped[str]           = mapped_column(String(32), nullable=False, index=True)
    otp_code_hash:    Mapped[str]           = mapped_column(String(64), nullable=False)
    expires_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    attempts:         Mapped[int]           = mapped_column(Integer, default=0)
    verified:         Mapped[bool]          = mapped_column(Boolean, default=False)
    verified_at:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)


class Parent(Base):
    __tablename__ = "breathquest_parents"

    id:               Mapped[uuid.UUID]    = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:       Mapped[uuid.UUID]    = mapped_column(ForeignKey("breathquest_patients.id"), unique=True, nullable=False)
    email:            Mapped[str]           = mapped_column(String(255), unique=True, nullable=False)
    hashed_password:  Mapped[str]           = mapped_column(String(255), nullable=False)
    full_name:        Mapped[str | None]    = mapped_column(String(255), nullable=True)
    is_active:        Mapped[bool]          = mapped_column(Boolean, default=True)
    created_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login:       Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["BreathQuestPatient"] = relationship(back_populates="parent")


class Subscription(Base):
    """Billing status for a Parent or Therapist account. Exactly one of
    owner_parent_id / owner_therapist_id is set."""
    __tablename__ = "breathquest_subscriptions"

    id:                       Mapped[uuid.UUID]     = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    owner_parent_id:          Mapped[uuid.UUID | None] = mapped_column(ForeignKey("breathquest_parents.id"), nullable=True, unique=True, index=True)
    # Repointed 2026-08-12, same root cause as BreathQuestPatient.therapist_id
    # above -- see that field's comment.
    owner_therapist_id:       Mapped[uuid.UUID | None] = mapped_column(ForeignKey("therapists.id"), nullable=True, unique=True, index=True)
    plan_type:                Mapped[str]           = mapped_column(String(50), nullable=False)
    status:                   Mapped[str]           = mapped_column(String(20), nullable=False, default="trialing")
    trial_ends_at:            Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end:       Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider:                 Mapped[str | None]    = mapped_column(String(30), nullable=True)
    provider_customer_id:     Mapped[str | None]    = mapped_column(String(255), nullable=True)
    provider_subscription_id: Mapped[str | None]    = mapped_column(String(255), nullable=True)
    created_at:               Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at:               Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AssignmentStatus(str, enum.Enum):
    assigned    = "assigned"
    in_progress = "in_progress"
    completed   = "completed"
    overdue     = "overdue"


class Assignment(Base):
    """Homework -- a specific level/word-set a therapist assigns to a patient."""
    __tablename__ = "breathquest_assignments"

    id:           Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:   Mapped[uuid.UUID] = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    # Repointed 2026-08-12, same root cause as BreathQuestPatient.therapist_id
    # above -- see that field's comment.
    assigned_by:  Mapped[uuid.UUID] = mapped_column(ForeignKey("therapists.id"), nullable=False)
    game:         Mapped[str]           = mapped_column(String(50), nullable=False)
    level_id:     Mapped[str | None]    = mapped_column(String(50))
    title:        Mapped[str]           = mapped_column(String(255), nullable=False)
    instructions: Mapped[str | None]    = mapped_column(Text)
    status:       Mapped[str]           = mapped_column(SAEnum(AssignmentStatus), default=AssignmentStatus.assigned)
    created_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    due_at:       Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped["BreathQuestPatient"] = relationship(back_populates="assignments")


class Goal(Base):
    """A measurable target tracked against GameSession aggregates."""
    __tablename__ = "breathquest_goals"

    id:             Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:     Mapped[uuid.UUID] = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    # Repointed 2026-08-12, same root cause as BreathQuestPatient.therapist_id
    # above -- see that field's comment.
    created_by:     Mapped[uuid.UUID] = mapped_column(ForeignKey("therapists.id"), nullable=False)
    target_metric:  Mapped[str]           = mapped_column(String(100), nullable=False)
    target_value:   Mapped[float]         = mapped_column(Float, nullable=False)
    baseline_value: Mapped[float | None]  = mapped_column(Float)
    target_date:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    achieved:       Mapped[bool]          = mapped_column(Boolean, default=False)
    achieved_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped["BreathQuestPatient"] = relationship(back_populates="goals")


class SenderRole(str, enum.Enum):
    therapist = "therapist"
    parent    = "parent"


class Message(Base):
    """In-app therapist <-> parent communication log, per patient."""
    __tablename__ = "breathquest_messages"

    id:          Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:  Mapped[uuid.UUID] = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    sender_role: Mapped[str]           = mapped_column(SAEnum(SenderRole), nullable=False)
    sender_id:   Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    body:        Mapped[str]           = mapped_column(Text, nullable=False)
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    read_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped["BreathQuestPatient"] = relationship(back_populates="messages")


class HomePracticeLog(Base):
    """Manual, parent-reported home practice -- distinct from in-app
    GameSession telemetry."""
    __tablename__ = "breathquest_home_practice_logs"

    id:               Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:       Mapped[uuid.UUID] = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    logged_at:        Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)
    practiced_on:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int | None]    = mapped_column(Integer)
    notes:            Mapped[str | None]    = mapped_column(Text)

    patient: Mapped["BreathQuestPatient"] = relationship(back_populates="home_practice_logs")


class KidLoginThrottle(Base):
    """Brute-force tracking for POST /auth/kid-login. Keyed by the raw
    identifier string a client attempts (name or player code), not by
    patient_id -- a 4-digit PIN attempt against a name/code that doesn't
    even exist yet is still an attempt worth counting, and kid_login
    itself doesn't know which (if any) patient an identifier resolves to
    until after the PIN check. Identifier is stored lowercased so
    'Milo'/'milo'/'MILO' all throttle the same underlying attempts,
    matching kid_login's own case-insensitive name matching."""
    __tablename__ = "breathquest_kid_login_throttle"

    id:              Mapped[uuid.UUID]        = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    identifier:      Mapped[str]              = mapped_column(String(255), nullable=False, unique=True, index=True)
    failed_attempts: Mapped[int]              = mapped_column(Integer, nullable=False, default=0)
    first_failed_at: Mapped[datetime | None]  = mapped_column(DateTime(timezone=True))
    last_failed_at:  Mapped[datetime | None]  = mapped_column(DateTime(timezone=True))
    locked_until:    Mapped[datetime | None]  = mapped_column(DateTime(timezone=True))
