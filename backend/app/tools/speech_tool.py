import os
import re
import tempfile
from typing import Optional
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from rapidfuzz import fuzz

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

    print("✅ Faster-Whisper multilingual model loaded")

except Exception as e:
    whisper_model = None
    print("❌ Faster-Whisper error:", e)
    # Fallback to English-only model if multilingual fails
    try:
        whisper_model = WhisperModel(
            "base.en",
            device="cpu",
            compute_type="int8"
        )
        print("✅ Faster-Whisper English-only model loaded as fallback")
    except Exception as e2:
        print("❌ Faster-Whisper fallback also failed:", e2)


# ---------------------------------------------------
# NORMALIZE TEXT
# ---------------------------------------------------
def normalize_text(text: str) -> str:
    # For non-English text, don't strip non-ASCII characters
    if any(ord(c) > 127 for c in text):
        return text.lower().strip()
    return re.sub(r'[^a-z ]', '', text.lower()).strip()


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
                print(f"🎤 Using Vosk for {language} transcription")
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
                print(f"⚠️ Vosk model not available for {language}, Whisper will return English transliteration")
                print(f"💡 Install Vosk models for native script output: python setup_vosk_models.py {language}")
        except ImportError:
            print("⚠️ Vosk not installed, Whisper will return English transliteration")
            print(f"💡 Install Vosk: pip install vosk && python setup_vosk_models.py {language}")
        except Exception as e:
            print(f"⚠️ Vosk transcription failed: {e}, falling back to Whisper")
    
    # Fallback to Whisper for English or if Vosk is not available
    if whisper_model is None:
        print("❌ Whisper model not available")
        return ""

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        sf.write(tmp_path, y, sr)
        print("🎤 Transcribing file:", tmp_path, "with language:", language, "audio length:", len(y), "sample rate:", sr)
        
        # Map language code to Whisper language code
        whisper_lang = LANGUAGE_CODES.get(language, "en")
        print("🌐 Using Whisper language code:", whisper_lang)
        
        segments, info = whisper_model.transcribe(
            tmp_path,
            language=whisper_lang,
            beam_size=5
        )

        text = " ".join(
            segment.text
            for segment in segments
        )
        print("📝 Transcription result:", text)
        
        # For Indian languages, Whisper returns English transliteration
        # We need to convert this back to native script for phoneme extraction
        if language in indian_languages and text:
            print(f"⚠️ Whisper returned English transliteration for {language}: {text}")
            print(f"💡 To get native script output, install Vosk models")
        
        return normalize_text(text)
    except Exception as e:
        print("❌ Transcription error:", e)
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
