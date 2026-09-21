from fastapi import APIRouter, Depends, HTTPException, Response, status, UploadFile, File, Form, Header
import asyncio
import os
from typing import Literal
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from pathlib import Path
from app.database import SessionLocal
from app.models.assessment_word import AssessmentWord
from app.models.patient import Patient
from app.models.breathquest_models import BreathQuestPatient
from app.models.therapist import Therapist
from app.models.session import Session as SessionModel
from app.services.image.matcher import get_image_for_phrase
from app.tools.audio_tool import save_audio, delete_audio
from app.state.assessment_state import AssessmentState
from app.graph.assessment_graph import assessment_graph
from app.services.audio_service import AudioService, CoquiTTSEngine
from app.deps.therapist_auth_deps import get_current_therapist
from app.retraining import data_store
from agent.service import AgentService


router = APIRouter(tags=["Assessment"])

# Assessment has no level_id/game loop like BreathQuest/Chime/VaakMirror/
# Flashcards -- each /analyze call is a one-off diagnostic on a possibly
# different target_word, so there's no repeated "same level" to accumulate
# RL events against at the word level. But phonemes DO repeat across
# different words (and even different languages' target-word translations),
# so -- same trick as Flashcards' fc_{phoneme} -- key the RL level_id per
# phoneme instead of per word. That's what gives tabular_q/etc. enough
# repeated observations of the same "level" to ever progress past
# rule_based here.
_agent_service = AgentService(db_path=data_store.DEFAULT_DB_PATH, recent_window=10)


def _assess_level_id(phoneme: str) -> str:
    return f"assess_{phoneme.strip().lower()}"


def _next_attempt_number(patient_id: str, level_id: str) -> int:
    """Assessment has no PhonemeMastery-style aggregate table (Flashcards'
    own running per-phoneme counter) to read from, so derive the next
    attempt_number from the shared RL event log itself -- the same store
    every game's events already live in and that get_status()/decide() read
    from. Fine at Assessment's call volume (diagnostic sessions, not a fast
    game loop); an aggregate table would be the right move if this needs to
    scale further."""
    events = data_store.get_events(child_id=patient_id)
    return 1 + sum(1 for e in events if e["level_id"] == level_id)

ASSESSMENT_SERVICE_API_KEY = os.getenv("ASSESSMENT_SERVICE_API_KEY")


def verify_service_api_key(x_api_key: str = Header(None)):
    """Service-to-service auth for cross-app calls (e.g. quest-games pulling
    a diagnostic result). Not a user-facing auth path."""
    if not ASSESSMENT_SERVICE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ASSESSMENT_SERVICE_API_KEY is not configured on this server",
        )
    if not x_api_key or x_api_key != ASSESSMENT_SERVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing service API key")

class ServicePatientCreate(BaseModel):
    """Sibling to the JWT-protected POST /api/v1/patients (routers/
    therapist_patients.py) -- for service-to-service creation on behalf of
    a quest-games therapist, who can't hold an agenti_ai JWT directly (see
    the 2026-08-10 branch note on the two separate Therapist auth systems).
    therapist_email is a soft link (matched against Therapist.email, not a
    stored FK) -- if the emails ever diverge between the two systems, this
    breaks. Acceptable tradeoff for now; a hard link would need its own
    migration this branch doesn't scope."""
    name: str
    therapist_email: str
    age: int | None = None
    date_of_birth: str | None = None
    language: str | None = None
    gender: str | None = None
    diagnosis: str | None = None
    parent_name: str | None = None
    parent_contact: str | None = None
    email: str | None = None


