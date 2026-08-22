"""
models/flashcards_models.py — Persistence for Flashcards attempts and
per-phoneme mastery, mirroring breathquest_models.py's style (PGUUID PKs,
FK straight to breathquest_patients.id since Flashcards reuses the same
kid JWT/patient identity as every other kid-facing game -- see
routers/flashcards/router.py's get_current_patient_id).

Two tables instead of one:
  - FlashcardAttempt: one row per /evaluate call, raw log (word, character,
    theme, per-phoneme matches, composite score). Kept even though
    PhonemeMastery below is the aggregate other code should actually read,
    because a raw log is what lets a therapist audit *why* a mastery
    number moved, and lets the aggregate be rebuilt later if the scoring
    model changes.
  - PhonemeMastery: one row per (patient, phoneme), continuously upserted
    by routers/flashcards/mastery.py on every attempt. This is the table
    other games / in-backend agent logic should query -- see
    get_weak_phonemes() in mastery.py -- rather than re-aggregating
    FlashcardAttempt.phoneme_matches every time.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)

def new_uuid():
    return uuid.uuid4()


class FlashcardAttempt(Base):
    """Raw per-attempt log. See module docstring -- query PhonemeMastery
    instead of this table for "is this kid good at /r/" type questions."""
    __tablename__ = "flashcard_attempts"

    id:              Mapped[uuid.UUID]  = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:      Mapped[uuid.UUID]  = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    session_id:      Mapped[str]        = mapped_column(String(64), nullable=False, index=True)
    theme_id:        Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    target_word:     Mapped[str]        = mapped_column(String(100), nullable=False, index=True)
    character:       Mapped[str | None] = mapped_column(String(50), nullable=True)
    language:        Mapped[str]        = mapped_column(String(20), nullable=False, default="english")
    transcript:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    phoneme_matches: Mapped[list]       = mapped_column(JSON, nullable=False, default=list)  # [{expected, detected, correct}, ...]
    accuracy:        Mapped[float]      = mapped_column(Float, nullable=False)
    composite_score: Mapped[float]      = mapped_column(Float, nullable=False)
    attempt_number:  Mapped[int]        = mapped_column(Integer, nullable=False, default=1)
    repeat_needed:   Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    created_at:      Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PhonemeMastery(Base):
    """One row per (patient, phoneme). Upserted -- never inserted twice
    for the same pair -- by routers/flashcards/mastery.py::record_attempt().
    This is the table other games and any agent logic should read via
    get_weak_phonemes() / get_mastery_summary() rather than recomputing
    from FlashcardAttempt on every call."""
    __tablename__ = "flashcard_phoneme_mastery"
    __table_args__ = (UniqueConstraint("patient_id", "phoneme", name="uq_patient_phoneme"),)

    id:                 Mapped[uuid.UUID]  = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    patient_id:         Mapped[uuid.UUID]  = mapped_column(ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    phoneme:            Mapped[str]        = mapped_column(String(10), nullable=False, index=True)
    attempts_count:     Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    correct_count:      Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    accuracy:           Mapped[float]      = mapped_column(Float, nullable=False, default=0.0)  # correct_count/attempts_count*100, denormalised for cheap ORDER BY
    last_word:          Mapped[str | None] = mapped_column(String(100), nullable=True)  # most recent word this phoneme was drilled on
    first_practiced_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=utcnow)
    last_practiced_at:  Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
