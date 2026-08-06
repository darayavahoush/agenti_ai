// Coarse color-heuristic tongue estimation. MediaPipe's face mesh has no
// tongue landmarks, so this crops the inner-mouth region from the video
// frame and classifies pixels by color to approximate whether the tongue
// is visible and how high it sits — a guide, not precision tracking (see
// the caveat already shown in TongueTamer's UI).

const MOUTH_CORNER_LEFT = 61
const MOUTH_CORNER_RIGHT = 291
const UPPER_LIP_INNER = 13
const LOWER_LIP_INNER = 14

// Downscaled crop size — small on purpose. This runs every animation
// frame, so keeping the sampled region tiny (worst case ~40x30 px) keeps
// per-frame pixel classification cheap.
const CROP_W = 48
const CROP_H = 36

function isTongueColored(r, g, b) {
  // Tongue: pink/red — red channel clearly dominant over green and blue,
  // not too dark (excludes the shadowed cavity interior/throat), not too
  // bright-and-balanced (excludes teeth, which read as near-white: high
  // r/g/b all close together).
  const brightness = (r + g + b) / 3
  if (brightness < 40) return false // cavity shadow
  const isWhitish = r > 190 && g > 170 && b > 160 && Math.abs(r - g) < 35
  if (isWhitish) return false // teeth
  return r > g * 1.12 && r > b * 1.05
}

// Returns { visibility, elevation, brightness } or null if landmarks/video
// aren't ready. visibility: 0-1 fraction of the mouth-interior crop that
// looks tongue-colored. elevation: 0 (low/back) to 1 (high/roof) weighted
// vertical position of those pixels within the crop. brightness: 0-255
// average brightness of the whole crop (used for the low-light warning).
export function computeTongueMetrics(video, landmarks, analysisCanvas, width, height) {
  if (!video || !landmarks || !analysisCanvas) return null
  if (landmarks.length <= MOUTH_CORNER_RIGHT) return null

  const left = landmarks[MOUTH_CORNER_LEFT]
  const right = landmarks[MOUTH_CORNER_RIGHT]
  const upper = landmarks[UPPER_LIP_INNER]
  const lower = landmarks[LOWER_LIP_INNER]
  if (!left || !right || !upper || !lower) return null

  // Inner-mouth bounding box in source video pixel space. Landmarks are
  // normalized (0-1); width/height here are the video's native pixel
  // dimensions (canvas was sized from videoRef.videoWidth/Height).
  const x0 = Math.max(0, Math.min(left.x, right.x) * width)
  const x1 = Math.min(width, Math.max(left.x, right.x) * width)
  const y0 = Math.max(0, upper.y * height)
  const y1 = Math.min(height, lower.y * height)
  const sw = x1 - x0
  const sh = y1 - y0
  if (sw < 4 || sh < 4) return null

  analysisCanvas.width = CROP_W
  analysisCanvas.height = CROP_H
  const ctx = analysisCanvas.getContext("2d", { willReadFrequently: true })
  ctx.drawImage(video, x0, y0, sw, sh, 0, 0, CROP_W, CROP_H)

  let data
  try {
    data = ctx.getImageData(0, 0, CROP_W, CROP_H).data
  } catch {
    // getImageData can throw on a tainted canvas (e.g. cross-origin video
    // source) — fail soft rather than crash the detection loop.
    return null
  }

  let totalBrightness = 0
  let tongueCount = 0
  let elevationWeightedSum = 0
  const pixelCount = CROP_W * CROP_H

  for (let py = 0; py < CROP_H; py++) {
    for (let px = 0; px < CROP_W; px++) {
      const i = (py * CROP_W + px) * 4
      const r = data[i]
      const g = data[i + 1]
      const b = data[i + 2]
      totalBrightness += (r + g + b) / 3

      if (isTongueColored(r, g, b)) {
        tongueCount += 1
        // Row 0 = top of crop = roof of mouth = high elevation.
        elevationWeightedSum += 1 - py / (CROP_H - 1)
      }
    }
  }

  const visibility = tongueCount / pixelCount
  const elevation = tongueCount > 0 ? elevationWeightedSum / tongueCount : 0
  const brightness = totalBrightness / pixelCount

  return { visibility, elevation, brightness }
}

function closenessScore(value, min, max) {
  if (value >= min && value <= max) return 1
  const span = Math.max(max - min, 0.001)
  const delta = value < min ? min - value : value - max
  return Math.max(0, 1 - delta / span)
}

// Scores smoothed tongue metrics against a TONGUE_MOVES target ({
// visibility: [min,max], elevation: [min,max] }). Same soft-score /
// three-tier shape as mouthMetrics.js's scoreAgainstTarget, so both games
// feel consistent to play.
export function scoreTongueMove(metrics, target) {
  if (!metrics || !target) return { score: 0, tier: "red" }

  const visScore = closenessScore(metrics.visibility, target.visibility[0], target.visibility[1])
  const elevScore = closenessScore(metrics.elevation, target.elevation[0], target.elevation[1])
  const score = Math.min(visScore, elevScore)

  let tier = "red"
  if (score >= 0.82) tier = "green"
  else if (score >= 0.5) tier = "yellow"

  return { score, tier }
}
