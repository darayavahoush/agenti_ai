"""
models/therapist.py — Assessment-native therapist accounts.

Distinct from the retiring app.models.breathquest_models.Therapist (see
main.py's 2026-08-07 disable notes) -- this is the real, going-forward
therapist identity for agenti_ai/Assessment, not tied to BreathQuest.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Therapist(Base):
    __tablename__ = "therapists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    clinic_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
