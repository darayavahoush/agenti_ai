from sqlalchemy import Column, String, Integer, TIMESTAMP, Boolean, Text
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
    parent_name = Column(String)
    parent_contact = Column(String)
    email = Column(String)  # 'email' in database, not 'email_address'
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
