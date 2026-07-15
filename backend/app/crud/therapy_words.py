from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.assessment_word import AssessmentWord

def get_word_by_key(db: Session, word_key: str) -> AssessmentWord | None:
    """
    Look up an AssessmentWord in the database by case-insensitive word or word_key.
    """
    if not word_key:
        return None
    cleaned_key = word_key.lower().strip()
    
    # 1. Search by word column
    word = db.query(AssessmentWord).filter(func.lower(AssessmentWord.word) == cleaned_key).first()
    if word:
        return word
        
    # 2. Search by word_key column
    word = db.query(AssessmentWord).filter(func.lower(AssessmentWord.word_key) == cleaned_key).first()
    return word
