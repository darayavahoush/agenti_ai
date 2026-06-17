from fastapi import APIRouter
from app.services.image.matcher import get_image_for_phrase
from app.routes.speech import get_basic_phonemes


router = APIRouter(
    prefix="/image",
    tags=["Image Learning"]
)

@router.post("/teach")
async def teach_word(payload: dict):

    word = payload.get("word", "")

    image = get_image_for_phrase(word)
    print("IMAGE RESULT =", image)

    phonemes = get_basic_phonemes(word)

    return {
        "word": word,
        "phonemes": phonemes,
        "image_found": image["found"],
        "match_type": image["match_type"],
        "matched_word": image.get("matched_word"),
        "image_path": image.get("path")
    }