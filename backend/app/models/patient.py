from sqlalchemy import Column, String, Integer, TIMESTAMP, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid
from datetime import datetime

class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    age = Column(Integer)
    date_of_birth = Column(String)  # VARCHAR in database
    language = Column(String)
    gender = Column(String)
    diagnosis = Column(String)
    therapist_name = Column(String)
    # Real link, added alongside the new app/models/therapist.py accounts.
    # therapist_name above stays as-is (free-text, from intake) -- this is
    # additive, not a replacement, since nothing currently sets it (no live
    # POST /patients endpoint exists yet -- separate, flagged gap).
    registered_therapist_id = Column(UUID(as_uuid=True), ForeignKey("therapists.id"), nullable=True, index=True)
    parent_name = Column(String)
    parent_contact = Column(String)
    email = Column(String)  # 'email' in database, not 'email_address'
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
