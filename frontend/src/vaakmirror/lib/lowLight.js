// Low-light handling shared by all four camera games (MirrorMirror,
// LipSyncHero, MinimalPairDrill, TongueTamer). Two problems, same root
// cause: a dim raw video frame gives both the MediaPipe FaceLandmarker
// (landmark confidence drops) and TongueTamer's own pixel-color tongue
// heuristic (isTongueColor/isDarkCavity in tongueTracking.js, which
// classifies by hue/saturation/value on raw RGB) a weak signal to work
// with. Fixing it once at the frame source — before either consumer sees
// the pixels — beats patching each one separately.
//
// Three independent pieces, meant to be used together:
//   1. sampleBrightness()       — cheap whole-frame brightness reading
//   2. getDetectionSource()     — boosts the frame when it's dark enough
//                                 to need it, returns the raw video
//                                 untouched otherwise
//   3. requestBrighterExposure() — best-effort ask the camera hardware
//                                  itself for more light, once up front
//
// The boost is adaptive (scaled to how dark the room actually is), not a
// fixed multiplier, so a normally-lit room is never needlessly washed out.

const BRIGHTNESS_SAMPLE_W = 24
const BRIGHTNESS_SAMPLE_H = 18

// 0-255 mean luma. Below this, the UI shows a lighting hint and
// getDetectionSource starts boosting. This is a whole-frame reading (face
// + background), not the mouth-region-only brightness TongueTamer used to
// compute internally — a fuller frame reads brighter on average than just
// the mouth, so this threshold sits higher than that old one did.
export const LOW_LIGHT_THRESHOLD = 70
// Anything darker than this is treated as "as dark as we boost for" — a
// near-black frame is mostly sensor noise by that point, so boosting
// further just amplifies noise instead of recovering real signal.
const DARK_FLOOR = 25

// Downsamples the whole video frame to a tiny canvas and returns its mean
// brightness (0-255), or null if the video isn't ready yet. Cheap enough
// to call every frame — same order of cost as the mouth-region sampling
// tongueTracking.js already does per frame for TongueTamer.
export function sampleBrightness(video, scratchCanvas) {
  if (!video || !scratchCanvas || video.readyState < 2) return null
  scratchCanvas.width = BRIGHTNESS_SAMPLE_W
  scratchCanvas.height = BRIGHTNESS_SAMPLE_H
  const ctx = scratchCanvas.getContext('2d', { willReadFrequently: true })
  ctx.drawImage(video, 0, 0, BRIGHTNESS_SAMPLE_W, BRIGHTNESS_SAMPLE_H)
  let data
  try {
    data = ctx.getImageData(0, 0, BRIGHTNESS_SAMPLE_W, BRIGHTNESS_SAMPLE_H).data
  } catch {
    return null
  }
  let sum = 0
  const total = BRIGHTNESS_SAMPLE_W * BRIGHTNESS_SAMPLE_H
  for (let i = 0; i < data.length; i += 4) {
    sum += (data[i] + data[i + 1] + data[i + 2]) / 3
  }
  return sum / total
}

// Linear ramp between DARK_FLOOR and LOW_LIGHT_THRESHOLD: no boost at/above
// threshold, capped boost at/below floor. Contrast is bumped alongside
// brightness so the boosted image doesn't look flat/washed out — a plain
// brightness lift alone tends to grey out shadows along with lifting them.
function boostFor(brightness) {
  if (brightness === null || brightness >= LOW_LIGHT_THRESHOLD) return null
  const clamped = Math.max(DARK_FLOOR, brightness)
  const t = (LOW_LIGHT_THRESHOLD - clamped) / (LOW_LIGHT_THRESHOLD - DARK_FLOOR) // 0..1
  return {
    brightness: 1 + t * 0.9, // up to +90%
    contrast: 1 + t * 0.25, // up to +25%
  }
}

// Returns what to feed detectForVideo() (and, in TongueTamer, its own
// pixel-color sampling) this frame: the raw video element when lighting is
// fine, or scratchCanvas drawn with a brightness/contrast boost when it's
// not. Callers always use the return value rather than branching on
// whether a boost happened, so normal lighting pays zero extra canvas cost
// (the common case) and dim lighting gets the boost applied once, shared
// by every downstream consumer of this frame.
export function getDetectionSource(video, scratchCanvas, brightness) {
  const boost = boostFor(brightness)
  if (!boost) return video
  scratchCanvas.width = video.videoWidth
  scratchCanvas.height = video.videoHeight
  const ctx = scratchCanvas.getContext('2d', { willReadFrequently: true })
  ctx.filter = `brightness(${boost.brightness}) contrast(${boost.contrast})`
  ctx.drawImage(video, 0, 0, scratchCanvas.width, scratchCanvas.height)
  ctx.filter = 'none'
  return scratchCanvas
}

// Best-effort only — most webcams/browsers don't expose manual exposure
// control at all, and this silently no-ops when they don't (the canvas
// boost above is the fallback that always works, everywhere). Call once
// right after getUserMedia resolves; not re-checked per frame, since
// re-adjusting on an interval would fight the camera's own auto-exposure
// and could cause visible hunting/flicker.
export async function requestBrighterExposure(track) {
  if (!track || typeof track.getCapabilities !== 'function') return
  try {
    const caps = track.getCapabilities()
    const advanced = []
    if (caps.exposureMode?.includes?.('continuous')) {
      advanced.push({ exposureMode: 'continuous' })
    }
    if (typeof caps.exposureCompensation?.max === 'number') {
      // Bias toward the brighter half of the supported range rather than
      // maxing it out — this runs once up front, before we know whether
      // the room is actually dark, so maxing it would blow out anyone who
      // wasn't in low light to begin with.
      const { min, max } = caps.exposureCompensation
      advanced.push({ exposureCompensation: min + (max - min) * 0.65 })
    }
    if (advanced.length) {
      await track.applyConstraints({ advanced })
    }
  } catch (err) {
    console.warn('Camera exposure adjustment not available:', err)
  }
}
