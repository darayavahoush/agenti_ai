import { FILTERS } from "../components/CharacterFilterPicker.jsx"

// MediaPipe FaceLandmarker face mesh indices (468-point topology).
// Outer lip contour, in order, forming a closed loop.
const LIPS_OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61]
const EYE_OUTER_LEFT = 33
const EYE_OUTER_RIGHT = 263
const FOREHEAD_TOP = 10

const FILTER_BY_ID = Object.fromEntries(FILTERS.map((f) => [f.id, f]))

function toPoint(lm, width, height) {
  return { x: lm.x * width, y: lm.y * height }
}

function faceScale(landmarks, width, height) {
  const l = toPoint(landmarks[EYE_OUTER_LEFT], width, height)
  const r = toPoint(landmarks[EYE_OUTER_RIGHT], width, height)
  return Math.hypot(r.x - l.x, r.y - l.y)
}

export function drawMouthOutline(ctx, landmarks, width, height, color) {
  if (!landmarks || landmarks.length <= 405) return
  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = Math.max(2, width * 0.006)
  ctx.lineJoin = "round"
  ctx.beginPath()
  LIPS_OUTER.forEach((idx, i) => {
    const p = toPoint(landmarks[idx], width, height)
    if (i === 0) ctx.moveTo(p.x, p.y)
    else ctx.lineTo(p.x, p.y)
  })
  ctx.closePath()
  ctx.stroke()
  ctx.restore()
}

// Renders the selected character as a single mascot badge that tracks and
// floats above the player's head, glowing in that filter's theme color.
// Deliberately not per-feature AR (no invented individual ear/whisker
// placement) — a tracked mascot always reads correctly regardless of head
// tilt, and matches what CharacterFilterPicker actually offers: a themed
// badge per character, not a full costume rig.
export function drawFaceFilter(ctx, landmarks, width, height, filterId) {
  const meta = FILTER_BY_ID[filterId]
  if (!landmarks || !meta || !meta.badge) return
  if (landmarks.length <= FOREHEAD_TOP) return

  const scale = faceScale(landmarks, width, height)
  const forehead = toPoint(landmarks[FOREHEAD_TOP], width, height)
  const anchor = { x: forehead.x, y: forehead.y - scale * 0.65 }
  const badgeSize = scale * 1.15

  ctx.save()
  ctx.shadowColor = meta.frameColor
  ctx.shadowBlur = scale * 0.25
  ctx.font = `${badgeSize}px system-ui, "Apple Color Emoji", "Segoe UI Emoji", sans-serif`
  ctx.textAlign = "center"
  ctx.textBaseline = "middle"
  ctx.fillText(meta.badge, anchor.x, anchor.y)
  ctx.restore()
}


const UPPER_LIP_INNER = 13
const LOWER_LIP_INNER = 14

// Draws a directional cue over the mouth: "up" for lifting the tongue tip
// to the roof, "back" for retracting it. This is illustrative (paired with
// the color-heuristic tracking in tongueTracking.js), not a rendering of
// an actually-tracked tongue position — MediaPipe's face mesh has no
// tongue landmarks to draw from.
export function drawTongueArrow(ctx, landmarks, width, height, direction, color) {
  if (!landmarks || landmarks.length <= LOWER_LIP_INNER) return
  const upper = toPoint(landmarks[UPPER_LIP_INNER], width, height)
  const lower = toPoint(landmarks[LOWER_LIP_INNER], width, height)
  const scale = faceScale(landmarks, width, height)
  const cx = (upper.x + lower.x) / 2
  const cy = (upper.y + lower.y) / 2
  const len = scale * 0.55

  let tipX = cx
  let tipY = cy
  let tailX = cx
  let tailY = cy

  if (direction === "up") {
    tipY = cy - len
    tailY = cy - len * 0.15
  } else {
    // "back": point toward the nearer ear (mirror-safe — video/canvas are
    // both CSS-flipped together, and landmarks are unmirrored, so picking
    // the ear closer to mouth-center in raw landmark space is correct
    // regardless of which side reads as "left" on screen).
    const dxToRightEye = landmarks[EYE_OUTER_RIGHT].x - landmarks[UPPER_LIP_INNER].x
    const goRight = dxToRightEye < 0
    tipX = cx + (goRight ? len : -len)
    tailX = cx + (goRight ? len * 0.15 : -len * 0.15)
  }

  ctx.save()
  ctx.strokeStyle = color
  ctx.fillStyle = color
  ctx.lineWidth = Math.max(2, width * 0.008)
  ctx.lineCap = "round"
  ctx.beginPath()
  ctx.moveTo(tailX, tailY)
  ctx.lineTo(tipX, tipY)
  ctx.stroke()

  // Arrowhead
  const angle = Math.atan2(tipY - tailY, tipX - tailX)
  const headLen = scale * 0.14
  ctx.beginPath()
  ctx.moveTo(tipX, tipY)
  ctx.lineTo(
    tipX - headLen * Math.cos(angle - Math.PI / 6),
    tipY - headLen * Math.sin(angle - Math.PI / 6),
  )
  ctx.lineTo(
    tipX - headLen * Math.cos(angle + Math.PI / 6),
    tipY - headLen * Math.sin(angle + Math.PI / 6),
  )
  ctx.closePath()
  ctx.fill()
  ctx.restore()
}
