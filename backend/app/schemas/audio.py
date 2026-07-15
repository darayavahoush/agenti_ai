from pydantic import BaseModel


class AudioResponse(BaseModel):
    audio_url: str
    generated: bool
    localized_word: str | None = None
