from sqlalchemy import Column, Float, Integer, TIMESTAMP, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid
from datetime import datetime

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id")
    )

    # Voice Metrics
    f0_mean = Column(Float)
    mpt = Column(Float)
    jitter = Column(Float)
    shimmer = Column(Float)
    hnr = Column(Float)

    # AI Therapy Fields
    target_word = Column(String)
    spoken_word = Column(String)
    accuracy = Column(Integer)
    feedback = Column(String)
    stars = Column(Integer)

    # Session Metadata
    audio_file = Column(String)
    session_type = Column(String, default="word_practice")

    trs_score = Column(Integer)

    created_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def pitch(self):
        return self.f0_mean

    @pitch.setter
    def pitch(self, value):
        self.f0_mean = value

    @property
    def duration(self):
        return self.mpt

    @duration.setter
    def duration(self, value):
        self.mpt = value

    @property
    def loudness(self):
        return self.hnr

    @loudness.setter
    def loudness(self, value):
        self.hnr = value