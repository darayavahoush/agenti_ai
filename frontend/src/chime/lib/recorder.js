// lib/recorder.js -- build the short "verification window" recorders the Chime
// games use to have the server confirm the child really made the target sound.
//
// The games used to hard-code `new MediaRecorder(stream, { mimeType:
// 'audio/webm;codecs=opus' })`. Chrome, Edge and Firefox accept that; Safari
// and every iPhone browser (all WebKit) do not, so the constructor threw and
// verification silently never ran. Ask the browser what it CAN record instead,
// in order of preference, and fall back to its own default.
//
// Formats other than webm/opus are recorded as-is: the scoring endpoint decodes
// with ffmpeg, which identifies the container from the bytes, not the filename.

const PREFERRED_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4;codecs=mp4a.40.2',
  'audio/mp4',
  'audio/ogg;codecs=opus',
]

/** Returns null when this browser has no MediaRecorder at all. */
export function pickRecorderMimeType() {
  if (typeof MediaRecorder === 'undefined') return null
  if (typeof MediaRecorder.isTypeSupported !== 'function') return ''
  return PREFERRED_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) ?? ''
}

/** Throws (like `new MediaRecorder` would) when recording isn't possible. */
export function createRecorder(stream) {
  const mimeType = pickRecorderMimeType()
  if (mimeType === null) throw new Error('MediaRecorder is not available in this browser')
  return new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
}

/** File extension for an upload, from the recorded blob's own MIME type. */
export function recordingFilename(mimeType) {
  const type = (mimeType || '').toLowerCase()
  if (type.includes('mp4') || type.includes('aac')) return 'recording.mp4'
  if (type.includes('ogg')) return 'recording.ogg'
  return 'recording.webm'
}
