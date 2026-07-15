from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assessment_word import AssessmentWord
from app.models.assessment_word_translation import AssessmentWordTranslation
from app.utils.word_utils import normalize_word_key


def get_assessment_word_by_key(db: Session, word_key: str) -> AssessmentWord | None:
    normalized_key = normalize_word_key(word_key)
    candidate = (
        db.query(AssessmentWord)
        .filter(AssessmentWord.word_key == normalized_key)
        .first()
    )
    if candidate:
        return candidate

    normalized_word = func.regexp_replace(func.lower(AssessmentWord.word), "[^a-z0-9]+", "_", "g")
    return (
        db.query(AssessmentWord)
        .filter(normalized_word == normalized_key)
        .first()
    )


def get_translation_text(db: Session, word_key: str, language_code: str) -> str | None:
    language_code = language_code.strip().lower().split("-")[0]
    word = get_assessment_word_by_key(db, word_key)
    if word is None:
        return None

    translation = (
        db.query(AssessmentWordTranslation)
        .filter(
            AssessmentWordTranslation.assessment_word_id == word.id,
            AssessmentWordTranslation.language_code == language_code,
        )
        .first()
    )

    if translation:
        return translation.translated_word

    if language_code == "en":
        return word.word

    return None
