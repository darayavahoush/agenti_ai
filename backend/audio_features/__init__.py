"""
Phoneme-specific audio feature extractors for Chime.

Each module exposes a single extract(audio_chunk, sample_rate) -> FeatureResult
function. See common.py for the shared FeatureResult contract.

Chime is a separate game from BreathQuest, with its own mechanics —
they share the site (auth, DB, deployment) but not level designs.

Level -> extractor -> mechanic:
  aa   -> vowel_quality_aa  -> Rocket Launch
  oo   -> vowel_quality     -> Submarine Dive
  ma   -> syllable_rhythm   -> Drum Island
  fa   -> frication         -> Wind Chime Garden
  ha   -> aspiration_burst  -> Bubble Wrap Pop
  ee   -> vowel_quality_ee  -> Xylophone Tower (frontend's LEVEL_ORDER; extractor
                                docstring/quest-games history calls this "Kite Flyer")
  r    -> rhotic            -> Lion's Roar
  word -> word_level/asr_match.py -> Village Builder

ee/r restored 2026-08-12 -- dropped during the quest-games merge (frontend's
LEVEL_ORDER and LionsRoar.jsx/XylophoneTower.jsx already expected these, so
their absence here was a live scoring gap, not intentionally cut content).
See quest-games/breathquest/backend/audio_features/{rhotic,vowel_quality_ee}.py
for the original source this was ported from -- byte-identical common.py
confirmed the FeatureResult contract matches before porting.

aa switched 2026-09-07 from vowel_loudness (RMS volume only, no vowel-quality
check at all) to vowel_quality_aa (same formant-tracking approach as
oo/ee) -- "aa" was the one vowel-based level still scoring on loudness
alone, and RocketLaunch.jsx's frontend now calls this endpoint directly
(replacing its old client-side Whisper-transcript verification window) via
POST /chime/phoneme/score/aa. vowel_loudness.py itself is left in place,
unreferenced, rather than deleted -- SubmarineDive/XylophoneTower haven't
been switched over yet, and it's a reasonable reference for a pure-loudness
extractor if a future level wants one.
"""

from .common import FeatureResult
from . import (
    vowel_loudness, vowel_quality, vowel_quality_aa, syllable_rhythm, frication,
    aspiration_burst, vowel_quality_ee, rhotic,
)

EXTRACTORS = {
    "aa": vowel_quality_aa.extract,
    "oo": vowel_quality.extract,
    "ma": syllable_rhythm.extract,
    "fa": frication.extract,
    "ha": aspiration_burst.extract,
    "ee": vowel_quality_ee.extract,
    "r": rhotic.extract,
}

__all__ = ["FeatureResult", "EXTRACTORS", "vowel_loudness", "vowel_quality",
           "vowel_quality_aa", "syllable_rhythm", "frication", "aspiration_burst",
           "vowel_quality_ee", "rhotic"]
