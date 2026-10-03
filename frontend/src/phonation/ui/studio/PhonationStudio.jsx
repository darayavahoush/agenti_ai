import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { PhonationEngine, STARTER_LEVELS } from '../../index.js'
import { MockEngine } from './mockEngine.js'
import { adapt, TYPE_LABEL, levelList, levelTitle, levelPrompt, levelGoalMs, silenceEndMs } from './engineAdapter.js'
import VoiceStage from './VoiceStage.jsx'
import Clinician from './Clinician.jsx'
import './studio.css'

const GAIN = { soft: 0.6, normal: 1, strong: 1.5 }
const MAX_TRIAL_MS = 30000
const demo = () => new URLSearchParams(location.search).has('demo')

async function defaultRecognizer() {
  const m = await import('../../index.js')
  const k = Object.keys(m).find((n) => /^create.*recogni[sz]er$/i.test(n))
  if (!k) throw new Error('No create…Recognizer export found in phonation/index.js')
  return m[k]()
}

export default function PhonationStudio({ engineFactory, levels = STARTER_LEVELS, recognizerFactory = defaultRecognizer, denoiser, onResult }) {
  const [stage, setStage] = useState('welcome') // welcome | calibrating | menu | play | result
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)
  const [capture, setCapture] = useState(null)
  const [calWarn, setCalWarn] = useState([])
  const [level, setLevel] = useState(null)
  const [heard, setHeard] = useState(false)
  const [tally, setTally] = useState(0)
  const [result, setResult] = useState(null)
  const [set, setSet] = useState({ gain: 'normal', clinician: false, recog: false, denoise: false })
  const reduced = useMemo(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches, [])

  const A = useRef(null)
  const trial = useRef({ t0: 0, last: 0, heard: false })
  const recog = useRef(null)
  const onResultRef = useRef(onResult); onResultRef.current = onResult

  useEffect(() => () => A.current?.stop(), []) // always release the mic: browser recording indicator must go off
  const list = useMemo(() => levelList(levels), [levels])
  const groups = useMemo(() => list.reduce((m, l) => ((m[l.type] ||= []).push(l), m), {}), [list])

  const begin = async () => {
    if (busy) return
    setBusy(true); setNotice(null)
    try {
      const engine = engineFactory ? engineFactory() : demo() ? new MockEngine() : new PhonationEngine()
      A.current = adapt(engine)
      const cs = await A.current.start()
      setCapture(cs); setStage('calibrating')
      const cal = await A.current.calibrate(1500)
      setCalWarn(cal?.warnings || []); setStage('menu')
    } catch (e) {
      setNotice({ kind: 'warn', text: e?.name === 'NotAllowedError' ? 'The microphone is blocked. Allow it in your browser’s address bar, then press Start again.' : `Could not start the microphone: ${e?.message ?? e}` })
      setStage('welcome')
    } finally { setBusy(false) }
  }

  const recalibrate = async () => {
    setStage('calibrating')
    const cal = await A.current.calibrate(1500)
    setCalWarn(cal?.warnings || []); setStage('menu')
  }

  const play = useCallback((l) => {
    setLevel(l); setResult(null); setHeard(false); setTally(0); setNotice(null)
    trial.current = { t0: performance.now(), last: performance.now(), heard: false }
    A.current.begin(l, { captureAudio: set.recog })
    setStage('play')
  }, [set.recog])

  const finish = useCallback(async () => {
    if (trial.current.done) return
    trial.current.done = true
    try {
      let r
      if (set.recog) {
        try {
          if (!recog.current) { setNotice({ kind: 'info', text: 'Loading the sound check model…' }); recog.current = await recognizerFactory() }
          let rec = recog.current
          if (set.denoise && denoiser) { const { withDenoise } = await denoiser(); rec = withDenoise(rec) }
          r = await A.current.end(rec)
          setNotice(null)
        } catch (e) {
          setNotice({ kind: 'warn', text: `The sound check could not run (${e?.message ?? e}). Your acoustic results are still valid.` })
          r = await A.current.end()
        }
      } else r = await A.current.end()
      setResult(r); setStage('result'); onResultRef.current?.(r, level)
    } catch (e) {
      setNotice({ kind: 'warn', text: `That try could not be scored: ${e?.message ?? e}` }); setStage('menu')
    }
  }, [set.recog, set.denoise, recognizerFactory, denoiser, level])

  // trial end rules + hidden-tab abort (rAF pauses in background tabs, so a trial would overrun)
  useEffect(() => {
    if (stage !== 'play') return
    const id = setInterval(() => {
      const T = trial.current, now = performance.now(), v = A.current.read()
      if (v.voiced) { T.last = now; if (!T.heard) { T.heard = true; setHeard(true) } }
      if ((T.heard && now - T.last > silenceEndMs(level)) || now - T.t0 > MAX_TRIAL_MS) finish()
    }, 100)
    const hide = () => { if (document.hidden) { clearInterval(id); trial.current.done = true; A.current.end().catch(() => {}); setNotice({ kind: 'info', text: 'Paused because the tab was hidden. Pick a level to try again.' }); setStage('menu') } }
    document.addEventListener('visibilitychange', hide)
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', hide) }
  }, [stage, level, finish])

  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ level: { id: level.id, type: level.type, target: level.target }, result, exportedAt: new Date().toISOString() }, null, 2)], { type: 'application/json' })
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `phonation-${level.id ?? level.type}.json` })
    a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000)
  }

  const goal = stage === 'play' && level && (level.type === 'sustained_voicing') ? levelGoalMs(level) : null
  const reps = level?.reps
  const processing = capture && (capture.autoGainControl || capture.noiseSuppression || capture.echoCancellation)
  const recognition = result?.recognition ?? result?.recognizer ?? null

  return (
    <div className="st-root" data-stage={stage}>
      <header className="st-top">
        <h1>Voice Lantern</h1>
        {stage !== 'welcome' && (
          <details className="st-settings">
            <summary>Settings</summary>
            <div>
              <fieldset><legend>How strongly the lantern reacts</legend>
                {Object.keys(GAIN).map((g) => <label key={g}><input type="radio" name="gain" checked={set.gain === g} onChange={() => setSet({ ...set, gain: g })} />{g[0].toUpperCase() + g.slice(1)}</label>)}
              </fieldset>
              <label><input type="checkbox" checked={set.clinician} onChange={(e) => setSet({ ...set, clinician: e.target.checked })} />Clinician view <small>(display only, not access-controlled)</small></label>
              <label><input type="checkbox" checked={set.recog} onChange={(e) => setSet({ ...set, recog: e.target.checked })} />On-device sound check <small>(experimental; a short clip is held in memory until the try is scored)</small></label>
              {denoiser && <label className={set.recog ? '' : 'off'}><input type="checkbox" disabled={!set.recog} checked={set.denoise} onChange={(e) => setSet({ ...set, denoise: e.target.checked })} />Reduce room noise for the sound check only <small>(your loudness and pitch results always use the original sound)</small></label>}
            </div>
          </details>
        )}
      </header>

      {notice && <p role="status" className={`st-notice ${notice.kind}`}>{notice.text}</p>}

      {stage === 'welcome' && (
        <main className="st-welcome">
          <div className="st-idle" aria-hidden="true" />
          <h2>Turn your voice into light.</h2>
          <p>Make a sound and watch the lantern respond. Find a quiet spot first.</p>
          <p className="st-fine">Your voice is never recorded or sent anywhere. Only loudness and pitch measurements are used.</p>
          <button className="st-btn" onClick={begin} disabled={busy}>{busy ? 'Starting…' : 'Start'}</button>
        </main>
      )}

      {stage === 'calibrating' && (
        <main className="st-welcome"><div className="st-idle" aria-hidden="true" /><h2>Shh. Listening to the room.</h2><p>Stay quiet for a moment.</p></main>
      )}

      {stage === 'menu' && (
        <main className="st-menu">
          {processing && <p className="st-notice warn" role="alert">This device is changing the sound (noise, echo or volume processing). Results will be marked unreliable. Try another microphone or browser.</p>}
          {calWarn.includes('unstable_background') && <p className="st-notice warn">We heard sound while measuring the room, so quiet voices may be missed. <button className="st-link" onClick={recalibrate}>Measure the room again</button></p>}
          {Object.entries(groups).map(([type, ls]) => (
            <section key={type}>
              <h2>{TYPE_LABEL[type] ?? type}</h2>
              <div className="st-levels">{ls.map((l) => <button key={l.id ?? levelTitle(l)} className="st-level" onClick={() => play(l)}><strong>{levelTitle(l)}</strong><span>{levelPrompt(l)}</span></button>)}</div>
            </section>
          ))}
          <button className="st-link" onClick={recalibrate}>Measure the room again</button>
        </main>
      )}

      {(stage === 'play' || stage === 'result') && level && (
        <main className="st-play">
          <VoiceStage read={A.current.read} active={stage === 'play'} goalMs={goal} glide={level.type === 'pitch_glide'} gain={GAIN[set.gain]} reduced={reduced} onOnset={() => setTally((n) => n + 1)} />
          <div className="st-copy" aria-live="polite">
            {stage === 'play' && <>
              <h2>{levelPrompt(level)}</h2>
              <p>{heard ? 'Nice, I can hear you.' : 'Waiting for your voice…'}</p>
              {reps && <div className="st-dots" aria-label={`${Math.min(tally, reps)} of ${reps}`}>{Array.from({ length: reps }, (_, i) => <i key={i} className={i < tally ? 'on' : ''} />)}</div>}
              <button className="st-btn ghost" onClick={finish}>I’m done</button>
            </>}
            {stage === 'result' && result && <>
              <div className="st-stars" aria-label={`${result.stars ?? 0} of 3 stars`}>{[0, 1, 2].map((i) => <b key={i} className={i < (result.stars ?? 0) ? 'on' : ''}>★</b>)}</div>
              <h2>{result.quality?.reliable === false ? 'That one was hard to hear.' : result.passed ? 'Lovely. You did it.' : 'Good try. Let’s go again.'}</h2>
              {result.quality?.reliable === false && <p>Try somewhere quieter, or move a little closer to the microphone.</p>}
              <div className="st-actions"><button className="st-btn" onClick={() => play(level)}>Again</button><button className="st-btn ghost" onClick={() => setStage('menu')}>Pick another</button></div>
            </>}
          </div>
          {stage === 'result' && result && set.clinician && <Clinician result={result} level={level} recognition={recognition} onExport={exportJson} />}
        </main>
      )}
    </div>
  )
}
