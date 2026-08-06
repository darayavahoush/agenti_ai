// Lightweight sound effects (Web Audio oscillators — no audio files to
// ship or fail to load) plus browser TTS for reading out each target sound.

let audioCtx = null
function getCtx() {
  if (!audioCtx) {
    const Ctx = window.AudioContext || window.webkitAudioContext
    audioCtx = new Ctx()
  }
  // Browsers suspend the context until a user gesture; games only ever
  // call these from within a user-driven flow (camera already granted),
  // so resuming here is safe and keeps call sites simple.
  if (audioCtx.state === "suspended") audioCtx.resume()
  return audioCtx
}

function tone(freq, { duration = 0.15, type = "sine", gain = 0.2, delay = 0 } = {}) {
  const ctx = getCtx()
  const osc = ctx.createOscillator()
  const g = ctx.createGain()
  osc.type = type
  osc.frequency.value = freq
  const start = ctx.currentTime + delay
  g.gain.setValueAtTime(0, start)
  g.gain.linearRampToValueAtTime(gain, start + 0.01)
  g.gain.exponentialRampToValueAtTime(0.0001, start + duration)
  osc.connect(g)
  g.connect(ctx.destination)
  osc.start(start)
  osc.stop(start + duration + 0.02)
}

// Short bright ping — a single note caught.
export function playChime() {
  tone(880, { duration: 0.12, type: "sine", gain: 0.22 })
  tone(1318.5, { duration: 0.18, type: "sine", gain: 0.16, delay: 0.05 })
}

// Ascending three-note flourish — full round completed.
export function playFanfare() {
  tone(523.25, { duration: 0.14, type: "triangle", gain: 0.2 })
  tone(659.25, { duration: 0.14, type: "triangle", gain: 0.2, delay: 0.12 })
  tone(783.99, { duration: 0.28, type: "triangle", gain: 0.22, delay: 0.24 })
}

// Soft low blip — deliberately gentle, not punishing, matching the "no
// pressure if you miss one" copy already in LipSyncHero's UI.
export function playMiss() {
  tone(220, { duration: 0.18, type: "sine", gain: 0.12 })
}

// Reads a target sound aloud via the browser's built-in TTS. LipSyncHero
// already documents the caveat (letter names, not isolated phonemes) in
// its own UI copy, so this stays a plain, undecorated speak call.
export function speakSound(label) {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(label)
  utter.rate = 0.85
  utter.pitch = 1.05
  window.speechSynthesis.speak(utter)
}
