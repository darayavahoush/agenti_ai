import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Settings, Volume2 } from 'lucide-react'
import { logEvent, getAgentDecision, transcribeAudio } from './lib/api'
import { getNextLevelRoute } from './lib/levelProgress'
import { useSpokenInstruction, stopSpeaking } from '../lib/speech'

const LEVEL_ID = 'fa'
const AGENT_POLICY = 'tabular_q'
const MIN_VOICING_FRAMES = 3 // ~50ms at 60fps; filters out single-frame noise blips

// ============================================================
// Pure logic — ported 1:1 from wind_chime_garden.html / chime_garden_logic.js.
// Do not change the math without re-running chime_garden_logic.test.js
// against an equivalent copy.
//
// "ya" is a glide into a voiced vowel — tonal/harmonic, the opposite acoustic
// signature from the earlier "ffff" target (turbulent, noise-shaped
// frication). Detection is periodicity-based (autocorrelation on raw
// time-domain samples), not spectral-centroid-based — see computePeriodicity.
// ============================================================
function computePeriodicity(timeDomainData, sampleRate, minFreqHz = 120, maxFreqHz = 500) {
  const n = timeDomainData.length
  let energy = 0
  for (let i = 0; i < n; i++) energy += timeDomainData[i] * timeDomainData[i]
  if (energy < 1e-6) return 0
  const minLag = Math.max(1, Math.floor(sampleRate / maxFreqHz))
  const maxLag = Math.min(n - 1, Math.floor(sampleRate / minFreqHz))
  let bestCorr = 0
  for (let lag = minLag; lag <= maxLag; lag++) {
    let corr = 0
    for (let i = 0; i < n - lag; i++) corr += timeDomainData[i] * timeDomainData[i + lag]
    const normCorr = corr / energy
    if (normCorr > bestCorr) bestCorr = normCorr
  }
  return Math.max(0, Math.min(1, bestCorr))
}
const MIN_PERIODICITY_DEFAULT = 0.15
const MAX_EXPECTED_PERIODICITY_DEFAULT = 0.85
function computeVoicingScore(rms, periodicity, noiseFloor = 0.01, minPeriodicity = MIN_PERIODICITY_DEFAULT, maxPeriodicity = MAX_EXPECTED_PERIODICITY_DEFAULT) {
  if (rms < noiseFloor) return { score: 0, isValidAttempt: false }
  if (periodicity < minPeriodicity) return { score: 0.05, isValidAttempt: true }
  const score = Math.max(0, Math.min(1, (periodicity - minPeriodicity) / (maxPeriodicity - minPeriodicity)))
  return { score, isValidAttempt: true }
}
function personalizeVoicingRange(periodicityReadings, fallbackMin = MIN_PERIODICITY_DEFAULT, fallbackMax = MAX_EXPECTED_PERIODICITY_DEFAULT) {
  const valid = periodicityReadings.filter(p => p > 0)
  if (valid.length < 3) return { minPeriodicity: fallbackMin, maxPeriodicity: fallbackMax, usedFallback: true }
  const mean = valid.reduce((s, p) => s + p, 0) / valid.length
  const minPeriodicity = Math.max(0.05, mean * 0.5)
  const maxPeriodicity = Math.min(0.98, mean * 1.25)
  return { minPeriodicity, maxPeriodicity, usedFallback: false }
}
function updateChimeRotation(currentAngle, currentSpeed, voicingScore, dt, config, sustainedSeconds = 0) {
  const { maxSpeed, spinUpRate, decayRate } = config
  const durationMultiplier = 1 + DURATION_BOOST_MAX * Math.min(1, sustainedSeconds / DURATION_BOOST_SECONDS)
  const targetSpeed = voicingScore * maxSpeed * durationMultiplier
  const nextSpeed = currentSpeed < targetSpeed ? Math.min(targetSpeed, currentSpeed + spinUpRate * dt) : Math.max(targetSpeed, currentSpeed - decayRate * dt)
  const nextAngle = currentAngle + nextSpeed * dt
  const fullRotations = Math.floor(nextAngle / (2 * Math.PI)) - Math.floor(currentAngle / (2 * Math.PI))
  return { angle: nextAngle, speed: nextSpeed, chimesRung: fullRotations }
}

const ROTATION_CONFIG = { maxSpeed: 5, spinUpRate: 8, decayRate: 3 }
const TARGET_BUBBLES_DEFAULT = 4

// Rewards sticking with the "ya" sound, not just being voiced for one frame:
// the chimes spin faster the longer voicing has been continuously held, capping
// at DURATION_BOOST_MAX extra once DURATION_BOOST_SECONDS of unbroken voicing
// is reached. Resets to 0 the instant voicing breaks (see gameLoop) — ported
// 1:1 from Rocket Launch / Submarine Dive's duration-boost mechanic.
const DURATION_BOOST_MAX = 0.6
const DURATION_BOOST_SECONDS = 2.5

// Rolling window for real speech verification — same approach as Bubble Wrap
// Pop / Rocket Launch / Submarine Dive. Bubbles still spawn the instant the
// local periodicity detector rings a rotation (kids need snappy feedback),
// but every ~2s the window's audio gets transcribed and checked for a real
// "ya" attempt. If it wasn't real voicing, whatever bubbles that window
// spawned are quietly popped and taken back.
const VERIFY_WINDOW_MS = 2000

