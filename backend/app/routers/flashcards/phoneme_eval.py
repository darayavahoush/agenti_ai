import torch
import torchaudio
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

MODEL_IDS = {
    "hindi": "ai4bharat/indicwav2vec-hindi",
    "kannada": "amoghsgopadi/wav2vec2-large-xlsr-kn",
}

import gc

_processors = {}
_models = {}
_current_language = None

def _get_model(language: str):
    global _current_language

    if language == _current_language and language in _models:
        return _models[language], _processors[language]

    # Evict whatever's currently loaded to keep memory footprint to one model at a time
    if _current_language is not None and _current_language in _models:
        print(f"Unloading {_current_language} phoneme model to load {language}")
        del _models[_current_language]
        del _processors[_current_language]
        gc.collect()

    model_id = MODEL_IDS[language]
    _processors[language] = Wav2Vec2Processor.from_pretrained(model_id)
    _models[language] = Wav2Vec2ForCTC.from_pretrained(model_id)
    _models[language].eval()
    _current_language = language

    return _models[language], _processors[language]

# Hindi confusable groups (dental/retroflex, aspiration, nukta, sibilants)
HINDI_CONFUSABLE_GROUPS = [
    # Dental vs retroflex place of articulation
    {"त", "ट"}, {"थ", "ठ"}, {"द", "ड"}, {"ध", "ढ"}, {"न", "ण"},
    # Aspiration
    {"क", "ख"}, {"ग", "घ"}, {"च", "छ"}, {"ज", "झ"}, {"प", "फ"}, {"ब", "भ"},
    # Nukta retroflex flaps
    {"ड़", "ड"}, {"ढ़", "ढ"},
    # Sibilants
    {"स", "श", "ष"},
    # Vowel length (short vs long) — very common speech therapy targets
    {"इ", "ई"}, {"उ", "ऊ"}, {"ए", "ऐ"}, {"ओ", "औ"}, {"अ", "आ"},
    # Glide/semivowel endings often blurred in casual/child speech
    {"य", "ई"}, {"व", "उ"},
    # Nasalization
    {"न", "ं"},
]

# Kannada confusable groups (dental/retroflex, aspiration, sibilants, retroflex lateral)
KANNADA_CONFUSABLE_GROUPS = [
    # Dental vs retroflex
    {"ತ", "ಟ"}, {"ಥ", "ಠ"}, {"ದ", "ಡ"}, {"ಧ", "ಢ"}, {"ನ", "ಣ"},
    # Aspiration pairs
    {"ಕ", "ಖ"}, {"ಗ", "ಘ"}, {"ಚ", "ಛ"}, {"ಜ", "ಝ"}, {"ಪ", "ಫ"}, {"ಬ", "ಭ"},
    # Sibilants
    {"ಸ", "ಶ", "ಷ"},
    # Retroflex lateral vs dental lateral (ಳ vs ಲ) — distinctly Kannada/Dravidian
    {"ಳ", "ಲ"},
    # Retroflex approximant vs retroflex lateral (ಱ vs ಳ), less common but real
    {"ರ", "ಱ"},
    # Vowel length (short vs long)
    {"ಇ", "ಈ"}, {"ಉ", "ಊ"}, {"ಎ", "ಏ"}, {"ಒ", "ಓ"}, {"ಅ", "ಆ"},
]

CONFUSABLE_GROUPS_BY_LANGUAGE = {
    "hindi": HINDI_CONFUSABLE_GROUPS,
    "kannada": KANNADA_CONFUSABLE_GROUPS,
}

def load_audio(path, target_sr=16000):
    waveform, sr = torchaudio.load(path)
    if sr != target_sr:
        waveform = torchaudio.functional.resample(waveform, sr, target_sr)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    return waveform.squeeze(0)

def get_phoneme_probs(audio_path, language):
    model, processor = _get_model(language)
    audio = load_audio(audio_path)
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
    with torch.no_grad():
        logits = model(inputs.input_values).logits
    probs = torch.softmax(logits, dim=-1)[0]
    return probs, processor.tokenizer

def score_target_char(audio_path, target_char, confusable_chars, language):
    probs, tokenizer = get_phoneme_probs(audio_path, language)
    vocab = tokenizer.get_vocab()

    target_id = vocab.get(target_char)
    confusable_ids = {c: vocab.get(c) for c in confusable_chars}

    target_score = probs[:, target_id].max().item() if target_id is not None else 0.0
    confusable_scores = {
        c: probs[:, cid].max().item()
        for c, cid in confusable_ids.items() if cid is not None
    }

    best = max([("target", target_score)] + list(confusable_scores.items()), key=lambda x: x[1])
    return {
        "target_score": target_score,
        "confusable_scores": confusable_scores,
        "predicted": best[0],
        "correct": best[0] == "target",
    }

def find_all_confusable_groups(word: str, language: str):
    """
    Returns ALL (char, group) matches found in the word, deduplicated by char,
    instead of stopping at the first one — important for words with multiple
    tricky sounds (e.g. मछली has both a sibilant and an aspiration pair).
    """
    groups = CONFUSABLE_GROUPS_BY_LANGUAGE.get(language, [])
    seen_chars = set()
    matches = []
    for char in word:
        if char in seen_chars:
            continue
        for group in groups:
            if char in group:
                matches.append((char, group))
                seen_chars.add(char)
                break
    return matches

def check_confusable_phonemes(audio_path: str, target_word: str, language: str):
    """
    Checks EVERY known confusable character in target_word (not just the first),
    scoring the audio against each one vs its confusables. This gives a full
    picture of pronunciation accuracy across all tricky sounds in the word,
    which matters for speech therapy use where multiple sounds may need
    individual feedback.

    Returns a list of per-character results, or None if language isn't
    supported or no confusable chars are present. Model is loaded once and
    reused across all checks in the word (no repeated eviction/reload).
    """
    if language not in MODEL_IDS:
        return None
    matches = find_all_confusable_groups(target_word, language)
    if not matches:
        return None

    results = []
    for target_char, group in matches:
        confusables = [c for c in group if c != target_char]
        result = score_target_char(audio_path, target_char, confusables, language)
        result["character"] = target_char
        results.append(result)
    return results
