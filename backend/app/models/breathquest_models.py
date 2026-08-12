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

    patients: Mapped[list["BreathQuestPatient"]] = relationship(back_populates="therapist", cascade="all, delete-orphan")


class BreathQuestPatient(Base):
    __tablename__ = "breathquest_patients"

    id:               Mapped[uuid.UUID]    = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    therapist_id:     Mapped[uuid.UUID | None] = mapped_column(ForeignKey("breathquest_therapists.id"), nullable=True, index=True)
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
    created_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow)

    # Fully module-qualified string ref -- bare "Therapist" is ambiguous now
    # that app/models/therapist.py also registers a class named Therapist
    # on this same shared Base (see that module's docstring). This
    # relationship specifically means the old breathquest_therapists-mapped
    # class, not the new Assessment-native one.
    therapist: Mapped["app.models.breathquest_models.Therapist | None"] = relationship(back_populates="patients")
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
    therapist_id: Mapped[uuid.UUID]   = mapped_column(ForeignKey("breathquest_therapists.id"), nullable=False)
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
    owner_therapist_id:       Mapped[uuid.UUID | None] = mapped_column(ForeignKey("breathquest_therapists.id"), nullable=True, unique=True, index=True)
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
    assigned_by:  Mapped[uuid.UUID] = mapped_column(ForeignKey("breathquest_therapists.id"), nullable=False)
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
    created_by:     Mapped[uuid.UUID] = mapped_column(ForeignKey("breathquest_therapists.id"), nullable=False)
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
