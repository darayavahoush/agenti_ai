import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Volume2 } from 'lucide-react'
import { sessionsAPI, beaconPost, meAPI } from '../../api/client'
import { BreathEngine } from '../../game/engine/BreathEngine.js'
import { LEVEL_FACTORIES, LEVEL_META } from '../../game/index.js'
import { calcStars, saveScore, loadScores, mergeServerScores, isUnlocked, LEVEL_ORDER } from '../../game/scoring/index.js'
import { getBreathAgentDecision, logBreathEvent, submitEventFeedback } from '../../game/lib/api.js'
import {
  DEFAULT_DIFFICULTY, applyAction, loadStoredDifficulty, saveStoredDifficulty,
  loadAttemptNumber, saveAttemptNumber,
} from '../../game/lib/difficulty.js'
import { useSpokenInstruction } from '../../lib/speech'

const W = 800, H = 580

export default function GamePage() {
  const { levelId } = useParams()
  const navigate    = useNavigate()
  const meta        = LEVEL_META[levelId]

  const canvasRef   = useRef(null)
  const engineRef   = useRef(null)
  const levelRef    = useRef(null)
  const rafRef      = useRef(null)
  const sessionRef  = useRef(null)
  const breathLog   = useRef([])
  const eventBatch  = useRef([])
  const flushTimer  = useRef(null)
  const breatheTimer = useRef(null)
  const breatheMaxTimer = useRef(null)
  const breatheSpeechDone = useRef(false)
  const breatheMinElapsed = useRef(false)
  const breatheStarted = useRef(false)
  // Always points at the CURRENT render's maybeBeginPlaying. onBreatheSpeechEnd
  // below is memoized with [] (useSpokenInstruction fires it from a speech
  // event, long after the render that created it), so calling
  // maybeBeginPlaying directly there would keep running the FIRST level's
  // closures (levelId, startGameLoop, complete) after "Next Level ->"
  // reuses this same component instance for a different :levelId.
  const maybeBeginPlayingRef = useRef(() => {})
  const lastTime    = useRef(null)
  const metricsRef  = useRef({ timeSeconds: 0, mistakes: 0, targetHits: 0, puffs: 0, progress: 0 })
  const startTime   = useRef(null)
  const difficultyRef = useRef(DEFAULT_DIFFICULTY)
  // Synchronous re-entry guard for startGame -- phase stays 'ready' through
  // the first await (sessionsAPI.start), so the Start button has no state-based
  // way to disable itself in time to block a fast double-click, which would
  // otherwise create two sessions via sessionsAPI.start. A ref check/set
  // happens on the same tick as the click, before any await, so it can't race.
  const startingRef = useRef(false)

  const [phase,       setPhase]       = useState('ready')
  const [errorReason, setErrorReason] = useState(null) // 'session' | 'mic' | null
  const [calProgress, setCalProgress] = useState(0)
  const [result,      setResult]      = useState(null)
  const [earnedStars, setEarnedStars] = useState(0)
  const [starAnim,    setStarAnim]    = useState(0)
  // RLTrainingEvent id for the level just completed, once logBreathEvent
  // resolves -- null until then, which the feedback chip uses to decide
  // whether it has anything to attach to yet.
  const [rlEventId,     setRlEventId]     = useState(null)
  const [feedbackGiven, setFeedbackGiven] = useState(null)
  // Plain-language line from the adaptive-difficulty agent's own decision
  // (agent/service.py's get_status/decide messages -- already kid-safe
  // copy, no raw stats). Only shown when the round actually changed
  // something (action !== 'hold'), so it reads as a real callout instead
  // of routine noise every single round.
  const [buddyMessage, setBuddyMessage] = useState(null)
  const [buddyAction, setBuddyAction] = useState(null) // 'raise' | 'lower' | null -- drives the pill's color, so it's never guessed from message text
  const [debug,       setDebug]       = useState({ raw: 0, floor: 0, above: 0, breath: 0 })

  // Check unlock. Seeded from whatever this browser's localStorage cache
  // already has so there's no loading flicker on a returning device, then
  // reconciled against the server's real per-level history right after --
  // a fresh device/cleared browser/private mode used to mean this cache
  // was empty and every level looked locked again despite the server
  // remembering everything (see mergeServerScores).
  const [scores, setScores] = useState(() => loadScores())
  useEffect(() => {
    meAPI.breathquestLevelScores()
      .then(({ data }) => setScores(mergeServerScores(data)))
      .catch(() => {})
  }, [])
  const unlocked = isUnlocked(levelId, scores)
  const bestStars = scores[levelId]?.stars || 0

  // Verbal instructions: speak the level's tagline once each time the
  // "ready" screen is (re-)entered (only once it's actually unlocked — no
  // point narrating a level the kid can't play yet), and the breathe-in
  // cue once each time that phase comes up — it recurs every attempt, and
  // useSpokenInstruction correctly re-speaks on every re-entry into an
  // enabled state, not just the first time ever (see its doc comment).
  const replayReady = useSpokenInstruction(meta?.tagline, { enabled: phase === 'ready' && unlocked })
  // Real (scored) gameplay used to start on a flat 2200ms timer that raced
  // this sentence's actual read-aloud length -- on a slower device voice
  // the exhale window could start scoring while the cue was still talking.
  // beginPlaying (below) now waits for this callback (real speech
  // completion, not a guess) AND a minimum floor, with a safety cap in
  // case a browser never fires the completion event at all.
  const onBreatheSpeechEnd = useCallback(() => {
    breatheSpeechDone.current = true
    maybeBeginPlayingRef.current()
  }, [])
  const replayBreathe = useSpokenInstruction(
    'Take a big breath in! Fill up your belly like a balloon, then get ready to blow.',
    { enabled: phase === 'breathe', onEnd: onBreatheSpeechEnd },
  )

  // beginPlaying is the single place real (scored) gameplay actually
  // starts, guarded so it only ever fires once per breathe-in cue no
  // matter which of the two paths below reaches it first.
  const beginPlaying = () => {
    if (breatheStarted.current) return
    breatheStarted.current = true
    clearTimeout(breatheTimer.current)
    clearTimeout(breatheMaxTimer.current)
    setPhase('playing')
    startTime.current = performance.now()
    startGameLoop()
    flushTimer.current = setInterval(flushEvents, 2500)
  }
  // Only actually begins once the breathe-in cue has genuinely finished
  // AND a minimum floor has elapsed (so it never feels instant on a
  // device where TTS is unavailable/silent and onEnd fires immediately).
  const maybeBeginPlaying = () => {
    if (breatheSpeechDone.current && breatheMinElapsed.current) beginPlaying()
  }
  useEffect(() => { maybeBeginPlayingRef.current = maybeBeginPlaying })

  const startGame = async () => {
    if (!unlocked) return
    if (startingRef.current) return
    startingRef.current = true
    try {
      const { data } = await sessionsAPI.start({ level_id: levelId })
      sessionRef.current = data.id
    } catch {
      // Session creation failed - bail instead of playing a session-less
      // round that would score the kid but never write to
      // rl_training_events (start/end/logEvents all silently no-op on an
      // undefined session id). Surface it as the existing 'error' phase so
      // GamePage's error UI (whatever that already renders) picks it up.
      setErrorReason('session')
      setPhase('error')
      startingRef.current = false
      return
    }

    // Ask the same adaptive-difficulty agent Chime's phoneme levels use
    // (routers/breath_agent.py -> agent.service.AgentService) whether to
    // raise/hold/lower this level's difficulty, then nudge our locally
    // stored value accordingly. Falls back to last-known difficulty if the
    // backend call fails, so a flaky connection never blocks play.
    const priorDifficulty = loadStoredDifficulty(levelId)
    let nextDifficulty = priorDifficulty
    try {
      const decision = await getBreathAgentDecision(levelId)
      nextDifficulty = applyAction(priorDifficulty, decision.action)
      setBuddyMessage(decision.action !== 'hold' ? decision.message : null)
      setBuddyAction(decision.action !== 'hold' ? decision.action : null)
    } catch {}
    difficultyRef.current = nextDifficulty
    saveStoredDifficulty(levelId, nextDifficulty)

    const engine = new BreathEngine()
    engineRef.current = engine

    engine.onCalibrated = () => {
      // Give the kid a beat to take a big breath in before the level starts
      // scoring their exhale — the in-breath is what actually powers a
      // strong, controlled out-breath, so cueing it explicitly matters more
      // here than in a typical "ready, set, go" countdown.
      //
      // This used to be a flat setTimeout(2200) with no relationship at
      // all to how long "Take a big breath in..." actually takes a given
      // device's voice to read -- real scoring (startGameLoop) could and
      // did start while the cue was still talking. Now it waits for the
      // real completion signal from useSpokenInstruction's onEnd (see
      // onBreatheSpeechEnd above), gated by a floor so a silent/unavailable
      // TTS engine doesn't make the screen feel instant, and a safety cap
      // in case a browser never fires the completion event at all (real,
      // known Web Speech API flakiness -- see lib/speech.js).
      breatheStarted.current = false
      breatheSpeechDone.current = false
      breatheMinElapsed.current = false
      setPhase('breathe')
      breatheTimer.current = setTimeout(() => {
        breatheMinElapsed.current = true
        maybeBeginPlaying()
      }, 1200)
      breatheMaxTimer.current = setTimeout(beginPlaying, 6000)
    }

    engine.onBreath = (v) => {
      breathLog.current.push(v)
      eventBatch.current.push({ event_type: 'breath_sample', breath_value: v })
      setDebug({
        raw:   +(engine._lastRaw    || 0).toFixed(3),
        floor: +(engine._baseline   || 0).toFixed(3),
        above: +(Math.max(0,(engine._lastRaw||0)-(engine._baseline||0))).toFixed(3),
        breath: +v.toFixed(3),
      })
    }

    setPhase('calibrating')
    try { await engine.start() }
    catch { setErrorReason('mic'); setPhase('error') }

    const calTick = () => {
      if (engine.calibrating) { setCalProgress(engine.calProgress); requestAnimationFrame(calTick) }
    }
    requestAnimationFrame(calTick)
  }

  const startGameLoop = () => {
    const factory = LEVEL_FACTORIES[levelId]
    if (!factory) { setPhase('error'); return }
    levelRef.current = factory(difficultyRef.current)
    lastTime.current = performance.now()

    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx) return

    const tick = (now) => {
      const dt     = Math.min((now - lastTime.current) / 1000, 0.05)
      lastTime.current = now
      const breath = engineRef.current?.breathValue ?? 0
      const elapsed = (now - startTime.current) / 1000
      metricsRef.current.timeSeconds = elapsed

      const res = levelRef.current.update(breath, dt)
      levelRef.current.draw(ctx, W, H, breath)

      // Draw breath bar overlay on top
      drawBreathOverlay(ctx, W, breath, meta.color)

      if (res) { endGame(res); return }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
  }

  const endGame = useCallback(async (res) => {
    cancelAnimationFrame(rafRef.current)
    clearInterval(flushTimer.current)
    engineRef.current?.stop()
    setRlEventId(null)
    setFeedbackGiven(null)

    const m = metricsRef.current
    // Let level pass its own metrics via result object
    if (res.targetHits !== undefined) m.targetHits = res.targetHits
    if (res.mistakes   !== undefined) m.mistakes   = res.mistakes
    if (res.puffs      !== undefined) m.puffs      = res.puffs
    m.progress = 1

    // Levels that compute their own performance-based star count (all six
    // now do) are authoritative — they have domain knowledge calcStars can't
    // reconstruct from generic metrics. calcStars is the fallback for a level
    // that doesn't report its own stars.
    const stars = res.stars ?? calcStars(levelId, m)
    const updatedLevelScore = saveScore(levelId, stars)
    setScores(prev => ({ ...prev, [levelId]: updatedLevelScore }))
    setEarnedStars(stars)
    setResult(res)
    setPhase('complete')

    // Animate stars in
    let s = 0
    const starInterval = setInterval(() => {
      s++; setStarAnim(s)
      if (s >= stars) clearInterval(starInterval)
    }, 400)

    const log = breathLog.current
    const avg = log.length ? log.reduce((a,b)=>a+b,0)/log.length : 0
    const max = log.length ? Math.max(...log) : 0
    if (sessionRef.current) {
      try {
        await sessionsAPI.end(sessionRef.current, {
          stars_earned: stars, completed: true,
          completion_message: res.message,
          avg_breath_strength: +avg.toFixed(3),
          max_breath_strength: +max.toFixed(3),
        })
      } catch {}
    }

    // Feed this play back to the same adaptive-difficulty agent that just
    // picked this level's difficulty — score is stars/3 so it lines up with
    // the same >=0.6-is-a-success convention Chime's events already use.
    const attemptNumber = loadAttemptNumber(levelId) + 1
    saveAttemptNumber(levelId, attemptNumber)
    try {
      const logged = await logBreathEvent({
        level_id: levelId,
        attempt_number: attemptNumber,
        score: stars / 3,
        is_valid_attempt: true,
        threshold_at_time: difficultyRef.current,
        quit_flag: false,
      })
      setRlEventId(logged?.id ?? null)
    } catch (err) {
      console.error('logBreathEvent failed:', err)
    }
  }, [levelId])

  const flushEvents = async () => {
    const batch = eventBatch.current.splice(0)
    if (batch.length && sessionRef.current) {
      try { await sessionsAPI.logEvents(sessionRef.current, batch) } catch {}
    }
  }

  const cleanup = () => {
    cancelAnimationFrame(rafRef.current)
    clearInterval(flushTimer.current)
    clearTimeout(breatheTimer.current)
    clearTimeout(breatheMaxTimer.current)
    engineRef.current?.stop()
  }

  // Kept in sync with `phase` state so the pagehide handler below — which
  // has to be registered once and can't re-subscribe on every phase change
  // — always reads the *current* phase instead of whatever it was when the
  // listener was first attached.
  const phaseRef = useRef(phase)
  useEffect(() => { phaseRef.current = phase }, [phase])

  // Route reuses this same GamePage instance across levels (React Router
  // doesn't remount on a param change alone), so without this, navigating
  // Dandelion -> Dragon leaves Dandelion's phase/result/stars/metrics still
  // set while only levelId itself has actually updated -- e.g. the
  // 'complete' screen and its earned-star count showing under the new
  // level's header, or a stale breathLog feeding the next level's average.
  // cleanup() alone isn't enough here: it only tears down timers/RAF/engine,
  // never this component state.
  useEffect(() => {
    cleanup()
    setPhase('ready')
    setErrorReason(null)
    setCalProgress(0)
    setResult(null)
    setEarnedStars(0)
    setStarAnim(0)
    setBuddyMessage(null)
    setBuddyAction(null)
    setDebug({ raw: 0, floor: 0, above: 0, breath: 0 })
    setRlEventId(null)
    setFeedbackGiven(null)
    breathLog.current = []
    eventBatch.current = []
    metricsRef.current = { timeSeconds: 0, mistakes: 0, targetHits: 0, puffs: 0, progress: 0 }
    breatheSpeechDone.current = false
    breatheMinElapsed.current = false
    breatheStarted.current = false
    sessionRef.current = null
    levelRef.current = null
    startingRef.current = false
  }, [levelId])

  // Backing out mid-level (or the tab just closing — see the pagehide
  // handler below) is a real signal for the difficulty agent, same idea as
  // the quit_flag Chime logs. This used to only log the agent event and
  // never actually closed the GameSession row itself, leaving it open
  // forever (started_at set, ended_at null) — skewing completion-rate
  // stats and the weekly summary. Now closes both.
  const logQuitIfPlaying = () => {
    if (phase !== 'playing' && phase !== 'breathe' && phase !== 'calibrating') return
    if (sessionRef.current) {
      sessionsAPI.end(sessionRef.current, { stars_earned: 0, completed: false }).catch(() => {})
    }
    const attemptNumber = loadAttemptNumber(levelId) + 1
    saveAttemptNumber(levelId, attemptNumber)
    logBreathEvent({
      level_id: levelId,
      attempt_number: attemptNumber,
      score: 0,
      is_valid_attempt: false,
      threshold_at_time: difficultyRef.current,
      quit_flag: true,
    }).catch(err => console.error('logBreathEvent (quit) failed:', err))
  }

  // The above only covers backing out *within* the SPA. If the kid just
  // closes the tab, hits browser-back off the site, or the browser dies,
  // neither logQuitIfPlaying nor any other in-app handler ever runs — a
  // regular axios call gets cancelled mid-flight the instant the page
  // unloads. `pagehide` + a keepalive beacon is the one combination
  // browsers guarantee still gets sent after the page is gone.
  useEffect(() => {
    const handlePageHide = () => {
      const p = phaseRef.current
      if (p !== 'playing' && p !== 'breathe' && p !== 'calibrating') return
      if (sessionRef.current) {
        beaconPost(`/sessions/${sessionRef.current}/end`, { stars_earned: 0, completed: false })
      }
      const attemptNumber = loadAttemptNumber(levelId) + 1
      saveAttemptNumber(levelId, attemptNumber)
      beaconPost('/breath/events', {
        level_id: levelId,
        attempt_number: attemptNumber,
        score: 0,
        is_valid_attempt: false,
        threshold_at_time: difficultyRef.current,
        quit_flag: true,
      })
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [levelId])

  const replay = () => {
    cleanup()
    breathLog.current = []; eventBatch.current = []
    metricsRef.current = { timeSeconds:0, mistakes:0, targetHits:0, puffs:0, progress:0 }
    setPhase('ready'); setResult(null); setStarAnim(0); setBuddyMessage(null); setBuddyAction(null); startingRef.current = false
  }

  useEffect(() => () => cleanup(), [])

  // GamePage stays mounted when navigating from one level to the next
  // (route param change only, e.g. clicking "Next Level" on the result
  // screen) — React Router doesn't remount the component just because
  // :levelId changed. `meta`/`nextId`/etc. are derived fresh from levelId
  // each render, so the header and button labels update correctly, but
  // `phase`/`result`/`earnedStars` are state and silently carried over
  // from the level just finished. That left the result screen stuck
  // showing the *previous* level's completion state forever — the header
  // says the new level, but nothing ever actually starts it, and clicking
  // "Next Level" again just advances levelId further without ever playing
  // anything in between. Reset everything the same way `replay()` does
  // whenever levelId changes (this also fires harmlessly on first mount).
  useEffect(() => {
    cleanup()
    breathLog.current = []; eventBatch.current = []
    metricsRef.current = { timeSeconds: 0, mistakes: 0, targetHits: 0, puffs: 0, progress: 0 }
    setPhase('ready'); setResult(null); setStarAnim(0); setBuddyMessage(null); setBuddyAction(null); startingRef.current = false
    setEarnedStars(0); setErrorReason(null); setCalProgress(0)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [levelId])

  if (!meta) return <div className="text-white p-8">Unknown level</div>

  // Find next level
  const curIdx  = LEVEL_ORDER.indexOf(levelId)
  const nextId  = LEVEL_ORDER[curIdx + 1]

  return (
    <div className="min-h-screen flex flex-col bg-brand-dark">
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 flex-shrink-0">
        <button onClick={() => { logQuitIfPlaying(); cleanup(); navigate('/play/levels') }}
                className="text-white/40 hover:text-white/70 text-sm transition-colors">
          ← Levels
        </button>
        <span className="font-display font-bold text-white">{meta.emoji} {meta.name}</span>
        <div className="flex items-center gap-2">
          {bestStars > 0 && (
            <span className="text-xs text-brand-amber">Best: {'★'.repeat(bestStars)}{'☆'.repeat(3-bestStars)}</span>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-4">
        <div className="relative w-full" style={{ maxWidth: W }}>

          {/* Canvas */}
          <canvas ref={canvasRef} width={W} height={H}
            className="rounded-2xl shadow-2xl w-full"
            style={{ display: phase === 'playing' ? 'block' : 'none' }} />

          {/* READY */}
          {phase === 'ready' && (
            <div className="flex flex-col items-center justify-center text-center py-16 rounded-2xl"
                 style={{ minHeight: H, background: 'linear-gradient(135deg, #1a1a2e, #12122A)',
                          border: `2px solid ${meta.color}33` }}>
              <div className="text-8xl mb-5" style={{ animation: 'float 3s ease-in-out infinite' }}>
                {meta.emoji}
              </div>
              <h2 className="font-display text-4xl font-black text-white mb-1">{meta.name}</h2>
              <p className="text-white/40 mb-2 flex items-center justify-center gap-1.5">
                {meta.tagline}
                <button onClick={replayReady} className="text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-full p-1.5 active:scale-90 transition-colors" aria-label="Hear this again">
                  <Volume2 size={16} />
                </button>
              </p>

              {!unlocked ? (
                <div className="mt-6 text-center">
                  <div className="text-5xl mb-3">🔒</div>
                  <p className="text-white/50">Complete the previous level first!</p>
                  <button onClick={() => navigate('/play/levels')}
                    className="mt-4 px-6 py-2 rounded-xl border border-white/20 text-white/60 hover:bg-white/10 text-sm">
                    Back to levels
                  </button>
                </div>
              ) : (
                <>
                  {bestStars > 0 && (
                    <div className="flex gap-1 mb-6">
                      {Array.from({length:3},(_,i) => (
                        <span key={i} className="text-2xl" style={{ color: i<bestStars ? '#FAC775' : 'rgba(255,255,255,0.15)' }}>★</span>
                      ))}
                    </div>
                  )}
                  <button onClick={startGame}
                    className="px-10 py-4 rounded-2xl font-display text-xl font-black text-brand-dark
                               transition-all active:scale-95 shadow-lg mt-4"
                    style={{ background: meta.color,
                             boxShadow: `0 0 30px ${meta.color}44` }}>
                    🎤 Start!
                  </button>
                  <p className="text-white/20 text-xs mt-4">Allow mic when asked</p>
                </>
              )}
            </div>
          )}

          {/* CALIBRATING */}
          {phase === 'calibrating' && (
            <div className="flex flex-col items-center justify-center text-center py-16 rounded-2xl"
                 style={{ minHeight: H, background: 'linear-gradient(135deg, #1a1a2e, #12122A)' }}>
              <div className="text-7xl mb-6" style={{ animation: 'pulse 1.5s infinite' }}>🎤</div>
              <h2 className="font-display text-3xl font-black text-white mb-2">Getting Ready…</h2>
              <p className="text-white/60 mb-1">Stay <strong className="text-white">completely quiet!</strong> 🤫</p>
              <p className="text-white/30 text-sm mb-8">Don't blow yet — learning your room's sound</p>
              <div className="w-72 h-3 bg-white/10 rounded-full overflow-hidden mb-2">
                <div className="h-full rounded-full transition-all duration-100"
                     style={{ width: `${calProgress * 100}%`, background: meta.color }} />
              </div>
              <p className="text-white/20 text-xs">Filtering background noise…</p>
            </div>
          )}

          {/* BREATHE — cue the inhale before scoring starts */}
          {phase === 'breathe' && (
            <div className="flex flex-col items-center justify-center text-center py-16 rounded-2xl"
                 style={{ minHeight: H, background: 'linear-gradient(135deg, #1a1a2e, #12122A)',
                          border: `2px solid ${meta.color}33` }}>
              <div className="text-8xl mb-6" style={{ animation: 'breatheIn 2.2s ease-in-out' }}>
                👃
              </div>
              <h2 className="font-display text-3xl font-black text-white mb-2">
                Take a big breath in!
              </h2>
              <p className="text-white/40 flex items-center justify-center gap-1.5">
                Fill up your belly like a balloon… then get ready to blow 💨
                <button onClick={replayBreathe} className="text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-full p-1.5 active:scale-90 transition-colors" aria-label="Hear this again">
                  <Volume2 size={16} />
                </button>
              </p>
            </div>
          )}

          {/* COMPLETE */}
          {phase === 'complete' && result && (
            <div className="flex flex-col items-center justify-center text-center py-10 rounded-2xl relative overflow-hidden"
                 style={{ minHeight: H, background: 'linear-gradient(135deg, #0d1a0d, #12122A)',
                          border: '2px solid rgba(168,255,111,0.3)' }}>

              {/* Confetti */}
              {Array.from({length:20},(_,i)=>(
                <div key={i} className="absolute w-3 h-3 rounded-full pointer-events-none"
                     style={{
                       left:`${(i*97+10)%100}%`, top:`${(i*67+5)%100}%`,
                       background:['#A8FF6F','#FAC775','#E24B4A','#60A5FA','#A855F7'][i%5],
                       animation:`float ${1.5+i*0.1}s ease-in-out infinite`,
                       animationDelay:`${i*0.07}s`, opacity: 0.7,
                     }} />
              ))}

              <div className="text-7xl mb-4" style={{ animation: 'float 1s ease-in-out infinite' }}>
                {earnedStars === 3 ? '🏆' : earnedStars === 2 ? '🎉' : '👍'}
              </div>

              <h2 className="font-display text-4xl font-black text-white mb-1">
                {earnedStars === 3 ? 'Perfect!' : earnedStars === 2 ? 'Great job!' : 'Level done!'}
              </h2>
              <p className="text-white/50 mb-6">{result.message}</p>

              {buddyMessage && (
                <div
                  className="flex items-center gap-2.5 mb-6 px-4 py-2.5 rounded-full border"
                  style={{
                    background: buddyAction === 'raise' ? 'rgba(168,255,111,0.10)' : 'rgba(96,165,250,0.10)',
                    borderColor: buddyAction === 'raise' ? 'rgba(168,255,111,0.35)' : 'rgba(96,165,250,0.35)',
                    boxShadow: buddyAction === 'raise'
                      ? '0 0 20px -4px rgba(168,255,111,0.35)'
                      : '0 0 20px -4px rgba(96,165,250,0.35)',
                    animation: 'buddyPop 0.4s cubic-bezier(0.34,1.56,0.64,1) both',
                  }}
                >
                  <span
                    className="text-base shrink-0"
                    role="img"
                    aria-label="buddy"
                    style={{ animation: buddyAction === 'raise' ? 'buddyBounce 1.2s ease-in-out infinite' : 'none' }}
                  >
                    🤖
                  </span>
                  <span
                    className="text-sm font-semibold"
                    style={{ color: buddyAction === 'raise' ? '#A8FF6F' : '#93C5FD' }}
                  >
                    {buddyMessage}
                  </span>
                </div>
              )}

              {/* Stars */}
              <div className="flex gap-3 mb-2">
                {Array.from({length:3},(_,i)=>(
                  <span key={i} className="text-5xl transition-all duration-300"
                        style={{
                          color: i < starAnim ? '#FAC775' : 'rgba(255,255,255,0.1)',
                          transform: i < starAnim ? 'scale(1.2)' : 'scale(0.8)',
                          filter: i < starAnim ? 'drop-shadow(0 0 10px #FAC775)' : 'none',
                        }}>★</span>
                ))}
              </div>

              {/* Time */}
              <p className="text-white/30 text-sm mb-8">
                Time: {Math.floor(metricsRef.current.timeSeconds)}s
                {bestStars > 0 && earnedStars > bestStars && (
                  <span className="ml-2 text-brand-green">↑ New best!</span>
                )}
              </p>

              {rlEventId && (
                <div className="flex flex-col items-center gap-2 mb-6 max-w-sm text-sm font-semibold text-white/70">
                  {feedbackGiven ? (
                    <span>✅ Saved — thank you!</span>
                  ) : (
                    <>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-white/50">Grown-up check</span>
                      <div className="flex items-center gap-3">
                      <span>Did we score that right?</span>
                      <button
                        onClick={() => {
                          setFeedbackGiven('up')
                          submitEventFeedback(rlEventId, 'up').catch(() => {})
                        }}
                        aria-label="Yes, that was scored correctly"
                        className="hover:scale-110 transition-transform text-lg"
                      >
                        👍
                      </button>
                      <button
                        onClick={() => {
                          setFeedbackGiven('down')
                          submitEventFeedback(rlEventId, 'down').catch(() => {})
                        }}
                        aria-label="No, that was scored wrong"
                        className="hover:scale-110 transition-transform text-lg"
                      >
                        👎
                      </button>
                      </div>
                      <p className="text-xs font-normal leading-snug text-white/60 text-center">
                        A parent or therapist watching can answer. Tap 👍 if the stars and result matched what you
                        saw and heard, or 👎 if not. It is saved with this attempt so scoring mistakes can be found and fixed.
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-3 flex-wrap justify-center">
                <button onClick={replay}
                  className="px-6 py-3 rounded-xl border border-white/20 text-white hover:bg-white/10 transition-all font-semibold text-sm">
                  Play Again
                </button>
                {nextId && (
                  <button onClick={() => { cleanup(); navigate(`/play/game/${nextId}`) }}
                    className="px-8 py-3 rounded-xl font-display font-black text-brand-dark transition-all active:scale-95 text-sm"
                    style={{ background: meta.color }}>
                    Next Level →
                  </button>
                )}
                <button onClick={() => { cleanup(); navigate('/play/levels') }}
                  className="px-6 py-3 rounded-xl border border-white/20 text-white hover:bg-white/10 transition-all font-semibold text-sm">
                  All Levels
                </button>
              </div>
            </div>
          )}

          {/* ERROR */}
          {phase === 'error' && (
            <div className="flex flex-col items-center justify-center text-center py-20 rounded-2xl"
                 style={{ minHeight: H, background: 'linear-gradient(135deg, #1a1a2e, #12122A)' }}>
              <div className="text-6xl mb-4">😕</div>
              <p className="text-white/60 mb-2 text-lg">
                {errorReason === 'session' ? "Couldn't start this level" : "Couldn't access microphone"}
              </p>
              <p className="text-white/30 text-sm mb-8">
                {errorReason === 'session' ? 'Check your internet connection and try again' : 'Check mic permissions in your browser'}
              </p>
              <button onClick={() => { setErrorReason(null); setPhase('ready') }}
                className="px-8 py-3 rounded-xl font-bold hover:bg-opacity-90 transition-all"
                style={{ background: meta.color, color: '#12122A' }}>
                Try Again
              </button>
            </div>
          )}

        </div>
      </div>

      <style>{`
        @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-10px)} }
        @keyframes breatheIn { 0%{transform:scale(0.85)} 70%{transform:scale(1.25)} 100%{transform:scale(1.15)} }
        @keyframes buddyPop { 0%{opacity:0; transform:scale(0.7) translateY(6px)} 100%{opacity:1; transform:scale(1) translateY(0)} }
        @keyframes buddyBounce { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-2px) rotate(-6deg)} }
      `}</style>
    </div>
  )
}

function drawBreathOverlay(ctx, W, breath, color) {
  // Minimal breath bar at very bottom of canvas
  const bx = 20, by = 560, bw = W - 40, bh = 10
  ctx.fillStyle = 'rgba(0,0,0,0.4)'
  ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, 5); ctx.fill()
  if (breath > 0) {
    const grd = ctx.createLinearGradient(bx, 0, bx + bw, 0)
    grd.addColorStop(0, '#A8FF6F')
    grd.addColorStop(1, color)
    ctx.fillStyle = grd
    ctx.beginPath(); ctx.roundRect(bx, by, bw * Math.min(1, breath), bh, 5); ctx.fill()
    if (breath > 0.2) {
      ctx.shadowColor = color; ctx.shadowBlur = 10
      ctx.fillStyle = grd
      ctx.beginPath(); ctx.roundRect(bx, by, bw * Math.min(1, breath), bh, 5); ctx.fill()
      ctx.shadowBlur = 0
    }
  }
  ctx.fillStyle = breath > 0.05 ? '#A8FF6F' : 'rgba(255,255,255,0.2)'
  ctx.font = '12px sans-serif'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
  ctx.fillText('💨', bx - 2, by - 10)
}