// "ya" is a glide (the onset "y") into a vowel, not a bare sustained vowel —
// unlike Rocket Launch's "aaa" or Submarine Dive's "oooo", whisper may or
// may not render the glide's onset. Require a lower vowel-dominance ratio
// when the onset did come through (the "y" itself is real signal), and a
// stricter one when it didn't, so stray non-"ya" noise can't false-accept.
function isYaSound(transcript) {
  const cleaned = (transcript || '').toLowerCase().replace(/[^a-z]/g, '')
  if (cleaned.length < 2) return false
  const aRatio = (cleaned.match(/a/g) || []).length / cleaned.length
  return cleaned.startsWith('y') ? aRatio >= 0.3 : aRatio >= 0.5
}

const DIFFICULTY_AGENT = {
  SAFE_RANGE: [4, 14],
  STEP: 1,
  FAST_S: 6,
  SLOW_S: 18,
  decide(timeToWinSeconds) {
    if (timeToWinSeconds < this.FAST_S) return { action: 'more', message: "Beautiful sustained breath! Let's blow a few more bubbles next time 🫧" }
    if (timeToWinSeconds > this.SLOW_S) return { action: 'fewer', message: "Lovely effort! Let's blow a few less bubbles next time 🌙" }
    return { action: 'hold', message: "Wonderful, steady airflow! Let's keep this the same for now 💛" }
  },
  apply(targetBubbles, decision) {
    let next = targetBubbles
    if (decision.action === 'more') next += this.STEP
    if (decision.action === 'fewer') next -= this.STEP
    return Math.max(this.SAFE_RANGE[0], Math.min(this.SAFE_RANGE[1], next))
  },
}

