from typing import List, Tuple, Optional
from g2p_en import G2p
from rapidfuzz import fuzz

g2p_converter = G2p()

WORD_MAPPER_DISPLAY_MAP = {
    "AA": "a",
    "AE": "Ai",
    "AH": "u",
    "AO": "aw",
    "AW": "au",
    "AY": "Ai",
    "B": "b",
    "CH": "ch",
    "D": "d",
    "DH": "th",
    "EH": "e",
    "ER": "er",
    "EY": "ay",
    "F": "f",
    "G": "g",
    "HH": "h",
    "IH": "i",
    "IY": "ee",
    "JH": "j",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ng",
    "OW": "o",
    "OY": "oy",
    "P": "p",
    "R": "r",
    "SH": "sh",
    "S": "s",
    "T": "t",
    "TH": "th",
    "UH": "oo",
    "UW": "oo",
    "V": "v",
    "W": "w",
    "Y": "y",
    "Z": "z",
    "ZH": "zh",
}

COMMON_WORD_MAPPER_OVERRIDES = {
    "apple": ["Ai", "p", "p", "l"],
    "ball": ["b", "aw", "l"],
    "teacher": ["t", "ee", "ch", "er"],
    "umbrella": ["u", "m", "b", "r", "e", "l", "u"],
    "cat": ["k", "a", "t"],
    "dog": ["d", "o", "g"],
    "sun": ["s", "u", "n"],
    "ship": ["sh", "i", "p"],
    "boat": ["b", "oa", "t"],
}


# ---------------------------------------------------
# BASIC PHONEME
# ---------------------------------------------------
def get_basic_phonemes(word: str) -> List[str]:
    phonemes = g2p_converter(word)
    clean = []

    for p in phonemes:
        p = p.replace("0", "").replace("1", "").replace("2", "")
        if p.isalpha():
            clean.append(p)

    return clean


# ---------------------------------------------------
# compare phoneme
# ---------------------------------------------------
def compare_phonemes(expected: List[str], spoken: List[str]) -> dict:
    matches = []
    correct = 0
    total = max(len(expected), 1)

    for i in range(len(expected)):
        exp = expected[i]
        got = spoken[i] if i < len(spoken) else None
        is_correct = exp == got

        if is_correct:
            correct += 1

        matches.append({
            "expected": exp,
            "detected": got,
            "correct": is_correct
        })

    accuracy = int((correct / total) * 100)
    return {
        "matches": matches,
        "accuracy": accuracy
    }


# ---------------------------------------------------
# SCORE
# ---------------------------------------------------
def compute_score(target: str, spoken: str) -> int:
    if spoken == "":
        return 0

    target = target.lower()
    spoken = spoken.lower()

    # Base similarity
    similarity = fuzz.ratio(target, spoken)

    # Length penalty (VERY IMPORTANT)
    length_ratio = len(spoken) / len(target)

    # Penalize short pronunciations
    if length_ratio < 0.5:
        return int(similarity * length_ratio)

    # Medium partial
    if length_ratio < 0.8:
        return int(similarity * 0.8)

    # Full word attempt
    return int(similarity)


# ---------------------------------------------------
# DISPLAY PHONEME HELPERS
# ---------------------------------------------------
def get_display_phoneme_label(token: str) -> str:
    return WORD_MAPPER_DISPLAY_MAP.get(token.upper(), token.upper())


def get_word_mapper_display(word: str, tokens: List[str]) -> List[str]:
    normalized = word.lower().strip()

    if normalized in COMMON_WORD_MAPPER_OVERRIDES:
        return COMMON_WORD_MAPPER_OVERRIDES[normalized]

    labels = []
    i = 0

    while i < len(tokens):
        token = tokens[i].upper()

        if token == "AH" and i + 1 < len(tokens) and tokens[i + 1].upper() == "L":
            labels.append("ul")
            i += 2
            continue

        if token == "AH" and i + 1 < len(tokens) and tokens[i + 1].upper() == "R":
            labels.append("ur")
            i += 2
            continue

        if token == "AE" and i + 1 < len(tokens) and tokens[i + 1].upper() == "L":
            labels.append("al")
            i += 2
            continue

        if token in {"EY", "AY", "AI"}:
            labels.append("Ai")
            i += 1
            continue

        if token in {"OW", "OE", "OH"}:
            labels.append("o")
            i += 1
            continue

        if token in {"IY", "EE"}:
            labels.append("ee")
            i += 1
            continue

        if token in {"UW", "UH", "OO"}:
            labels.append("oo")
            i += 1
            continue

        labels.append(get_display_phoneme_label(token))
        i += 1

    return labels


def get_display_phoneme_list(tokens: List[str], word: Optional[str] = None) -> List[str]:
    if word is not None:
        return get_word_mapper_display(word, tokens)
    return [get_display_phoneme_label(t) for t in tokens]


# ---------------------------------------------------
# FEEDBACK
# ---------------------------------------------------
def generate_feedback(score: int, target: str, spoken: str) -> Tuple[str, int]:
    if spoken == "":
        return "No speech detected. Try again slowly.", 1

    if score >= 90:
        return "Excellent pronunciation! 🎉", 5

    if score >= 70:
        return f"Very good! Improve ending of '{target}'.", 4

    if score >= 50:
        return f"You said '{spoken}'. Try full word '{target}'.", 3

    return f"Break it: {target[:2]}...{target}", 2
