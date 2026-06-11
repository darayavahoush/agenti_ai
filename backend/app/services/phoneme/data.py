# Complete phoneme library with mouth positions, tips, and example words

PHONEME_DATA = {
    # ─── CONSONANTS ───────────────────────────────────────────────
    "B": {
        "ipa": "b",
        "name": "b sound",
        "example_word": "ball",
        "tip": "Press both lips together firmly, then pop them open with your voice on.",
        "mouth_shape": "lips_closed_puff",
        "acoustic_target": {"min_duration_ms": 100, "voiced": True},
        "common_errors": ["P", "W", "M"],
        "category": "stop"
    },
    "P": {
        "ipa": "p",
        "name": "p sound",
        "example_word": "pen",
        "tip": "Press both lips together firmly, then pop them open with a puff of air. No voice.",
        "mouth_shape": "lips_closed_puff_voiceless",
        "acoustic_target": {"min_duration_ms": 100, "voiced": False},
        "common_errors": ["B", "F"],
        "category": "stop"
    },
    "M": {
        "ipa": "m",
        "name": "m sound",
        "example_word": "moon",
        "tip": "Close your lips and hum. Feel the buzz in your nose.",
        "mouth_shape": "lips_closed_hum",
        "acoustic_target": {"min_duration_ms": 150, "voiced": True},
        "common_errors": ["B", "N"],
        "category": "nasal"
    },
    "D": {
        "ipa": "d",
        "name": "d sound",
        "example_word": "dog",
        "tip": "Touch the tip of your tongue just behind your top teeth, then drop it with your voice on.",
        "mouth_shape": "tongue_tip_up",
        "acoustic_target": {"min_duration_ms": 100, "voiced": True},
        "common_errors": ["T", "G", "N"],
        "category": "stop"
    },
    "T": {
        "ipa": "t",
        "name": "t sound",
        "example_word": "tree",
        "tip": "Touch the tip of your tongue just behind your top teeth, then flick it down with a puff of air.",
        "mouth_shape": "tongue_tip_up_voiceless",
        "acoustic_target": {"min_duration_ms": 100, "voiced": False},
        "common_errors": ["D", "K"],
        "category": "stop"
    },
    "N": {
        "ipa": "n",
        "name": "n sound",
        "example_word": "nose",
        "tip": "Touch the tip of your tongue behind your top teeth and hum. Air comes through your nose.",
        "mouth_shape": "tongue_tip_up_hum",
        "acoustic_target": {"min_duration_ms": 150, "voiced": True},
        "common_errors": ["M", "D"],
        "category": "nasal"
    },
    "G": {
        "ipa": "ɡ",
        "name": "g sound",
        "example_word": "goat",
        "tip": "Let the back of your tongue touch the roof of your mouth, then drop it with your voice on.",
        "mouth_shape": "tongue_back_up",
        "acoustic_target": {"min_duration_ms": 100, "voiced": True},
        "common_errors": ["D", "K"],
        "category": "stop"
    },
    "K": {
        "ipa": "k",
        "name": "k sound",
        "example_word": "cat",
        "tip": "Let the back of your tongue touch the roof of your mouth, then drop it with a puff of air.",
        "mouth_shape": "tongue_back_up_voiceless",
        "acoustic_target": {"min_duration_ms": 100, "voiced": False},
        "common_errors": ["T", "G"],
        "category": "stop"
    },
    "F": {
        "ipa": "f",
        "name": "f sound",
        "example_word": "fish",
        "tip": "Touch your top teeth gently to your bottom lip and blow air through.",
        "mouth_shape": "teeth_on_lip",
        "acoustic_target": {"min_duration_ms": 150, "voiced": False},
        "common_errors": ["P", "TH", "V"],
        "category": "fricative"
    },
    "V": {
        "ipa": "v",
        "name": "v sound",
        "example_word": "van",
        "tip": "Touch your top teeth gently to your bottom lip and blow air with your voice on.",
        "mouth_shape": "teeth_on_lip_voiced",
        "acoustic_target": {"min_duration_ms": 150, "voiced": True},
        "common_errors": ["B", "F", "W"],  # V/W merge is standard in Indian English
        "category": "fricative"
    },
    "S": {
        "ipa": "s",
        "name": "s sound",
        "example_word": "sun",
        "tip": "Keep your tongue behind your teeth and blow a thin stream of air. Make a hissing sound.",
        "mouth_shape": "teeth_together_hiss",
        "acoustic_target": {"min_duration_ms": 150, "voiced": False},
        "common_errors": ["TH", "SH", "Z"],
        "category": "fricative"
    },
    "Z": {
        "ipa": "z",
        "name": "z sound",
        "example_word": "zebra",
        "tip": "Same as S but turn your voice on. Feel the buzz.",
        "mouth_shape": "teeth_together_hiss_voiced",
        "acoustic_target": {"min_duration_ms": 150, "voiced": True},
        "common_errors": ["S", "D"],
        "category": "fricative"
    },
    "SH": {
        "ipa": "ʃ",
        "name": "sh sound",
        "example_word": "ship",
        "tip": "Round your lips slightly and push air over your tongue. Shhhh.",
        "mouth_shape": "lips_rounded_push",
        "acoustic_target": {"min_duration_ms": 150, "voiced": False},
        "common_errors": ["S", "CH"],
        "category": "fricative"
    },
    "CH": {
        "ipa": "tʃ",
        "name": "ch sound",
        "example_word": "chair",
        "tip": "Touch the roof of your mouth with your tongue, then release with a SH sound.",
        "mouth_shape": "lips_rounded_push",
        "acoustic_target": {"min_duration_ms": 150, "voiced": False},
        "common_errors": ["SH", "T"],
        "category": "affricate"
    },
    "JH": {
        "ipa": "dʒ",
        "name": "j sound",
        "example_word": "jump",
        "tip": "Same as CH but with your voice on.",
        "mouth_shape": "lips_rounded_push_voiced",
        "acoustic_target": {"min_duration_ms": 150, "voiced": True},
        "common_errors": ["CH", "D"],
        "category": "affricate"
    },
    "L": {
        "ipa": "l",
        "name": "l sound",
        "example_word": "lamp",
        "tip": "Place your tongue tip just behind your top teeth and let air flow around the sides.",
        "mouth_shape": "tongue_tip_up_sides_open",
        "acoustic_target": {"min_duration_ms": 150, "voiced": True},
        "common_errors": ["W", "R", "Y"],
        "category": "liquid"
    },
    "R": {
        "ipa": "r",
        "name": "r sound",
        "example_word": "rabbit",
        "tip": "Curl your tongue tip toward the roof of your mouth without touching it. Round your lips slightly.",
        "mouth_shape": "tongue_curled_lips_rounded",
        "acoustic_target": {"min_duration_ms": 150, "voiced": True},
        "common_errors": ["W", "L"],
        "category": "liquid"
    },
    "W": {
        "ipa": "w",
        "name": "w sound",
        "example_word": "water",
        "tip": "Round your lips like you are about to whistle, then open them as you make the sound.",
        "mouth_shape": "lips_rounded_open",
        "acoustic_target": {"min_duration_ms": 100, "voiced": True},
        "common_errors": ["V", "B"],
        "category": "glide"
    },
    "Y": {
        "ipa": "j",
        "name": "y sound",
        "example_word": "yellow",
        "tip": "Start with your tongue high in your mouth and slide it down as you make the sound.",
        "mouth_shape": "tongue_high_slide",
        "acoustic_target": {"min_duration_ms": 100, "voiced": True},
        "common_errors": ["JH", "L"],
        "category": "glide"
    },
    "H": {
        "ipa": "h",
        "name": "h sound",
        "example_word": "house",
        "tip": "Open your mouth and breathe out gently. Like fogging up a mirror.",
        "mouth_shape": "mouth_open_breathe",
        "acoustic_target": {"min_duration_ms": 100, "voiced": False},
        "common_errors": [],
        "category": "fricative"
    },
    "TH": {
        "ipa": "θ",
        "name": "th sound",
        "example_word": "thumb",
        "tip": "Put the tip of your tongue gently between your teeth and blow air through.",
        "mouth_shape": "tongue_between_teeth",
        "acoustic_target": {"min_duration_ms": 150, "voiced": False},
        "common_errors": ["S", "F"],  # D substitution is standard Indian English variant, not flagged
        "category": "fricative"
    },
    # ─── VOWELS ───────────────────────────────────────────────────
    "AE": {
        "ipa": "æ",
        "name": "a sound (cat)",
        "example_word": "cat",
        "tip": "Open your mouth wide and push your tongue forward and down.",
        "mouth_shape": "mouth_wide_open",
        "acoustic_target": {"f1_range": [700, 1000], "f2_range": [1500, 2000]},
        "common_errors": ["EH", "AH"],
        "category": "vowel"
    },
    "AO": {
        "ipa": "ɔ",
        "name": "aw sound (ball)",
        "example_word": "ball",
        "tip": "Round your lips and open your mouth. Your tongue is low and back.",
        "mouth_shape": "lips_rounded_wide",
        "acoustic_target": {"f1_range": [500, 800], "f2_range": [700, 1100]},
        "common_errors": ["AH", "UH"],
        "category": "vowel"
    },
    "EH": {
        "ipa": "ɛ",
        "name": "e sound (bed)",
        "example_word": "bed",
        "tip": "Open your mouth halfway. Your tongue is in the middle.",
        "mouth_shape": "mouth_half_open",
        "acoustic_target": {"f1_range": [500, 700], "f2_range": [1700, 2100]},
        "common_errors": ["AE", "IH"],
        "category": "vowel"
    },
    "IH": {
        "ipa": "ɪ",
        "name": "i sound (sit)",
        "example_word": "sit",
        "tip": "Your mouth is nearly closed. Tongue is high and forward.",
        "mouth_shape": "mouth_nearly_closed_smile",
        "acoustic_target": {"f1_range": [300, 500], "f2_range": [1800, 2300]},
        "common_errors": ["IY", "EH"],
        "category": "vowel"
    },
    "IY": {
        "ipa": "iː",
        "name": "ee sound (see)",
        "example_word": "see",
        "tip": "Smile wide and keep your tongue high. Like saying cheese.",
        "mouth_shape": "mouth_smile_closed",
        "acoustic_target": {"f1_range": [200, 400], "f2_range": [2200, 2800]},
        "common_errors": ["IH"],
        "category": "vowel"
    },
    "UW": {
        "ipa": "uː",
        "name": "oo sound (moon)",
        "example_word": "moon",
        "tip": "Round your lips into a small circle. Tongue is high and back.",
        "mouth_shape": "lips_small_circle",
        "acoustic_target": {"f1_range": [200, 400], "f2_range": [700, 1100]},
        "common_errors": ["UH", "OW"],
        "category": "vowel"
    },
    # ─── INDIAN-SPECIFIC ──────────────────────────────────────────
    "RT": {
        "ipa": "ʈ",
        "name": "retroflex t sound",
        "example_word": "taal",
        "tip": "Curl your tongue back and touch the roof of your mouth further back than usual.",
        "mouth_shape": "tongue_curled_back_touch",
        "acoustic_target": {"min_duration_ms": 100, "voiced": False},
        "common_errors": ["T"],
        "category": "stop"
    },
    "RD": {
        "ipa": "ɖ",
        "name": "retroflex d sound",
        "example_word": "daal",
        "tip": "Curl your tongue back and touch the roof of your mouth further back, then drop it with voice.",
        "mouth_shape": "tongue_curled_back_touch_voiced",
        "acoustic_target": {"min_duration_ms": 100, "voiced": True},
        "common_errors": ["D"],
        "category": "stop"
    },
}

