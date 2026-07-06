from fastapi import APIRouter, Depends, HTTPException, Response, status, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import SessionLocal
from app.models.assessment_word import AssessmentWord
from app.services.image.matcher import get_image_for_phrase
from app.tools.audio_tool import save_audio, delete_audio
from app.state.assessment_state import AssessmentState
from app.graph.assessment_graph import assessment_graph


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
        "image_url": f"/assessment/words/image/{item.word}",
    }


@router.post("/words", status_code=status.HTTP_201_CREATED)
def add_word(payload: AssessmentWordCreate, db: Session = Depends(get_db)):
    word = payload.word.strip()
    if not word:

        raise HTTPException(status_code=422, detail="Word is required")
    if len(word) > 120:
        raise HTTPException(status_code=422, detail="Word must be 120 characters or fewer")

    image_prompt = payload.image_prompt.strip() if payload.image_prompt else None
    if image_prompt and image_prompt.lower() in ["string", "none", "null", ""]:
        image_prompt = None
    animation_prompt = payload.animation_prompt.strip() if payload.animation_prompt else None
    if animation_prompt and animation_prompt.lower() in ["string", "none", "null", ""]:
        animation_prompt = None

    item = AssessmentWord(
        word=word,
        image_prompt=image_prompt,
        display_order=payload.display_order or 0,
        animation_prompt=animation_prompt
    )
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

    prompt = item.image_prompt
    if prompt and prompt.lower() in ["string", "none", "null", ""]:
        prompt = None
    result = get_image_for_phrase(prompt or item.word)
    image_bytes = result.get("image_bytes")
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Could not generate an image for this word")

    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/words/image/{word}")
def word_image_by_name(word: str):
    prompt = word.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Word parameter is required")
    if prompt.lower() in ["string", "none", "null", ""]:
        raise HTTPException(status_code=404, detail="Placeholder values not allowed")

    from app.services.image.matcher import get_image_for_phrase
    result = get_image_for_phrase(prompt)
    image_bytes = result.get("image_bytes")
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Could not find image for this word")

    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.post("/analyze")
async def analyze_assessment_pronunciation(
    file: UploadFile = File(...),
    patient_name: str = Form(...),
    patient_age: int | None = Form(None),
    target_word: str = Form(...)
):
    """
    Run diagnostic Multi-Agent Assessment Graph on child voice recording.
    """
    # 1. Save audio file locally
    path = save_audio(file)

    try:
        # 2. Build initial AssessmentState
        initial_state = AssessmentState(
            patient_name=patient_name,
            age=patient_age,
            target_word=target_word,
            audio_path=path,
            sample_rate=None,
            audio=None,
            child_audio=None,
            transcript=None,
            spoken_word=None,
            expected_phonemes=[],
            spoken_phonemes=[],
            phoneme_accuracy=None,
            phoneme_matches=[],
            expected_phonemes_display=[],
            spoken_phonemes_display=[],
            duration=None,
            pitch=None,
            loudness=None,
            accuracy=None,
            feedback=None,
            stars=None,
            reasoning=None,
            recommendations=[],
            error_patterns=[],
            severity_score=None,
            diagnostic_report=None,
            targeted_quests=[],
            error=None
        )

        # 3. Invoke assessment diagnostic graph
        result_state = assessment_graph.invoke(initial_state)

        if result_state.get("error"):
            raise Exception(result_state["error"])

        # 4. Return results payload
        return {
            "patient_name": patient_name,
            "target_word": target_word,
            "accuracy": result_state["accuracy"],
            "phoneme_matches": result_state["phoneme_matches"],
            "expected_phonemes": result_state["expected_phonemes"],
            "spoken_phonemes": result_state["spoken_phonemes"],
            "expected_phonemes_display": result_state["expected_phonemes_display"],
            "spoken_phonemes_display": result_state["spoken_phonemes_display"],
            "pitch": result_state["pitch"],
            "duration": result_state["duration"],
            "loudness": result_state["loudness"],
            "reasoning": result_state["reasoning"],
            "recommendations": result_state["recommendations"],
            "error_patterns": result_state["error_patterns"],
            "severity_score": result_state["severity_score"],
            "diagnostic_report": result_state["diagnostic_report"],
            "targeted_quests": result_state["targeted_quests"]
        }

    except Exception as e:
        print("DIAGNOSTIC ASSESSMENT ERROR:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostic check failed: {str(e)}"
        )
    finally:
        # Cleanup audio
        delete_audio(path)