export const LETTER_NAME_GUIDES = {
  ay: {
    svg: "front_mid",
    anatomy: "Jaw half open · Lips gently spread · Tongue moves from mid-front to high-front",
    steps: [
      "Begin with the tongue at mid height near the front of the mouth",
      "Keep the jaw comfortably open and the lips gently spread",
      "Glide the tongue upward and forward to finish with a short 'ee' sound",
      "Keep the voice on throughout the smooth glide",
    ],
  },
  ee: {
    svg: "front_high",
    anatomy: "Tongue high + front · Lips spread · Jaw nearly closed",
    steps: [
      "Raise the front of the tongue close to the roof of the mouth",
      "Spread the lips gently as if smiling",
      "Keep a small gap between the teeth",
      "Hold the clear 'ee' sound with the voice on",
    ],
  },
  eh: {
    svg: "front_mid",
    anatomy: "Tongue mid + front · Lips relaxed · Jaw half open",
    steps: [
      "Start with a short 'eh' sound",
      "Keep the tongue at mid height toward the front",
      "Keep the lips relaxed and the jaw half open",
      "Move cleanly into the final consonant without adding another vowel",
    ],
  },
  eye: {
    svg: "front_open",
    anatomy: "Jaw opens then closes · Tongue moves low-central to high-front · Lips relaxed",
    steps: [
      "Open the jaw for a short 'ah' sound",
      "Start with the tongue low and relaxed",
      "Glide the tongue upward and forward while the jaw closes slightly",
      "Finish with a light 'ee' sound and keep the voice on",
    ],
  },
  oh: {
    svg: "back_low",
    anatomy: "Lips rounded · Tongue mid-back then high-back · Jaw partly open",
    steps: [
      "Round the lips into a medium circle",
      "Begin with the tongue at mid height toward the back",
      "Glide the tongue slightly upward and let the lips narrow",
      "Keep the voice on for the full 'oh' sound",
    ],
  },
  you: {
    svg: "back_high",
    anatomy: "Tongue starts high-front then moves high-back · Lips become rounded",
    steps: [
      "Start with the tongue high and toward the front for a quick 'y' glide",
      "Move the tongue toward the back of the mouth",
      "Round the lips into a small circle",
      "Hold the final 'oo' sound with the voice on",
    ],
  },
  ar: {
    svg: "retroflex",
    anatomy: "Jaw open · Tongue low for 'aa', then tip curls slightly back for Indian-English 'r'",
    steps: [
      "Open the mouth and begin with a clear 'aa' sound",
      "Keep the tongue low and relaxed at the start",
      "Curl the tongue tip slightly upward and back without pressing hard",
      "Keep the voice on as you finish the letter name",
    ],
  },
  doubleYou: {
    svg: "back_high",
    anatomy: "Three-part name · Lips alternate relaxed and rounded · Tongue finishes high-back",
    steps: [
      "Say 'double' clearly with light, even stress",
      "For the final part, begin with a quick 'y' glide",
      "Move the tongue high and back while rounding the lips",
      "Finish by holding the 'oo' sound briefly",
    ],
  },
};

