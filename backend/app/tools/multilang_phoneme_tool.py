from typing import List, Optional
from g2p_en import G2p
from app.tools.phoneme_tool import get_display_phoneme_list

# Initialize English G2P converter
g2p_converter = G2p()

# Indian language character mappings for basic phoneme extraction
# For Indian languages, characters generally map directly to phonemes
INDIAN_LANG_MAPPINGS = {
    "hi": {  # Hindi
        "vowels": "अ आ इ ई उ ऊ ऋ ए ऐ ओ औ अं अः".split(),
        "consonants": "क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह".split(),
        "matras": "ा ि ी ु ू ृ े ै ो ौ ं ः".split(),
        "combos": ["क्ष", "त्र", "ज्ञ", "श्र", "द्व", "स्व", "स्त", "स्न", "स्प", "स्म", "स्क", "स्क्र"]
    },
    "te": {  # Telugu
        "vowels": "అ ఆ ఇ ఈ ఉ ఊ ఋ ౠ ఌ ౡ ఎ ఏ ఐ ఒ ఓ ఔ అం అః".split(),
        "consonants": "క ఖ గ ఘ ఙ చ ఛ జ ఝ ఞ ట ఠ డ ఢ ణ త థ ద ధ న ప ఫ బ భ మ య ర ల వ శ ష స హ ళ క్ష".split(),
        "matras": "ా ి ీ ు ూ ృ ౄ ె ే ై ొ ో ౌ ం ః".split(),
        "combos": ["క్ష", "త్ర", "జ్ఞ", "శ్ర", "ద్వ", "స్వ", "స్త", "స్న", "స్ప", "స్మ", "స్క", "స్క్ర"]
    },
    "kn": {  # Kannada
        "vowels": "ಅ ಆ ಇ ಈ ಉ ಊ ಋ ೠ ಌ ೡ ಎ ಏ ಐ ಒ ಓ ಔ ಅಂ ಅಃ".split(),
        "consonants": "ಕ ಖ ಗ ಘ ಙ ಚ ಛ ಜ ಝ ಞ ಟ ಠ ಡ ಢ ಣ ತ ಥ ದ ಧ ನ ಪ ಫ ಬ ಭ ಮ ಯ ರ ಲ ವ ಶ ಷ ಸ ಹ ಳ ಕ್ಷ".split(),
        "matras": "ಾ ಿ ೀ ು ೂ ೃ ೄ ೆ ೇ ೈ ೊ ೋ ೌ ಂ ಃ".split(),
        "combos": ["ಕ್ಷ", "ತ್ರ", "ಜ್ಞ", "ಶ್ರ", "ದ್ವ", "ಸ್ವ", "ಸ್ತ", "ಸ್ನ", "ಸ್ಪ", "ಸ್ಮ", "ಸ್ಕ", "ಸ್ಕ್ರ"]
    },
    "ta": {  # Tamil
        "vowels": "அ ஆ இ ஈ உ ஊ எ ஏ ஐ ஒ ஓ ஔ".split(),
        "consonants": "க் ங் ச் ஞ் ட் ண் த் ந் ப் ம் ய் ர் ல் வ் ழ் ள் ற் ன்".split(),
        "combos": ["க்ஷ", "ஸ்ரீ", "ஜ்", "ஷ்", "ஹ்"]
    },
    "ml": {  # Malayalam
        "vowels": "അ ആ ഇ ഈ ഉ ഊ ഋ ൠ ഌ ൡ എ ഏ ഐ ഒ ഓ ഔ ം ഃ".split(),
        "consonants": "ക ഖ ഗ ഘ ങ ച ഛ ജ ഝ ഞ ട ഠ ഡ ഢ ണ ത ഥ ദ ധ ന പ ഫ ബ ഭ മ യ ര ല വ ശ ഷ സ ഹ ള ക്ഷ".split(),
        "combos": ["ക്ഷ", "ത്ര", "ജ്ഞ", "ശ്ര", "ദ്വ", "സ്വ", "സ്ത", "സ്ന", "സ്പ", "സ്മ", "സ്ക", "സ്ക്ര"]
    },
    "bn": {  # Bengali
        "vowels": "অ আ ই ঈ উ ঊ ঋ এ ঐ ও ঔ".split(),
        "consonants": "ক খ গ ঘ ঙ চ ছ জ ঝ ঞ ট ঠ ড ঢ ণ ত থ দ ধ ন প ফ ব ভ ম য র ল ব শ ষ স হ য় ড় ঢ়".split(),
        "combos": ["ক্ষ", "জ্ঞ", "স্ত", "স্ন", "স্প", "স্ম", "স্ক", "স্ক্র"]
    },
    "mr": {  # Marathi
        "vowels": "अ आ इ ई उ ऊ ऋ ए ऐ ओ औ अं अः".split(),
        "consonants": "क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह ळ".split(),
        "combos": ["क्ष", "त्र", "ज्ञ", "श्र", "द्व", "स्व", "स्त", "स्न", "स्प", "स्म", "स्क", "स्क्र"]
    }
}


