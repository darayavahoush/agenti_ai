// Minimal-pair contrasts for Minimal Pair Drill.
//
// IMPORTANT SCOPE NOTE: Mirror Mirror's scoring is entirely mouth-shape
// based (openness + spread from mouthMetrics.js) — it has no microphone/
// voicing signal. That means any pair that differs ONLY in voicing
// (p/b, t/d, k/g, f/v, s/z, th-unvoiced/th-voiced, ch/j, w/wh) or ONLY in
// a manner distinction that doesn't move the mouth differently (l/n — both
// tongue-tip-up) is NOT included here: the camera would score both sides
// of the pair identically, so a "drill" on it would silently always pass
// and teach nothing. This list is deliberately restricted to pairs whose
// two sounds map to different `shape` targets in soundTaxonomy.js, which
// is the actual population of contrasts this camera-based game can honestly
// referee. Voicing-pair drills belong in an ASR-scored game (Village
// Builder) instead, not here.
//
// `common` marks the handful of contrasts that show up most often in real
// caseloads (place-of-articulation errors like fronting/backing, and the
// classic s/sh, l/w, l/r substitution patterns) — used to rank the default
// suggestion when a kid has no attempt history yet to derive weak sounds from.
export const MINIMAL_PAIRS = [
  { a: 's', b: 'sh', label: 's / sh', note: 'Sibilant place contrast — a common lisp/distortion pair.', common: true },
  { a: 't', b: 'k', label: 't / k', note: 'Alveolar vs velar — classic fronting/backing pattern.', common: true },
  { a: 'd', b: 'g', label: 'd / g', note: 'Alveolar vs velar — the voiced counterpart of t/k, same fronting/backing pattern. Not excluded like the voicing-only pairs below: d and g map to different mouth-shape targets (tongue-tip-up vs open-wide), same as t/k.', common: true },
  { a: 'l', b: 'w', label: 'l / w', note: 'Liquid vs glide — common gliding substitution.', common: true },
  { a: 'l', b: 'r', label: 'l / r', note: 'The two liquids — frequently confused with each other.', common: true },
  { a: 'p', b: 't', label: 'p / t', note: 'Bilabial vs alveolar plosive — a fronting/backing pattern at the front of the mouth, same family as t/k but less frequently the target sound clinically.', common: false },
  { a: 'p', b: 'k', label: 'p / k', note: 'Bilabial vs velar plosive — the widest place contrast among the stops, useful as an easier starting drill before narrower contrasts like t/k.', common: false },
  { a: 's', b: 'th-unvoiced', label: 's / th', note: 'Alveolar fricative vs interdental — frontal lisp pair.', common: true },
  { a: 't', b: 'th-unvoiced', label: 't / th', note: 'Stop vs interdental fricative.', common: false },
  { a: 'f', b: 'th-unvoiced', label: 'f / th', note: 'Labiodental vs interdental fricative.', common: false },
  { a: 's', b: 'f', label: 's / f', note: 'Alveolar vs labiodental fricative place contrast.', common: false },
  { a: 'ch', b: 't', label: 'ch / t', note: 'Affricate vs plosive — de-affrication pattern.', common: false },
  { a: 'j', b: 'd', label: 'j / d', note: 'Affricate vs alveolar plosive — the voiced counterpart of ch/t, same de-affrication pattern (e.g. "jump" heard as "dump"). Maps to different shapes (round-forward vs tongue-tip-up), so it is honestly scoreable.', common: true },
  { a: 'th-voiced', b: 'd', label: 'th / d (voiced)', note: 'Interdental fricative vs alveolar plosive — "stopping," one of the most frequent substitution patterns in English speech development (this/that heard as dis/dat). Maps to different shapes (tongue-between-teeth vs tongue-tip-up).', common: true },
  { a: 'r', b: 'w', label: 'r / w', note: 'Rhotic vs glide — common gliding substitution.', common: true },
  // Note: p/b, t/d, k/g-as-stops-alone, f/v, s/z, th-unvoiced/th-voiced,
  // ch/j, w/wh are deliberately NOT here as same-place voicing-only pairs
  // — the camera cannot tell voicing apart. d/g, j/d, and th-voiced/d ARE
  // included above despite one side being a "voiced" sound: each of those
  // three contrasts differs by PLACE or MANNER (not voicing alone), so the
  // two sides land on genuinely different shape targets in
  // soundTaxonomy.js and the camera can honestly referee them. See file
  // header for the general scope rule.
]

// sound_id -> the SOUNDS entry it should be looked up against is done by the
// caller (soundTaxonomy.js), this file only defines which ids pair up.

export function findPairForSound(soundId) {
  return MINIMAL_PAIRS.find((p) => p.a === soundId || p.b === soundId) || null
}

export function defaultPair() {
  return MINIMAL_PAIRS.find((p) => p.common) || MINIMAL_PAIRS[0]
}
