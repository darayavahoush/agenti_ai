import os
import tempfile
import wave
import json
from typing import Optional
from vosk import Model, KaldiRecognizer
import soundfile as sf

# Vosk model paths - these need to be downloaded
# Models can be downloaded from: https://alphacephei.com/vosk/models
VOSK_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "vosk_models")

# Language to Vosk model mapping (based on available models)
VOSK_LANG_MODELS = {
    "hi": "vosk-model-hi-0.22",  # Hindi
    "te": "vosk-model-small-te-0.42",  # Telugu  
    "kn": "vosk-model-small-ka-0.42",  # Kannada (Note: ka=Georgian, may not work)
    "ta": "vosk-model-ta-0.22",  # Tamil (not available)
    "ml": "vosk-model-ml-0.22",  # Malayalam (not available)
    "bn": "vosk-model-bn-0.22",  # Bengali (not available)
    "mr": "vosk-model-mr-0.22",  # Marathi (not available)
    "en": "vosk-model-en-us-0.22"  # English
}

# Cached models
loaded_models = {}


def get_vosk_model(language: str) -> Optional[Model]:
    """
    Load or get cached Vosk model for the specified language.
    
    Args:
        language: Language code (hi, te, kn, en, etc.)
    
    Returns:
        Vosk Model object or None if not available
    """
    if language in loaded_models:
        return loaded_models[language]
    
    model_name = VOSK_LANG_MODELS.get(language)
    if not model_name:
        print(f"⚠️ No Vosk model available for language: {language}")
        return None
    
    model_path = os.path.join(VOSK_MODELS_DIR, model_name)
    
    if not os.path.exists(model_path):
        print(f"⚠️ Vosk model not found at: {model_path}")
        print(f"📥 Please download model from: https://alphacephei.com/vosk/models")
        print(f"📁 Extract to: {VOSK_MODELS_DIR}")
        return None
    
    try:
        print(f"🔧 Loading Vosk model for {language}: {model_name}")
        model = Model(model_path)
        loaded_models[language] = model
        print(f"✅ Vosk model loaded for {language}")
        return model
    except Exception as e:
        print(f"❌ Error loading Vosk model for {language}: {e}")
        return None


def transcribe_with_vosk(audio_path: str, language: str = "hi") -> str:
    """
    Transcribe audio file using Vosk model.
    
    Args:
        audio_path: Path to audio file
        language: Language code (hi, te, kn, en, etc.)
    
    Returns:
        Transcribed text in the native script
    """
    model = get_vosk_model(language)
    if not model:
        return ""
    
    try:
        # Convert audio to WAV format required by Vosk
        # Vosk requires 16kHz, 16-bit, mono WAV
        y, sr = sf.read(audio_path)
        
        # Resample to 16kHz if needed
        if sr != 16000:
            import librosa
            y = librosa.resample(y, orig_sr=sr, target_sr=16000)
            sr = 16000
        
        # Convert to mono if stereo
        if len(y.shape) > 1:
            y = y.mean(axis=1)
        
        # Create temporary WAV file
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav_path = tmp_wav.name
        tmp_wav.close()
        
        # Write WAV file
        with wave.open(tmp_wav_path, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)  # 16kHz
            # Convert float to int16
            y_int16 = (y * 32767).astype('int16')
            wf.writeframes(y_int16.tobytes())
        
        # Perform recognition
        rec = KaldiRecognizer(model, 16000)
        
        with wave.open(tmp_wav_path, "rb") as wf:
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    pass
        
        # Get final result
        result = rec.FinalResult()
        result_json = json.loads(result)
        
        # Clean up temp file
        os.remove(tmp_wav_path)
        
        text = result_json.get("text", "")
        print(f"📝 Vosk transcription ({language}): {text}")
        return text
        
    except Exception as e:
        print(f"❌ Vosk transcription error: {e}")
        import traceback
        traceback.print_exc()
        return ""


def is_vosk_available(language: str) -> bool:
    """
    Check if Vosk model is available for the given language.
    
    Args:
        language: Language code
    
    Returns:
        True if model is available, False otherwise
    """
    model_name = VOSK_LANG_MODELS.get(language)
    if not model_name:
        return False
    
    model_path = os.path.join(VOSK_MODELS_DIR, model_name)
    return os.path.exists(model_path)


def setup_vosk_models_directory():
    """
    Create the Vosk models directory if it doesn't exist.
    """
    if not os.path.exists(VOSK_MODELS_DIR):
        os.makedirs(VOSK_MODELS_DIR)
        print(f"📁 Created Vosk models directory: {VOSK_MODELS_DIR}")
        print(f"📥 Download models from: https://alphacephei.com/vosk/models")
        print(f"📋 Recommended models:")
        for lang_code, model_name in VOSK_LANG_MODELS.items():
            print(f"   - {lang_code}: {model_name}")
