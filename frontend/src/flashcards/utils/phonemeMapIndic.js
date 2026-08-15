// IPA → friendly display for Hindi/Kannada phonemes from epitran

export const INDIC_PHONEME_MAP = {
  // Stops
  "p": { label: "प/ಪ", hint: "p" },
  "b": { label: "ब/ಬ", hint: "b" },
  "t": { label: "त/ತ", hint: "t" },
  "d": { label: "द/ದ", hint: "d" },
  "k": { label: "क/ಕ", hint: "k" },
  "g": { label: "ग/ಗ", hint: "g" },
  // Aspirated stops
  "pʰ": { label: "फ/ಫ", hint: "ph" },
  "bʱ": { label: "भ/ಭ", hint: "bh" },
  "tʰ": { label: "थ/ಥ", hint: "th" },
  "dʱ": { label: "ध/ಧ", hint: "dh" },
  "kʰ": { label: "ख/ಖ", hint: "kh" },
  "gʱ": { label: "घ/ಘ", hint: "gh" },
  // Retroflex
  "ʈ": { label: "ट/ಟ", hint: "ṭ" },
  "ɖ": { label: "ड/ಡ", hint: "ḍ" },
  "ʈʰ": { label: "ठ/ಠ", hint: "ṭh" },
  "ɖʱ": { label: "ढ/ಢ", hint: "ḍh" },
  // Affricates
  "tʃ": { label: "च/ಚ", hint: "ch" },
  "dʒ": { label: "ज/ಜ", hint: "j" },
  "tʃʰ": { label: "छ/ಛ", hint: "chh" },
  "dʒʱ": { label: "झ/ಝ", hint: "jh" },
  // Nasals
  "m": { label: "म/ಮ", hint: "m" },
  "n": { label: "न/ನ", hint: "n" },
  "ŋ": { label: "ङ/ಙ", hint: "ng" },
  "ɲ": { label: "ञ/ಞ", hint: "ny" },
  "ɳ": { label: "ण/ಣ", hint: "ṇ" },
  // Fricatives
  "s": { label: "स/ಸ", hint: "s" },
  "z": { label: "ज़/ಝ", hint: "z" },
  "ʃ": { label: "श/ಶ", hint: "sh" },
  "ʂ": { label: "ष/ಷ", hint: "ṣ" },
  "h": { label: "ह/ಹ", hint: "h" },
  "f": { label: "फ़/ಫ", hint: "f" },
  // Liquids & glides
  "r": { label: "र/ರ", hint: "r" },
  "l": { label: "ल/ಲ", hint: "l" },
  "ɭ": { label: "ळ/ಳ", hint: "ḷ" },
  "v": { label: "व/ವ", hint: "v" },
  "j": { label: "य/ಯ", hint: "y" },
  "w": { label: "व/ವ", hint: "w" },
  // Vowels
  "a": { label: "अ/ಅ", hint: "a" },
  "aː": { label: "आ/ಆ", hint: "aa" },
  "i": { label: "इ/ಇ", hint: "i" },
  "iː": { label: "ई/ಈ", hint: "ee" },
  "u": { label: "उ/ಉ", hint: "u" },
  "uː": { label: "ऊ/ಊ", hint: "oo" },
  "e": { label: "ए/ಏ", hint: "e" },
  "eː": { label: "ए/ಏ", hint: "e" },
  "o": { label: "ओ/ಒ", hint: "o" },
  "oː": { label: "ओ/ಓ", hint: "oo" },
  "ə": { label: "अ/ಅ", hint: "a" },
  "ɛ": { label: "ऐ/ಐ", hint: "ai" },
  "ɔ": { label: "औ/ಔ", hint: "au" },
};

export function displayPhoneme(p, language) {
  if (language === "english") return null;
  const entry = INDIC_PHONEME_MAP[p];
  if (!entry) return { label: p, hint: p };
  // Show only relevant script
  const parts = entry.label.split("/");
  if (language === "hindi") return { label: parts[0], hint: entry.hint };
  if (language === "kannada") return { label: parts[1], hint: entry.hint };
  return { label: p, hint: p };
}
