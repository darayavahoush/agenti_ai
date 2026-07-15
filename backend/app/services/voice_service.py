import os
import time
import logging
import threading
import torch
import torchaudio
import soundfile as sf
from pathlib import Path
from fastapi import HTTPException, UploadFile

# Bypass torchcodec requirement check in coqui-tts (since torchaudio works fine)
import transformers.utils.import_utils as import_utils
orig_is_torch_greater_or_equal = import_utils.is_torch_greater_or_equal
import_utils.is_torch_greater_or_equal = lambda v, *args, **kwargs: False if v >= "2.9" else orig_is_torch_greater_or_equal(v, *args, **kwargs)

# Mock torchaudio.load and save using soundfile to bypass torchcodec/FFmpeg dynamic C++ requirements entirely
def mock_torchaudio_load(uri, frame_offset=0, num_frames=-1, normalize=True, channels_first=True, format=None, buffer_size=4096, backend=None):
    data, samplerate = sf.read(uri, dtype='float32')
    tensor = torch.from_numpy(data)
    if channels_first:
        if tensor.ndim == 1:
            tensor = tensor.unsqueeze(0)
        else:
            tensor = tensor.T
    else:
        if tensor.ndim == 1:
            tensor = tensor.unsqueeze(1)
    return tensor, samplerate

def mock_torchaudio_save(uri, src, sample_rate, channels_first=True, compression=None, format=None, encoding=None, bits_per_sample=None, buffer_size=4096, backend=None):
    data = src.numpy()
    if channels_first:
        if data.ndim == 2:
            data = data.T
    sf.write(uri, data, sample_rate)

torchaudio.load = mock_torchaudio_load
torchaudio.save = mock_torchaudio_save

# Bypass torchcodec requirement check in coqui-tts
torch.__version__ = "2.1.2"

# Auto-accept Coqui CPML model license
os.environ["COQUI_TOS_AGREED"] = "1"

# Auto-accept Coqui CPML model license
os.environ["COQUI_TOS_AGREED"] = "1"
from app.utils.audio_utils import (
    get_reference_voice_path,
    get_generated_audio_path,
    validate_audio_file
)

logger = logging.getLogger("uvicorn.error")

LANGUAGE_CODE_MAP = {
    "en-in": "en",
    "en": "en",
    "hi-in": "hi",
    "hi": "hi",
    "ta-in": "ta",
    "ta": "ta",
    "te-in": "te",
    "te": "te",
    "bn-in": "bn",
    "bn": "bn",
    "mr-in": "mr",
    "mr": "mr",
}

