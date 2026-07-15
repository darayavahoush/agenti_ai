from fastapi import APIRouter, File, Form, UploadFile, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.services.voice_service import VoiceService

router = APIRouter(prefix="/voice", tags=["Voice Cloning & Generation"])

# Service dependency
def get_voice_service() -> VoiceService:
    return VoiceService()

TRANSLATION_DICTIONARY = {
    "monkey": {
        "hi-IN": "बंदर",
        "ta-IN": "குரங்கு",
        "te-IN": "కురంగు",
        "bn-IN": "বানর",
        "mr-IN": "माकड",
    },
    "banana": {
        "hi-IN": "केला",
        "ta-IN": "வாழைப்பழம்",
        "te-IN": "అరిటి",
        "bn-IN": "কলা",
        "mr-IN": "केळी",
    },
    "apple": {
        "hi-IN": "सेब",
        "ta-IN": "ஆப்பிள்",
        "te-IN": "సфера",
        "bn-IN": "আপেল",
        "mr-IN": "सफरचंद",
    },
    "cat": {
        "hi-IN": "बिल्ली",
        "ta-IN": "பூனை",
        "te-IN": "పిల్లి",
        "bn-IN": "বিড়াল",
        "mr-IN": "मांजर",
    },
    "dog": {
        "hi-IN": "कुत्ता",
        "ta-IN": "நாய்",
        "te-IN": "కుక్క",
        "bn-IN": "কুকুর",
        "mr-IN": "कुत्रा",
    },
}


def translate_text(text: str, language: str) -> str:
    if not text or not language:
        return text
    key = text.strip().lower()
    translations = TRANSLATION_DICTIONARY.get(key)
    if not translations:
        return text
    return translations.get(language, text)

class GenerateRequest(BaseModel):
    therapist_id: str | None = Field(default=None, description="Optional unique identifier for the therapist")
    text: str = Field(..., min_length=1, description="Text to synthesize speech for")
    language: str = Field(default="en-IN", description="Language code such as en-IN, hi-IN, ta-IN, te-IN, bn-IN, mr-IN")

@router.post("/register")
async def register_voice(
    therapist_id: str = Form(..., description="Unique identifier for the therapist"),
    reference_audio: UploadFile = File(..., description="20-30 second reference WAV file"),
    service: VoiceService = Depends(get_voice_service)
):
    """
    Upload and register a therapist's 20-30 second WAV reference voice sample.
    Only allows registration once per therapist.
    """
    return await service.register_voice(therapist_id, reference_audio)

@router.post("/generate")
async def generate_voice(
    request_data: GenerateRequest,
    service: VoiceService = Depends(get_voice_service)
):
    """
    Generate speech WAV file for the requested text using the therapist's reference voice sample.
    Checks for cache hit first and returns existing file if available.
    """
    translated_text = translate_text(request_data.text, request_data.language)
    file_path = service.generate_voice(request_data.therapist_id, translated_text, language=request_data.language)
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=file_path.name
    )