@router.post("/patients", dependencies=[Depends(verify_service_api_key)])
def create_patient_for_therapist(data: ServicePatientCreate):
    """Service-authenticated patient creation, called by quest-games'
    routers/patients.py proxy so a therapist logged into BreathQuest can
    create a real Assessment-origin patient without holding an agenti_ai
    JWT. Resolves the therapist by email (see ServicePatientCreate's
    docstring) -- 404s clearly rather than creating an orphaned patient
    with no registered_therapist_id if no match exists.

    Manual SessionLocal(), not Depends(get_db) -- get_db is async-only
    (see app/database.py), while this file's other routes all use the
    sync ORM API via manually opened/closed sessions. Matching that
    pattern here rather than mixing an AsyncSession into sync .query()
    calls, which would fail at request time despite compiling fine."""
    db = SessionLocal()
    try:
        therapist = db.query(Therapist).filter(Therapist.email == data.therapist_email).first()
        if not therapist:
            raise HTTPException(
                status_code=404,
                detail=f"No Assessment therapist account found for email {data.therapist_email!r}",
            )

        patient = Patient(
            name=data.name, age=data.age, date_of_birth=data.date_of_birth,
            language=data.language, gender=data.gender, diagnosis=data.diagnosis,
            therapist_name=therapist.full_name, parent_name=data.parent_name,
            parent_contact=data.parent_contact, email=data.email,
            registered_therapist_id=therapist.id,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return {"id": str(patient.id), "name": patient.name}
    finally:
        db.close()


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
        "translations": {
            "english": item.english,
            "telugu": item.telugu,
            "hindi": item.hindi,
            "tamil": item.tamil,
            "kannada": item.kannada,
            "malayalam": item.malayalam,
            "bengali": item.bengali,
            "marathi": item.marathi,
        }
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


@router.get("/audio/{word_key}/{language}")
def get_word_audio(word_key: str, language: str, db: Session = Depends(get_db)):
    """
    Get audio pronunciation for a word in a specific language.
    Uses cached audio if available, otherwise generates it using TTS.
    
    Path parameters:
        word_key: The word key to look up in the database
        language: Language code (en, te, hi, ta, kn, ml, bn, mr)
    
    Returns:
        WAV audio file
    """
    if not word_key or not word_key.strip():
        raise HTTPException(status_code=400, detail="word_key parameter is required")
    if not language or not language.strip():
        raise HTTPException(status_code=400, detail="language parameter is required")
    
    # Validate language code
    valid_languages = {"en", "te", "hi", "ta", "kn", "ml", "bn", "mr"}
    if language.lower() not in valid_languages:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid language code. Valid codes: {', '.join(sorted(valid_languages))}"
        )
    
    try:
        # Initialize AudioService with CoquiTTSEngine
        tts_engine = CoquiTTSEngine()
        audio_service = AudioService(tts_engine=tts_engine, db=db)
        
        # Generate or retrieve cached audio
        audio_path, was_generated = audio_service.generate_audio(word_key, language)
        
        if not audio_path or not audio_path.exists():
            raise HTTPException(status_code=500, detail="Failed to generate audio file")
        
        # Read audio file
        audio_bytes = audio_path.read_bytes()
        
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"inline; filename={word_key}_{language}.wav",
                "Cache-Control": "public, max-age=31536000",  # Cache for 1 year
                "X-Audio-Generated": "true" if was_generated else "false"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Audio generation failed: {str(e)}"
        )


@router.get("/audio/{word_key}/{language}/exists")
def check_audio_exists(word_key: str, language: str, db: Session = Depends(get_db)):
    """
    Check if audio file exists for a word in a specific language.
    
    Path parameters:
        word_key: The word key to look up in the database
        language: Language code (en, te, hi, ta, kn, ml, bn, mr)
    
    Returns:
        JSON with exists boolean
    """
    if not word_key or not word_key.strip():
        raise HTTPException(status_code=400, detail="word_key parameter is required")
    if not language or not language.strip():
        raise HTTPException(status_code=400, detail="language parameter is required")
    
    # Validate language code
    valid_languages = {"en", "te", "hi", "ta", "kn", "ml", "bn", "mr"}
    if language.lower() not in valid_languages:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid language code. Valid codes: {', '.join(sorted(valid_languages))}"
        )
    
    try:
        # Initialize AudioService
        tts_engine = CoquiTTSEngine()
        audio_service = AudioService(tts_engine=tts_engine, db=db)
        
        # Check if audio exists
        exists = audio_service.audio_exists(word_key, language)
        
        return {"exists": exists, "word_key": word_key, "language": language}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check audio existence: {str(e)}"
        )


