"""
models/retraining_models.py — Postgres models for the RL training event
store, ported from quest-games' retraining/models.py.

Deliberately NOT the same table as breathquest_models.SessionEvent -- that
one is FK'd to GameSession and stores generic real-time gameplay telemetry
for session detail views. This table is a purpose-built RL training log
(score, severity_numeric, policy_used, downgrade_reason, etc.) written by
BreathQuest/Chime/VoiceHurdleRace alike, read by the adaptive-difficulty
agent (top-level agent/service.py -- not app/breathquest_agent, which
was an unused duplicate and has been removed).

child_id FKs to breathquest_patients.id (not quest-games' own standalone
patients.id) -- that's who actually plays these games in agenti_ai.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models import breathquest_models  # noqa: F401 -- registers breathquest_patients (this file's FK target below) with Base before RLTrainingEvent's mapper is configured. Without this, anything that imports this module without having imported breathquest_models first (a standalone script, a test, a future retraining worker) hits NoReferencedTableError on first query -- this makes the module self-sufficient regardless of import order elsewhere.


def utcnow():
    return datetime.now(timezone.utc)


class RLTrainingEvent(Base):
    """One row per real gameplay attempt. Kept as an auto-incrementing
    integer id (not a UUID) to preserve the old SQLite table's
    "ORDER BY id ASC" == chronological-by-insertion behavior that
    get_events()/count_events_since() rely on."""
    __tablename__ = "breathquest_rl_training_events"

    id:                      Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    child_id:                Mapped[uuid.UUID]     = mapped_column(PGUUID(as_uuid=True), ForeignKey("breathquest_patients.id"), nullable=False, index=True)
    timestamp:               Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    level_id:                Mapped[str]           = mapped_column(String, nullable=False)
    attempt_number:          Mapped[int]           = mapped_column(Integer, nullable=False)
    score:                   Mapped[float]         = mapped_column(Float, nullable=False)
    is_valid_attempt:        Mapped[bool]          = mapped_column(Boolean, nullable=False)
    threshold_at_time:       Mapped[float | None]  = mapped_column(Float, nullable=True)
    action:                  Mapped[str | None]    = mapped_column(String, nullable=True)
    quit_flag:                Mapped[bool]          = mapped_column(Boolean, default=False)
    raw_features:             Mapped[dict | None]   = mapped_column(JSON, nullable=True)
    severity_numeric:         Mapped[float]         = mapped_column(Float, default=0.0)
    is_targeted_sound:        Mapped[bool]          = mapped_column(Boolean, default=False)
    policy_used:               Mapped[str | None]    = mapped_column(String, nullable=True)
    downgrade_reason:          Mapped[str | None]    = mapped_column(String, nullable=True)
    recommended_action:         Mapped[str | None]    = mapped_column(String, nullable=True)
    recommendation_message:     Mapped[str | None]    = mapped_column(String, nullable=True)


class RetrainCheckpoint(Base):
    """Tracks when the shared policy was last retrained and on how many
    events -- one row per scope (currently only "global" is used)."""
    __tablename__ = "breathquest_retrain_checkpoints"

    scope:                     Mapped[str]      = mapped_column(String, primary_key=True)
    last_retrained_at:         Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    event_count_at_checkpoint: Mapped[int]      = mapped_column(Integer, nullable=False)