export const ALPHABET_SOUNDS = {
  A: { ipa: "/eɪ/", spoken: "ay", guide: "ay", transition: "Begin directly with the 'ay' glide." },
  B: { ipa: "/biː/", spoken: "bee", guide: "ee", transition: "Press both lips together for /b/, release them, then continue into long 'ee'." },
  C: { ipa: "/siː/", spoken: "see", guide: "ee", transition: "Start with a narrow, voiceless /s/ hiss, then continue into long 'ee'." },
  D: { ipa: "/diː/", spoken: "dee", guide: "ee", transition: "Touch the tongue tip behind the top teeth for /d/, release it, then say long 'ee'." },
  E: { ipa: "/iː/", spoken: "ee", guide: "ee", transition: "Begin directly with the long 'ee' vowel." },
  F: { ipa: "/ɛf/", spoken: "eff", guide: "eh", transition: "Say short 'eh', then touch the top teeth to the lower lip and blow air for /f/." },
  G: { ipa: "/dʒiː/", spoken: "gee", guide: "ee", transition: "Start with voiced /j/ as in 'jam', then continue into long 'ee'." },
  H: { ipa: "/eɪtʃ/", spoken: "aitch", guide: "ay", transition: "Say 'ay', then finish with a quick /t/ release flowing into 'sh'." },
  I: { ipa: "/aɪ/", spoken: "eye", guide: "eye", transition: "Begin directly with the 'eye' glide." },
  J: { ipa: "/dʒeɪ/", spoken: "jay", guide: "ay", transition: "Start with voiced /j/ as in 'jam', then glide smoothly into 'ay'." },
  K: { ipa: "/keɪ/", spoken: "kay", guide: "ay", transition: "Release /k/ from the back of the tongue, then glide smoothly into 'ay'." },
  L: { ipa: "/ɛl/", spoken: "ell", guide: "eh", transition: "Say short 'eh', then place the tongue tip behind the top teeth to finish /l/." },
  M: { ipa: "/ɛm/", spoken: "em", guide: "eh", transition: "Say short 'eh', then close both lips and hum to finish /m/." },
  N: { ipa: "/ɛn/", spoken: "en", guide: "eh", transition: "Say short 'eh', then touch the tongue tip behind the top teeth and hum through the nose." },
  O: { ipa: "/oʊ/", spoken: "oh", guide: "oh", transition: "Begin directly with the rounded 'oh' glide." },
  P: { ipa: "/piː/", spoken: "pee", guide: "ee", transition: "Press both lips together and release a puff for /p/, then continue into long 'ee'." },
  Q: { ipa: "/kjuː/", spoken: "cue", guide: "you", transition: "Release /k/ at the back of the tongue, then say 'you' with rounded lips." },
  R: { ipa: "/ɑːr/", spoken: "are", guide: "ar", transition: "Begin with open 'aa', then finish with the light retroflex /r/ common in Indian English." },
  S: { ipa: "/ɛs/", spoken: "ess", guide: "eh", transition: "Say short 'eh', then bring the tongue near the ridge and finish with a voiceless hiss." },
  T: { ipa: "/tiː/", spoken: "tee", guide: "ee", transition: "Touch the tongue tip behind the top teeth for /t/, release it, then say long 'ee'." },
  U: { ipa: "/juː/", spoken: "you", guide: "you", transition: "Begin directly with 'you': a quick /y/ glide followed by rounded 'oo'." },
  V: { ipa: "/viː/", spoken: "vee", guide: "ee", transition: "Touch the top teeth to the lower lip with voice for /v/, then continue into long 'ee'." },
  W: { ipa: "/ˈdʌbəljuː/", spoken: "double you", guide: "doubleYou", transition: "Say all three parts clearly: 'dub' + 'uhl' + 'you'. Stress the first part." },
  X: { ipa: "/ɛks/", spoken: "ex", guide: "eh", transition: "Say short 'eh', release /k/ at the back, then finish immediately with an /s/ hiss." },
  Y: { ipa: "/waɪ/", spoken: "why", guide: "eye", transition: "Round the lips briefly for /w/, then open and glide through the 'eye' sound." },
  Z: { ipa: "/zɛd/", spoken: "zed", guide: "eh", transition: "Use voiced /z/, say short 'eh', then touch the tongue behind the top teeth to finish /d/." },
};

