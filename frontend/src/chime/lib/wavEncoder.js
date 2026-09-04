// Encodes a mono Float32 PCM buffer (the shape AnalyserNode/ScriptProcessorNode
// hand back) into a 16-bit PCM WAV Blob faster-whisper can read directly.
//
// Why not MediaRecorder: it has real startup latency between `.start()` and
// actually capturing audio, and a burst is often already a few frames into
// happening by the time we know we want to record it (gameLoop only knows a
// burst has *ended*, not that one is about to begin). A ring buffer already
// holds the raw samples leading up to and through the burst, so this encoder
// just needs to turn a plain Float32Array into a valid WAV file, no capture
// timing to get right.

function floatTo16BitPCM(view, offset, input) {
  for (let i = 0; i < input.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, input[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
}

function writeString(view, offset, str) {
  for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
}

export function encodeWavMono(float32Samples, sampleRate) {
  const numSamples = float32Samples.length
  const bytesPerSample = 2
  const blockAlign = bytesPerSample // 1 channel
  const byteRate = sampleRate * blockAlign
  const dataSize = numSamples * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)       // fmt chunk size
  view.setUint16(20, 1, true)        // PCM
  view.setUint16(22, 1, true)        // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, byteRate, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true)       // bits per sample
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)
  floatTo16BitPCM(view, 44, float32Samples)

  return new Blob([buffer], { type: 'audio/wav' })
}