export default function WindChimeGarden() {
  const navigate = useNavigate()
  const canvasRef = useRef(null)
  const rafRef = useRef(null)

  const [screen, setScreen] = useState('start')
  const [micErrorMsg, setMicErrorMsg] = useState('')
  const [calibLabel, setCalibLabel] = useState({ title: "Let's find quiet...", subtitle: 'Stay nice and quiet for a moment', emoji: '🤫' })
  const [calibProgress, setCalibProgress] = useState(0)
  const [hudVisible, setHudVisible] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [reduceMotion, setReduceMotion] = useState(() => localStorage.getItem('chime_reduce_motion') === 'true')
  const [muted, setMuted] = useState(() => localStorage.getItem('chime_muted') === 'true')
  const [encourageVisible, setEncourageVisible] = useState(false)
  const [successVisible, setSuccessVisible] = useState(false)
  const [agentFeedback, setAgentFeedback] = useState('')
  const [ariaMsg, setAriaMsg] = useState('')

  const stateRef = useRef({
    audioCtx: null, analyser: null, timeDomainData: null, mediaStream: null,
    noiseFloor: 0.01,
    angle: 0, speed: 0, bubblesSpawned: 0, targetBubbles: TARGET_BUBBLES_DEFAULT,
    smoothedScore: 0, lastFrameTime: 0, quietStreak: 0,
    hasFinished: false, particles: [],
    attemptStartTime: 0, attemptNumber: 0,
    stars: [], fireflies: [], bubbles: [],
    minPeriodicity: MIN_PERIODICITY_DEFAULT, maxPeriodicity: MAX_EXPECTED_PERIODICITY_DEFAULT,
    bubbleNotes: [523.25, 587.33, 659.25, 698.46, 783.99, 880.0, 987.77, 1046.5],
    inVoicing: false, voicingScores: [], sustainedSeconds: 0,
    W: 0, H: 0, DPR: 1,
    // Rolling ~2s speech-verification window (see VERIFY_WINDOW_MS above).
    spawnedThisWindow: [], verifyTimer: null, mediaRecorderRef: null,
  })

  const reduceMotionRef = useRef(reduceMotion)
  const mutedRef = useRef(muted)
  useEffect(() => { reduceMotionRef.current = reduceMotion; localStorage.setItem('chime_reduce_motion', reduceMotion) }, [reduceMotion])
  useEffect(() => { mutedRef.current = muted; localStorage.setItem('chime_muted', muted) }, [muted])

  const replayInstruction = useSpokenInstruction(
    'Say a long yaaa to blow glowing bubbles into the evening sky!',
    { enabled: screen === 'start' && !muted },
  )

  useEffect(() => {
    const state = stateRef.current
    return () => {
      cancelAnimationFrame(rafRef.current)
      clearTimeout(state.verifyTimer)
      if (state.mediaRecorderRef && state.mediaRecorderRef.state !== 'inactive') {
        try { state.mediaRecorderRef.onstop = null; state.mediaRecorderRef.stop() } catch { /* already stopped */ }
      }
      if (state.audioCtx) state.audioCtx.close().catch(() => {})
      if (state.mediaStream) state.mediaStream.getTracks().forEach(t => t.stop())
    }
  }, [])

  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const s = stateRef.current
    s.DPR = Math.min(window.devicePixelRatio || 1, 2)
    s.W = window.innerWidth
    s.H = window.innerHeight
    canvas.width = s.W * s.DPR
    canvas.height = s.H * s.DPR
    canvas.style.width = s.W + 'px'
    canvas.style.height = s.H + 'px'
    const ctx = canvas.getContext('2d')
    ctx.setTransform(s.DPR, 0, 0, s.DPR, 0, 0)
    initStars()
  }, [])

  function initStars() {
    const s = stateRef.current
    const count = Math.floor((s.W * s.H) / 12000)
    s.stars = Array.from({ length: count }, () => ({ x: Math.random() * s.W, y: Math.random() * s.H * 0.5, r: Math.random() * 1.4 + 0.5, phase: Math.random() * Math.PI * 2 }))
    const fireflyCount = Math.floor((s.W * s.H) / 55000)
    s.fireflies = Array.from({ length: fireflyCount }, () => ({
      x: Math.random() * s.W, y: s.H * 0.4 + Math.random() * s.H * 0.5,
      phase: Math.random() * Math.PI * 2, driftPhase: Math.random() * Math.PI * 2, speed: Math.random() * 0.3 + 0.15,
    }))
  }

  useEffect(() => {
    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)
    return () => window.removeEventListener('resize', resizeCanvas)
  }, [resizeCanvas])

  function readCurrentRMS() {
    const s = stateRef.current
    s.analyser.getFloatTimeDomainData(s.timeDomainData)
    let sum = 0
    for (let i = 0; i < s.timeDomainData.length; i++) sum += s.timeDomainData[i] * s.timeDomainData[i]
    return Math.sqrt(sum / s.timeDomainData.length)
  }

  function playBubbleNote(index) {
    const s = stateRef.current
    if (mutedRef.current || !s.audioCtx) return
    const freq = s.bubbleNotes[index % s.bubbleNotes.length]
    const a = s.audioCtx
    const osc = a.createOscillator(), gain = a.createGain()
    osc.type = 'sine'; osc.frequency.value = freq
    gain.gain.setValueAtTime(0, a.currentTime)
    gain.gain.linearRampToValueAtTime(0.045, a.currentTime + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + 0.6)
    osc.connect(gain).connect(a.destination)
    osc.start(); osc.stop(a.currentTime + 0.65)
  }

  // Soft descending tone when a window's bubbles turn out not to be real
  // voicing once the transcript comes back — deliberately gentler than
  // playSuccessChime, not a "wrong buzzer". Matches RocketLaunch/SubmarineDive.
  function playRetract() {
    const s = stateRef.current
    ;[440, 330].forEach((f, i) => setTimeout(() => {
      if (mutedRef.current || !s.audioCtx) return
      const a = s.audioCtx
      const osc = a.createOscillator(), gain = a.createGain()
      osc.type = 'sine'; osc.frequency.value = f
      gain.gain.setValueAtTime(0, a.currentTime)
      gain.gain.linearRampToValueAtTime(0.035, a.currentTime + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + 0.18)
      osc.connect(gain).connect(a.destination)
      osc.start(); osc.stop(a.currentTime + 0.2)
    }, i * 60))
  }

  function playSuccessChime() {
    const s = stateRef.current
    ;[523.25, 659.25, 783.99, 1046.5, 1318.5].forEach((f, i) => setTimeout(() => {
      if (mutedRef.current || !s.audioCtx) return
      const a = s.audioCtx
      const osc = a.createOscillator(), gain = a.createGain()
      osc.type = 'triangle'; osc.frequency.value = f
      gain.gain.setValueAtTime(0, a.currentTime)
      gain.gain.linearRampToValueAtTime(0.045, a.currentTime + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + 0.5)
      osc.connect(gain).connect(a.destination)
      osc.start(); osc.stop(a.currentTime + 0.55)
    }, i * 110))
  }

  async function requestMicAndCalibrate() {
    try {
      stopSpeaking()
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: false, autoGainControl: false } })
      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      const s = stateRef.current
      s.mediaStream = stream
      s.audioCtx = new AudioContextClass()
      const source = s.audioCtx.createMediaStreamSource(stream)
      s.analyser = s.audioCtx.createAnalyser()
      s.analyser.fftSize = 2048
      s.timeDomainData = new Float32Array(s.analyser.fftSize)
      source.connect(s.analyser)
      runCalibration()
    } catch (err) {
      setMicErrorMsg(err.name === 'NotAllowedError'
        ? 'Please allow microphone access so the garden can hear your voice.'
        : 'Something went wrong reaching the microphone. Please try again.')
      setScreen('micError')
    }
  }

  function runCalibration() {
    setScreen('calibrate')
    const QUIET_MS = 1200
    const LOUD_MS = 1800
    let quietSamples = []
    let periodicityReadings = []

    setCalibLabel({ title: "Let's find quiet...", subtitle: 'Stay nice and quiet for a moment', emoji: '🤫' })
    setCalibProgress(0)

    const quietStart = performance.now()
    function quietStep(now) {
      const elapsed = now - quietStart
      quietSamples.push(readCurrentRMS())
      setCalibProgress(Math.min(1, elapsed / QUIET_MS))
      if (elapsed < QUIET_MS) {
        requestAnimationFrame(quietStep)
      } else {
        const sorted = [...quietSamples].sort((a, b) => a - b)
        const p90 = sorted[Math.floor(sorted.length * 0.9)] || 0.01
        stateRef.current.noiseFloor = Math.max(0.006, p90 * 1.4)
        startLoudPhase()
      }
    }

    function startLoudPhase() {
      setCalibLabel({ title: 'Now say "yaaa"!', subtitle: 'Nice and clear, like cheering', emoji: '🗣️' })
      setCalibProgress(0)
      const loudStart = performance.now()
      function loudStep(now) {
        const elapsed = now - loudStart
        const s = stateRef.current
        const rms = readCurrentRMS()
        if (rms > s.noiseFloor * 1.5) {
          s.analyser.getFloatTimeDomainData(s.timeDomainData)
          periodicityReadings.push(computePeriodicity(s.timeDomainData, s.audioCtx.sampleRate))
        }
        setCalibProgress(Math.min(1, elapsed / LOUD_MS))
        if (elapsed < LOUD_MS) {
          requestAnimationFrame(loudStep)
        } else {
          const { minPeriodicity, maxPeriodicity } = personalizeVoicingRange(periodicityReadings)
          s.minPeriodicity = minPeriodicity
          s.maxPeriodicity = maxPeriodicity
          finishCalibration()
        }
      }
      requestAnimationFrame(loudStep)
    }

    requestAnimationFrame(quietStep)
  }

  function finishCalibration() {
    setScreen('playing')
    setHudVisible(true)
    const s = stateRef.current
    s.angle = 0; s.speed = 0; s.bubblesSpawned = 0; s.bubbles = []; s.hasFinished = false; s.sustainedSeconds = 0
    s.spawnedThisWindow = []
    s.lastFrameTime = performance.now()
    s.attemptStartTime = performance.now()
    setAriaMsg('Ready! Say a long "yaaa" to blow bubbles.')
    rafRef.current = requestAnimationFrame(gameLoop)
    startVerificationWindow()
  }

  // One backend event per sustained stretch of "ya" voicing, scored on the
  // real average voicing quality (periodicity/pitch match), not on how long
  // filling the whole sky took.
  async function logVoicingAttempt(scores) {
    const s = stateRef.current
    if (scores.length < MIN_VOICING_FRAMES) return
    const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length
    s.attemptNumber++
    try {
      await logEvent({ level_id: LEVEL_ID, attempt_number: s.attemptNumber, score: avgScore, is_valid_attempt: true })
    } catch (err) {
      console.warn('Backend event logging unavailable:', err)
    }
  }

  // Garden-completion pacing only: asks the difficulty agent whether to
  // raise/lower the target bubble count. timeToWinSeconds is a local signal
  // only — never sent to the backend as "score".
  async function updateDifficultyFromAttempt(timeToWinSeconds) {
    const s = stateRef.current
    let decision = null
    try {
      decision = await getAgentDecision(LEVEL_ID, AGENT_POLICY)
    } catch (err) {
      console.warn('Trained-agent endpoint unavailable, falling back to local rule-based agent:', err)
    }
    if (!decision) decision = DIFFICULTY_AGENT.decide(timeToWinSeconds)

    s.targetBubbles = DIFFICULTY_AGENT.apply(s.targetBubbles, decision)
    setAgentFeedback(decision.message)
  }

  function spawnBubble(index) {
    const s = stateRef.current
    const bubble = {
      x: s.W / 2 + (Math.random() - 0.5) * 40, y: s.H * 0.85,
      r: Math.random() * 22 + 32,
      vy: -(0.35 + Math.random() * 0.3),
      swayPhase: Math.random() * Math.PI * 2, swayAmount: Math.random() * 22 + 12,
      shimmerPhase: Math.random() * Math.PI * 2,
      hue: index / s.bubbleNotes.length,
    }
    s.bubbles.push(bubble)
    s.spawnedThisWindow.push(bubble)
    playBubbleNote(index)
  }

  // Records a rolling ~2s clip of whatever the mic hears, independent of the
  // client-side periodicity detector above. Bubbles have already been spawning
  // for the whole window (for snappy feedback — see gameLoop), but that spawn
  // isn't "confirmed" until this resolves: only bubbles spawned during a
  // window backed by a real "ya" attempt get to stay in the sky.
  function startVerificationWindow() {
    const s = stateRef.current
    if (s.hasFinished || !s.mediaStream) return

    s.spawnedThisWindow = []

    const chunks = []
    let recorder
    try {
      recorder = new MediaRecorder(s.mediaStream, { mimeType: 'audio/webm;codecs=opus' })
    } catch (err) {
      console.warn('MediaRecorder unavailable, skipping speech verification for this window:', err)
      return
    }
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }
    recorder.onstop = () => finishVerificationWindow(chunks)
    s.mediaRecorderRef = recorder
    recorder.start()
    s.verifyTimer = setTimeout(() => {
      if (recorder.state !== 'inactive') recorder.stop()
    }, VERIFY_WINDOW_MS)
  }

  async function finishVerificationWindow(chunks) {
    const s = stateRef.current
    const spawned = s.spawnedThisWindow

    if (spawned.length > 0 && chunks.length > 0) {
      const blob = new Blob(chunks, { type: 'audio/webm;codecs=opus' })
      let transcript = ''
      try {
        const res = await transcribeAudio(blob)
        transcript = res.transcript || ''
      } catch (err) {
        console.warn('Backend transcription unavailable — window left unverified, provisional bubbles stand:', err)
        transcript = null
      }
      // An empty-but-successful transcript is common for a real "ya" — Whisper
      // often can't render a short glide+vowel as text at all, even when it
      // was said perfectly. Only retract when we got a real, non-empty
      // transcript that clearly isn't "ya"; a failed request or a blank
      // result is treated as unverifiable, not as proof the sound was wrong.
      if (transcript !== null && transcript.trim() && !isYaSound(transcript)) {
        // Un-spawn exactly the bubbles this window optimistically added — by
        // reference, not by count, so a bubble from an already-confirmed
        // earlier window can never accidentally get swept up here.
        s.bubbles = s.bubbles.filter(b => !spawned.includes(b))
        s.bubblesSpawned = Math.max(0, s.bubblesSpawned - spawned.length)
        s.sustainedSeconds = 0
        playRetract()
        setAriaMsg('That wasn\'t quite a "yaaa" — try again!')
      }
    }

    // Only check garden completion here, after this window's bubble count is
    // final — not the instant a provisional spawn hits targetBubbles in
    // gameLoop, since those bubbles could still get taken back moments later.
    if (s.bubblesSpawned >= s.targetBubbles && !s.hasFinished) {
      s.hasFinished = true
      onGardenSuccess()
      return
    }
    if (!s.hasFinished) startVerificationWindow()
  }

  function gameLoop(now) {
    const s = stateRef.current
    const dt = Math.min(0.1, (now - s.lastFrameTime) / 1000)
    s.lastFrameTime = now

    const rms = readCurrentRMS()
    s.analyser.getFloatTimeDomainData(s.timeDomainData)
    const periodicity = computePeriodicity(s.timeDomainData, s.audioCtx.sampleRate)
    const { score, isValidAttempt } = computeVoicingScore(rms, periodicity, s.noiseFloor, s.minPeriodicity, s.maxPeriodicity)
    s.smoothedScore = s.smoothedScore * 0.7 + score * 0.3

    // Track sustained voicing duration BEFORE computing rotation, so this
    // frame's boost reflects voicing held up to (not including) this frame —
    // matches Rocket Launch / Submarine Dive's ordering exactly.
    if (isValidAttempt && score > 0.05) {
      s.sustainedSeconds += dt
    } else {
      s.sustainedSeconds = 0
    }

    const result = updateChimeRotation(s.angle, s.speed, score, dt, ROTATION_CONFIG, s.sustainedSeconds)
    s.angle = result.angle; s.speed = result.speed
    if (result.chimesRung > 0 && s.bubblesSpawned < s.targetBubbles) {
      for (let i = 0; i < result.chimesRung && s.bubblesSpawned < s.targetBubbles; i++) {
        spawnBubble(s.bubblesSpawned)
        s.bubblesSpawned++
      }
    }

    // Track sustained voicing segments for real per-attempt logging.
    if (isValidAttempt && score > 0.05) {
      s.inVoicing = true
      s.voicingScores.push(score)
    } else if (s.inVoicing) {
      logVoicingAttempt(s.voicingScores)
      s.inVoicing = false
      s.voicingScores = []
    }

    if (score < 0.1) s.quietStreak += dt; else s.quietStreak = 0
    setEncourageVisible(s.quietStreak > 3 && s.bubblesSpawned < 1)

    render()

    // Garden completion is checked in finishVerificationWindow, not here — a
    // provisional bubble count that hits targetBubbles this frame might
    // still get taken back once that window's transcript comes back.
    if (!s.hasFinished) rafRef.current = requestAnimationFrame(gameLoop)
  }

  // Marks the level as passed independent of any single attempt's score — bubbles
  // fill up continuously from any nonzero-quality attempt with no hard gate, so
  // no individual logged attempt may ever clear PASS_THRESHOLD even when the
  // garden genuinely fills. levelProgress.js treats this as a pass.
  async function logLevelComplete() {
    const s = stateRef.current
    try {
      await logEvent({ level_id: LEVEL_ID, attempt_number: s.attemptNumber, score: 1, is_valid_attempt: true, action: 'level_complete' })
    } catch (err) {
      console.warn('Backend event logging unavailable:', err)
    }
  }

  function onGardenSuccess() {
    const s = stateRef.current
    const completePromise = logLevelComplete()
    if (s.inVoicing) {
      logVoicingAttempt(s.voicingScores)
      s.inVoicing = false
      s.voicingScores = []
    }
    playSuccessChime()
    setAriaMsg('You filled the sky with bubbles!')
    spawnCelebrationParticles()
    const timeToWinSeconds = (performance.now() - s.attemptStartTime) / 1000
    updateDifficultyFromAttempt(timeToWinSeconds)
    let frames = 0
    function celebrateLoop() {
      render()
      frames++
      if (frames < 90) requestAnimationFrame(celebrateLoop)
    }
    requestAnimationFrame(celebrateLoop)
    // Show the success screen (with its "Next Level" button) only once the
    // level_complete write has actually landed -- and always wait at least
    // 500ms so the celebration doesn't feel instant/jarring. Racing the two
    // is what let a kid tap "Next Level" before the backend event committed,
    // which then bounced them at RequireLevelUnlocked and made it look like
    // the level "needed to be played twice."
    Promise.all([
      completePromise,
      new Promise(resolve => setTimeout(resolve, 500)),
    ]).then(() => setSuccessVisible(true))
  }

  function spawnCelebrationParticles() {
    const s = stateRef.current
    const count = reduceMotionRef.current ? 16 : 50
    for (let i = 0; i < count; i++) {
      s.particles.push({
        x: s.W / 2, y: s.H * 0.35,
        vx: (Math.random() - 0.5) * 6, vy: (Math.random() - 0.5) * 6 - 1,
        life: 1, color: ['#FFD166', '#A6E8FF', '#7B5EA7', '#FFF8EC'][i % 4],
        r: Math.random() * 3 + 2,
      })
    }
  }

  function render() {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const s = stateRef.current
    const grad = ctx.createLinearGradient(0, 0, 0, s.H)
    grad.addColorStop(0, '#4A3B7C'); grad.addColorStop(0.5, '#7B5EA7'); grad.addColorStop(1, '#2A2158')
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, s.W, s.H)
    drawMoon(ctx, s)
    drawStars(ctx, s)
    drawFireflies(ctx, s)
    drawParticles(ctx, s)
    drawFloatingBubbles(ctx, s)
    drawGardenSilhouette(ctx, s)
    drawWand(ctx, s)
  }

  function drawMoon(ctx, s) {
    ctx.save()
    const mx = s.W * 0.82, my = s.H * 0.14, r = 30
    ctx.globalAlpha = 0.9
    ctx.fillStyle = '#FFF3D6'
    ctx.beginPath(); ctx.arc(mx, my, r, 0, Math.PI * 2); ctx.fill()
    ctx.globalCompositeOperation = 'destination-out'
    ctx.beginPath(); ctx.arc(mx - r * 0.4, my - r * 0.15, r * 0.9, 0, Math.PI * 2); ctx.fill()
    ctx.restore()
  }

  const starTimeRef = useRef(0)
  function drawStars(ctx, s) {
    if (!reduceMotionRef.current) starTimeRef.current += 0.016
    ctx.save()
    for (const star of s.stars) {
      ctx.globalAlpha = 0.5 + 0.5 * Math.sin(starTimeRef.current + star.phase)
      ctx.fillStyle = '#FFF8EC'
      ctx.beginPath(); ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2); ctx.fill()
    }
    ctx.restore()
  }

  function drawFireflies(ctx, s) {
    ctx.save()
    for (const f of s.fireflies) {
      if (!reduceMotionRef.current) {
        f.phase += 0.03; f.driftPhase += 0.008
        f.y -= f.speed * 0.15
        if (f.y < s.H * 0.35) f.y = s.H * 0.95
      }
      const bx = f.x + Math.sin(f.driftPhase) * 18
      const glow = 0.35 + 0.65 * Math.max(0, Math.sin(f.phase))
      const g = ctx.createRadialGradient(bx, f.y, 0, bx, f.y, 7)
      g.addColorStop(0, `rgba(255, 245, 180, ${0.8 * glow})`)
      g.addColorStop(1, 'rgba(255, 245, 180, 0)')
      ctx.fillStyle = g
      ctx.beginPath(); ctx.arc(bx, f.y, 7, 0, Math.PI * 2); ctx.fill()
      ctx.fillStyle = `rgba(255, 255, 230, ${glow})`
      ctx.beginPath(); ctx.arc(bx, f.y, 1.5, 0, Math.PI * 2); ctx.fill()
    }
    ctx.restore()
  }

  function drawParticles(ctx, s) {
    ctx.save()
    s.particles = s.particles.filter(p => p.life > 0)
    for (const p of s.particles) {
      p.x += p.vx; p.y += p.vy; p.vy += 0.05; p.life -= 0.014
      ctx.globalAlpha = Math.max(0, p.life)
      ctx.fillStyle = p.color
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill()
    }
    ctx.restore()
  }

  function drawGardenSilhouette(ctx, s) {
    ctx.save()
    ctx.fillStyle = 'rgba(20, 15, 45, 0.75)'
    ctx.beginPath()
    ctx.moveTo(0, s.H)
    ctx.lineTo(0, s.H * 0.93)
    for (let x = 0; x <= s.W; x += s.W / 12) {
      const bumpH = 18 + 14 * Math.sin(x * 0.02 + 1.5)
      ctx.quadraticCurveTo(x + s.W / 24, s.H * 0.93 - bumpH, x + s.W / 12, s.H * 0.93)
    }
    ctx.lineTo(s.W, s.H)
    ctx.closePath()
    ctx.fill()

    const flowerXs = [s.W * 0.15, s.W * 0.32, s.W * 0.68, s.W * 0.85]
    for (const fx of flowerXs) {
      const fy = s.H * 0.9
      ctx.strokeStyle = 'rgba(20, 15, 45, 0.75)'; ctx.lineWidth = 3
      ctx.beginPath(); ctx.moveTo(fx, fy + 14); ctx.lineTo(fx, fy - 6); ctx.stroke()
      ctx.fillStyle = 'rgba(166, 232, 255, 0.5)'
      for (let i = 0; i < 5; i++) {
        const angle = (i / 5) * Math.PI * 2
        ctx.beginPath()
        ctx.ellipse(fx + Math.cos(angle) * 6, fy - 6 + Math.sin(angle) * 6, 4, 2.5, angle, 0, Math.PI * 2)
        ctx.fill()
      }
    }
    ctx.restore()
  }

  function drawFloatingBubbles(ctx, s) {
    ctx.save()
    for (const b of s.bubbles) {
      if (!reduceMotionRef.current) { b.y += b.vy; b.swayPhase += 0.02; b.shimmerPhase += 0.03 }
      const sway = Math.sin(b.swayPhase) * b.swayAmount
      const bx = b.x + sway, by = b.y
      const shimmer = Math.sin(b.shimmerPhase) * 25

      const bubbleGrad = ctx.createRadialGradient(bx - b.r * 0.3, by - b.r * 0.3, b.r * 0.1, bx, by, b.r)
      bubbleGrad.addColorStop(0, 'rgba(255,255,255,0.9)')
      bubbleGrad.addColorStop(0.45, `hsla(${185 + b.hue * 90 + shimmer}, 95%, 82%, 0.5)`)
      bubbleGrad.addColorStop(0.8, `hsla(${260 + b.hue * 60 - shimmer}, 90%, 75%, 0.35)`)
      bubbleGrad.addColorStop(1, 'rgba(255,255,255,0.12)')
      ctx.fillStyle = bubbleGrad
      ctx.beginPath(); ctx.arc(bx, by, b.r, 0, Math.PI * 2); ctx.fill()

      ctx.strokeStyle = `hsla(${200 + shimmer}, 100%, 90%, 0.6)`
      ctx.lineWidth = 1.3
      ctx.stroke()

      ctx.fillStyle = 'rgba(255,255,255,0.85)'
      ctx.beginPath(); ctx.ellipse(bx - b.r * 0.35, by - b.r * 0.35, b.r * 0.2, b.r * 0.12, -0.5, 0, Math.PI * 2); ctx.fill()
      ctx.fillStyle = 'rgba(255,255,255,0.4)'
      ctx.beginPath(); ctx.ellipse(bx + b.r * 0.3, by + b.r * 0.25, b.r * 0.12, b.r * 0.08, 0.3, 0, Math.PI * 2); ctx.fill()
    }
    ctx.restore()
  }

  function drawWand(ctx, s) {
    const wandX = s.W / 2, wandY = s.H * 0.9
    const pulse = 1 + s.smoothedScore * 0.35
    ctx.save()
    ctx.translate(wandX, wandY)

    const handleGrad = ctx.createLinearGradient(0, 34, 0, 6)
    handleGrad.addColorStop(0, '#C99A2E'); handleGrad.addColorStop(1, '#FFD166')
    ctx.strokeStyle = handleGrad; ctx.lineWidth = 6; ctx.lineCap = 'round'
    ctx.beginPath(); ctx.moveTo(0, 34); ctx.lineTo(0, 4); ctx.stroke()

    ctx.save()
    ctx.scale(pulse, pulse)
    ctx.strokeStyle = '#FFD166'; ctx.lineWidth = 3
    ctx.beginPath(); ctx.ellipse(0, -10, 20, 13, 0, 0, Math.PI * 2); ctx.stroke()
    if (s.smoothedScore > 0.1) {
      const shimmerAngle = (performance.now() * 0.05) % 360
      const filmGrad = ctx.createRadialGradient(-4, -14, 1, 0, -10, 16)
      filmGrad.addColorStop(0, `hsla(${190 + shimmerAngle}, 90%, 85%, 0.5)`)
      filmGrad.addColorStop(1, 'rgba(255,255,255,0.05)')
      ctx.fillStyle = filmGrad
      ctx.beginPath(); ctx.ellipse(0, -10, 19, 12, 0, 0, Math.PI * 2); ctx.fill()
    }
    ctx.restore()
    ctx.restore()
  }

  function handlePlayAgain() {
    const s = stateRef.current
    setSuccessVisible(false)
    s.angle = 0; s.speed = 0; s.bubblesSpawned = 0; s.bubbles = []; s.hasFinished = false; s.particles = []; s.sustainedSeconds = 0
    s.spawnedThisWindow = []
    s.lastFrameTime = performance.now()
    s.attemptStartTime = performance.now()
    rafRef.current = requestAnimationFrame(gameLoop)
    startVerificationWindow()
  }

  function handleRecalibrate() {
    setSettingsOpen(false)
    setHudVisible(false)
    cancelAnimationFrame(rafRef.current)
    clearTimeout(stateRef.current.verifyTimer)
    if (stateRef.current.mediaRecorderRef && stateRef.current.mediaRecorderRef.state !== 'inactive') {
      try { stateRef.current.mediaRecorderRef.onstop = null; stateRef.current.mediaRecorderRef.stop() } catch { /* already stopped */ }
    }
    runCalibration()
  }

  const circ = 2 * Math.PI * 60

  return (
    <div className="fixed inset-0 bg-[#2A2158] text-[#FFF8EC] overflow-hidden select-none" style={{ fontFamily: "'Quicksand', sans-serif" }}>
      <canvas ref={canvasRef} className="fixed inset-0 w-full h-full block" aria-hidden="true" />

      <button
        onClick={() => navigate('/play/chime')}
        className="fixed top-4 left-4 z-30 flex items-center gap-2 text-white/50 hover:text-white/80 text-sm transition-colors bg-black/20 rounded-full px-3 py-2"
      >
        <ArrowLeft size={16} /> Back
      </button>

      {screen === 'start' && (
        <div className="fixed inset-0 flex flex-col items-center justify-center text-center px-6 z-10">
          <div className="bg-[rgba(42,33,88,0.65)] border border-white/10 rounded-[28px_28px_40px_28px] p-10 max-w-md w-full backdrop-blur-md shadow-2xl">
            <div className="text-6xl mb-3">🫧</div>
            <h1 className="font-['Baloo_2'] text-4xl font-extrabold mb-2">Bubble Garden</h1>
            <p className="text-lg font-bold text-[#FFD166] mb-7 leading-relaxed flex items-center justify-center gap-2 flex-wrap">
              Say a long "yaaa" to blow glowing bubbles into the evening sky!
              <button onClick={replayInstruction} className="text-[#FFD166]/60 hover:text-[#FFD166] transition-colors" aria-label="Hear this again">
                <Volume2 size={18} />
              </button>
            </p>
            <button
              onClick={requestMicAndCalibrate}
              className="font-['Baloo_2'] font-bold text-xl rounded-full px-10 py-4 text-[#2A2158] bg-[#FFD166] shadow-[0_6px_0_#C99A2E] hover:-translate-y-0.5 transition-transform"
            >
              Let's Play!
            </button>
          </div>
        </div>
      )}

      {screen === 'micError' && (
        <div className="fixed inset-0 flex flex-col items-center justify-center text-center px-6 z-10">
          <div className="bg-[rgba(42,33,88,0.65)] border border-white/10 rounded-[28px_28px_40px_28px] p-10 max-w-md w-full backdrop-blur-md shadow-2xl">
            <div className="text-6xl mb-3">🎤</div>
            <h1 className="font-['Baloo_2'] text-2xl font-extrabold mb-2">We need to hear you!</h1>
            <p className="text-sm text-[#FFD3D3] mb-5">{micErrorMsg}</p>
            <button onClick={requestMicAndCalibrate} className="font-['Baloo_2'] font-bold text-xl rounded-full px-10 py-4 text-[#2A2158] bg-[#FFD166] shadow-[0_6px_0_#C99A2E]">
              Try Again
            </button>
          </div>
        </div>
      )}

      {screen === 'calibrate' && (
        <div className="fixed inset-0 flex flex-col items-center justify-center text-center px-6 z-10">
          <div className="bg-[rgba(42,33,88,0.65)] border border-white/10 rounded-[28px_28px_40px_28px] p-10 max-w-md w-full backdrop-blur-md shadow-2xl">
            <div className="relative w-[150px] h-[150px] mx-auto mb-5">
              <svg width="150" height="150" className="-rotate-90 overflow-visible">
                <circle cx="75" cy="75" r="60" fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth="14" />
                <circle cx="75" cy="75" r="60" fill="none" stroke="#FFD166" strokeWidth="14" strokeLinecap="round"
                  strokeDasharray={circ} strokeDashoffset={circ * (1 - calibProgress)}
                  style={{ transition: 'stroke-dashoffset 0.08s linear', filter: 'drop-shadow(0 0 8px rgba(255,209,102,0.85))' }} />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center text-3xl">{calibLabel.emoji}</div>
            </div>
            <h1 className="font-['Baloo_2'] text-2xl font-extrabold mb-2">{calibLabel.title}</h1>
            <p className="text-lg font-bold text-[#FFD166]">{calibLabel.subtitle}</p>
          </div>
        </div>
      )}

      {hudVisible && (
        <div className="fixed top-0 left-0 right-0 flex justify-between items-start px-5 py-4 z-20">
          <div
            className={`font-bold text-lg bg-[rgba(42,33,88,0.65)] border border-white/10 rounded-full px-6 py-2.5 backdrop-blur-md max-w-[70vw] transition-opacity ${encourageVisible ? 'opacity-100' : 'opacity-0'}`}
          >
            Try a long "yaaa" sound, nice and clear!
          </div>
          <button
            onClick={() => setSettingsOpen(v => !v)}
            className="w-[46px] h-[46px] rounded-full bg-[rgba(42,33,88,0.65)] border border-white/10 flex items-center justify-center backdrop-blur-md shadow-lg"
            aria-label="Settings"
          >
            <Settings size={20} />
          </button>
        </div>
      )}

      {settingsOpen && (
        <div className="fixed top-[74px] right-[18px] bg-[rgba(42,33,88,0.65)] border border-white/10 rounded-[20px_20px_28px_20px] p-5 z-30 w-[240px] text-left backdrop-blur-md shadow-2xl">
          <h3 className="font-extrabold mb-3">Settings</h3>
          <label className="flex items-center justify-between mb-3 font-bold text-sm cursor-pointer">
            <span>Reduce motion</span>
            <input type="checkbox" checked={reduceMotion} onChange={e => setReduceMotion(e.target.checked)} className="accent-[#3E6B4F]" />
          </label>
          <label className="flex items-center justify-between mb-3 font-bold text-sm cursor-pointer">
            <span>Mute sounds</span>
            <input type="checkbox" checked={muted} onChange={e => setMuted(e.target.checked)} className="accent-[#3E6B4F]" />
          </label>
          <button onClick={handleRecalibrate} className="w-full mt-1 text-sm border border-white/20 rounded-full px-4 py-2.5">
            Recalibrate mic
          </button>
        </div>
      )}

      {successVisible && (
        <div className="fixed inset-0 flex items-center justify-center z-40 bg-[rgba(42,33,88,0.4)]">
          <div className="bg-[rgba(42,33,88,0.65)] border border-white/10 rounded-[28px_28px_40px_28px] p-10 max-w-md w-full text-center backdrop-blur-md shadow-2xl">
            <div className="text-6xl mb-3">🫧</div>
            <h1 className="font-['Baloo_2'] text-3xl font-extrabold mb-2">Garden full of bubbles!</h1>
            <p className="text-lg font-bold text-[#FFD166] mb-1">You filled the evening sky with glowing bubbles!</p>
            {agentFeedback && <p className="text-sm opacity-85 mb-5">{agentFeedback}</p>}
            <div className="flex flex-col gap-3 items-center">
              {getNextLevelRoute(LEVEL_ID) && (
                <button
                  onClick={() => navigate(getNextLevelRoute(LEVEL_ID))}
                  className="font-['Baloo_2'] font-bold text-xl rounded-full px-10 py-4 text-[#2A2158] bg-[#FFD166] shadow-[0_6px_0_#C99A2E] hover:-translate-y-0.5 transition-transform"
                >
                  Next Level →
                </button>
              )}
              <button onClick={handlePlayAgain} className="font-bold text-sm text-white/70 hover:text-white/90 underline underline-offset-4">
                Play Again!
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="sr-only" aria-live="polite">{ariaMsg}</div>
    </div>
  )
}