def get_indian_phonemes(word: str, language: str) -> List[str]:
    """
    Extract phonemes from Indian language text using character-based approach.
    Indian scripts have relatively direct character-to-sound mappings.
    For display purposes, we show the actual characters which represent sounds.
    """
    if not word:
        return []
    
    # For Indian languages, each character generally represents a phoneme
    # We'll split by characters while keeping compound characters together
    phonemes = []
    i = 0
    
    while i < len(word):
        char = word[i]
        
        # Skip spaces
        if char.isspace():
            i += 1
            continue
        
        # Check for common compound characters (consonant clusters)
        # This is a simplified check - real implementation would need Unicode analysis
        if i + 1 < len(word):
            # Check if next character is a matra (vowel sign)
            # Matras typically have specific Unicode ranges
            next_char = word[i + 1]
            # Common matra ranges (simplified)
            is_devanagari = ord(next_char) >= 0x0900 and ord(next_char) <= 0x097F
            is_telugu = ord(next_char) >= 0x0C00 and ord(next_char) <= 0x0C7F
            is_kannada = ord(next_char) >= 0x0C80 and ord(next_char) <= 0x0CFF
            
            if is_devanagari or is_telugu or is_kannada:
                # This might be a consonant + matra combination
                phonemes.append(char + next_char)
                i += 2
                continue
        
        # Single character phoneme
        phonemes.append(char)
        i += 1
    
    return phonemes


def get_basic_phonemes_multilang(word: str, language: str = "en") -> List[str]:
    """
    Get phonemes for a word in the specified language.
    
    Args:
        word: The word to extract phonemes from
        language: Language code (en, hi, te, kn, ta, ml, bn, mr)
    
    Returns:
        List of phonemes
    """
    if not word:
        return []
    
    # For English, use existing g2p_en
    if language == "en":
        phonemes = g2p_converter(word)
        clean = []
        for p in phonemes:
            p = p.replace("0", "").replace("1", "").replace("2", "")
            if p.isalpha():
                clean.append(p)
        return clean
    
    # For Indian languages, use character-based extraction
    return get_indian_phonemes(word, language)


def get_display_phonemes_multilang(phonemes: List[str], language: str = "en") -> List[str]:
    """
    Get display-friendly phoneme labels for the given language.
    
    Args:
        phonemes: List of phonemes
        language: Language code
    
    Returns:
        List of display-friendly phoneme labels
    """
    if language == "en":
        # Use existing English display logic
        return get_display_phoneme_list(phonemes)
    
    # For Indian languages, phonemes are already in display format (characters)
    return phonemes


def compare_phonemes_multilang(expected: List[str], spoken: List[str], language: str = "en") -> dict:
    """
    Compare expected and spoken phonemes for any language.
    
    Args:
        expected: Expected phonemes
        spoken: Spoken phonemes  
        language: Language code
    
    Returns:
        Dictionary with matches and accuracy
    """
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
