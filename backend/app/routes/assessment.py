from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.models.assessment_word import AssessmentWord
from app.services.image.matcher import get_image_for_phrase


router = APIRouter(prefix="/assessment", tags=["Assessment"])

class AssessmentWordCreate(BaseModel):
    word: str = Field(min_length=1, max_length=120)
    display_order: int = 0
    image_prompt: str | None = Field(default=None, max_length=240)
    animation_prompt: str | None = Field(default=None, max_length=500)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_word(item: AssessmentWord) -> dict:
    return {
        "id": item.id,
        "word": item.word,
        "image_prompt": item.image_prompt,
        "image_url": f"/assessment/words/{item.id}/image",
    }


@router.post("/words", status_code=status.HTTP_201_CREATED)
def add_word(payload: AssessmentWordCreate, db: Session = Depends(get_db)):
    word = payload.word.strip()
    if not word:

        raise HTTPException(status_code=422, detail="Word is required")
    if len(word) > 120:
        raise HTTPException(status_code=422, detail="Word must be 120 characters or fewer")

    image_prompt = payload.image_prompt.strip() if payload.image_prompt else None
    item = AssessmentWord(word=word, image_prompt=image_prompt)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This assessment word already exists")
    db.refresh(item)
    return serialize_word(item)


@router.get("/words")
def list_words(db: Session = Depends(get_db)):
    items = (
        db.query(AssessmentWord)
        .filter(AssessmentWord.is_active.is_(True))
        .order_by(AssessmentWord.word)
        .all()
    )
    return [serialize_word(item) for item in items]


@router.get("/words/random")
def random_word(db: Session = Depends(get_db)):
    item = (
        db.query(AssessmentWord)
        .filter(AssessmentWord.is_active.is_(True))
        .order_by(func.random())
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=404,
            detail="No assessment words found. Add one with POST /assessment/words.",
        )
    return serialize_word(item)


@router.get("/words/{word_id}/image")
def word_image(word_id: int, db: Session = Depends(get_db)):
    item = db.get(AssessmentWord, word_id)
    if item is None or not item.is_active:
        raise HTTPException(status_code=404, detail="Assessment word not found")

    result = get_image_for_phrase(item.image_prompt or item.word)
    image_bytes = result.get("image_bytes")
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Could not generate an image for this word")

    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )