from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP

from app.database import Base


class AssessmentWord(Base):
    __tablename__ = "assessment_words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(120), unique=True, nullable=False, index=True)
    image_prompt = Column(String(240), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)