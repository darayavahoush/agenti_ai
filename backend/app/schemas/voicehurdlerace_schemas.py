"""
schemas/voicehurdlerace_schemas.py — ported from quest-games' standalone
schemas/voicehurdlerace_schemas.py 2026-08-12. No changes needed beyond the
import location: these are plain Pydantic models with no cross-module
references, unlike breathquest_schemas.py's model-linked classes.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VoiceHurdleRaceSessionCreate(BaseModel):
    level_id: int
    level_name: str
    score: int
    time_remaining: float
    pitch_accuracy: float
    loudness_accuracy: float
    stars: int


class VoiceHurdleRaceSessionOut(BaseModel):
    # id/patient_id are UUID (not str) to match how this codebase's Postgres
    # UUID columns actually deserialize -- see breathquest_schemas.SessionOut
    # for the same pattern. This schema was ported verbatim from
    # quest-games' standalone SQLite-backed service (see module docstring),
    # where ids were plain strings; against Postgres UUID columns, `id: str`
    # made every /sessions and /leaderboard response fail Pydantic's
    # response_model validation with "Input should be a valid string" for
    # every row, 500ing both the therapist-facing patient history and the
    # leaderboard endpoint entirely.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    level_id: int
    level_name: str
    score: int
    time_remaining: float
    pitch_accuracy: float
    loudness_accuracy: float
    stars: int
    created_at: datetime
    rl_event_id: int | None = None  # RLTrainingEvent id for this race, if agent logging succeeded -- lets the frontend attach feedback


class LeaderboardEntryOut(BaseModel):
    session_id: UUID
    patient_name: str
    level_name: str
    stars: int
    created_at: datetime
