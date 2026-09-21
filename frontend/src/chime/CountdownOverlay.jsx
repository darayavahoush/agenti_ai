import { useEffect, useState } from 'react'

// Shared "ready, set, go" beat for every Chime game. Calibration finishes
// and then, previously, scoring/recording started on literally the very
// next frame — no visual or spoken cue that the mic was about to start
// listening for real. This sits between finishCalibration() and the game
// actually starting: a few numbers, then "Go!", then onDone() fires and the
// caller does whatever finishCalibration() used to do immediately.
const STEPS = ['3', '2', '1', 'Go!']
const STEP_MS = 700

export default function CountdownOverlay({ onDone }) {
  const [i, setI] = useState(0)

  useEffect(() => {
    if (i >= STEPS.length) {
      onDone()
      return
    }
    const t = setTimeout(() => setI(v => v + 1), STEP_MS)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i])

  if (i >= STEPS.length) return null

  const label = STEPS[i]
  const isGo = label === 'Go!'

  return (
    <div className="fixed inset-0 flex items-center justify-center z-20 pointer-events-none">
      <div
        key={i}
        className={`font-extrabold text-white drop-shadow-[0_4px_18px_rgba(0,0,0,0.45)] animate-countdown-pop ${isGo ? 'text-7xl' : 'text-8xl'}`}
      >
        {label}
      </div>
      <div className="sr-only" aria-live="assertive">{label}</div>
    </div>
  )
}
