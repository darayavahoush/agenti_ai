from kokoro_onnx import Kokoro
import numpy as np
import io
import wave
import subprocess
import tempfile
import os

kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
_cache = {}

CHARACTERS = {
    "BOLT": {
        "voice": "hm_omega", "speed": 1.0,
        # Deep robotic — power-on ramp, heavy echo
        "ffmpeg": "asetrate=16000,aresample=24000,atempo=1.5,aecho=0.9:0.7:35:0.5,volume=4.0",
        "ffmpeg_question": "asetrate=16000,aresample=24000,atempo=1.5,aecho=0.9:0.7:35:0.5,vibrato=f=2:d=0.15,volume=4.0",
    },
    "ZARA": {
        "voice": "hf_alpha", "speed": 1.0,
        # Alien wobble — fast vibrato always on
        "ffmpeg": "asetrate=32000,aresample=24000,atempo=0.75,vibrato=f=5:d=0.25,aphaser=in_gain=0.8:out_gain=0.9:delay=3:decay=0.4:speed=1.5:type=t,volume=3.0",
        "ffmpeg_question": "asetrate=32000,aresample=24000,atempo=0.75,vibrato=f=7:d=0.35,aphaser=in_gain=0.8:out_gain=0.9:delay=3:decay=0.4:speed=2.0:type=t,volume=3.5",
    },
    "NOVA": {
        "voice": "hf_beta", "speed": 1.0,
        # Calm sci-fi — gentle chorus
        "ffmpeg": "asetrate=21000,aresample=24000,atempo=1.14,chorus=0.5:0.9:50:0.4:0.25:2,volume=3.0",
        "ffmpeg_question": "asetrate=21000,aresample=24000,atempo=1.14,chorus=0.6:0.9:50:0.5:0.3:2,vibrato=f=1.5:d=0.1,volume=3.0",
    },
    "BEEP": {
        "voice": "hm_psi", "speed": 1.0,
        # Tiny squeaky — high vibrato blips
        "ffmpeg": "asetrate=38000,aresample=24000,atempo=0.63,vibrato=f=8:d=0.3,volume=4.0",
        "ffmpeg_question": "asetrate=38000,aresample=24000,atempo=0.63,vibrato=f=12:d=0.4,aecho=0.7:0.4:15:0.2,volume=4.5",
    },
    "ECHO": {
        "voice": "hm_omega", "speed": 1.0,
        # Eerie glitchy — tremolo fade
        "ffmpeg": "asetrate=18000,aresample=24000,atempo=1.33,aecho=0.8:0.6:60:0.4,tremolo=f=2:d=0.3,volume=4.0",
        "ffmpeg_question": "asetrate=18000,aresample=24000,atempo=1.33,aecho=0.8:0.6:60:0.4,tremolo=f=3:d=0.4,vibrato=f=1:d=0.2,volume=4.0",
    },
    "MIRA": {
        "voice": "hf_alpha", "speed": 1.0,
        # Bubbly underwater — slow tremolo pulse
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

def _is_question(text: str) -> bool:
    t = text.strip()
    question_words = ("shall", "can", "could", "would", "should", "is", "are", "do", "does", "did", "ready", "want")
    return t.endswith("?") or t.lower().startswith(question_words)

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
        print(f"ffmpeg error: {e.stderr.decode()}")
        return raw_bytes
    finally:
        os.unlink(in_tmp.name)
        if os.path.exists(out_tmp.name):
            os.unlink(out_tmp.name)

def _render(text: str, voice: str, speed: float, ffmpeg_filters: str = "", ffmpeg_question: str = "") -> bytes:
    samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((samples * 32767).astype(np.int16).tobytes())
    raw_bytes = buf.getvalue()

    # Use question filter if text is a question
    if ffmpeg_question and _is_question(text):
        return _apply_ffmpeg(raw_bytes, ffmpeg_question)
    elif ffmpeg_filters:
        return _apply_ffmpeg(raw_bytes, ffmpeg_filters)
    return raw_bytes

def speak_word(word: str, speed: float = 1.0, voice: str = "hf_alpha") -> bytes:
    key = f"word_{word}_{speed}_{voice}"
    if key not in _cache:
        _cache[key] = _render(word, voice, speed)
    return _cache[key]

def speak_intro(character: str) -> bytes:
    char = character.upper()
    key = f"intro_{char}"
    if key not in _cache:
        cfg = CHARACTERS.get(char, CHARACTERS["BOLT"])
        line = INTRO_LINES.get(char, "Hello! Let us learn together!")
        _cache[key] = _render(line, cfg["voice"], cfg["speed"], cfg["ffmpeg"], cfg.get("ffmpeg_question", ""))
    return _cache[key]

def speak(text: str, character: str = "BOLT", mood: str = "default", speed: float = None) -> bytes:
    char = character.upper()
    cfg = CHARACTERS.get(char, CHARACTERS["BOLT"])
    s = speed if speed is not None else cfg["speed"]
    key = f"speak_{char}_{mood}_{text[:30]}_{s}"
    if key not in _cache:
        _cache[key] = _render(text, cfg["voice"], s, cfg["ffmpeg"], cfg.get("ffmpeg_question", ""))
    return _cache[key]

def get_characters():
    return [{"id": k, "name": k, "tagline": INTRO_LINES[k][:40]} for k in CHARACTERS]

def warm_cache():
    pass

def precache_words(words):
    for word in words:
        try:
            speak_word(word)
            print(f"Cached: {word}")
        except Exception as e:
            print(f"Failed: {word} — {e}")
