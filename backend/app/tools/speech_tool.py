import os
import re
import tempfile
from typing import Optional
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from rapidfuzz import fuzz
from app.utils.transliteration_utils import convert_whisper_output_to_native
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# LOAD MODELS
# ---------------------------------------------------
# Language code mapping for Whisper
LANGUAGE_CODES = {
    "en": "en",
    "hi": "hi",
    "te": "te",
    "kn": "kn",
    "ta": "ta",
    "ml": "ml",
    "bn": "bn",
    "mr": "mr"
}

try:
    # Load multilingual model instead of English-only
    whisper_model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )

    logger.info("✅ Faster-Whisper multilingual model loaded")

except Exception as e:
    whisper_model = None
    logger.error(f"❌ Faster-Whisper error: {e}")
    # Fallback to English-only model if multilingual fails
    try:
        whisper_model = WhisperModel(
            "base.en",
            device="cpu",
            compute_type="int8"
        )
        logger.info("✅ Faster-Whisper English-only model loaded as fallback")
    except Exception as e2:
        logger.error(f"❌ Faster-Whisper fallback also failed: {e2}")


# ---------------------------------------------------
# NORMALIZE TEXT
# ---------------------------------------------------
_NUMBER_WORDS = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


def normalize_text(text: str) -> str:
    if text is None:
        return ""

    text = str(text).strip().lower()
    if not text:
        return ""

    # Convert numeric tokens like "7" or "7." into spoken words before
    # stripping punctuation so assessment targets and transcripts match.
    text = re.sub(r"\d+", lambda m: " ".join(_NUMBER_WORDS[d] for d in m.group(0)), text)

    # Preserve multilingual scripts but drop punctuation and normalize spacing.
    if any(ord(c) > 127 for c in text):
        normalized = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        return " ".join(normalized.split())

    normalized = re.sub(r"[^a-z\s]", " ", text)
    normalized = " ".join(normalized.split())
    return normalized


# ---------------------------------------------------
# TRANSCRIPTION
# ---------------------------------------------------
def transcribe(y: np.ndarray, sr: int, prompt: Optional[str] = None, language: str = "en") -> str:
    # For Indian languages, try Vosk first (lightweight, native script output)
    indian_languages = ["hi", "te", "kn", "ta", "ml", "bn", "mr"]
    
    if language in indian_languages:
        try:
            from app.tools.vosk_tool import transcribe_with_vosk, is_vosk_available
            
            if is_vosk_available(language):
                logger.info(f"🎤 Using Vosk for {language} transcription")
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp_path = tmp.name
                tmp.close()
                
                try:
                    sf.write(tmp_path, y, sr)
                    text = transcribe_with_vosk(tmp_path, language)
                    if text:
                        return text
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            else:
                logger.warning(f"⚠️ Vosk model not available for {language}, Whisper will return English transliteration")
                logger.info(f"💡 Install Vosk models for native script output: python setup_vosk_models.py {language}")
        except ImportError:
            logger.warning("⚠️ Vosk not installed, Whisper will return English transliteration")
            logger.info(f"💡 Install Vosk: pip install vosk && python setup_vosk_models.py {language}")
        except Exception as e:
            logger.warning(f"⚠️ Vosk transcription failed: {e}, falling back to Whisper")
    
    # Fallback to Whisper for English or if Vosk is not available
    if whisper_model is None:
        logger.error("❌ Whisper model not available")
        return ""

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        sf.write(tmp_path, y, sr)
        logger.info(f"🎤 Transcribing file: {tmp_path} with language: {language} audio length: {len(y)} sample rate: {sr}")
        
        # Map language code to Whisper language code
        whisper_lang = LANGUAGE_CODES.get(language, "en")
        logger.info(f"🌐 Using Whisper language code: {whisper_lang}")
        
        # `prompt` (the target word the child was asked to say) was being
        # accepted as a parameter but never actually passed to Whisper --
        # it was silently dropped, so short/ambiguous kid audio ("eight" vs
        # noise) got no bias toward the expected word at all. initial_prompt
        # nudges Whisper toward vocabulary matching the assessment target.
        segments, info = whisper_model.transcribe(
            tmp_path,
            language=whisper_lang,
            beam_size=5,
            initial_prompt=prompt if prompt else None
        )

        text = " ".join(
            segment.text
            for segment in segments
        )
        logger.info(f"📝 Transcription result: {text}")
        
        # For Indian languages, Whisper returns English transliteration
        # Convert it back to native script for proper phoneme extraction
        if language in indian_languages and text:
            native_text = convert_whisper_output_to_native(text, language)
            if native_text != text:
                logger.info(f"✅ Converted English transliteration to native script: '{text}' → '{native_text}'")
                text = native_text
            else:
                logger.warning(f"⚠️ Whisper returned English transliteration for {language}: {text}")
                logger.info(f"💡 To get native script output reliably, install Vosk models: python setup_vosk_models.py {language}")
        
        return normalize_text(text)
    except Exception as e:
        logger.error(f"❌ Transcription error: {e}")
        import traceback
        traceback.print_exc()
        return ""
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------
# FIRST LETTER
# ---------------------------------------------------
def extract_first_sound(text: str) -> str:
    if text == "":
        return ""

    words = text.split()

    if len(words) == 0:
        return ""

    return words[0][0]


# ---------------------------------------------------
# BEST WORD MATCH
# ---------------------------------------------------
def extract_spoken_part(transcript: str, target: str) -> str:
    words = transcript.split()

    if not words:
        return ""

    target = target.lower()

    best_match = ""
    best_score = 0

    for word in words:
        for i in range(1, len(word) + 1):
            part = word[:i]

            score = fuzz.ratio(
                part,
                target[:len(part)]
            )

            if score > best_score:
                best_score = score
                best_match = part

    if len(best_match) > len(target):
        best_match = best_match[:len(target)]

    return best_match