// Phonics-teaching sounds -- what a synthetic-phonics program (Jolly
// Phonics / UFLI, matching the convention VaakMirror's SPOKEN_FORM table
// already uses for consistency across the app) actually wants said for
// each letter: the isolated sound the letter makes in a word ("sss", not
// "ess"; "puh", not "pee"), not the letter's name. This was previously
// missing entirely -- the alphabet screen only ever spoke/showed letter
// names, which is backwards for early phonics instruction.
//
// svgKey points directly at a place/manner articulation shape already
// built in MouthDiagram.jsx (alveolar_fric, bilabial_stop, etc.) -- these
// existed and were fully unused by the letter-name guide system, which
// only ever showed a letter-name vowel glide (front_mid, back_high, ...)
// instead of the shape for the actual consonant/vowel being taught.
export const PHONIC_SOUNDS = {
  A: { ipa: "/æ/", spoken: "a", svgKey: "front_open", anatomy: "Jaw open · Tongue low and front · Lips relaxed", steps: ["Open the jaw fairly wide", "Keep the tongue low and toward the front", "Say a short, flat 'a' as in 'cat' — don't glide into another vowel", "Keep it short and clipped, not held long"] },
  B: { ipa: "/b/", spoken: "buh", svgKey: "bilabial_stop", anatomy: "Both lips pressed together · Voice on · Quick release", tip: "Press both lips together, hum briefly, then release with a soft 'uh' — feel the buzz on the lips before they pop open.", steps: ["Press both lips gently together", "Hum with the voice on while lips are closed", "Release the lips and let a light 'uh' escape", "Keep the vowel after it as quiet as possible — it's just a release, not a full syllable"] },
  C: { ipa: "/k/", spoken: "kuh", svgKey: "velar_stop", anatomy: "Back of tongue against the soft palate · No voice · Quick release", tip: "Same as K — this is the hard-C sound taught first in phonics.", steps: ["Lift the back of the tongue to touch the soft palate", "Build a little pressure, then release with a puff of air", "Add only a light, quiet 'uh' after the release", "No hum — this sound is voiceless"] },
  D: { ipa: "/d/", spoken: "duh", svgKey: "alveolar_stop", anatomy: "Tongue tip against the ridge behind the top teeth · Voice on · Quick release", tip: "Same tongue spot as T, but with the voice on — feel the tongue tap and a soft buzz.", steps: ["Touch the tongue tip to the ridge behind the top front teeth", "Hum lightly while holding contact", "Release the tongue down and let a light 'uh' escape", "Keep the vowel after it quiet and quick"] },
  E: { ipa: "/ɛ/", spoken: "eh", svgKey: "front_mid", anatomy: "Tongue mid-height and front · Lips relaxed · Jaw half open", steps: ["Keep the tongue at mid-height, toward the front", "Relax the lips — no rounding, no spreading", "Say a short, clipped 'eh' as in 'bed'", "Stop cleanly, don't glide into 'ee'"] },
  F: { ipa: "/f/", spoken: "fff", svgKey: "labiodental", anatomy: "Top teeth resting on the bottom lip · No voice · Steady airflow", tip: "Same placement as V, but blow air without humming — a continuous hiss you can hold.", steps: ["Rest the top teeth gently on the bottom lip", "Blow a steady stream of air through the gap", "Hold the sound — it can be stretched out, unlike a stop sound", "No voice/hum, just air"] },
  G: { ipa: "/g/", spoken: "guh", svgKey: "velar_stop", anatomy: "Back of tongue against the soft palate · Voice on · Quick release", tip: "Same tongue spot as K, but with the voice/hum on.", steps: ["Lift the back of the tongue to touch the soft palate", "Hum lightly while holding contact", "Release with a light 'uh' — keep it short", "This is the hard-G sound, as in 'go'"] },
  H: { ipa: "/h/", spoken: "huh", svgKey: "glottal", anatomy: "Mouth relaxed and open · No specific tongue placement · Breath only", steps: ["Relax the mouth into a neutral, open shape", "Breathe out with a light puff, adding a little voice", "There's no tongue or lip contact at all for this sound", "Keep it soft — it's just breath with a hint of voice"] },
  I: { ipa: "/ɪ/", spoken: "ih", svgKey: "front_high", anatomy: "Tongue high and front, but relaxed · Lips loosely spread · Jaw nearly closed", steps: ["Raise the front of the tongue high, but keep it relaxed (not tense like 'ee')", "Keep the lips loosely open, not tightly spread", "Say a short, clipped 'ih' as in 'sit'", "Stop cleanly — don't glide into 'ee'"] },
  J: { ipa: "/dʒ/", spoken: "juh", svgKey: "postalveolar", anatomy: "Tongue tip near the ridge just behind the alveolar ridge, lips slightly rounded · Voice on", tip: "Same starting shape as CH, but voiced — feel the buzz.", steps: ["Bring the tongue tip close to the ridge just behind the front teeth", "Round the lips slightly", "Release with voice on into a light 'uh'", "Keep it a single quick sound, not drawn out"] },
  K: { ipa: "/k/", spoken: "kuh", svgKey: "velar_stop", anatomy: "Back of tongue against the soft palate · No voice · Quick release", steps: ["Lift the back of the tongue to touch the soft palate", "Build a little pressure, then release with a puff of air", "Add only a light, quiet 'uh' after the release", "No hum — this sound is voiceless"] },
  L: { ipa: "/l/", spoken: "lll", svgKey: "alveolar_lateral", anatomy: "Tongue tip on the ridge behind the top teeth, sides of the tongue down · Voice on", tip: "Air flows around the sides of the tongue, not over the top — that's what makes it 'l' and not 'd' or 'n'.", steps: ["Touch just the tongue tip to the ridge behind the top teeth", "Keep the sides of the tongue down and relaxed so air can flow around them", "Hum with the voice on", "Hold the sound — it can be stretched, unlike a stop"] },
  M: { ipa: "/m/", spoken: "mmm", svgKey: "bilabial_nasal", anatomy: "Both lips closed · Voice on · Air flows out through the nose", tip: "Same lip position as B and P, but the sound flows through the nose instead of being released through the mouth.", steps: ["Close both lips gently", "Hum with the voice on, letting the sound flow through the nose", "Hold the sound — it doesn't need a release like B does", "Keep the jaw relaxed"] },
  N: { ipa: "/n/", spoken: "nnn", svgKey: "alveolar_nasal", anatomy: "Tongue tip on the ridge behind the top teeth · Voice on · Air flows out through the nose", tip: "Same tongue spot as T and D, but the sound flows through the nose instead of releasing through the mouth.", steps: ["Touch the tongue tip to the ridge behind the top teeth", "Hum with the voice on, letting the sound flow through the nose", "Hold the sound — it doesn't need a release", "Keep the sides of the tongue up against the back teeth"] },
  O: { ipa: "/ɒ/", spoken: "o", svgKey: "back_low", anatomy: "Jaw open · Tongue low and back · Lips slightly rounded", steps: ["Open the jaw", "Keep the tongue low, toward the back of the mouth", "Round the lips just slightly", "Say a short, clipped 'o' as in 'hot' — don't glide into 'oh'"] },
  P: { ipa: "/p/", spoken: "puh", svgKey: "bilabial_stop", anatomy: "Both lips pressed together · No voice · Quick release", tip: "Same lip position as B, but no hum — just a puff of air on release.", steps: ["Press both lips gently together", "Build a little air pressure behind the closed lips", "Release with a light puff and a quiet 'uh'", "No hum — this sound is voiceless"] },
  Q: { ipa: "/kw/", spoken: "kwuh", svgKey: "velar_stop", anatomy: "Back of tongue against the soft palate, then lips round quickly for the follow-through 'w' · No voice on release", tip: "Two quick motions back to back: release /k/ at the back, then round the lips right away for the 'w' that always follows Q.", steps: ["Lift the back of the tongue to touch the soft palate for /k/", "Release with a puff of air", "Immediately round the lips into a small circle for the 'w' glide", "Keep the two parts close together, almost one motion"] },
  R: { ipa: "/r/", spoken: "rrr", svgKey: "retroflex", anatomy: "Jaw open, tongue tip curls slightly back and up · Voice on", tip: "The light retroflex 'r' common in Indian English — the tongue tip curls back without touching the roof of the mouth.", steps: ["Open the mouth slightly", "Curl the tongue tip up and back, without pressing it against the roof of the mouth", "Hum with the voice on", "Hold the sound — it can be stretched out"] },
  S: { ipa: "/s/", spoken: "sss", svgKey: "alveolar_fric", anatomy: "Teeth close together, tongue near the ridge behind the top teeth · No voice · Steady airflow", tip: "Smile with teeth close together and blow a thin, steady stream of air — you should be able to feel it on your palm.", steps: ["Bring the teeth close together, in a slight smile", "Bring the tongue tip close to (not touching) the ridge behind the top teeth", "Blow a thin, steady stream of air through the narrow gap", "No hum — this sound is voiceless, and it can be held/stretched"] },
  T: { ipa: "/t/", spoken: "tuh", svgKey: "alveolar_stop", anatomy: "Tongue tip against the ridge behind the top teeth · No voice · Quick release", tip: "Same tongue spot as D, but no hum — just a light puff on release.", steps: ["Touch the tongue tip to the ridge behind the top front teeth", "Build a little air pressure behind the tongue", "Release with a light puff and a quiet 'uh'", "No hum — this sound is voiceless"] },
  U: { ipa: "/ʌ/", spoken: "uh", svgKey: "mid_mid", anatomy: "Tongue mid-height and central · Jaw relaxed and slightly open · Lips neutral", steps: ["Relax the jaw into a slightly open, neutral position", "Keep the tongue central, not pushed forward or back", "Say a short, clipped 'uh' as in 'cup'", "Keep it brief — this sound is never held long"] },
  V: { ipa: "/v/", spoken: "vvv", svgKey: "labiodental", anatomy: "Top teeth resting on the bottom lip · Voice on · Steady airflow", tip: "Same placement as F, but hum instead of just blowing — feel the buzz on the bottom lip.", steps: ["Rest the top teeth gently on the bottom lip", "Hum while air passes through the gap", "Hold the sound — it can be stretched out", "Feel the buzz on the lip with a fingertip if it helps"] },
  W: { ipa: "/w/", spoken: "wuh", svgKey: "back_high", anatomy: "Lips rounded into a small circle, tongue high and back · Voice on", tip: "Round the lips tightly like blowing out a candle, then relax into the vowel that follows.", steps: ["Round the lips into a small, tight circle", "Raise the back of the tongue toward the soft palate", "Hum with the voice on as the lips relax outward", "Keep it a quick glide, not a held sound"] },
  X: { ipa: "/ks/", spoken: "ks", svgKey: "alveolar_fric", anatomy: "Two sounds back to back: back of tongue lifts for /k/, then teeth close and tongue moves near the ridge for /s/ · No voice", tip: "X is a genuine two-sound blend, not a single phoneme — say the /k/ release immediately followed by the /s/ hiss.", steps: ["Lift the back of the tongue for a quick, quiet /k/", "Immediately bring the teeth close together and the tongue near the ridge", "Finish with a brief /s/ hiss", "Keep both parts short — this isn't a sound to hold, unlike standalone /s/"] },
  Y: { ipa: "/j/", spoken: "yuh", svgKey: "palatal", anatomy: "Tongue high and forward, close to the roof of the mouth · Lips loosely spread · Voice on", tip: "Start in a wide smile with the tongue high and forward, like starting to say 'ee', then relax into the next sound.", steps: ["Raise the front of the tongue high, close to the roof of the mouth", "Spread the lips loosely, as if starting a smile", "Hum with the voice on as the tongue relaxes down", "Keep it a quick glide, not held"] },
  Z: { ipa: "/z/", spoken: "zzz", svgKey: "alveolar_fric", anatomy: "Teeth close together, tongue near the ridge behind the top teeth · Voice on · Steady airflow", tip: "Same tongue position as S, but hum through it instead of just blowing — like a buzzing bee.", steps: ["Bring the teeth close together, in a slight smile", "Bring the tongue tip close to the ridge behind the top teeth", "Hum while air passes through the narrow gap", "Hold the sound — it can be stretched, and you should feel a buzz"] },
};

