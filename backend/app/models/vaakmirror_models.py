import enum
from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class GameName(str, enum.Enum):
    mirror_mirror = "mirror_mirror"
    tongue_tamer = "tongue_tamer"
    lip_sync_hero = "lip_sync_hero"


class AttemptOutcome(str, enum.Enum):
    passed = "passed"
    caught = "caught"
    missed = "missed"


class AssignmentStatus(str, enum.Enum):
    not_started = "not_started"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"


class VaakMirrorSession(Base):
    __tablename__ = "vaakmirror_sessions"

    id = Column(Integer, primary_key=True)
    patient_id = Column(String, nullable=False, index=True)
    game = Column(Enum(GameName), nullable=False)
    started_at = Column(DateTime(timezone=True), default=utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    attempts = relationship("Attempt", back_populates="session", cascade="all, delete-orphan")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("vaakmirror_sessions.id"), nullable=False)
    sound_id = Column(String(16), nullable=True)
    place = Column(String(32), nullable=True)
    manner = Column(String(32), nullable=True)
    voicing = Column(String(16), nullable=True)
    outcome = Column(Enum(AttemptOutcome), nullable=False)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    session = relationship("VaakMirrorSession", back_populates="attempts")


class ExerciseTemplate(Base):
    __tablename__ = "exercise_templates"

    id = Column(Integer, primary_key=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    duration_label = Column(String(32), nullable=False)
    target_categories = Column(ARRAY(String), nullable=False, default=list)

    assignments = relationship("ExerciseAssignment", back_populates="exercise")


class ExerciseAssignment(Base):
    __tablename__ = "exercise_assignments"

    id = Column(Integer, primary_key=True)
    patient_id = Column(String, nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercise_templates.id"), nullable=False)
    status = Column(Enum(AssignmentStatus), nullable=False, default=AssignmentStatus.assigned)
    assigned_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    exercise = relationship("ExerciseTemplate", back_populates="assignments")
