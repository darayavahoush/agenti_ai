"""
Utility functions for transliterating between English and Indian language scripts.
Converts Whisper's English transliteration output back to native scripts using ITRANS standard.
"""

import logging
from typing import Dict

logger = logging.getLogger("uvicorn.error")

# ITRANS to Native Script Mappings
# Based on ITRANS (Indian Languages TRANSliteration) standard
ITRANS_MAPPINGS = {
    # Hindi (Devanagari)
    "hi": {
        # Vowels
        "a": "अ", "aa": "आ", "i": "इ", "ii": "ई", "u": "उ", "uu": "ऊ",
        "ri": "ऋ", "e": "ए", "ai": "ऐ", "o": "ओ", "au": "औ",
        # Consonants
        "k": "क", "kh": "ख", "g": "ग", "gh": "घ", "ng": "ङ",
        "ch": "च", "chh": "छ", "j": "ज", "jh": "झ", "ny": "ञ",
        "t": "ट", "th": "ठ", "d": "ड", "dh": "ढ", "n": "ण",
        "ta": "त", "tha": "थ", "da": "द", "dha": "ध", "na": "न",
        "p": "प", "ph": "फ", "b": "ब", "bh": "भ", "m": "म",
        "y": "य", "r": "र", "l": "ल", "v": "व", "w": "व",
        "sh": "श", "s": "स", "h": "ह",
        # With vowels (consonant + vowel)
        "ka": "क", "ki": "कि", "ku": "कु", "ke": "के", "ko": "को",
        "ga": "ग", "gi": "गि", "gu": "गु", "ge": "गे", "go": "गो",
        "ja": "ज", "ji": "जि", "ju": "जु", "je": "जे", "jo": "जो",
        "ta": "त", "ti": "ति", "tu": "तु", "te": "ते", "to": "तो",
        "da": "द", "di": "दि", "du": "दु", "de": "दे", "do": "दो",
        "pa": "प", "pi": "पि", "pu": "पु", "pe": "पे", "po": "पो",
        "ba": "ब", "bi": "बि", "bu": "बु", "be": "बे", "bo": "बो",
        "ma": "म", "mi": "मि", "mu": "मु", "me": "मे", "mo": "मो",
        "ya": "य", "yi": "यि", "yu": "यु", "ye": "ये", "yo": "यो",
        "ra": "र", "ri": "रि", "ru": "रु", "re": "रे", "ro": "रो",
        "la": "ल", "li": "लि", "lu": "लु", "le": "ले", "lo": "लो",
        "sa": "स", "si": "सि", "su": "सु", "se": "से", "so": "सो",
    },
    # Telugu
    "te": {
        # Vowels
        "a": "అ", "aa": "ఆ", "i": "ఇ", "ii": "ఈ", "u": "ఉ", "uu": "ఊ",
        "ri": "ఋ", "e": "ఏ", "ai": "ఐ", "o": "ఓ", "au": "ఔ",
        # Consonants
        "k": "క", "kh": "ఖ", "g": "గ", "gh": "ఘ", "ng": "ఙ",
        "ch": "చ", "chh": "ఛ", "j": "జ", "jh": "ఝ", "ny": "ఞ",
        "t": "ట", "th": "ఠ", "d": "డ", "dh": "ఢ", "n": "ణ",
        "ta": "త", "tha": "థ", "da": "ద", "dha": "ధ", "na": "న",
        "p": "ప", "ph": "ఫ", "b": "బ", "bh": "భ", "m": "ము",
        "y": "య", "r": "ర", "l": "ల", "v": "వ", "w": "వ",
        "sh": "శ", "s": "స", "h": "హ",
        # With vowels
        "ka": "క", "ki": "కి", "ku": "కు", "ke": "కే", "ko": "కో",
        "ga": "గ", "gi": "గి", "gu": "గు", "ge": "గే", "go": "గో",
        "ja": "జ", "ji": "జి", "ju": "జు", "je": "జే", "jo": "జో",
        "ta": "త", "ti": "తి", "tu": "తు", "te": "తే", "to": "తో",
        "da": "ద", "di": "ది", "du": "దు", "de": "దే", "do": "దో",
        "pa": "ప", "pi": "పి", "pu": "పు", "pe": "పే", "po": "పో",
        "ba": "బ", "bi": "బి", "bu": "బు", "be": "బే", "bo": "బో",
        "ma": "మ", "mi": "మి", "mu": "ము", "me": "మే", "mo": "మో",
        "ya": "య", "yi": "యి", "yu": "యు", "ye": "యే", "yo": "యో",
        "ra": "ర", "ri": "రి", "ru": "రు", "re": "రే", "ro": "రో",
        "la": "ల", "li": "లి", "lu": "లు", "le": "లే", "lo": "లో",
        "sa": "స", "si": "సి", "su": "సు", "se": "సే", "so": "సో",
    },
    # Kannada
    "kn": {
        # Vowels
        "a": "ಅ", "aa": "ಆ", "i": "ಇ", "ii": "ಈ", "u": "ಉ", "uu": "ಊ",
        "ri": "ಋ", "e": "ಏ", "ai": "ಐ", "o": "ಓ", "au": "ಔ",
        # Consonants
        "k": "ಕ", "kh": "ಖ", "g": "ಗ", "gh": "ಘ", "ng": "ಙ",
        "ch": "ಚ", "chh": "ಛ", "j": "ಜ", "jh": "ಝ", "ny": "ಞ",
        "t": "ಟ", "th": "ಠ", "d": "ಡ", "dh": "ಢ", "n": "ಣ",
        "ta": "ತ", "tha": "ಥ", "da": "ದ", "dha": "ಧ", "na": "ನ",
        "p": "ಪ", "ph": "ಫ", "b": "ಬ", "bh": "ಭ", "m": "ಮ",
        "y": "ಯ", "r": "ರ", "l": "ಲ", "v": "ವ", "w": "ವ",
        "sh": "ಶ", "s": "ಸ", "h": "ಹ",
        # With vowels
        "ka": "ಕ", "ki": "ಕಿ", "ku": "ಕು", "ke": "ಕೆ", "ko": "ಕೋ",
        "ga": "ಗ", "gi": "ಗಿ", "gu": "ಗು", "ge": "ಗೆ", "go": "ಗೋ",
        "ja": "ಜ", "ji": "ಜಿ", "ju": "ಜು", "je": "ಜೆ", "jo": "ಜೋ",
        "ta": "ತ", "ti": "ತಿ", "tu": "ತು", "te": "ತೆ", "to": "ತೋ",
        "da": "ದ", "di": "ದಿ", "du": "ದು", "de": "ದೆ", "do": "ದೋ",
        "pa": "ಪ", "pi": "ಪಿ", "pu": "ಪು", "pe": "ಪೆ", "po": "ಪೋ",
        "ba": "ಬ", "bi": "ಬಿ", "bu": "ಬು", "be": "ಬೆ", "bo": "ಬೋ",
        "ma": "ಮ", "mi": "ಮಿ", "mu": "ಮು", "me": "ಮೆ", "mo": "ಮೋ",
        "ya": "ಯ", "yi": "ಯಿ", "yu": "ಯು", "ye": "ಯೆ", "yo": "ಯೋ",
        "ra": "ರ", "ri": "ರಿ", "ru": "ರು", "re": "ರೆ", "ro": "ರೋ",
        "la": "ಲ", "li": "ಲಿ", "lu": "ಲು", "le": "ಲೆ", "lo": "ಲೋ",
        "sa": "ಸ", "si": "ಸಿ", "su": "ಸು", "se": "ಸೆ", "so": "ಸೋ",
    }
}


