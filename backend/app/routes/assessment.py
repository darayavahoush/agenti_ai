from fastapi import APIRouter, Depends, HTTPException, Response, status, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from pathlib import Path
from app.database import SessionLocal
from app.models.assessment_word import AssessmentWord
from app.services.image.matcher import get_image_for_phrase
from app.tools.audio_tool import save_audio, delete_audio
from app.state.assessment_state import AssessmentState
from app.graph.assessment_graph import assessment_graph
from app.services.audio_service import AudioService, CoquiTTSEngine


router = APIRouter(tags=["Assessment"])

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
        logger.info("✅ Assessment analysis completed successfully")
        logger.info(f"📊 Final accuracy: {result_state['accuracy']}")
        logger.info(f"🗣️ Spoken word: {result_state['spoken_word']}")
        logger.info(f"🔊 Phoneme accuracy: {result_state['phoneme_accuracy']}")
        
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
        logger.error(f"DIAGNOSTIC ASSESSMENT ERROR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostic check failed: {str(e)}"
        )
    finally:
        # Cleanup audio
        delete_audio(path)