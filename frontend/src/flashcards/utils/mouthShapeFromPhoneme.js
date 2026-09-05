import { SOUNDS } from '../../vaakmirror/data/soundTaxonomy'

// Flashcards' phoneme chips use ARPABET codes (from CMUdict, via
// grapheme_to_phoneme.py -- e.g. "F", "AO1", "SH"), but vaakmirror's
// soundTaxonomy (the source of the real illustrated mouth-shape photos
// used by every vaakmirror game and now Assessment's alphabet screen too)
// is keyed by plain phonics letters/blends ("f", "sh"). This bridges the two
// so Flashcards can show the same real photos instead of the backend's
// abstract line-art SVG.
//
// Deliberately CONSONANTS ONLY. Vowels have no entry here on purpose: the
// 8 existing shape images were illustrated for consonant articulation
// (lip/teeth/tongue placement), and forcing a vowel onto the closest-looking
// one risks showing a child an inaccurate mouth position for a sound this
// app is actively trying to teach them to produce correctly. Better to fall
// back to the existing (already-correct, just plainer) backend SVG for
// vowels than to guess.
const ARPABET_TO_TAXONOMY_ID = {
  P: 'p', B: 'b', M: 'm',
  F: 'f', V: 'v',
  S: 's', Z: 'z',
  T: 't', D: 'd', N: 'n', L: 'l', R: 'r',
  SH: 'sh', ZH: 'sh', CH: 'ch', JH: 'j',
  K: 'k', G: 'g',
  NG: 'g',   // no dedicated velar-nasal image yet; k/g's back-of-mouth closure is the closest visual proxy
  TH: 'f',   // interdental th has no image of its own yet; lip-teeth is the closest available approximation, not a perfect substitute
  DH: 'v',
}

const byId = Object.fromEntries(SOUNDS.map(s => [s.id, s]))

// Returns { shape, manner } for a real mouth-shape illustration, or null if
// this phoneme isn't covered (vowels, glides, HH) -- callers should fall
// back to their existing rendering in that case.
export function mouthShapeForArpabet(phoneme) {
  const base = (phoneme || '').replace(/[0-9]/g, '').toUpperCase()
  const taxonomyId = ARPABET_TO_TAXONOMY_ID[base]
  const entry = taxonomyId && byId[taxonomyId]
  if (!entry) return null
  return { shape: entry.shape, manner: entry.manner }
}
