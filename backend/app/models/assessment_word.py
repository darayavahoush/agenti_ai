from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship

from app.database import Base


class AssessmentWord(Base):
    __tablename__ = "assessment_words"

    id = Column(Integer, primary_key=True, index=True)
    word_key = Column(String(120), unique=True, nullable=True, index=True)
    word = Column(String(120), unique=True, nullable=False, index=True)
    image_prompt = Column(String(240), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    
    animation_prompt = Column(String(500), nullable=True)
    animation_filename = Column(String(240), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    media_filename = Column(String(240), nullable=True)

    translations = relationship(
        "AssessmentWordTranslation",
        back_populates="word",
        cascade="all, delete-orphan",
        lazy="selectin",
    )