import re


def normalize_word_key(word: str) -> str:
    if not word:
        return ""

    key = word.strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    key = re.sub(r"_+", "_", key)
    key = key.strip("_")
    return key
