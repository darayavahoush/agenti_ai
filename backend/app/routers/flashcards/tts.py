import io
import subprocess
import tempfile
import os
import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# backend/app/services/voice/tts.py -> parents[2] is backend/app,
# matching the app/data/ convention chat_cache.py already uses.
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "tts_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CHARACTERS = {
    "BOLT": {
        "voice": "hm_omega", "speed": 1.0,
        "ffmpeg": "asetrate=16000,aresample=24000,atempo=1.5,aecho=0.9:0.7:35:0.5,volume=4.0",
        "ffmpeg_question": "asetrate=16000,aresample=24000,atempo=1.5,aecho=0.9:0.7:35:0.5,vibrato=f=2:d=0.15,volume=4.0",
    },
    "ZARA": {
        "voice": "hf_alpha", "speed": 1.0,
        "ffmpeg": "asetrate=32000,aresample=24000,atempo=0.75,vibrato=f=5:d=0.25,aphaser=in_gain=0.8:out_gain=0.9:delay=3:decay=0.4:speed=1.5:type=t,volume=3.0",
        "ffmpeg_question": "asetrate=32000,aresample=24000,atempo=0.75,vibrato=f=7:d=0.35,aphaser=in_gain=0.8:out_gain=0.9:delay=3:decay=0.4:speed=2.0:type=t,volume=3.5",
    },
    "NOVA": {
        "voice": "hf_beta", "speed": 1.0,
        "ffmpeg": "asetrate=21000,aresample=24000,atempo=1.14,chorus=0.5:0.9:50:0.4:0.25:2,volume=3.0",
        "ffmpeg_question": "asetrate=21000,aresample=24000,atempo=1.14,chorus=0.6:0.9:50:0.5:0.3:2,vibrato=f=1.5:d=0.1,volume=3.0",
    },
    "BEEP": {
        "voice": "hm_psi", "speed": 1.0,
        "ffmpeg": "asetrate=38000,aresample=24000,atempo=0.63,vibrato=f=8:d=0.3,volume=4.0",
        "ffmpeg_question": "asetrate=38000,aresample=24000,atempo=0.63,vibrato=f=12:d=0.4,aecho=0.7:0.4:15:0.2,volume=4.5",
    },
    "ECHO": {
        "voice": "hm_omega", "speed": 1.0,
        "ffmpeg": "asetrate=18000,aresample=24000,atempo=1.33,aecho=0.8:0.6:60:0.4,tremolo=f=2:d=0.3,volume=4.0",
        "ffmpeg_question": "asetrate=18000,aresample=24000,atempo=1.33,aecho=0.8:0.6:60:0.4,tremolo=f=3:d=0.4,vibrato=f=1:d=0.2,volume=4.0",
    },
    "MIRA": {
        "voice": "hf_alpha", "speed": 1.0,
        "ffmpeg": "asetrate=20000,aresample=24000,atempo=1.2,aphaser=in_gain=0.8:out_gain=0.9:delay=5:decay=0.5:speed=0.8:type=t,chorus=0.6:0.9:60:0.4:0.3:2,volume=6.0",
        "ffmpeg_question": "asetrate=20000,aresample=24000,atempo=1.2,aphaser=in_gain=0.8:out_gain=0.9:delay=5:decay=0.5:speed=1.2:type=t,chorus=0.7:0.9:60:0.5:0.35:2,tremolo=f=4:d=0.3,volume=6.0",
    },
}

INTRO_LINES = {
    "BOLT": "Hi! I am Bolt, your brave space robot friend. Let us learn together!",
    "ZARA": "Hello! I am Zara, from planet Zorb. I love learning new words with you!",
    "NOVA": "Greetings. I am Nova, your calm and wise guide. Ready to begin?",
    "BEEP": "Beep beep! I am Beep, your tiny helper robot. Let us have fun learning!",
    "ECHO": "Hello there. I am Echo, an ancient computer from a distant galaxy. Shall we start?",
    "MIRA": "Hi friend! I am Mira, your friendly underwater robot. Let us explore words today!",
}

