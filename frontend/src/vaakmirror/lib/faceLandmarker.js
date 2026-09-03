import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision'

// All four camera games (MirrorMirror, LipSyncHero, TongueTamer,
// MinimalPairDrill) need the same MediaPipe FaceLandmarker, requested with
// the GPU delegate for speed. On some devices/browsers the GPU delegate
// can't get a WebGL2 context at all — hardware acceleration disabled,
// driver blocklisted, battery-saver/low-power mode, too many contexts
// already open elsewhere on the page — and createFromOptions throws
// (typically "emscripten_webgl_create_context() returned error 0").
// Previously that exception just failed setup entirely and the game
// dropped straight to its "Couldn't start the camera" error screen even
// though CPU inference would have worked fine (slower, but functional).
// Retrying once with delegate: 'CPU' turns that into a working — if less
// smooth — session instead of a hard failure.
export async function loadFaceLandmarker(wasmUrl, modelUrl) {
  const fileset = await FilesetResolver.forVisionTasks(wasmUrl)
  const baseConfig = { runningMode: 'VIDEO', numFaces: 1 }
  try {
    return await FaceLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: modelUrl, delegate: 'GPU' },
      ...baseConfig,
    })
  } catch (err) {
    console.warn('FaceLandmarker GPU delegate failed, retrying on CPU:', err)
    return await FaceLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: modelUrl, delegate: 'CPU' },
      ...baseConfig,
    })
  }
}
