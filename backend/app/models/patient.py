from sqlalchemy import Column, String, Integer, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime

class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String, nullable=False)
    age = Column(Integer)
    language = Column(String)

    gender = Column(String)
    diagnosis = Column(String)

    therapist_name = Column(String)
    parent_contact = Column(String)

    is_active = Column(Boolean, default=True)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    sessions = relationship("Session", back_populates="patient")
