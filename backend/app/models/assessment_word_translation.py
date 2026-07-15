from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class AssessmentWordTranslation(Base):
    __tablename__ = "assessment_word_translations"

    id = Column(Integer, primary_key=True, index=True)
    assessment_word_id = Column(Integer, ForeignKey("assessment_words.id", ondelete="CASCADE"), nullable=False, index=True)
    language_code = Column(String(10), nullable=False, index=True)
    translated_word = Column(String(240), nullable=False)
    ipa = Column(String(120), nullable=True)

    word = relationship("AssessmentWord", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("assessment_word_id", "language_code", name="uq_assessment_word_language"),
    )
