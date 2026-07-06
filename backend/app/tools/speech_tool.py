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
try:
    whisper_model = WhisperModel(
        "base.en",
        device="cpu",
        compute_type="int8"
    )

    print("✅ Faster-Whisper loaded")

except Exception as e:
    whisper_model = None
    print("❌ Faster-Whisper error:", e)


# ---------------------------------------------------
# NORMALIZE TEXT
# ---------------------------------------------------
def normalize_text(text: str) -> str:
    return re.sub(r'[^a-z ]', '', text.lower()).strip()


# ---------------------------------------------------
# TRANSCRIPTION
# ---------------------------------------------------
def transcribe(y: np.ndarray, sr: int, prompt: Optional[str] = None) -> str:
    if whisper_model is None:
        return ""

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        sf.write(tmp_path, y, sr)
        print("Transcribing file:", tmp_path)
        segments, info = whisper_model.transcribe(
            tmp_path,
            language="en",
            beam_size=5
        )

        text = " ".join(
            segment.text
            for segment in segments
        )
        return normalize_text(text)
    except Exception as e:
        print("transcription error:", e)
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
