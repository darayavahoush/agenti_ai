"""
services/phoneme_crosswalk.py — maps each game's own raw sound/level
identifiers onto one canonical phoneme vocabulary (the keys of
routers/flashcards/phoneme_data.py's PHONEME_DATA), so phoneme_summary.py
can merge accuracy across Flashcards, VaakMirror, and Chime for the same
underlying sound.

Three different identifier spaces feed this:

  - Flashcards (PhonemeMastery.phoneme) already stores canonical
    ARPABET-style keys ("R", "S", "TH", "IY", ...) — no translation
    needed, it *is* PHONEME_DATA's vocabulary already.

  - VaakMirror (Attempt.sound_id) uses its own lowercase ids from
    frontend/src/vaakmirror/data/soundTaxonomy.js's SOUNDS list ("r",
    "sh", "th-voiced", "ee", ...). Mapped below via VAAKMIRROR_TO_PHONEME.

  - Chime (RLTrainingEvent.level_id, via app.retraining.data_store)
    uses its own short level ids ("aa", "oo", "r", "fa", "ha", "ee") —
    see audio_features/__init__.py's EXTRACTORS mapping and each
    extractor module's own docstring for what phoneme each one actually
    measures. Mapped below via CHIME_TO_PHONEME.

VAAKMIRROR_TO_PHONEME was built by cross-checking each candidate
soundTaxonomy.js entry's (place, manner, voicing) tags against
PHONEME_DATA — not by string-guessing off the id spelling. That check
surfaced a real ambiguity: several taxonomy entries share identical
(place, manner, voicing) triples (most notably "ee"/"y", both
Palatal+Approximant+Voiced, and "oo"/"w", both Labio-velar+
Approximant+Voiced; the vowel corner Glottal+Approximant+Voiced is
worse — "ah", "ae", "eh", "ih", and "uh" all collide there). Articulatory
tags alone can't disambiguate those, so this module does NOT try to
reconstruct a sound_id from an Attempt's place/manner/voicing columns.
It only ever maps the id VaakMirror actually stored — the tags were
just how each mapping below was audited for correctness, not how it's
computed at runtime.

Several soundTaxonomy.js ids are deliberately left unmapped (so
attempts on them are excluded from cross-game phoneme rollups, not
mis-mapped):
  - blends/combos ("bl", "st", "ta", "ap", "ang", ...) — a blend isn't
    a single PHONEME_DATA entry, and guessing which member of the
    blend to credit would misattribute the attempt.
  - "qu" — tagged complexity: 'single' in soundTaxonomy.js but is
    acoustically /kw/, a two-phoneme onset with no matching single
    PHONEME_DATA key.
  - "uh" (as in "cup") — PHONEME_DATA has no AH/UH vowel entry to map
    it onto (AE/EH/IH/IY/UW/AA cover the other five short/tense
    vowels VaakMirror tracks, but not this one).

PHONEME_DATA itself was missing two keys these games do measure —
"AA" (the open back vowel VaakMirror's "ah" and Chime's "aa" both
target, per vowel_quality_aa.py's own docstring: '"aa" (as in
"father")') and "NG" (VaakMirror's word-final "ng"/"ang" nasal).
Rather than silently dropping data for two real, distinct sounds these
games score, phoneme_summary.py supplements those two entries when
building its own phoneme metadata lookup (see SUPPLEMENTAL_PHONEMES
below) instead of patching the Flashcards-owned PHONEME_DATA module.
"""

# ------------------------------------------------------------------ #
#  VaakMirror: Attempt.sound_id -> canonical PHONEME_DATA key           #
# ------------------------------------------------------------------ #
VAAKMIRROR_TO_PHONEME: dict[str, str] = {
    # Consonants — single, unambiguous id -> phoneme.
    "p": "P", "b": "B", "m": "M",
    "f": "F", "v": "V",
    "s": "S", "z": "Z",
    "t": "T", "d": "D", "n": "N", "l": "L",
    "r": "R",
    "sh": "SH", "ch": "CH", "j": "JH",
    "k": "K", "g": "G",
    "h": "H",
    "ng": "NG",  # supplemental — see module docstring
    # th-voiced/th-unvoiced both roll up onto PHONEME_DATA's single "TH"
    # entry (which itself only models the unvoiced /θ/ target) — there's
    # no separate voiced-TH key to preserve the distinction against.
    "th-unvoiced": "TH", "th-voiced": "TH",
    # w/wh both roll up onto "W" for the same reason — voicing isn't a
    # distinct PHONEME_DATA entry here either.
    "w": "W", "wh": "W",
    "y": "Y",
    # Vowels.
    "ah": "AA",  # supplemental — see module docstring
    "ee": "IY",
    "oo": "UW",
    "ae": "AE",
    "eh": "EH",
    "ih": "IH",
    # Deliberately absent: "qu" (kw digraph, no single-phoneme target)
    # and "uh" (no AH/UH entry in PHONEME_DATA to map onto). All blend
    # ("bl", "tr", "sk", ...) and combo/word-final ("ta", "ap", "ang",
    # ...) ids are likewise absent — see module docstring.
}

# ------------------------------------------------------------------ #
#  Chime: RLTrainingEvent.level_id -> canonical PHONEME_DATA key        #
# ------------------------------------------------------------------ #
CHIME_TO_PHONEME: dict[str, str] = {
    "aa": "AA",  # vowel_quality_aa.py: "'aa' (as in 'father')" — supplemental
    "oo": "UW",  # vowel_quality.py: Submarine Dive, rounded "oo"
    "ee": "IY",  # vowel_quality_ee.py: Kite Flyer, high-front "ee" (as in "see")
    "r":  "R",   # rhotic.py: F3-lowering /r/ marker
    "fa": "F",   # frication.py: sustained fricative /f/
    "ha": "H",   # aspiration_burst.py: aspirated /h/ burst
    # Deliberately excluded:
    #   "ma" (syllable_rhythm.py) — measures diadochokinetic rhythm/
    #        repetition rate, not phoneme accuracy; including it would
    #        blend a timing metric into an accuracy rollup.
    #   "word" (word_level/asr_match.py) — whole-word ASR match score,
    #        not a single phoneme.
}

# Supplemental phoneme metadata for the two keys VaakMirror/Chime need
# that Flashcards' PHONEME_DATA doesn't define (it only covers what
# Flashcards itself drills). Shape matches a PHONEME_DATA entry closely
# enough for phoneme_summary.py to treat them uniformly, but deliberately
# thinner — these were never designed as flashcard content, just as
# aggregation targets.
SUPPLEMENTAL_PHONEMES: dict[str, dict] = {
    "AA": {
        "ipa": "ɑ", "name": "ah sound (father)", "example_word": "father",
        "category": "vowel",
    },
    "NG": {
        "ipa": "ŋ", "name": "ng sound (sing)", "example_word": "sing",
        "category": "nasal",
    },
}


def vaakmirror_sound_to_phoneme(sound_id: str | None) -> str | None:
    """None means "exclude this attempt from cross-game rollups" —
    either sound_id wasn't recorded, or it's a blend/combo/unmapped id
    (see module docstring). Never guesses from place/manner/voicing."""
    if not sound_id:
        return None
    return VAAKMIRROR_TO_PHONEME.get(sound_id)


def chime_level_to_phoneme(level_id: str | None) -> str | None:
    """Same None-means-exclude contract as vaakmirror_sound_to_phoneme."""
    if not level_id:
        return None
    return CHIME_TO_PHONEME.get(level_id)
