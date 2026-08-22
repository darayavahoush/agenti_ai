"""
models/voicehurdlerace_models.py — VoiceHurdleRace game sessions.

FKs to breathquest_patients.id, same as GameSession/TherapistNote.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


class VoiceHurdleRaceSession(Base):
    __tablename__ = "breathquest_voicehurdlerace_sessions"

    id:                Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:        Mapped[uuid.UUID] = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    level_id:          Mapped[int]      = mapped_column(Integer, nullable=False)
    level_name:        Mapped[str]      = mapped_column(String(100), nullable=False)
    score:             Mapped[int]      = mapped_column(Integer, nullable=False)
    time_remaining:    Mapped[float]    = mapped_column(Float, nullable=False)
    pitch_accuracy:    Mapped[float]    = mapped_column(Float, nullable=False)
    loudness_accuracy: Mapped[float]    = mapped_column(Float, nullable=False)
    stars:             Mapped[int]      = mapped_column(Integer, nullable=False)
    created_at:        Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
