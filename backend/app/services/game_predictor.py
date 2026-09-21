"""
services/game_predictor.py -- "which games would help this kid?" from the
words they said during the Assessment.

The Assessment graph (graph/assessment_graph.py) analyses ONE word per call
and never looks across words, and nothing maps its findings onto the games.
This module is that missing step: it folds every analysed word's
phoneme_matches / error_patterns into per-sound evidence, then scores each
game against the sounds it actually trains.

Deliberately deterministic (no LLM in here): the ranking has to be
explainable to a therapist and stable between runs. The agent wrapper
(agents/game_predictor_agent.py) may phrase the explanation with an LLM, but
it can only pick from what this module ranked.

Sound vocabulary is the same canonical ARPABET-style set the rest of the app
uses (services/phoneme_crosswalk.py, flashcards PHONEME_DATA). Game -> sound
targets come from that crosswalk: Chime's level ids and what each extractor
measures, and VaakMirror's own sound taxonomy.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

# Kid-friendly label per canonical sound, for the explanations.
SOUND_LABEL: dict[str, str] = {
    "B": "b", "P": "p", "M": "m", "D": "d", "T": "t", "N": "n", "G": "g", "K": "k",
    "F": "f", "V": "v", "S": "s", "Z": "z", "SH": "sh", "CH": "ch", "JH": "j",
    "L": "l", "R": "r", "W": "w", "Y": "y", "H": "h", "TH": "th", "NG": "ng",
    "AA": "ah", "AE": "a (cat)", "EH": "e (bed)", "IH": "i (sit)", "IY": "ee", "UW": "oo",
}

# CMUdict phoneme spellings (what phoneme_matches carries) -> canonical keys.
# Anything not listed and not already canonical is ignored rather than guessed.
_CMU_ALIASES = {"HH": "H", "DH": "TH", "ZH": "SH", "ER": "R", "AO": "AA"}

_LIP_SOUNDS = {"P", "B", "M", "F", "V", "W", "UW", "IY", "AA"}
_TONGUE_SOUNDS = {"T", "D", "N", "L", "S", "Z", "SH", "CH", "JH", "K", "G", "R", "TH", "Y", "NG"}
_ALL_SOUNDS = set(SOUND_LABEL)

# id, display name, family, route, sounds it trains, weight (1.0 = trains
# exactly these sounds; lower = a general-purpose game that only helps a bit
# with each), and what kind of practice it is.
CATALOG: list[dict[str, Any]] = [
    {"id": "chime_aa", "name": "Rocket Launch", "family": "Chime", "path": "/play/chime/rocket-launch",
     "sounds": {"AA"}, "weight": 1.0, "how": "a big open \"aaa\""},
    {"id": "chime_oo", "name": "Submarine Dive", "family": "Chime", "path": "/play/chime/submarine-dive",
     "sounds": {"UW"}, "weight": 1.0, "how": "a long round \"oooo\""},
    {"id": "chime_ee", "name": "Xylophone", "family": "Chime", "path": "/play/chime/xylophone-tower",
     "sounds": {"IY"}, "weight": 1.0, "how": "a bright \"eeee\""},
    {"id": "chime_r", "name": "Lion's Roar", "family": "Chime", "path": "/play/chime/lions-roar",
     "sounds": {"R"}, "weight": 1.0, "how": "a growly \"rrrr\""},
    {"id": "chime_fa", "name": "Bubble Garden", "family": "Chime", "path": "/play/chime/wind-chime-garden",
     "sounds": {"F"}, "weight": 1.0, "how": "a steady \"fff\""},
    {"id": "chime_ha", "name": "Bubble Wrap Pop", "family": "Chime", "path": "/play/chime/bubble-wrap-pop",
     "sounds": {"H"}, "weight": 1.0, "how": "a sharp \"ha!\""},
    {"id": "vm_lip_sync_hero", "name": "Lip Sync Hero", "family": "Orpheus", "path": "/play/vaakmirror/lip-sync-hero",
     "sounds": _LIP_SOUNDS, "weight": 0.8, "how": "shaping your lips for each sound"},
    {"id": "vm_tongue_tamer", "name": "Tongue Tamer", "family": "Orpheus", "path": "/play/vaakmirror/tongue-tamer",
     "sounds": _TONGUE_SOUNDS, "weight": 0.8, "how": "putting your tongue in the right place"},
    {"id": "vm_mirror_mirror", "name": "Mirror, Mirror", "family": "Orpheus", "path": "/play/vaakmirror/mirror-mirror",
     "sounds": _ALL_SOUNDS, "weight": 0.4, "how": "copying the mouth shape you see"},
    {"id": "flashcards", "name": "Flashcards", "family": "Flashcards", "path": "/play/flashcards",
     "sounds": _ALL_SOUNDS, "weight": 0.6, "how": "practising each sound with picture cards"},
]
CATALOG_BY_ID = {g["id"]: g for g in CATALOG}

# Games driven by a pattern/skill rather than one sound.
FIREFLY = {"id": "chime_ma", "name": "Firefly Jar", "family": "Chime", "path": "/play/chime/firefly-jar",
           "how": "saying \"ma-ma-ma\" quickly and evenly"}
VILLAGE = {"id": "chime_village", "name": "Village Builder", "family": "Chime", "path": "/play/chime/village-builder",
           "how": "saying whole words"}
MINIMAL_PAIRS = {"id": "vm_minimal_pairs", "name": "Minimal Pair Drill", "family": "Orpheus",
                 "path": "/play/vaakmirror/minimal-pair-drill", "how": "hearing the difference between look-alike sounds"}
BREATH = {"id": "breathquest", "name": "BreathQuest", "family": "BreathQuest", "path": "/play/levels",
          "how": "steady breath control, which every sound sits on top of"}
SKILL_GAMES = {g["id"]: g for g in (FIREFLY, VILLAGE, MINIMAL_PAIRS, BREATH)}

TARGET_WORDS = 5          # how many words the assessment aims for
MIN_MISS_RATE = 0.34      # a sound only counts as "weak" past this miss rate...
STRONG_ACCURACY = 85      # ...unless the word overall was already this good


def canon(p: Any) -> str | None:
    """CMUdict/ARPABET phoneme -> canonical key, or None if we don't model it."""
    if not p:
        return None
    s = "".join(ch for ch in str(p).upper() if ch.isalpha())
    s = _CMU_ALIASES.get(s, s)
    return s if s in _ALL_SOUNDS else None