// Maps each PHONIC_SOUNDS svgKey (a place/manner articulation label) to one
// of the 8 real mouth-shape reference photos already shot for VaakMirror
// (src/vaakmirror/assets/mouth-shapes) plus that same manner->animation
// vocabulary MouthShapeGuide uses, so the alphabet screen shows the same
// real images kids already see in VaakMirror instead of the abstract
// sagittal-view line art in MouthDiagram.jsx. There are 18 distinct
// svgKeys across the alphabet and only 8 photographed shapes, so several
// keys share the closest-matching image (e.g. every alveolar tongue-tip
// sound -- D/T/N/L/R -- maps to the one tongue-tip-up photo); manner is
// omitted (no animation) for vowels, since MouthShapeGuide's motion set
// is built for consonant manners and a vowel is meant to be held steady
// rather than popped/shimmered.
export const SVGKEY_TO_MOUTH_SHAPE = {
  // Vowels -- steady hold, no manner/animation
  front_open: { shape: "open-wide" },       // A /æ/
  front_mid: { shape: "neutral-open" },     // E /ɛ/
  front_high: { shape: "wide-narrow" },     // I /ɪ/
  back_low: { shape: "round-forward" },     // O /ɒ/
  back_high: { shape: "round-forward" },    // W /w/ (rounded glide)
  mid_mid: { shape: "neutral-open" },       // U /ʌ/
  retroflex: { shape: "tongue-tip-up", manner: "Approximant" }, // R /r/
  // Consonants
  bilabial_stop: { shape: "lips-closed", manner: "Plosive" },       // B, P
  bilabial_nasal: { shape: "lips-closed", manner: "Nasal" },        // M
  labiodental: { shape: "lip-teeth", manner: "Fricative" },         // F, V
  alveolar_stop: { shape: "tongue-tip-up", manner: "Plosive" },     // D, T
  alveolar_nasal: { shape: "tongue-tip-up", manner: "Nasal" },      // N
  alveolar_lateral: { shape: "tongue-tip-up", manner: "Lateral Approximant" }, // L
  alveolar_fric: { shape: "wide-narrow", manner: "Fricative" },     // S, X, Z
  velar_stop: { shape: "neutral-open", manner: "Plosive" },         // C, G, K, Q
  postalveolar: { shape: "round-forward", manner: "Affricate" },    // J
  palatal: { shape: "wide-narrow", manner: "Approximant" },         // Y
  glottal: { shape: "neutral-open", manner: "Fricative" },          // H
};

export const KEYBOARD_ROWS = [
  ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
  ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
  ["Z", "X", "C", "V", "B", "N", "M"],
];