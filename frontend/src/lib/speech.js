// Shared browser text-to-speech utility for verbal instructions across the
// app — BreathQuest levels, Chime games, VaakMirror, and (as a manual
// tap-to-hear only, no auto-play) the login/nav flow. Generalizes the
// pattern VaakMirror's speakSound() already established in
// vaakmirror/lib/sound.js: cancel any in-flight utterance, speak the new
// one, fail silently if speech synthesis isn't available (some browsers
// block audio until a user gesture has happened somewhere on the page —
// the visual UI always carries the instruction on its own regardless).
//
// vaakmirror/lib/sound.js now re-exports `speak` as `speakSound` so its
// four existing call sites (MirrorMirror, LipSyncHero, TongueTamer,
// MinimalPairDrill) keep working unchanged.
//
// Voice: there's no server-side TTS provider wired into this app (no API
// key, no backend audio pipeline) — this is entirely the browser's
// built-in Web Speech API (`window.speechSynthesis`), which is free and
// needs no setup, but means the actual voice is whatever the device
// exposes, not something this code can force. `pickPreferredVoice()`
// below asks for an Indian-English voice (`en-IN`) when the device has
// one and otherwise falls back to the browser's default silently.
// Real-world availability: Chrome on Android/desktop commonly lists a
// network "Google" en-IN voice when online; iOS/macOS Safari ships a
// built-in en-IN voice ("Rishi") that works offline too. Devices with
// neither (e.g. some Windows/Chrome setups, or Chrome fully offline) will
// just get their normal default system voice — there's no way to
// guarantee an en-IN voice exists on every device short of adding a real
// paid cloud TTS backend, which isn't set up here.

import { useEffect, useRef } from 'react'

// Isolated single-letter sounds (e.g. "r", "s") read as the *letter name*
// through Web Speech API ("are" instead of the rolled /r/ sound) — there's
// no way to force phonetic pronunciation of a bare letter via plain text,
// so callers that legitimately speak single phonemes (VaakMirror's
// isolated-sound games) need a respelling before it reaches the utterance.
const SINGLE_LETTER_RESPELL = {
  r: 'rrr', s: 'sss', f: 'fff', m: 'mmm', n: 'nnn',
  l: 'lll', z: 'zzz', v: 'vvv', sh: 'shhh', th: 'thhh',
}

function respellIfBareLetter(text) {
  const trimmed = text?.trim().toLowerCase()
  if (trimmed && SINGLE_LETTER_RESPELL[trimmed]) return SINGLE_LETTER_RESPELL[trimmed]
  return text
}

// Chime's spoken instructions say a target sound as a plain respelling —
// "Say a big, loud aaaa to blast your rocket into space!" — matching the
// lowercase convention already used in every game's on-screen instructions
// and calibration labels. Read verbatim through Web Speech API, a repeated
// vowel cluster with no real dictionary match tends to get read as the
// letter's own *name* rather than sounded out phonetically, and capitals
// make this worse (a stronger trigger for that letter-name fallback).
// "aaaa" is the confirmed bad case: it comes out "ay, ay, ay, ay" instead
// of the open /ah/ sound the games are asking for, since the letter A's
// name doesn't match the target vowel at all (unlike, say, E or O, whose
// letter names already sound close to the target vowel).
//
// This used to be worked around inside RocketLaunch.jsx alone (hand-typed
// "ahhh" in its spoken line, kept as "aaaa" in the matching on-screen
// text) -- moved here so every Chime game's instruction gets the fix
// automatically from its normal lowercase phonetic text, without each one
// needing to know about or duplicate the workaround.
const PHONETIC_WORD_RESPELL = { aaaa: 'ahhh' }

function respellPhoneticWords(text) {
  if (!text) return text
  return text.replace(/\b[a-zA-Z]{2,}\b/g, (word) => {
    const lower = word.toLowerCase()
    if (PHONETIC_WORD_RESPELL[lower]) return PHONETIC_WORD_RESPELL[lower]
    // An all-caps, non-dictionary vowel-only cluster (OOOO, EEEE, ...) risks
    // the same letter-name misreading, worse than lowercase would -- at
    // minimum normalize its case so it reads the same as every other
    // game's already-fine lowercase instruction text.
    if (word === word.toUpperCase() && /^[aeiou]{3,}$/.test(lower)) return lower
    return word
  })
}

let cachedVoices = null
if (typeof window !== 'undefined' && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoices = window.speechSynthesis.getVoices()
  }
}