def _get(d: dict, *names: str, default=None):
    """word_results arrive camelCase from the frontend and snake_case from
    /analyze directly; accept both."""
    for n in names:
        if n in d and d[n] is not None:
            return d[n]
    return default


def summarize_words(word_results: Iterable[dict]) -> dict[str, Any]:
    """Per-sound evidence across every analysed word."""
    sounds: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"attempts": 0, "misses": 0, "words": [], "subs": defaultdict(int)}
    )
    accuracies: list[float] = []
    patterns: dict[str, int] = defaultdict(int)
    words = 0
    for w in word_results or []:
        if not isinstance(w, dict):
            continue
        words += 1
        acc = _get(w, "accuracy", default=None)
        if isinstance(acc, (int, float)):
            accuracies.append(float(acc))
        for pat in _get(w, "errorPatterns", "error_patterns", default=[]) or []:
            patterns[str(pat)] += 1
        target = str(_get(w, "targetWord", "target_word", default="") or "")
        for m in _get(w, "phonemeMatches", "phoneme_matches", default=[]) or []:
            if not isinstance(m, dict):
                continue
            key = canon(m.get("expected"))
            if key is None:
                continue
            s = sounds[key]
            s["attempts"] += 1
            if not m.get("correct"):
                s["misses"] += 1
                if target and target not in s["words"]:
                    s["words"].append(target)
                spoken = canon(m.get("spoken"))
                if spoken and spoken != key:
                    s["subs"][spoken] += 1
    return {
        "words": words,
        "avg_accuracy": round(sum(accuracies) / len(accuracies)) if accuracies else None,
        "sounds": sounds,
        "patterns": dict(patterns),
    }


def weak_sounds(summary: dict[str, Any]) -> list[tuple[str, float, dict]]:
    """[(sound, weight, evidence)] most-troubled first. weight = miss rate,
    nudged up when the miss repeated across more than one word."""
    out = []
    for key, s in summary["sounds"].items():
        if not s["misses"]:
            continue
        rate = s["misses"] / max(s["attempts"], 1)
        if rate < MIN_MISS_RATE and s["misses"] < 2:
            continue
        weight = rate * (1.0 + 0.25 * (min(len(s["words"]), 3) - 1))
        out.append((key, weight, s))
    out.sort(key=lambda t: t[1], reverse=True)
    return out


