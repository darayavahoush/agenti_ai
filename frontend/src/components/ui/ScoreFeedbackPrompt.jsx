import { useEffect, useRef, useState } from 'react'

// The "Did we score that right?" prompt every game shows after an attempt.
//
// It used to be a bare pill -- one question and two or three emoji -- that
// vanished after 4-6 seconds, so a parent or therapist glancing back from
// the child never had time to read it, and nothing said who was meant to
// answer, what the emoji meant, or what the answer was for. This one:
//   * says WHO answers (a grown-up watching, not the child mid-game),
//   * labels every button in words (the old 😖/😅 were only explained in
//     screen-reader text),
//   * says HOW to judge and WHY it matters,
//   * stays for 20s, pauses while it's being touched/hovered/focused, and
//     can be dismissed,
//   * confirms with a short "Saved" instead of just disappearing.
//
// The "why" is deliberately modest: answers are stored with the attempt so
// scoring mistakes can be found and fixed; nothing here claims the game
// learns from a tap in real time.

export const FEEDBACK_VISIBLE_MS = 20000
const MIN_AFTER_INTERACTION_MS = 8000
const THANKS_MS = 1600
const TICK_MS = 100

const THUMBS = [
  { value: 'up', emoji: '👍', label: 'Right', aria: 'Yes, that was scored correctly' },
  { value: 'down', emoji: '👎', label: 'Wrong', aria: 'No, that was scored wrong' },
]

const STRICTNESS = [
  { value: 'up', emoji: '👍', label: 'Right', aria: 'Yes, that was scored correctly' },
  { value: 'too_strict', emoji: '😖', label: 'Too strict', aria: 'No, too strict -- a good attempt should have scored higher' },
  { value: 'too_generous', emoji: '😅', label: 'Too generous', aria: 'No, too generous -- a weak attempt scored too well' },
]

const HOW = {
  thumbs: 'Tap Right if the result matched what you saw and heard, or Wrong if it did not.',
  strictness:
    'Tap Right if the result matched what you saw and heard. Tap Too strict if a good try scored too low, or Too generous if a weak try scored too high.',
}
const WHO = 'A parent or therapist watching can answer'
const WHY = 'It is saved with this attempt so scoring mistakes can be found and fixed.'

export default function ScoreFeedbackPrompt({
  onChoose,
  onExpire,
  submitted = false,
  what = 'that',
  variant = 'thumbs',
  durationMs = FEEDBACK_VISIBLE_MS,
}) {
  const options = variant === 'strictness' ? STRICTNESS : THUMBS
  const [remaining, setRemaining] = useState(durationMs)
  const remainingRef = useRef(durationMs)
  const pausedRef = useRef(false)
  // onExpire is a fresh closure every parent render; read it through a ref so
  // the interval below never calls a stale one.
  const onExpireRef = useRef(onExpire)
  useEffect(() => { onExpireRef.current = onExpire })

  useEffect(() => {
    const id = setInterval(() => {
      if (pausedRef.current) return
      remainingRef.current -= TICK_MS
      setRemaining(Math.max(0, remainingRef.current))
      if (remainingRef.current <= 0) {
        clearInterval(id)
        onExpireRef.current?.()
      }
    }, TICK_MS)
    return () => clearInterval(id)
  }, [])

  // Once an answer is in, show "Saved" briefly and then let go.
  useEffect(() => {
    if (submitted) {
      pausedRef.current = false
      remainingRef.current = Math.min(remainingRef.current, THANKS_MS)
    }
  }, [submitted])

  const pause = () => { pausedRef.current = true }
  const resume = () => { pausedRef.current = false }
  const touched = () => {
    // Anyone who is reading or reaching for a button gets at least a few
    // more seconds, even if the bar was nearly empty.
    remainingRef.current = Math.max(remainingRef.current, MIN_AFTER_INTERACTION_MS)
    setRemaining(remainingRef.current)
  }

  const pct = Math.max(0, Math.min(100, (remaining / durationMs) * 100))

  return (
    <div
      role="group"
      aria-label="Scoring feedback"
      onPointerEnter={pause}
      onPointerLeave={resume}
      onFocus={pause}
      onBlur={resume}
      onPointerDown={touched}
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-20 w-[min(92vw,26rem)] rounded-2xl border border-white/10
                 bg-[rgba(20,14,36,0.92)] px-4 py-3 text-left text-white shadow-xl backdrop-blur-md"
      style={{ fontFamily: 'inherit' }}
    >
      {submitted ? (
        <p className="py-1 text-sm font-bold" role="status">✅ Saved — thank you!</p>
      ) : (
        <>
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-white/60">Grown-up check</p>
              <p className="text-sm font-bold leading-tight">Did we score {what} right?</p>
            </div>
            <button
              type="button"
              onClick={() => onExpireRef.current?.()}
              aria-label="Dismiss feedback question"
              className="-mr-1 -mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white/70 hover:bg-white/10 hover:text-white"
            >
              ✕
            </button>
          </div>

          <div className="mt-2 flex flex-wrap gap-2">
            {options.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => onChoose(o.value)}
                aria-label={o.aria}
                className="flex min-h-[44px] items-center gap-1.5 rounded-full border border-white/15 bg-white/10 px-3.5 text-sm font-bold
                           transition-transform hover:scale-105 hover:bg-white/20 active:scale-95"
              >
                <span aria-hidden="true" className="text-lg leading-none">{o.emoji}</span>
                {o.label}
              </button>
            ))}
          </div>

          <p className="mt-2 text-xs leading-snug text-white/75">
            <span className="font-bold text-white/90">Who:</span> {WHO}.{' '}
            <span className="font-bold text-white/90">How:</span> {HOW[variant] || HOW.thumbs}{' '}
            <span className="font-bold text-white/90">Why:</span> {WHY}
          </p>

          <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10" aria-hidden="true">
            <div className="h-full rounded-full bg-white/50" style={{ width: `${pct}%` }} />
          </div>
        </>
      )}
    </div>
  )
}