# gTTS only gives one base voice per language — there's no per-character voice
# selection like Kokoro had. To still give each character a distinct identity,
# pitch is shifted per-character via asetrate BEFORE the ffmpeg effects chain
# runs, so BOLT/ZARA/etc sound different even on the shared gTTS base voice.
GTTS_LANG_CONFIG = {
    "english": {"lang": "en", "tld": "co.in"},   # Indian-accented English
    "hindi": {"lang": "hi", "tld": "co.in"},
    "kannada": {"lang": "kn", "tld": "co.in"},
}

GTTS_PITCH_SHIFT = {
    "BOLT": 0.85,   # deeper
    "ZARA": 1.25,   # higher/alien
    "NOVA": 1.0,    # neutral
    "BEEP": 1.5,    # very high/squeaky
    "ECHO": 0.75,   # lowest/eerie
    "MIRA": 1.1,    # slightly high
}


def _is_question(text: str) -> bool:
    t = text.strip()
    question_words = ("shall", "can", "could", "would", "should", "is", "are", "do", "does", "did", "ready", "want")
    return t.endswith("?") or t.lower().startswith(question_words)

def _cache_key(text: str, character: str, language: str, speed: float) -> str:
    # ffmpeg_filters/ffmpeg_question aren't part of the key: which one applies
    # is fully determined by _is_question(text), so text+character+language+speed
    # already pins down the exact audio that would be rendered.
    raw = f"{language}|{character}|{speed}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _cache_get(key: str) -> bytes | None:
    path = CACHE_DIR / f"{key}.wav"
    if path.exists():
        try:
            return path.read_bytes()
        except OSError as e:
            logger.info(f"TTS cache read failed for {key}: {e}")
    return None

def _cache_set(key: str, audio: bytes) -> None:
    path = CACHE_DIR / f"{key}.wav"
    tmp_path = path.with_suffix(".wav.tmp")
    try:
        tmp_path.write_bytes(audio)
        tmp_path.replace(path)  # atomic-ish: avoids serving a half-written file
    except OSError as e:
        logger.info(f"TTS cache write failed for {key}: {e}")

def _apply_ffmpeg(raw_bytes: bytes, filters: str) -> bytes:
    in_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    in_tmp.write(raw_bytes)
    in_tmp.close()
    out_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    out_tmp.close()
    try:
        cmd = ["ffmpeg", "-y", "-i", in_tmp.name, "-af", filters, "-ar", "24000", out_tmp.name]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(out_tmp.name, "rb") as f:
            return f.read()
    except subprocess.CalledProcessError as e:
        logger.info(f"ffmpeg error: {e.stderr.decode()}")
        return raw_bytes
    finally:
        os.unlink(in_tmp.name)
        if os.path.exists(out_tmp.name):
            os.unlink(out_tmp.name)