function pickPreferredVoice() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return null
  const voices = cachedVoices?.length ? cachedVoices : window.speechSynthesis.getVoices()
  if (!voices || voices.length === 0) return null
  cachedVoices = voices
  return (
    voices.find(v => v.lang === 'en-IN') ||
    voices.find(v => v.lang?.toLowerCase().startsWith('en-in')) ||
    voices.find(v => /india/i.test(v.name)) ||
    null
  )
}

let pendingSpeakTimer = null

// onEnd (optional) fires exactly once when this utterance finishes --
// on the real 'end' event, on an 'error' (e.g. no matching voice), or
// immediately if speech synthesis isn't available/there's no text at all.
// Added so callers can gate a real state transition (not just a "hear it
// again" button) on the instruction actually finishing, instead of a
// guessed setTimeout duration racing against however long the sentence
// actually takes a given device's voice to read -- see GamePage.jsx's
// breathe-in cue, the bug this was written for.
export function speak(text, { rate = 0.95, pitch = 1.0, onEnd } = {}) {
  try {
    if (!text || !window.speechSynthesis) { onEnd?.(); return }
    if (pendingSpeakTimer) clearTimeout(pendingSpeakTimer)
    window.speechSynthesis.cancel()
    // Chrome and Firefox both have a long-standing bug where calling
    // speak() in the same tick right after cancel() silently drops the
    // new utterance -- no error, no onstart, it just never speaks. Games
    // like Lip Sync Hero that re-trigger speech every note (sometimes
    // while the previous utterance is still finishing) hit this
    // cancel-then-speak collision often. The documented workaround is a
    // short delay so cancel() actually clears the queue before the next
    // speak() call lands.
    pendingSpeakTimer = setTimeout(() => {
      pendingSpeakTimer = null
      const utter = new SpeechSynthesisUtterance(respellPhoneticWords(respellIfBareLetter(text)))
      utter.rate = rate
      utter.pitch = pitch
      // Hint the language even when no exact-match voice object is found —
      // some browsers will still route to a same-language voice by lang code.
      utter.lang = 'en-IN'
      const voice = pickPreferredVoice()
      if (voice) utter.voice = voice
      if (onEnd) {
        let fired = false
        const fireOnce = () => { if (!fired) { fired = true; onEnd() } }
        utter.onend = fireOnce
        utter.onerror = fireOnce
      }
      window.speechSynthesis.speak(utter)
    }, 80)
  } catch {
    // Ignore — voice is a layer on top of the visual UI, never load-bearing.
    onEnd?.()
  }
}

export function stopSpeaking() {
  try {
    if (pendingSpeakTimer) {
      clearTimeout(pendingSpeakTimer)
      pendingSpeakTimer = null
    }
    if (window.speechSynthesis) window.speechSynthesis.cancel()
  } catch {
    // Ignore.
  }
}

// Speaks `text` once automatically each time it becomes relevant — either
// because `enabled` flips from false to true (entering/re-entering this
// screen or phase), or because `text` itself changes while already
// enabled (e.g. moving to a new level whose instruction text differs) —
// and returns a `replay` function to wire to a "hear it again" button.
//
// This is the "auto once + replay" pattern, but "once" means once per
// entry, not once ever: re-entering the same mode/phase a second time
// (e.g. tapping back into "register" after leaving it, or every attempt's
// breathe-in cue) re-speaks, since it tracks the *edge* of becoming
// enabled rather than deduping purely on text equality. A pure
// text-equality dedupe would silently go quiet on the second visit to any
// screen whose instruction text doesn't change between visits — a real
// bug caught while wiring this into GamePage.jsx's breathe-in cue, which
// recurs identically every attempt.
//
// Safe under React StrictMode's dev-only double-invoke: the second
// invocation sees the same (text, enabled) as the first and doesn't
// re-fire, since prevRef is only updated once per actual effect run.
export function useSpokenInstruction(text, { enabled = true, rate, pitch, onEnd } = {}) {
  const prevRef = useRef({ text: null, enabled: false })

  useEffect(() => {
    const prev = prevRef.current
    const enabledRisingEdge = enabled && !prev.enabled
    const textChangedWhileEnabled = enabled && prev.enabled && text !== prev.text
    if (enabled && text && (enabledRisingEdge || textChangedWhileEnabled)) {
      speak(text, { rate, pitch, onEnd })
    }
    prevRef.current = { text, enabled }
  }, [text, enabled, rate, pitch, onEnd])

  return () => { if (text) speak(text, { rate, pitch, onEnd }) }
}
