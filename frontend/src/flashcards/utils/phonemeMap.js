// ARPAbet → friendly display for kids/therapists
export const PHONEME_MAP = {
  // Vowels
  "IY": { label: "ee", example: "as in 'see'" },
  "IH": { label: "ih", example: "as in 'sit'" },
  "EH": { label: "eh", example: "as in 'bed'" },
  "AE": { label: "aa", example: "as in 'cat'" },
  "AA": { label: "ah", example: "as in 'hot'" },
  "AO": { label: "aw", example: "as in 'law'" },
  "UH": { label: "uh", example: "as in 'book'" },
  "UW": { label: "oo", example: "as in 'food'" },
  "AH": { label: "uh", example: "as in 'cup'" },
  "AX": { label: "uh", example: "as in 'ago'" },
  "ER": { label: "er", example: "as in 'bird'" },
  // Diphthongs
  "EY": { label: "ay", example: "as in 'say'" },
  "AY": { label: "eye", example: "as in 'my'" },
  "OY": { label: "oy", example: "as in 'boy'" },
  "AW": { label: "ow", example: "as in 'now'" },
  "OW": { label: "oh", example: "as in 'go'" },
  // Consonants
  "P":  { label: "p", example: "as in 'pen'" },
  "B":  { label: "b", example: "as in 'bed'" },
  "T":  { label: "t", example: "as in 'top'" },
  "D":  { label: "d", example: "as in 'dog'" },
  "K":  { label: "k", example: "as in 'cat'" },
  "G":  { label: "g", example: "as in 'go'" },
  "F":  { label: "f", example: "as in 'fun'" },
  "V":  { label: "v", example: "as in 'van'" },
  "TH": { label: "th", example: "as in 'thin'" },
  "DH": { label: "th", example: "as in 'this'" },
  "S":  { label: "s", example: "as in 'sun'" },
  "Z":  { label: "z", example: "as in 'zoo'" },
  "SH": { label: "sh", example: "as in 'she'" },
  "ZH": { label: "zh", example: "as in 'measure'" },
  "HH": { label: "h", example: "as in 'hat'" },
  "CH": { label: "ch", example: "as in 'chat'" },
  "JH": { label: "j", example: "as in 'jump'" },
  "M":  { label: "m", example: "as in 'man'" },
  "N":  { label: "n", example: "as in 'sun'" },
  "NG": { label: "ng", example: "as in 'sing'" },
  "L":  { label: "l", example: "as in 'leg'" },
  "R":  { label: "r", example: "as in 'run'" },
  "W":  { label: "w", example: "as in 'win'" },
  "Y":  { label: "y", example: "as in 'yes'" },
};

export function friendlyPhoneme(p) {
  return PHONEME_MAP[p]?.label || p.toLowerCase();
}

export function phonemeExample(p) {
  return PHONEME_MAP[p]?.example || "";
}
