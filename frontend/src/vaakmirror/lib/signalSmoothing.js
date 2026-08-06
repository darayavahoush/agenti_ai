// Exponential moving average over specific numeric keys of an object. Used
// to smooth noisy per-frame landmark metrics (openness/spread) so scoring
// doesn't flicker frame to frame with tiny tracking jitter.
export function emaUpdateObject(prev, next, keys, alpha = 0.3) {
  if (!next) return prev
  if (!prev) return { ...next }

  const result = { ...prev }
  for (const key of keys) {
    const nextVal = next[key]
    if (typeof nextVal !== "number") continue
    const prevVal = typeof prev[key] === "number" ? prev[key] : nextVal
    result[key] = prevVal + alpha * (nextVal - prevVal)
  }
  return result
}

// Debounces the raw per-frame tier (red/yellow/green) so a single flickery
// frame can't toggle the UI or trigger a catch. A tier only becomes the
// "stable" tier once it has been the raw result for `holdFrames`
// consecutive frames in a row.
export function createTierStabilizer(holdFrames = 4) {
  let stableTier = "red"
  let candidate = "red"
  let candidateCount = 0

  return {
    update(rawTier) {
      if (rawTier === candidate) {
        candidateCount += 1
      } else {
        candidate = rawTier
        candidateCount = 1
      }
      if (candidateCount >= holdFrames) {
        stableTier = candidate
      }
      return stableTier
    },
    reset() {
      stableTier = "red"
      candidate = "red"
      candidateCount = 0
    },
  }
}


// Scalar variant of the same exponential moving average, for smoothing a
// single number (e.g. mouth openness on its own) rather than several keys
// of an object at once.
export function emaUpdate(prev, next, alpha = 0.3) {
  if (next == null) return prev
  if (prev == null) return next
  return prev + alpha * (next - prev)
}