def transliterate_english_to_native(text: str, language: str) -> str:
    """
    Convert English transliteration (from Whisper) back to native script.
    Uses ITRANS (Indian Languages TRANSliteration) standard mappings.
    
    For example:
    - English "ka" (Hindi) → "क"
    - English "kaa" (Telugu) → "కా"
    - English "ki" (Kannada) → "ಕಿ"
    
    Args:
        text: English transliterated text (output from Whisper/ITRANS format)
        language: Language code (hi, te, kn)
    
    Returns:
        Text in native script, or original text if conversion fails
    """
    if not text or language not in ITRANS_MAPPINGS:
        return text
    
    try:
        mapping = ITRANS_MAPPINGS[language]
        text = text.lower().strip()
        
        # Try exact match first
        if text in mapping:
            native_text = mapping[text]
            logger.info(f"✅ Transliterated '{text}' ({language}) → '{native_text}'")
            return native_text
        
        # Try splitting into consonant+vowel patterns and process
        # Look for longest match first to handle multi-character sequences
        result = ""
        i = 0
        changed = False
        
        while i < len(text):
            found = False
            # Try 3-character, 2-character, then 1-character matches
            for length in [3, 2, 1]:
                if i + length <= len(text):
                    substring = text[i:i+length]
                    if substring in mapping:
                        result += mapping[substring]
                        i += length
                        found = True
                        changed = True
                        break
            
            if not found:
                # Keep unrecognized characters as-is
                result += text[i]
                i += 1
        
        if changed:
            logger.info(f"✅ Transliterated '{text}' ({language}) → '{result}'")
            return result
        
        return text
        
    except Exception as e:
        logger.warning(f"⚠️ Transliteration failed for '{text}' to {language}: {e}")
        return text


def convert_whisper_output_to_native(whisper_text: str, language: str) -> str:
    """
    Convert Whisper's English transliteration output to native script.
    
    This is a wrapper around transliterate_english_to_native that handles
    Whisper-specific quirks (lowercase, spacing, etc.)
    
    Args:
        whisper_text: Text output from Whisper (typically English transliteration)
        language: Language code (hi, te, kn)
    
    Returns:
        Text in native script
    """
    if not whisper_text or language == "en":
        return whisper_text
    
    # Whisper outputs lowercase and may have spacing issues
    return transliterate_english_to_native(whisper_text.lower(), language)


def should_transliterate(language: str) -> bool:
    """
    Check if transliteration should be applied for this language.
    
    Args:
        language: Language code
    
    Returns:
        True if language needs transliteration from English
    """
    return language in ITRANS_MAPPINGS