def _render_gtts_raw(text: str, language: str) -> bytes:
    """Render raw gTTS audio (no character effects, no pitch shift) as WAV bytes."""
    from gtts import gTTS
    cfg = GTTS_LANG_CONFIG.get(language, GTTS_LANG_CONFIG["english"])
    tts = gTTS(text, lang=cfg["lang"], tld=cfg["tld"], slow=False)
    mp3_buf = io.BytesIO()
    tts.write_to_fp(mp3_buf)
    mp3_buf.seek(0)
    in_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    in_tmp.write(mp3_buf.read())
    in_tmp.close()
    out_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    out_tmp.close()
    try:
        cmd = ["ffmpeg", "-y", "-i", in_tmp.name, "-ar", "24000", out_tmp.name]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(out_tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(in_tmp.name)
        if os.path.exists(out_tmp.name):
            os.unlink(out_tmp.name)

def _render_gtts(text: str, language: str, character: str, ffmpeg_filters: str = "", speed: float = 1.0) -> bytes:
    raw_bytes = _render_gtts_raw(text, language)
    pitch = GTTS_PITCH_SHIFT.get(character, 1.0)
    pitch_filter = f"asetrate=24000*{pitch},aresample=24000"
    # atempo must stay within ffmpeg's 0.5-2.0 range per filter instance; clamp to be safe
    clamped_speed = max(0.5, min(2.0, speed))
    speed_filter = f"atempo={clamped_speed}" if clamped_speed != 1.0 else ""
    parts = [p for p in [pitch_filter, speed_filter, ffmpeg_filters] if p]
    combined_filters = ",".join(parts)
    return _apply_ffmpeg(raw_bytes, combined_filters)

def _render(text: str, character: str, voice: str, speed: float, ffmpeg_filters: str = "", ffmpeg_question: str = "", language: str = "english") -> bytes:
    key = _cache_key(text, character, language, speed)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    filters = ffmpeg_question if (ffmpeg_question and _is_question(text)) else ffmpeg_filters
    audio = _render_gtts(text, language, character, filters, speed=speed)
    _cache_set(key, audio)
    return audio

def speak_word(word: str, speed: float = 1.0, voice: str = "hf_alpha", character: str = "BOLT", language: str = "english") -> bytes:
    cfg = CHARACTERS.get(character.upper(), CHARACTERS["BOLT"])
    return _render(word, character.upper(), voice, speed, cfg["ffmpeg"], cfg.get("ffmpeg_question", ""), language=language)

def speak_intro(character: str) -> bytes:
    char = character.upper()
    cfg = CHARACTERS.get(char, CHARACTERS["BOLT"])
    line = INTRO_LINES.get(char, "Hello! Let us learn together!")
    return _render(line, char, cfg["voice"], cfg["speed"], cfg["ffmpeg"], cfg.get("ffmpeg_question", ""))

def speak(text: str, character: str = "BOLT", mood: str = "default", speed: float = None, language: str = "english") -> bytes:
    char = character.upper()
    cfg = CHARACTERS.get(char, CHARACTERS["BOLT"])
    s = speed if speed is not None else cfg["speed"]
    return _render(text, char, cfg["voice"], s, cfg["ffmpeg"], cfg.get("ffmpeg_question", ""), language=language)

def get_characters():
    return [{"id": k, "name": k, "tagline": INTRO_LINES[k][:40]} for k in CHARACTERS]

WORD_SPEEDS = (1.0, 0.65, 0.8)  # matches the speed buttons in PracticeScreen.jsx / PhonemeScreen.jsx / DrillScreen.jsx

def precache_words(words, characters=None, languages=("english",), speeds=WORD_SPEEDS):
    """Render+cache every (word, character, language, speed) combo so the
    first real request for a common word is a cache hit instead of a live
    gTTS call. `languages` defaults to English only — Hindi/Kannada word text
    comes from translation, not this word list, so those fill in organically
    as real requests come in."""
    chars = characters or list(CHARACTERS.keys())
    for word in words:
        for char in chars:
            cfg = CHARACTERS[char]
            for lang in languages:
                for spd in speeds:
                    try:
                        _render(word, char, cfg["voice"], spd, cfg["ffmpeg"], cfg.get("ffmpeg_question", ""), language=lang)
                    except Exception as e:
                        logger.info(f"Precache failed for '{word}' ({char}, {lang}, speed={spd}): {e}")

def warm_cache():
    """Populate the cache with everything guaranteed to be spoken regardless
    of which words a session ends up practising: character intros plus the
    fixed encouragement/feedback/acoustic-tip phrases, across every character
    and every supported language."""
    for char in CHARACTERS:
        try:
            speak_intro(char)
        except Exception as e:
            logger.info(f"Intro cache failed: {char} — {e}")

    try:
        from app.services.phoneme.drill import ENCOURAGEMENT_MESSAGES, FEEDBACK_MESSAGES, ACOUSTIC_TIPS
    except ImportError as e:
        logger.info(f"warm_cache: skipping fixed phrases, drill module unavailable: {e}")
        return

    phrase_groups = list(ENCOURAGEMENT_MESSAGES.values()) + list(FEEDBACK_MESSAGES.values())
    for char in CHARACTERS:
        for group in phrase_groups:
            for lang, text in group.items():
                try:
                    speak(text, character=char, language=lang)
                except Exception as e:
                    logger.info(f"Phrase cache failed ({char}, {lang}): {e}")
        for lang, tips in ACOUSTIC_TIPS.items():
            for tip in tips:
                try:
                    speak(tip, character=char, language=lang)
                except Exception as e:
                    logger.info(f"Tip cache failed ({char}, {lang}): {e}")
