"""
routers/flashcards/themes.py — Groups the flat flashcard word index
(data/flashcard_images/index.json) into kid-facing themes. index.json
itself has no category concept, so this is a static mapping maintained
here rather than in the data file -- if a new word is added to the
image index without adding it to a theme below, it still works via
random_word()'s theme=None fallback, it just won't surface in any
theme-scoped picker until someone assigns it one.
"""

from pathlib import Path
import json

_DATA_DIR = Path(__file__).resolve().parents[3] / 'data' / 'flashcard_images'
_INDEX_PATH = _DATA_DIR / 'index.json'

THEMES = {
    "core_words":        {"name": "Core Words",        "emoji": "💬", "words": ["eat","drink","sleep","run","jump","sit","stand","walk","read","write","play","cry","laugh","sing"]},
    "safari_animals":    {"name": "Safari Animals",     "emoji": "🦁", "words": ["elephant","lion","tiger","monkey"]},
    "birds":             {"name": "Birds",              "emoji": "🐦", "words": ["bird","parrot"]},
    "sea_animals":       {"name": "Sea Animals",        "emoji": "🐬", "words": ["octopus","shark","dolphin","whale","crab"]},
    "insects":           {"name": "Insects",            "emoji": "🐝", "words": ["ant","bee","ladybug","mosquito","butterfly"]},
    "fruits":            {"name": "Fruits",             "emoji": "🍎", "words": ["apple","banana","mango","grapes","orange"]},
    "vegetables":        {"name": "Vegetables",         "emoji": "🥕", "words": ["carrot","onion","potato","tomato"]},
    "food":               {"name": "Food",               "emoji": "🍞", "words": ["bread","rice","milk","water","egg"]},
    "school_supplies":   {"name": "School Supplies",    "emoji": "✏", "words": ["pen","pencil","paper","book"]},
    "music":             {"name": "Music",              "emoji": "🎸", "words": ["guitar","piano","drum","trumpet","violin"]},
    "community_helpers": {"name": "Community Helpers",  "emoji": "👩", "words": ["teacher"]},
    "living_room":       {"name": "Living Room",        "emoji": "🛋", "words": ["chair","table","window","door"]},
    "bedroom":           {"name": "Bedroom",            "emoji": "🛏", "words": ["bed"]},
    "bathroom":          {"name": "Bathroom",           "emoji": "🛁", "words": ["toilet","bathtub","toothbrush","shower","soap"]},
    "numbers":           {"name": "Numbers",            "emoji": "🔢", "words": ["one","two","three","four","five"]},
    "ten_plus":          {"name": "Ten+",               "emoji": "🔟", "words": ["six","seven","eight","nine","ten"]},
    "shapes":            {"name": "Shapes",             "emoji": "⭐", "words": ["circle","square","triangle","star","diamond"]},
}


def _load_index() -> dict:
    with open(_INDEX_PATH) as f:
        return json.load(f)


def list_themes() -> list:
    """Only themes with at least one word that still exists in index.json
    are returned, so removing an image doesn't leave a phantom category."""
    index = _load_index()
    out = []
    for theme_id, t in THEMES.items():
        available = [w for w in t["words"] if w in index]
        if available:
            out.append({"id": theme_id, "name": t["name"], "emoji": t["emoji"], "word_count": len(available)})
    return out


def words_for_theme(theme_id: str) -> list:
    index = _load_index()
    t = THEMES.get(theme_id)
    if not t:
        return []
    return [w for w in t["words"] if w in index]


def theme_for_word(word: str) -> str | None:
    for theme_id, t in THEMES.items():
        if word in t["words"]:
            return theme_id
    return None
