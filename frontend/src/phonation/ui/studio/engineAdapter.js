// The ONLY file that talks to PhonationEngine. If a method name differs in your copy,
// fix it here and nothing else in the UI changes.
//   start()                      -> capture settings object (echoCancellation, ...)
//   calibrate(ms)                -> { warnings: string[] }
//   live                         -> getter with voiced / intensityNorm / pitch
//   beginTrial(level, opts)      -> void
//   endTrial() | endTrialAndRecognize(recognizer) -> trial result
//   stop()                       -> releases the microphone
const first = (obj, names) => names.map((n) => obj[n]).find((f) => typeof f === 'function')

export function adapt(engine) {
  const end = first(engine, ['endTrial', 'finishTrial', 'stopTrial'])
  return {
    start: () => engine.start(),
    calibrate: (ms) => engine.calibrate(ms),
    begin: (level, opts) => engine.beginTrial(level, opts),
    end: (recognizer) =>
      recognizer ? engine.endTrialAndRecognize(recognizer) : Promise.resolve(end.call(engine)),
    stop: () => engine.stop(),
    // Normalised read of the live state; call from requestAnimationFrame, never setState.
    read() {
      const l = engine.live || {}
      return {
        voiced: !!l.voiced,
        level: Math.max(0, Math.min(1, l.intensityNorm ?? l.intensity ?? 0)),
        pitch: l.pitchHz ?? l.f0 ?? l.pitch ?? null,
      }
    },
  }
}

// ---- level helpers (defensive: starter levels are placeholders a therapist edits) ----
export const TYPE_LABEL = {
  sustained_voicing: 'Hold a sound',
  cv_syllable: 'Pop a syllable',
  syllable_train: 'Say it again and again',
  pitch_glide: 'Slide your voice',
  loudness_ramp: 'Soft to loud',
}
export const levelList = (src) => (Array.isArray(src) ? src : Object.values(src || {}))
export const levelTitle = (l) => l.title ?? l.name ?? (l.target ? `“${l.target}”` : TYPE_LABEL[l.type] ?? l.id)
export const levelPrompt = (l) => {
  if (l.prompt || l.hint) return l.prompt || l.hint
  const t = l.target ? `“${l.target}”` : 'your voice'
  return {
    sustained_voicing: `Say ${t} and keep it going.`,
    cv_syllable: `Say ${t}, then rest. Do it ${l.reps ?? 'a few'} times.`,
    syllable_train: `Say ${t} again and again, steady and even.`,
    pitch_glide: 'Slide your voice up, or down, like a slide at the park.',
    loudness_ramp: 'Start quiet. Get louder, slowly.',
  }[l.type] ?? 'Use your voice.'
}
export const levelGoalMs = (l) => l.targetMs ?? l.minDurationMs ?? l.durationMs ?? (l.seconds ? l.seconds * 1000 : l.targetSeconds ? l.targetSeconds * 1000 : null)
export const silenceEndMs = (l) => (l.type === 'cv_syllable' ? 3000 : 1600)