ACOUSTIC_FEEDBACK_RULES = [
    {
        "id": "too_quiet",
        "condition": lambda a: a.get("loudness_db", 0) < -35,
        "tip": "Try speaking a little louder. Pretend you are talking to someone across the room.",
        "mood": "encourage"
    },
    {
        "id": "too_loud",
        "condition": lambda a: a.get("loudness_db", 0) > -10,
        "tip": "Great energy. Try speaking a little softer now.",
        "mood": "encourage"
    },
    {
        "id": "too_fast",
        "condition": lambda a: a.get("speaking_rate", 0) > 4.0,
        "tip": "Slow down a little. Take it one sound at a time.",
        "mood": "instruction"
    },
    {
        "id": "too_slow",
        "condition": lambda a: a.get("speaking_rate", 0) < 1.5 and a.get("speaking_rate", 0) > 0,
        "tip": "Good try. Now let the sounds flow together more smoothly.",
        "mood": "encourage"
    },
    {
        "id": "poor_voice_quality",
        "condition": lambda a: a.get("hnr_db", 25) < 10,
        "tip": "Take a breath and try again. Make sure your voice is nice and clear.",
        "mood": "encourage"
    },
    {
        "id": "high_jitter",
        "condition": lambda a: a.get("jitter_percent", 0) > 2.5,
        "tip": "Try to keep your voice steady and smooth, like a long smooth train track.",
        "mood": "instruction"
    },
]

DRILL_SEQUENCE_RULES = {
    "accuracy_threshold": 40,
    "max_attempts_before_drill": 3,
    "phonemes_per_session": 3,
}
