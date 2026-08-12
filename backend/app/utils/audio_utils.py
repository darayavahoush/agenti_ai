import re
import logging
from pathlib import Path
import soundfile as sf
from fastapi import HTTPException

logger = logging.getLogger("uvicorn.error")

# Base directory setup: backend root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Directories config
UPLOADS_DIR = BASE_DIR / "uploads" / "voices"
GENERATED_DIR = BASE_DIR / "generated_audio"

# Constraints
MIN_REF_DURATION = 20.0
MAX_REF_DURATION = 30.0

def get_reference_voice_path(therapist_id: str) -> Path:
    """
    Get the absolute path for the therapist's reference voice sample.
    Sanitizes therapist_id to prevent directory traversal.
    """
    if not therapist_id or not therapist_id.strip():
        raise HTTPException(status_code=400, detail="Invalid therapist_id.")
    
    # Sanitize therapist_id to keep alphanumeric, hyphens, and underscores only
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', therapist_id.strip())
    if not safe_id:
        raise HTTPException(status_code=400, detail="Invalid therapist_id format.")
        
    return UPLOADS_DIR / safe_id / "reference.wav"

def sanitize_text_for_filename(text: str) -> str:
    """
    Sanitize text to create a safe, lowercased WAV filename.
    E.g. "Elephant" -> "elephant.wav"
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    # Strip spaces and lowercase
    clean = text.strip().lower()
    # Replace non-alphanumeric/hyphen/underscore with underscore
    clean = re.sub(r'[^a-z0-9_-]', '_', clean)
    # Collapse multiple underscores
    clean = re.sub(r'_+', '_', clean)
    # Clean leading/trailing underscores
    clean = clean.strip('_')
    
    if not clean:
        raise HTTPException(status_code=400, detail="Invalid text for voice generation.")
        
    return f"{clean}.wav"

def get_generated_audio_path(therapist_id: str, text: str) -> Path:
    """
    Get the absolute path for the generated audio file.
    Sanitizes therapist_id and text to prevent directory traversal.
    """
    if not therapist_id or not therapist_id.strip():
        raise HTTPException(status_code=400, detail="Invalid therapist_id.")
        
    safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', therapist_id.strip())
    if not safe_id:
        raise HTTPException(status_code=400, detail="Invalid therapist_id format.")
        
    filename = sanitize_text_for_filename(text)
    return GENERATED_DIR / safe_id / filename

def validate_audio_file(file_path: Path) -> float:
    """
    Validate that the file exists, is in WAV format, and its duration
    is between 20 and 30 seconds.
    Returns the duration in seconds.
    """
    if not file_path.exists():
        logger.error(f"Validation failed: File does not exist at {file_path}")
        raise HTTPException(status_code=404, detail="Audio file not found.")
        
    try:
        info = sf.info(file_path)
    except Exception as e:
        logger.error(f"Validation failed: Soundfile cannot read {file_path}. Error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file is not a valid audio file. Error: {str(e)}"
        )
        
    # Verify WAV format
    if info.format.upper() != "WAV":
        logger.error(f"Validation failed: Format {info.format} is not WAV.")
        raise HTTPException(
            status_code=400,
            detail=f"Audio reference must be a WAV file. Got: {info.format}"
        )
        
    duration = info.duration
    
    # Check duration range (20-30s)
    if duration < MIN_REF_DURATION or duration > MAX_REF_DURATION:
        logger.error(f"Validation failed: Duration {duration:.2f}s is not within [{MIN_REF_DURATION}, {MAX_REF_DURATION}]s range.")
        raise HTTPException(
            status_code=400,
            detail=(
                f"Reference audio must be between {MIN_REF_DURATION} and {MAX_REF_DURATION} seconds. "
                f"Current duration: {duration:.2f} seconds."
            )
        )
        
    return duration
