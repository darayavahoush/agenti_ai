"""
services/alphabet_sounds.py -- what each letter is *tested* and *trained* as.

The Alphabet part of the Assessment used to be a read-only explorer. To make
it a real check, each letter is probed through a short keyword that starts
with that letter's sound (the kid says "ball" for B). The existing
speech-analysis agent scores the keyword as usual and the alphabet agents
then look only at the letter's own sound in it.

Every letter also carries the VaakMirror sound id it maps onto
(frontend/src/vaakmirror/data/soundTaxonomy.js) so the planner can hand
VaakMirror concrete sounds to focus on. tests/test_alphabet_agents.py checks
those ids against soundTaxonomy.js, so a rename there fails a test instead of
silently breaking the mapping.

Letters with no clean single-sound probe (Q, X) are left out on purpose: they
stay explorable on the keyboard but are never scored.
"""

from __future__ import annotations

# letter -> keyword, target ARPABET phoneme (initial sound of the keyword),
# VaakMirror sound id, articulation group, and what to try next if it is missed.
LETTERS: dict[str, dict] = {
    "A": {"word": "apple",    "arpa": "AE", "vm": "ae", "group": "vowel",      "next": ["E"]},
    "B": {"word": "ball",     "arpa": "B",  "vm": "b",  "group": "lips",       "next": ["P", "M"]},
    "C": {"word": "cat",      "arpa": "K",  "vm": "k",  "group": "tongue-back", "next": ["G"]},
    "D": {"word": "dog",      "arpa": "D",  "vm": "d",  "group": "tongue-tip", "next": ["T", "N"]},
    "E": {"word": "egg",      "arpa": "EH", "vm": "eh", "group": "vowel",      "next": ["I"]},
    "F": {"word": "fish",     "arpa": "F",  "vm": "f",  "group": "teeth-lip",  "next": ["V"]},
    "G": {"word": "goat",     "arpa": "G",  "vm": "g",  "group": "tongue-back", "next": ["K"]},
    "H": {"word": "hat",      "arpa": "HH", "vm": "h",  "group": "throat",     "next": ["F"]},
    "I": {"word": "insect",   "arpa": "IH", "vm": "ih", "group": "vowel",      "next": ["E"]},
    "J": {"word": "jam",      "arpa": "JH", "vm": "j",  "group": "tongue-tip", "next": ["S"]},
    "K": {"word": "kite",     "arpa": "K",  "vm": "k",  "group": "tongue-back", "next": ["G"]},
    "L": {"word": "leaf",     "arpa": "L",  "vm": "l",  "group": "tongue-tip", "next": ["R", "N"]},
    "M": {"word": "moon",     "arpa": "M",  "vm": "m",  "group": "lips",       "next": ["B"]},
    "N": {"word": "nose",     "arpa": "N",  "vm": "n",  "group": "tongue-tip", "next": ["D"]},
    "O": {"word": "octopus",  "arpa": "AA", "vm": "ah", "group": "vowel",      "next": ["U"]},
    "P": {"word": "pig",      "arpa": "P",  "vm": "p",  "group": "lips",       "next": ["B"]},
    "R": {"word": "rabbit",   "arpa": "R",  "vm": "r",  "group": "tongue-curl", "next": ["L", "W"]},
    "S": {"word": "sun",      "arpa": "S",  "vm": "s",  "group": "tongue-tip", "next": ["Z", "F"]},
    "T": {"word": "tiger",    "arpa": "T",  "vm": "t",  "group": "tongue-tip", "next": ["D", "N"]},
    "U": {"word": "up",       "arpa": "AH", "vm": "uh", "group": "vowel",      "next": ["O"]},
    "V": {"word": "van",      "arpa": "V",  "vm": "v",  "group": "teeth-lip",  "next": ["F"]},
    "W": {"word": "water",    "arpa": "W",  "vm": "w",  "group": "lips",       "next": ["V"]},
    "Y": {"word": "yellow",   "arpa": "Y",  "vm": "y",  "group": "tongue-tip", "next": ["L"]},
    "Z": {"word": "zebra",    "arpa": "Z",  "vm": "z",  "group": "tongue-tip", "next": ["S"]},
}

# A short first pass covering every place/manner family: lips, tongue-tip
# stop, back of tongue, hiss, and the two "l/r" liquids. Once these are done
# the agent suggests follow-up letters from LETTERS[x]["next"].
CORE_LETTERS = ["B", "T", "K", "S", "L", "R"]

MIN_LETTERS_FOR_PLAN = 4

# Groups that are shaped with the lips/teeth (Lip Sync Hero's territory) versus
# the tongue (Tongue Tamer / Mirror Mirror).
LIP_GROUPS = {"lips", "teeth-lip", "vowel"}
TONGUE_GROUPS = {"tongue-tip", "tongue-back", "tongue-curl", "throat"}


def strip_stress(p: str | None) -> str:
    """ARPABET with stress digits removed: 'AE1' -> 'AE'."""
    return "".join(ch for ch in str(p or "").upper() if ch.isalpha())


def is_probe_letter(letter: str) -> bool:
    return (letter or "").upper() in LETTERS
