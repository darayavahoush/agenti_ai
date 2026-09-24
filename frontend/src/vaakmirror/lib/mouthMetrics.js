// Turns raw MediaPipe FaceLandmarker points into two normalized metrics
// (openness, spread) that the games score shapes against. Landmark indices
// below follow the standard 478-point MediaPipe Face Mesh topology.
//
// NOTE: an earlier version derived a "roundness" metric as
// mouthWidth / (mouthOpen + 0.01). That divides by a near-zero number for
// any closed-lip target (p, b, m), so the value blows up and gets clamped
// to 0 — outside every closed-lip target range, so those sounds could never
// score a match no matter how correctly the child closed their lips.
// `spread` below replaces it with a metric computed independently of
// openness, so closed-lip and open-mouth shapes can both be scored.

const UPPER_LIP = 13
const LOWER_LIP = 14
const LEFT_MOUTH_CORNER = 61
const RIGHT_MOUTH_CORNER = 291
const LEFT_FACE = 234
const RIGHT_FACE = 454
const TOP_FACE = 10
const BOTTOM_FACE = 152

function dist(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

// Fallback denominator for openness, used until a player has a calibrated
// max-open baseline (or calibration was skipped) — roughly a wide-open
// mouth in these face-scale-normalized units. Personalized scoring
// replaces this with each player's own measured max, the same
// personalize-if-available pattern SPREAD_FALLBACK below uses for spread.
const OPENNESS_FALLBACK_MAX = 0.18

export function computeMouthMetrics(landmarks) {
  if (!landmarks || landmarks.length < 468) return null

  const faceWidth = dist(landmarks[LEFT_FACE], landmarks[RIGHT_FACE])
  const faceHeight = dist(landmarks[TOP_FACE], landmarks[BOTTOM_FACE])
  const scale = (faceWidth + faceHeight) / 2 || 1

  // mouthOpenRaw: vertical lip gap, normalized to face scale only — not yet
  // divided by any "how wide is wide" reference. Games that personalize
  // openness divide this by the player's own calibrated max via
  // resolveOpenness(); `openness` below is the same value pre-divided by
  // the shared fallback constant, for callers that only need a rough,
  // non-personalized reading (e.g. TongueTamer's "is the mouth open enough
  // to see the tongue" gate, which isn't scoring a shape match).
  const mouthOpenRaw = dist(landmarks[UPPER_LIP], landmarks[LOWER_LIP]) / scale
  const openness = Math.max(0, Math.min(1, mouthOpenRaw / OPENNESS_FALLBACK_MAX))

  // Spread: horizontal mouth width normalized to face scale, independent of
  // opening. A pursed/rounded mouth ('oo', 'sh') narrows this; a smile or
  // neutral rest widens it. Unlike the old roundness metric, this never
  // divides by the (possibly near-zero) opening value.
  //
  // FIX: this previously divided by `scale` a second time here, after
  // mouthWidth had already been scale-normalized above — e.g.
  // `mouthWidth = dist(...) / scale` then `spread = mouthWidth / scale`.
  // That shrank spread more for players sitting closer to the camera
  // (bigger scale), the opposite of what face-scale normalization is for.
  // It was self-consistent within one session (the same bug applied when
  // sampling baselineSpread during calibration and when scoring live
  // frames), so playing at a fixed distance from the camera mostly
  // canceled it out — but it broke the fallback ranges below for anyone
  // who skipped calibration, and broke scoring for anyone who moved closer
  // or farther between calibrating and playing. Fixed to divide once.
  const spread = dist(landmarks[LEFT_MOUTH_CORNER], landmarks[RIGHT_MOUTH_CORNER]) / scale

  return { openness, mouthOpenRaw, spread }
}

function inRangeDist(value, [lo, hi]) {
  if (value >= lo && value <= hi) return 0
  return Math.min(Math.abs(value - lo), Math.abs(value - hi))
}

// Fallback ranges used until a player has a calibrated baseline (or if
// calibration was skipped) — roughly tuned to an average adult/child face,
// same purpose the old fixed constants served.
const SPREAD_FALLBACK = { narrow: [0, 0.42], wide: [0.46, 1] }

// Resolves a target's relative spread tag ('narrow' | 'wide' | null) into a
// concrete [lo, hi] range. When a baseline is available, narrow/wide are
// expressed as a percentage of *this player's own* resting mouth width
// instead of a fixed number — so someone with a naturally wider or
// narrower mouth doesn't have to over- or under-shoot a generic target.
export function resolveSpreadRange(tag, baselineSpread) {
  if (!tag) return [0, 1]
  if (!baselineSpread) return SPREAD_FALLBACK[tag] ?? [0, 1]
  if (tag === 'narrow') return [0, baselineSpread * 0.86]
  if (tag === 'wide') return [baselineSpread * 1.08, 1]
  return [0, 1]
}

// Resolves a raw mouth-open distance into the same [0, 1] "how open" scale
// SHAPE_TARGETS' openness ranges are written in (0 = closed, 1 = wide
// open). Divides by the player's own calibrated max-open sample when one
// exists, falling back to the shared constant otherwise — the same
// personalize-if-available pattern resolveSpreadRange uses for spread, so
// a kid with a naturally smaller or larger opening range is judged against
// their own max rather than one generic number.
export function resolveOpenness(mouthOpenRaw, baselineOpenMax) {
  if (mouthOpenRaw == null) return 0
  const max = baselineOpenMax || OPENNESS_FALLBACK_MAX
  return Math.max(0, Math.min(1, mouthOpenRaw / max))
}

export function scoreAgainstTarget(metrics, target, baselineSpread, baselineOpenMax) {
  if (!metrics || !target) return { score: 0, tier: 'red' }

  const spreadRange = resolveSpreadRange(target.spread, baselineSpread)
  const opennessValue = resolveOpenness(metrics.mouthOpenRaw, baselineOpenMax)
  const opennessDist = inRangeDist(opennessValue, target.openness)
  const spreadDist = inRangeDist(metrics.spread, spreadRange)

  const distance = opennessDist + spreadDist
  const score = Math.max(0, 1 - distance * 1.7)

  let tier = 'red'
  if (score > 0.78) tier = 'green'
  else if (score > 0.42) tier = 'yellow'

  return { score, tier }
}