class VoiceService:
    _tts_model = None
    _loading_thread = None
    _lock = threading.Lock()

    @classmethod
    def load_model_background(cls):
        """
        Load the XTTS v2 model in a background thread to prevent blocking
        the FastAPI startup / uvicorn reload process.
        """
        with cls._lock:
            if cls._tts_model is not None:
                return
            if cls._loading_thread is not None and cls._loading_thread.is_alive():
                return
            
            cls._loading_thread = threading.Thread(target=cls._load_model_thread_wrapper, daemon=True)
            cls._loading_thread.start()
            logger.info("Background thread started to load XTTS v2 model.")

    @classmethod
    def _load_model_thread_wrapper(cls):
        try:
            cls.load_model()
        except Exception as e:
            logger.error(f"Background thread failed to load XTTS model: {e}")

    @classmethod
    def load_model(cls):
        """
        Load the XTTS v2 model only once.
        Optimized for CPU execution.
        """
        if cls._tts_model is not None:
            logger.info("XTTS v2 model already loaded.")
            return

        import torch
        logger.info("Starting XTTS v2 model loading on CPU...")
        start_time = time.time()
        
        # CPU Optimizations
        torch.set_num_threads(4)
        torch.set_grad_enabled(False)
        
        try:
            from TTS.api import TTS
            # Instantiate model on CPU
            cls._tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
            load_duration = time.time() - start_time
            logger.info(f"XTTS v2 model loaded successfully on CPU in {load_duration:.2f} seconds.")
        except Exception as e:
            load_duration = time.time() - start_time
            logger.error(f"Failed to load XTTS v2 model after {load_duration:.2f} seconds. Error: {e}")
            raise RuntimeError(f"Failed to load XTTS v2 model: {str(e)}")

    async def register_voice(self, therapist_id: str, file: UploadFile) -> dict:
        """
        Register the therapist's reference voice.
        Verifies duration (must be 20-30s) and WAV format.
        Only allows registration once.
        """
        if not therapist_id or not therapist_id.strip():
            raise HTTPException(status_code=400, detail="Invalid therapist_id.")
            
        ref_path = get_reference_voice_path(therapist_id)
        
        if ref_path.exists():
            logger.warning(f"Registration rejected: Reference voice already exists for therapist '{therapist_id}'.")
            raise HTTPException(
                status_code=400,
                detail="Reference voice already registered for this therapist."
            )
            
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            contents = await file.read()
            with open(ref_path, "wb") as f:
                f.write(contents)
        except Exception as e:
            logger.error(f"Failed to save reference file: {e}")
            if ref_path.exists():
                ref_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save reference audio file. Error: {str(e)}"
            )
            
        try:
            duration = validate_audio_file(ref_path)
            logger.info(f"Registered reference voice for therapist '{therapist_id}' successfully. Duration: {duration:.2f}s.")
        except HTTPException as he:
            if ref_path.exists():
                ref_path.unlink()
            raise he
        except Exception as e:
            if ref_path.exists():
                ref_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Failed to validate reference audio. Error: {str(e)}"
            )
            
        return {
            "success": True,
            "message": "Voice registered successfully."
        }

    def generate_voice(self, therapist_id: str | None, text: str, language: str = "en-IN") -> Path:
        """
        Generate voice WAV file for the requested text.
        If a therapist reference voice exists, it is used; otherwise the model generates speech in the requested language.
        """
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty.")

        normalized_language = LANGUAGE_CODE_MAP.get(language.strip().lower(), language.split("-")[0].lower() or "en")

        if therapist_id and therapist_id.strip():
            ref_path = get_reference_voice_path(therapist_id)
            out_path = get_generated_audio_path(therapist_id, f"{text.strip()}_{normalized_language}")
        else:
            ref_path = None
            out_path = get_generated_audio_path("default", f"{text.strip()}_{normalized_language}")

        # 1. Check if generated file already exists (Cache Hit)
        if out_path.exists():
            logger.info(f"Cache HIT: Returning existing audio for text='{text}', language='{normalized_language}'. Path: {out_path}")
            return out_path

        # 2. Cache Miss
        logger.info(f"Cache MISS: Generating audio for text='{text}', language='{normalized_language}'")

        # Ensure model is loaded
        if self._tts_model is None:
            with self._lock:
                thread = self._loading_thread

            if thread is not None and thread.is_alive():
                logger.info("Waiting for background XTTS v2 model loading thread to complete...")
                thread.join()

            if self._tts_model is None:
                self.load_model()

        # Ensure destination directory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # 3. Generate speech
        import torch
        logger.info(f"Synthesizing speech for text: '{text}' in language '{normalized_language}'")
        start_time = time.time()
        try:
            with torch.inference_mode():
                kwargs = {
                    "text": text,
                    "language": normalized_language,
                    "file_path": str(out_path),
                }
                if ref_path and ref_path.exists():
                    kwargs["speaker_wav"] = str(ref_path)
                self._tts_model.tts_to_file(**kwargs)
            gen_time = time.time() - start_time
            logger.info(f"Speech generation complete in {gen_time:.2f} seconds. Saved to: {out_path}")
        except Exception as e:
            gen_time = time.time() - start_time
            logger.error(f"Speech generation failed after {gen_time:.2f} seconds. Error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Speech generation failed. Error: {str(e)}"
            )

        return out_path