def _sound_phrase(keys: list[str]) -> str:
    labels = [f"\"{SOUND_LABEL.get(k, k.lower())}\"" for k in keys]
    if len(labels) <= 1:
        return labels[0] if labels else ""
    return ", ".join(labels[:-1]) + " and " + labels[-1]


def _word_phrase(words: list[str]) -> str:
    words = [f"'{w}'" for w in words[:2]]
    return " and ".join(words)


def rank_games(word_results: Iterable[dict], limit: int = 4) -> dict[str, Any]:
    """The prediction. Returns {words_analyzed, confidence, headline_sounds,
    avg_accuracy, plan: [ {id,name,family,path,score,targets,reason}, ... ]}.
    Empty plan means no clear weak sound (nothing to recommend, not an error)."""
    summary = summarize_words(word_results)
    weak = weak_sounds(summary)
    n = summary["words"]
    confidence = "low" if n < 3 else ("medium" if n < TARGET_WORDS else "good")

    scored: dict[str, dict[str, Any]] = {}

    def add(game: dict, score: float, sound_keys: list[str], reason: str):
        cur = scored.get(game["id"])
        if cur is None:
            scored[game["id"]] = {
                "id": game["id"], "name": game["name"], "family": game["family"],
                "path": game["path"], "score": score, "targets": list(sound_keys), "reason": reason,
            }
        else:
            cur["score"] += score
            cur["targets"] = list(dict.fromkeys(cur["targets"] + sound_keys))
            cur["reason"] = reason if score > 0 else cur["reason"]

    # 1) sound-driven games
    for game in CATALOG:
        hits = [(k, w, s) for (k, w, s) in weak if k in game["sounds"]]
        if not hits:
            continue
        score = game["weight"] * sum(w for _, w, _ in hits)
        keys = [k for k, _, _ in hits]
        top_words = list(dict.fromkeys(x for _, _, s in hits for x in s["words"]))
        if game["family"] == "Flashcards":
            reason = (f"Picture cards to practise {_sound_phrase(keys[:4])}, "
                      f"the sounds that were tricky in {_word_phrase(top_words)}.")
        elif len(game["sounds"]) == 1:
            reason = (f"Trains the {_sound_phrase(keys)} sound directly by {game['how']}. "
                      f"It was tricky in {_word_phrase(top_words)}.")
        else:
            reason = (f"Helps with {_sound_phrase(keys[:3])} by {game['how']}. "
                      f"Those sounds were tricky in {_word_phrase(top_words)}.")
        add(game, score, keys, reason)

    # 2) pattern-driven games
    pats = " ".join(summary["patterns"]).lower()
    subs_seen = sum(len(s["subs"]) for _, _, s in weak)
    if "final consonant deletion" in pats:
        add(FIREFLY, 0.9, [], "Practises finishing every sound in a word. "
            "Some ending sounds were dropped, and repeating \"ma-ma-ma\" builds steady, complete syllables.")
    if subs_seen >= 2 or "fronting" in pats:
        add(MINIMAL_PAIRS, 0.8, [], "Some sounds were swapped for others (like k said as t). "
            "This game trains hearing and saying the difference between look-alike sounds.")
    avg = summary["avg_accuracy"]
    if avg is not None and avg < 65 and weak:
        add(VILLAGE, 0.7, [], "Whole-word practice: say a word and see how close you got. "
            "A good next step once the single sounds feel easier.")
    if avg is not None and avg < 45:
        add(BREATH, 0.6, [], "Words were hard to get through overall, so start with steady breathing: "
            "every sound is built on it.")

    plan = sorted(scored.values(), key=lambda g: g["score"], reverse=True)
    # Keep the plan varied: at most two games from one family.
    picked, per_family = [], defaultdict(int)
    for g in plan:
        if per_family[g["family"]] >= 2:
            continue
        per_family[g["family"]] += 1
        picked.append(g)
        if len(picked) >= limit:
            break
    for i, g in enumerate(picked, 1):
        g["priority"] = i
        g["score"] = round(g["score"], 2)

    return {
        "words_analyzed": n,
        "target_words": TARGET_WORDS,
        "confidence": confidence,
        "avg_accuracy": avg,
        "weak_sounds": [k for k, _, _ in weak[:5]],
        "plan": picked,
    }
