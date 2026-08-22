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
    "animals":  {"name": "Animals",     "emoji": "🐶", "words": ["dog","cat","cow","elephant","lion","tiger","monkey","parrot","fish","bird","rabbit","horse","goat","duck","butterfly"]},
    "food":     {"name": "Food",        "emoji": "🍎", "words": ["apple","banana","mango","rice","bread","milk","water","egg","potato","tomato","onion","carrot","orange","grapes"]},
    "family":   {"name": "Family",      "emoji": "👨‍👩‍👧", "words": ["mother","father","baby","girl","boy","grandfather","grandmother"]},
    "body":     {"name": "My Body",     "emoji": "🖐️", "words": ["hand","eye","ear","nose","mouth","foot","head","hair"]},
    "home":     {"name": "Around Home", "emoji": "🏠", "words": ["ball","book","chair","table","cup","bag","car","bus","house","door","window","bed"]},
    "nature":   {"name": "Nature",      "emoji": "🌳", "words": ["tree","flower","sun","moon"]},
    "actions":  {"name": "Actions",     "emoji": "🏃", "words": ["eat","drink","sleep","run","jump","sit","stand","walk","read","write","play","cry","laugh","sing"]},
    "feelings": {"name": "Feelings",    "emoji": "😊", "words": ["happy","sad","angry","scared","surprised"]},
    "colors":   {"name": "Colors",      "emoji": "🎨", "words": ["red","blue","green","yellow","purple","white","black"]},
    "numbers":  {"name": "Numbers",     "emoji": "🔢", "words": ["one","two","three","four","five"]},
    "school":   {"name": "School",      "emoji": "✏️", "words": ["pencil","pen","paper","school","teacher"]},
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
