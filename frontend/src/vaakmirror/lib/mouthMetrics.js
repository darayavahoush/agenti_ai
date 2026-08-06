// Mouth-shape scoring against MediaPipe FaceLandmarker's 468-point face
// mesh. All distances are normalized against interocular distance (the
// gap between the outer eye corners) rather than raw pixels, so scoring
// works the same regardless of how close someone sits to the camera.

const MOUTH_CORNER_LEFT = 61
const MOUTH_CORNER_RIGHT = 291
const UPPER_LIP_INNER = 13
const LOWER_LIP_INNER = 14
const EYE_OUTER_LEFT = 33
const EYE_OUTER_RIGHT = 263

function dist(a, b) {
  const dx = a.x - b.x
  const dy = a.y - b.y
  return Math.sqrt(dx * dx + dy * dy)
}

// Returns { openness, spread } normalized to interocular distance, or null
// if landmarks aren't available / don't include the indices we need.
export function computeMouthMetrics(landmarks) {
  if (!landmarks || landmarks.length <= MOUTH_CORNER_RIGHT) return null

  const left = landmarks[MOUTH_CORNER_LEFT]
  const right = landmarks[MOUTH_CORNER_RIGHT]
  const upper = landmarks[UPPER_LIP_INNER]
  const lower = landmarks[LOWER_LIP_INNER]
  const eyeLeft = landmarks[EYE_OUTER_LEFT]
  const eyeRight = landmarks[EYE_OUTER_RIGHT]
  if (!left || !right || !upper || !lower || !eyeLeft || !eyeRight) return null

  const scale = dist(eyeLeft, eyeRight)
  if (!scale) return null

  return {
    openness: dist(upper, lower) / scale,
    spread: dist(left, right) / scale,
  }
}

// SHAPE_TARGETS describes `spread` relatively ('narrow' | 'wide'), not as
// an absolute number, because mouth-width-to-interocular-distance ratios
// vary meaningfully between faces. This resolves that relative label into
// a concrete [min, max] range using the player's own calibrated resting
// mouth spread as the reference point.
export function resolveSpreadRange(kind, baselineSpread) {
  if (!baselineSpread) return null
  if (kind === 'narrow') return [0, baselineSpread * 0.94]
  if (kind === 'wide') return [baselineSpread * 1.12, Infinity]
  return null
}

// 1.0 when value is inside [min, max], falling off linearly the further
// outside the range it is. A soft score (not boolean pass/fail) is what
// lets the game show a "yellow / getting close" tier instead of only ever
// hard catching or missing.
function closenessScore(value, min, max) {
  if (value >= min && value <= max) return 1
  const span = Math.max(max - min, 0.001)
  const delta = value < min ? min - value : value - max
  return Math.max(0, 1 - delta / span)
}

// Scores the player's current (smoothed) mouth metrics against a shape
// target. Returns a continuous 0-1 score (useful for logging/analytics via
// logAttempt) plus the discrete tier the UI actually reacts to.
export function scoreAgainstTarget(metrics, target, baselineSpread) {
  if (!metrics || !target) return { score: 0, tier: 'red' }

  const [openMin, openMax] = target.openness
  const openScore = closenessScore(metrics.openness, openMin, openMax)

  let spreadScore = 1 // null discriminator = spread doesn't matter for this shape
  if (target.spread) {
    const range = resolveSpreadRange(target.spread, baselineSpread)
    if (range) {
      spreadScore = range[1] === Infinity
        ? closenessScore(metrics.spread, range[0], range[0] * 1.25)
        : closenessScore(metrics.spread, range[0], range[1])
    }
  }

  const score = Math.min(openScore, spreadScore)
  let tier = 'red'
  if (score >= 0.82) tier = 'green'
  else if (score >= 0.5) tier = 'yellow'

  return { score, tier }
}