@router.post("/audio/{word_key}/{language}/upload")
async def upload_audio(
    word_key: str, 
    language: str, 
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a recorded audio file for a word in a specific language.
    Saves the audio to the cache directory, overwriting any existing file.
    
    Path parameters:
        word_key: The word key to look up in the database
        language: Language code (en, te, hi, ta, kn, ml, bn, mr)
    
    Request body:
        file: Audio file (WAV format recommended)
    
    Returns:
        JSON with success status
    """
    if not word_key or not word_key.strip():
        raise HTTPException(status_code=400, detail="word_key parameter is required")
    if not language or not language.strip():
        raise HTTPException(status_code=400, detail="language parameter is required")
    
    # Validate language code
    valid_languages = {"en", "te", "hi", "ta", "kn", "ml", "bn", "mr"}
    if language.lower() not in valid_languages:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid language code. Valid codes: {', '.join(sorted(valid_languages))}"
        )
    
    try:
        # Initialize AudioService
        tts_engine = CoquiTTSEngine()
        audio_service = AudioService(tts_engine=tts_engine, db=db)
        
        # Get the target audio path
        audio_path = audio_service.get_audio_path(word_key, language)
        
        # Create directory if it doesn't exist
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read and save the uploaded file
        audio_bytes = await file.read()
        audio_path.write_bytes(audio_bytes)
        
        return {
            "success": True,
            "word_key": word_key,
            "language": language,
            "path": str(audio_path),
            "message": "Audio uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload audio: {str(e)}"
        )


@router.post("/analyze")
async def analyze_assessment_pronunciation(
    file: UploadFile = File(...),
    patient_name: str = Form(...),
    patient_age: int | None = Form(None),
    patient_id: str | None = Form(None),
    target_word: str = Form(...),
    language: str = Form(default="en")
):
    """
    Run diagnostic Multi-Agent Assessment Graph on child voice recording.
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("🎯 Assessment analyze request received")
    logger.info(f"👤 Patient: {patient_name}")
    logger.info(f"🎯 Target word: {target_word}")
    logger.info(f"🌐 Language: {language}")
    
    # Common word mappings for Indian languages (fallback when database translations are missing)
    COMMON_WORD_MAPPINGS = {
        "te": {  # Telugu
            # Animals
            "dog": "కుక్క",
            "cat": "పిల్లి", 
            "bird": "పక్షి",
            "cow": "ఆవు",
            "horse": "గుర్రం",
            # Objects
            "ball": "బంతి",
            "book": "పుస్తకం",
            "car": "కారు",
            "house": "ఇల్లు",
            "tree": "చెట్టు",
            # Nature
            "water": "నీరు",
            "food": "ఆహారం",
            "sun": "సూర్యుడు",
            "moon": "చంద్రుడు",
            "star": "నక్షత్రం",
            "flower": "పూవు",
            "fruit": "పండు",
            # Family
            "mother": "తల్లి",
            "father": "తండ్రి",
            "child": "పిల్ల",
            "brother": "తమ్ముడు",
            "sister": "చెల్లి",
            # Education
            "school": "పాఠశాల",
            "teacher": "ఉపాధ్యాయుడు",
            # Numbers
            "one": "ఒకటి",
            "two": "రెండు",
            "three": "మూడు",
            "four": "నాలుగు",
            "five": "ఐదు",
            "six": "ఆరు",
            "seven": "ఏడు",
            "eight": "ఎనిమిది",
            "nine": "తొమ్మిది",
            "ten": "పది",
            # Body parts
            "head": "తల",
            "eye": "కన్ను",
            "ear": "చెవి",
            "nose": "ముక్కు",
            "mouth": "నోరు",
            "hand": "చేయి",
            "leg": "కాలు",
            "heart": "గుండె",
            # Emotions
            "happy": "సంతోషం",
            "sad": "బాధ",
            "angry": "కోపం",
            "love": "ప్రేమ",
            "fear": "భయం",
            # Colors
            "red": "ఎరుపు",
            "blue": "నీలం",
            "green": "ఆకుపచ్చ",
            "yellow": "పసుపు",
            "white": "తెలుపు",
            "black": "నలుపు"
        },
        "kn": {  # Kannada
            # Animals
            "dog": "ನಾಯಿ",
            "cat": "ಬೆಕ್ಕು",
            "bird": "ಹಕ್ಕಿ", 
            "cow": "ಹಸು",
            "horse": "ಕುದುರೆ",
            # Objects
            "ball": "ಚೆಂಡು",
            "book": "ಪುಸ್ತಕ",
            "car": "ಕಾರ್",
            "house": "ಮನೆ",
            "tree": "ಮರ",
            # Nature
            "water": "ನೀರು",
            "food": "ಆಹಾರ",
            "sun": "ಸೂರ್ಯ",
            "moon": "ಚಂದ್ರ",
            "star": "ನಕ್ಷತ್ರ",
            "flower": "ಹೂವು",
            "fruit": "ಹಣ್ಣು",
            # Family
            "mother": "ತಾಯಿ",
            "father": "ತಂದೆ",
            "child": "ಮಗು",
            "brother": "ಸಹೋದರ",
            "sister": "ಸಹೋದರಿ",
            # Education
            "school": "ಶಾಲೆ",
            "teacher": "ಶಿಕ್ಷಕ",
            # Numbers
            "one": "ಒಂದು",
            "two": "ಎರಡು",
            "three": "ಮೂರು",
            "four": "ನಾಲ್ಕು",
            "five": "ಐದು",
            "six": "ಆರು",
            "seven": "ಏಳು",
            "eight": "ಎಂಟು",
            "nine": "ಒಂಬತ್ತು",
            "ten": "ಹತ್ತು",
            # Body parts
            "head": "ತಲೆ",
            "eye": "ಕಣ್ಣು",
            "ear": "ಕಿವಿ",
            "nose": "ಮೂಗು",
            "mouth": "ಬಾಯಿ",
            "hand": "ಕೈ",
            "leg": "ಕಾಲು",
            "heart": "ಹೃದಯ",
            # Emotions
            "happy": "ಸಂತೋಷ",
            "sad": "ದುಃಖ",
            "angry": "ಕೋಪ",
            "love": "ಪ್ರೀತಿ",
            "fear": "ಭಯ",
            # Colors
            "red": "ಕೆಂಪು",
            "blue": "ನೀಲಿ",
            "green": "ಹಸಿರು",
            "yellow": "ಹಳದಿ",
            "white": "ಬಿಳಿ",
            "black": "ಕಪ್ಪು"
        },
        "hi": {  # Hindi
            # Animals
            "dog": "कुत्ता",
            "cat": "बिल्ली",
            "bird": "पक्षी",
            "cow": "गाय",
            "horse": "घोड़ा",
            # Objects
            "ball": "गेंद",
            "book": "किताब",
            "car": "गाड़ी",
            "house": "घर",
            "tree": "पेड़",
            # Nature
            "water": "पानी",
            "food": "खाना",
            "sun": "सूरज",
            "moon": "चाँद",
            "star": "तारा",
            "flower": "फूल",
            "fruit": "फल",
            # Family
            "mother": "माँ",
            "father": "पिता",
            "child": "बच्चा",
            "brother": "भाई",
            "sister": "बहन",
            # Education
            "school": "स्कूल",
            "teacher": "शिक्षक",
            # Numbers
            "one": "एक",
            "two": "दो",
            "three": "तीन",
            "four": "चार",
            "five": "पाँच",
            "six": "छह",
            "seven": "सात",
            "eight": "आठ",
            "nine": "नौ",
            "ten": "दस",
            # Body parts
            "head": "सिर",
            "eye": "आँख",
            "ear": "कान",
            "nose": "नाक",
            "mouth": "मुँह",
            "hand": "हाथ",
            "leg": "पैर",
            "heart": "दिल",
            # Emotions
            "happy": "खुशी",
            "sad": "दुख",
            "angry": "गुस्सा",
            "love": "प्यार",
            "fear": "डर",
            # Colors
            "red": "लाल",
            "blue": "नीला",
            "green": "हरा",
            "yellow": "पीला",
            "white": "सफेद",
            "black": "काला"
        }
    }
    
    # For Indian languages, try to get translated target word from database or common mappings
    indian_languages = ["hi", "te", "kn", "ta", "ml", "bn", "mr"]
    
    if language in indian_languages:
        # First try database
        db = SessionLocal()
        try:
            word_record = db.query(AssessmentWord).filter(
                AssessmentWord.word == target_word
            ).first()
            
            if word_record:
                # Map language codes to database columns
                lang_column_map = {
                    "hi": "hindi",
                    "te": "telugu", 
                    "kn": "kannada",
                    "ta": "tamil",
                    "ml": "malayalam",
                    "bn": "bengali",
                    "mr": "marathi",
                    "en": "english"
                }
                
                column_name = lang_column_map.get(language, "english")
                translated_word = getattr(word_record, column_name, None)
                
                if translated_word and translated_word.strip():
                    logger.info(f"🌐 Using translated word from database: {target_word} -> {translated_word}")
                    target_word = translated_word
                else:
                    logger.info(f"⚠️ No database translation for {language}, checking common word mappings")
                    # Try common word mappings
                    if language in COMMON_WORD_MAPPINGS and target_word.lower() in COMMON_WORD_MAPPINGS[language]:
                        mapped_word = COMMON_WORD_MAPPINGS[language][target_word.lower()]
                        logger.info(f"📖 Using common word mapping: {target_word} -> {mapped_word}")
                        target_word = mapped_word
                    else:
                        logger.info(f"⚠️ No mapping found for {target_word}, using original English word")
            else:
                logger.info(f"⚠️ Word record not found for: {target_word}, checking common word mappings")
                # Try common word mappings
                if language in COMMON_WORD_MAPPINGS and target_word.lower() in COMMON_WORD_MAPPINGS[language]:
                    mapped_word = COMMON_WORD_MAPPINGS[language][target_word.lower()]
                    logger.info(f"📖 Using common word mapping: {target_word} -> {mapped_word}")
                    target_word = mapped_word
                else:
                    logger.info(f"⚠️ No mapping found for {target_word}, using original English word")
        finally:
            db.close()
    
    # 1. Save audio file locally
    path = save_audio(file)

    try:
        # 2. Build initial AssessmentState
        initial_state = AssessmentState(
            patient_name=patient_name,
            age=patient_age,
            target_word=target_word,
            language=language,
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
            vocal_reasoning=None,
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

        # 4. Save session to database if patient_id is provided
        session_id = None
        logger.info(f"🔍 Checking patient_id: {patient_id}, type: {type(patient_id)}")
        if patient_id and patient_id.strip() and patient_id != "":
            try:
                db = SessionLocal()
                # Verify patient exists
                patient = db.query(Patient).filter(Patient.id == patient_id).first()
                logger.info(f"🔍 Patient lookup result: {patient}")
                if patient:
                    # Calculate stars based on accuracy
                    accuracy = result_state.get("accuracy", 0)
                    if accuracy >= 90:
                        stars = 5
                    elif accuracy >= 75:
                        stars = 4
                    elif accuracy >= 60:
                        stars = 3
                    elif accuracy >= 45:
                        stars = 2
                    else:
                        stars = 1

                    # Create session record
                    session = SessionModel(
                        patient_id=patient_id,
                        target_word=target_word,
                        spoken_word=result_state.get("spoken_word", ""),
                        accuracy=int(accuracy) if accuracy else 0,
                        # NOTE: was result_state.get("reasoning", ...) -- "reasoning"
                        # is speech_analysis_agent's internal audio-channel-selection
                        # note (e.g. "Isolated child voice segment selected"), which
                        # was also getting silently overwritten by vocal_acoustic_agent
                        # writing to the same key (see vocal_acoustic_agent.py). Neither
                        # value is meant for the child/parent -- the actual pronunciation
                        # feedback ("Excellent pronunciation! 🎉", "Try full word 'X'.")
                        # is generate_feedback()'s output, stored in state["feedback"].
                        feedback=result_state.get("feedback", "")[:500],  # Limit feedback length
                        stars=stars,
                        f0_mean=result_state.get("pitch"),
                        mpt=result_state.get("duration"),
                        hnr=result_state.get("loudness"),
                        session_type="word_practice",
                        # Diagnostic findings — previously computed by the assessment graph
                        # and returned to the frontend, but never persisted. severity_score is
                        # a text classification (e.g. "Mild to Moderate"), not numeric — see
                        # articulation_diagnostic_agent.py / assessment_state.py.
                        severity_classification=(
                            str(result_state.get("severity_score"))
                            if result_state.get("severity_score") is not None
                            else None
                        ),
                        error_patterns=result_state.get("error_patterns") or [],
                        targeted_quests=result_state.get("targeted_quests") or [],
                        diagnostic_report=result_state.get("diagnostic_report"),
                    )
                    db.add(session)
                    db.commit()
                    db.refresh(session)
                    session_id = session.id
                    logger.info(f"✅ Session saved for patient {patient_id} (session_id={session_id})")

                    # Log one RL event per phoneme in this attempt (not one
                    # per word) -- see _assess_level_id's docstring above
                    # for why per-phoneme is what makes the agent ladder
                    # viable for a diagnostic app with no repeated levels.
                    #
                    # child_id here must be BreathQuestPatient.id, not
                    # patient_id (the Assessment-side Patient.id): every
                    # other game's RL events are keyed by the FK target of
                    # breathquest_rl_training_events.child_id, which is
                    # breathquest_patients.id (see breath_agent.py/chime.py/
                    # voicehurdlerace.py, which all use patient.id off a
                    # BreathQuestPatient row). Logging against patient_id
                    # directly -- as this block did before -- passes an ID
                    # that doesn't exist in breathquest_patients at all,
                    # which raised a silent-at-call-time-but-fatal
                    # ForeignKeyViolation on every single /analyze call
                    # since this shipped (confirmed via log_test_assessment_event.py).
                    bq_patient = (
                        db.query(BreathQuestPatient)
                        .filter(BreathQuestPatient.assessment_patient_id == patient_id)
                        .first()
                    )
                    if bq_patient is None:
                        logger.warning(
                            f"⚠️ Patient {patient_id} has no linked BreathQuestPatient "
                            "(assessment_patient_id link missing) -- skipping RL event "
                            "logging for this attempt. Session was still saved."
                        )
                    else:
                        child_id = str(bq_patient.id)
                        for match in (result_state.get("phoneme_matches") or []):
                            expected = match.get("expected")
                            if not expected:
                                continue
                            level_id = _assess_level_id(str(expected))
                            attempt_number = await asyncio.to_thread(
                                _next_attempt_number, child_id, level_id
                            )
                            await asyncio.to_thread(
                                data_store.add_event,
                                child_id=child_id,
                                level_id=level_id,
                                attempt_number=attempt_number,
                                score=1.0 if match.get("correct") else 0.0,
                                is_valid_attempt=True,
                                threshold_at_time=None,
                                action=None,
                                quit_flag=False,
                                raw_features={
                                    "target_word": target_word,
                                    "detected": match.get("detected"),
                                },
                                severity_numeric=0.0,
                                is_targeted_sound=False,
                                policy_used=None,
                                downgrade_reason=None,
                                recommended_action=None,
                                recommendation_message=None,
                                db_path=data_store.DEFAULT_DB_PATH,
                            )
                            _agent_service.maybe_update_tabular_q_from_new_event(
                                child_id, level_id, quit_flag=False
                            )
                else:
                    logger.warning(f"⚠️ Patient {patient_id} not found, session not saved")
                db.close()
            except Exception as e:
                logger.error(f"❌ Failed to save session: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Don't raise error, continue to return results
        else:
            logger.warning(f"⚠️ No valid patient_id provided, skipping session save")

        # 5. Return results payload
        logger.info("✅ Assessment analysis completed successfully")
        logger.info(f"📊 Final accuracy: {result_state['accuracy']}")
        logger.info(f"🗣️ Spoken word: {result_state['spoken_word']}")
        logger.info(f"🔊 Phoneme accuracy: {result_state['phoneme_accuracy']}")
        
        return {
            "session_id": session_id,
            "patient_name": patient_name,
            "target_word": target_word,
            "spoken_word": result_state["spoken_word"],
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
        logger.error(f"DIAGNOSTIC ASSESSMENT ERROR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostic check failed: {str(e)}"
        )
    finally:
        # Cleanup audio
        delete_audio(path)



@router.post("/alphabet/analyze")
async def analyze_alphabet_letter(
    file: UploadFile = File(...),
    letter: str = Form(...),
    patient_name: str = Form(default="Child"),
):
    """
    One letter of the Alphabet check. The child says a short keyword that
    starts with the letter's sound ("ball" for B); the alphabet LangGraph
    (graph/alphabet_graph.py) runs the same speech + articulation agents the
    word assessment uses, then keeps only that letter's own sound.

    Deliberately writes nothing: results are collected by the client and
    saved once, with the VaakMirror plan, by POST /assessment/alphabet/complete
    (which is authenticated). Same unauthenticated shape as /analyze.
    """
    from app.services.alphabet_sounds import LETTERS
    from app.graph.alphabet_graph import get_letter_graph
    from app.state.alphabet_state import AlphabetState

    key = (letter or "").strip().upper()
    spec = LETTERS.get(key)
    if spec is None:
        raise HTTPException(status_code=400, detail=f"'{letter}' can't be checked by voice.")

    path = save_audio(file)
    try:
        initial = AlphabetState(
            patient_name=patient_name, age=None, target_word=spec["word"], language="en",
            audio_path=path, sample_rate=None, audio=None, child_audio=None,
            transcript=None, spoken_word=None, expected_phonemes=[], spoken_phonemes=[],
            phoneme_accuracy=None, phoneme_matches=[], expected_phonemes_display=[],
            spoken_phonemes_display=[], duration=None, pitch=None, loudness=None,
            accuracy=None, feedback=None, stars=None, reasoning=None, vocal_reasoning=None,
            recommendations=[], error_patterns=[], severity_score=None,
            diagnostic_report=None, targeted_quests=[], error=None,
            letter=key, letter_result=None,
        )
        result = await asyncio.to_thread(get_letter_graph().invoke, initial)
        if result.get("error"):
            raise HTTPException(status_code=500, detail=f"Letter check failed: {result['error']}")
        letter_result = result.get("letter_result")
        if letter_result is None:
            raise HTTPException(status_code=500, detail="Letter check produced no result")
        return {"letter_result": letter_result}
    finally:
        delete_audio(path)


@router.get("/patients/{patient_id}/latest", dependencies=[Depends(verify_service_api_key)])
def get_latest_assessment_for_patient(patient_id: str, db: Session = Depends(get_db)):
    """
    Service-to-service read of a patient's most recent word_practice
    diagnostic — used by quest-games' agent/diagnostic_client.py to pull
    current severity + targeted quests. Unlike GET /{ref} below (which
    needs a specific session id), this answers "what's this kid's current
    diagnosis" by patient id, most-recent-first. Same
    ASSESSMENT_SERVICE_API_KEY auth as the existing route.
    """
    session = (
        db.query(SessionModel)
        .filter(SessionModel.patient_id == patient_id, SessionModel.session_type == "word_practice")
        .order_by(SessionModel.created_at.desc())
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="No assessment found for this patient")

    return {
        "session_id": session.id,
        "patient_id": session.patient_id,
        "severity_classification": session.severity_classification,
        "targeted_quests": session.targeted_quests,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.get("/therapists", dependencies=[Depends(verify_service_api_key)])
def list_therapist_candidates(db: Session = Depends(get_db)):
    """
    Distinct therapist names already recorded during Assessment intake —
    used by quest-games' auth.py to populate a therapist-selection dropdown
    at BreathQuest registration instead of requiring a fresh typed name.
    """
    names = (
        db.query(Patient.therapist_name)
        .filter(Patient.therapist_name.isnot(None), func.trim(Patient.therapist_name) != "")
        .distinct()
        .order_by(Patient.therapist_name)
        .all()
    )
    return [name for (name,) in names]


@router.get("/patients", dependencies=[Depends(verify_service_api_key)])
def list_patient_candidates(db: Session = Depends(get_db)):
    """
    Active patients already created through Assessment — used by
    quest-games' auth.py to populate the kid-selection list at BreathQuest
    PIN setup.
    """
    patients = (
        db.query(Patient)
        .filter(Patient.is_active.is_(True))
        .order_by(Patient.name)
        .all()
    )
    return [{"id": str(p.id), "name": p.name} for p in patients]


@router.get("/patients/{patient_id}", dependencies=[Depends(verify_service_api_key)])
def get_patient_record(patient_id: str, db: Session = Depends(get_db)):
    """
    Single Assessment patient record by id (name + active status) — used by
    quest-games' auth.py to verify a patient exists and is active before
    linking a BreathQuest PIN account to them. Distinct from
    /patients/{patient_id}/latest below, which returns a diagnostic session,
    not the patient record itself.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"id": str(patient.id), "name": patient.name, "is_active": patient.is_active}


@router.get("/{ref}", dependencies=[Depends(verify_service_api_key)])
def get_assessment_result(ref: str, db: Session = Depends(get_db)):
    """
    Service-to-service read of a persisted diagnostic result, keyed by the
    Session row id returned from POST /assessment/analyze. Protected by
    ASSESSMENT_SERVICE_API_KEY (X-API-Key header) — not a user-facing route.
    """
    try:
        session_id = int(ref)
    except ValueError:
        raise HTTPException(status_code=422, detail="ref must be a numeric session id")

    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.session_type == "word_practice")
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Assessment result not found")

    return {
        "session_id": session.id,
        "patient_id": session.patient_id,
        "target_word": session.target_word,
        "accuracy": session.accuracy,
        "severity_classification": session.severity_classification,
        "error_patterns": session.error_patterns,
        "targeted_quests": session.targeted_quests,
        "diagnostic_report": session.diagnostic_report,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


class AgentStatusObs(BaseModel):
    success_rate: float
    difficulty: float
    frustration: float
    severity_numeric: float
    is_targeted_sound: bool


class AgentStatusOut(BaseModel):
    policy: str
    requested_policy: str
    n_events_considered: int
    downgrade_reason: str | None
    obs: AgentStatusObs


def _get_own_patient(patient_id: str, therapist: Therapist, db: Session) -> Patient:
    """Assessment's own Patient IS the assessment-origin record (unlike
    BreathQuest/Chime/etc., which look it up indirectly via
    BreathQuestPatient.assessment_patient_id) -- so patient_id here is just
    Patient.id, ownership-checked directly against the calling therapist."""
    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id, Patient.registered_therapist_id == therapist.id)
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _get_rl_child_id(patient: Patient, db: Session) -> str:
    """RL events for Assessment are logged with child_id = BreathQuestPatient.id,
    not Patient.id (see the /analyze RL-logging fix -- breathquest_rl_training_events.child_id
    has an FK on breathquest_patients.id, same as every other game). Reads
    must resolve the same BreathQuestPatient link, or they'll query a
    child_id that was never actually written -- which is what quietly broke
    AgentInsight even after fixing the write side, since both this read
    path and the old write path agreed on using Patient.id directly."""
    bq_patient = (
        db.query(BreathQuestPatient)
        .filter(BreathQuestPatient.assessment_patient_id == patient.id)
        .first()
    )
    if bq_patient is None:
        raise HTTPException(
            status_code=404,
            detail="This child has no linked BreathQuest account, so no Assessment agent data exists yet.",
        )
    return str(bq_patient.id)


@router.get("/agent/status/{patient_id}", response_model=AgentStatusOut)
def assessment_agent_status(
    patient_id: str,
    level_id: str,
    policy: Literal["rule_based", "bandit", "tabular_q", "ppo", "recurrent_ppo"] = "tabular_q",
    therapist: Therapist = Depends(get_current_therapist),
    db: Session = Depends(get_db),
):
    patient = _get_own_patient(patient_id, therapist, db)
    child_id = _get_rl_child_id(patient, db)
    result = _agent_service.get_status(child_id, level_id, policy)
    return AgentStatusOut(**result)


@router.get("/agent/levels/{patient_id}")
def assessment_agent_levels(
    patient_id: str,
    therapist: Therapist = Depends(get_current_therapist),
    db: Session = Depends(get_db),
):
    """Unlike the other four games, Assessment has no fixed level list --
    which phonemes exist for this child depends on which words (in which
    language) they've actually been assessed on. Derive the list from this
    child's own logged agent events rather than a static table, so
    AgentInsight.jsx can build its level picker dynamically per patient."""
    patient = _get_own_patient(patient_id, therapist, db)
    child_id = _get_rl_child_id(patient, db)
    events = data_store.get_events(child_id=child_id)
    phonemes = sorted({
        e["level_id"][len("assess_"):]
        for e in events
        if e["level_id"].startswith("assess_")
    })
    return {"phonemes": phonemes}
