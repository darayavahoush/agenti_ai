import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import MouthShapeGuide from "../vaakmirror/components/MouthShapeGuide";
import {
  PHONIC_SOUNDS, SVGKEY_TO_MOUTH_SHAPE, KEYBOARD_ROWS,
  LETTER_PROBES, CORE_LETTERS, MIN_LETTERS_FOR_PLAN, GROUPS, VAAKMIRROR_GAMES,
} from "./alphabetData";
import "./AlphabetCheck.css";

const MAX_RECORD_MS = 3500;

// Status of a letter for the keyboard badge: ok | missed | unclear | null.
function statusOf(r) {
  if (!r) return null;
  if (r.correct === true) return "ok";
  if (r.correct === false) return "missed";
  return "unclear";
}

const BADGE = { ok: "✓", missed: "✗", unclear: "?" };

/**
 * "Sound Check" -- the Alphabet part of the Assessment.
 *
 * Tap a letter, see and hear how it is made, then say a short keyword that
 * starts with it. Each recording goes to the backend's alphabet LangGraph
 * agent (POST /assessment/alphabet/analyze), which scores just that sound.
 * When enough letters are done, "Set up my mouth games" sends the results
 * to POST /assessment/alphabet/complete, where the VaakMirror planner agent
 * turns them into game parameters (focus sounds, round size, ...) that the
 * VaakMirror games then start with.
 *
 * `onSave` is only provided for a signed-in child; without it the check still
 * works and gives per-letter feedback, it just can't set up the games.
 */
export default function AlphabetCheck({
  letter, onLetterChange, language, onLanguageChange, languages, speak,
  apiUrl, patientName, onBack, backLabel, onSave,
}) {
  const navigate = useNavigate();
  const [results, setResults] = useState({});      // letter -> letter_result
  const [phase, setPhase] = useState("idle");      // idle | recording | analyzing
  const [error, setError] = useState("");
  const [plan, setPlan] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showSteps, setShowSteps] = useState(false);

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const stopTimerRef = useRef(null);
  const studioRef = useRef(null);

  const sound = PHONIC_SOUNDS[letter];
  const probe = LETTER_PROBES[letter];
  const result = results[letter];
  const shape = SVGKEY_TO_MOUTH_SHAPE[sound.svgKey] || SVGKEY_TO_MOUTH_SHAPE.mid_mid;
  const voice = /no voice/i.test(sound.anatomy) ? "Voice off" : /voice on/i.test(sound.anatomy) ? "Voice on" : null;

  const scored = Object.values(results).filter((r) => r.correct !== null && r.correct !== undefined);
  const coreDone = CORE_LETTERS.filter((l) => results[l] && results[l].correct !== null).length;
  const canFinish = scored.length >= MIN_LETTERS_FOR_PLAN;

  // Follow-up letters: the look-alike partners of anything missed, not yet tried.
  const suggested = useMemo(() => {
    const out = [];
    for (const r of Object.values(results)) {
      if (r.correct !== false) continue;
      for (const n of r.next || []) if (!results[n] && !out.includes(n)) out.push(n);
    }
    return out.slice(0, 3);
  }, [results]);

  useEffect(() => () => {
    clearTimeout(stopTimerRef.current);
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") {
      rec.onstop = null;
      rec.stop();
      rec.stream?.getTracks().forEach((t) => t.stop());
    }
  }, []);

  function pickLetter(key) {
    if (phase !== "idle") return;
    onLetterChange(key);
    setError("");
    setShowSteps(false);
    studioRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  async function startRecording() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        analyze(new Blob(chunksRef.current, { type: "audio/wav" }), letter);
      };
      recorderRef.current = recorder;
      recorder.start();
      setPhase("recording");
      stopTimerRef.current = setTimeout(stopRecording, MAX_RECORD_MS);
    } catch (err) {
      console.error(err);
      setError("I need the microphone to listen. Please allow it and try again.");
    }
  }

  function stopRecording() {
    clearTimeout(stopTimerRef.current);
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") rec.stop();
  }

  async function analyze(blob, forLetter) {
    setPhase("analyzing");
    try {
      const form = new FormData();
      form.append("file", blob, "recording.wav");
      form.append("letter", forLetter);
      form.append("patient_name", patientName || "Student");
      const res = await fetch(`${apiUrl}/assessment/alphabet/analyze`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { letter_result } = await res.json();
      setResults((prev) => ({ ...prev, [forLetter]: letter_result }));
      setPlan(null); // results changed, so any saved plan is out of date
    } catch (err) {
      console.error(err);
      setError("I couldn't check that one. Please try again.");
    } finally {
      setPhase("idle");
    }
  }

  async function finish() {
    if (!onSave) return;
    setSaving(true);
    setError("");
    try {
      setPlan(await onSave(Object.values(results)));
    } catch (err) {
      console.error(err);
      setError("I couldn't set up your games just now. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const params = plan?.vaakmirror_params;
  const game = params ? VAAKMIRROR_GAMES[params.primary_game] : null;

  return (
    <section className="sc-page">
      <div className="sc-topbar">
        <button className="sc-back" onClick={onBack}>{backLabel}</button>
      </div>

      <header className="sc-hero">
        <div>
          <span className="sc-eyebrow">Sound Check</span>
          <h1>Let's explore your sounds{patientName ? `, ${patientName.split(" ")[0]}` : ""}!</h1>
          <p>Tap a letter, see how your mouth makes it, then say the picture word. Your helper listens and sets up your mouth games.</p>
        </div>
        <div className="sc-progress" aria-label={`${coreDone} of ${CORE_LETTERS.length} starter sounds done`}>
          <div className="sc-progress-dots">
            {CORE_LETTERS.map((l) => {
              const st = statusOf(results[l]);
              return (
                <button key={l} className={`sc-dot ${st || ""}`} onClick={() => pickLetter(l)}
                        aria-label={`Starter sound ${l}${st ? `, ${st}` : ""}`}>
                  {l}
                </button>
              );
            })}
          </div>
          <span className="sc-progress-label">{coreDone} of {CORE_LETTERS.length} starter sounds</span>
        </div>
      </header>

      <div className="sc-grid">
        <div className="sc-card sc-keys">
          <div className="sc-card-title">
            <h2>Pick a sound</h2>
            <div className="sc-legend">
              {Object.entries(GROUPS).map(([k, g]) => (
                <span key={k} className="sc-legend-item"><i style={{ background: g.color }} />{g.label}</span>
              ))}
            </div>
          </div>

          <div className="sc-keyboard">
            {KEYBOARD_ROWS.map((row) => (
              <div className="sc-row" key={row.join("")}>
                {row.map((key) => {
                  const p = LETTER_PROBES[key];
                  const st = statusOf(results[key]);
                  const color = p ? GROUPS[p.group].color : "#b8b0cf";
                  const isCore = CORE_LETTERS.includes(key) && !results[key];
                  return (
                    <button key={key} onClick={() => pickLetter(key)} disabled={phase !== "idle"}
                            className={`sc-key ${letter === key ? "active" : ""} ${st || ""} ${!p ? "explore" : ""} ${isCore ? "core" : ""} ${suggested.includes(key) ? "suggested" : ""}`}
                            style={{ "--kc": color }}
                            aria-label={`${key}${p ? `, ${GROUPS[p.group].label}` : ", explore only"}${st ? `, ${st}` : ""}${suggested.includes(key) ? ", try this next" : ""}`}>
                      {key}
                      {st && <span className="sc-badge" aria-hidden="true">{BADGE[st]}</span>}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {suggested.length > 0 && (
            <p className="sc-suggest">
              ✨ Try next: {suggested.map((l) => (
                <button key={l} className="sc-chip" onClick={() => pickLetter(l)}>{l}</button>
              ))} (they sound like the ones you just found tricky)
            </p>
          )}

          <label className="sc-lang">
            <span>🌐 Voice accent for 🔊</span>
            <span className="sc-select">
              <select value={language} onChange={(e) => onLanguageChange(e.target.value)}>
                {languages.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
              </select>
              <ChevronDown size={16} aria-hidden="true" />
            </span>
          </label>
        </div>

        <article className="sc-card sc-studio" ref={studioRef} style={{ "--kc": probe ? GROUPS[probe.group].color : "#7c5cff" }}>
          <div className="sc-studio-head">
            <div className="sc-big-letter" aria-hidden="true">{letter}</div>
            <div className="sc-studio-title">
              <span>{probe ? GROUPS[probe.group].label : "Explore"} sound</span>
              <h2>{sound.ipa}</h2>
              <p>say <strong>“{sound.spoken}”</strong></p>
            </div>
            <button className="sc-hear" onClick={() => speak(sound.spoken, false, language)} aria-label={`Hear the sound for ${letter}`}>🔊</button>
          </div>

          <div className="sc-studio-body">
            <div className="sc-mouth">
              <div className="sc-mouth-frame">
                <MouthShapeGuide shape={shape.shape} manner={shape.manner} />
              </div>
              <div className="sc-facts">
                {voice && <span className={`sc-fact ${voice === "Voice on" ? "on" : ""}`}>{voice === "Voice on" ? "🔔" : "🔕"} {voice}</span>}
                {probe && <span className="sc-fact">👄 {GROUPS[probe.group].label}</span>}
              </div>
            </div>

            <div className="sc-how">
              <p className="sc-anatomy">{sound.anatomy}</p>
              {sound.tip && <p className="sc-tip">💡 {sound.tip}</p>}
              <button className="sc-more" onClick={() => setShowSteps((v) => !v)} aria-expanded={showSteps}>
                {showSteps ? "Hide" : "Show"} the steps <ChevronDown size={14} className={showSteps ? "up" : ""} aria-hidden="true" />
              </button>
              {showSteps && (
                <ol className="sc-steps">{sound.steps.map((s) => <li key={s}>{s}</li>)}</ol>
              )}
            </div>
          </div>

          {probe ? (
            <div className="sc-say">
              <div className="sc-word">
                <span className="sc-emoji" aria-hidden="true">{probe.emoji}</span>
                <div>
                  <small>Now you say</small>
                  <strong>“{probe.word}”</strong>
                </div>
                <button className="sc-hear small" onClick={() => speak(probe.word, false, language)} aria-label={`Hear the word ${probe.word}`}>🔊</button>
              </div>

              {phase === "idle" && (
                <button className="sc-mic" onClick={startRecording}>🎤 {result ? "Try again" : "Say it"}</button>
              )}
              {phase === "recording" && (
                <button className="sc-mic recording" onClick={stopRecording}>
                  <span className="sc-pulse" aria-hidden="true" /> Listening… tap when done
                </button>
              )}
              {phase === "analyzing" && <div className="sc-mic busy" role="status">🧠 Checking your sound…</div>}

              {error && <p className="sc-error" role="alert">{error}</p>}

              {result && phase === "idle" && (
                <div className={`sc-result ${statusOf(result)}`} role="status">
                  <span aria-hidden="true">{result.correct === true ? "🌟" : result.correct === false ? "💪" : "🎧"}</span>
                  <p>{result.message}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="sc-explore-note">This one is just for exploring. Try the coloured letters to check your sounds.</p>
          )}
        </article>
      </div>

      <div className="sc-card sc-finish">
        <div>
          <h2>Your mouth-game plan</h2>
          {!plan && (
            <p>
              {scored.length} sound{scored.length === 1 ? "" : "s"} checked.{" "}
              {canFinish
                ? (onSave ? "Ready! The helper will set up your VaakMirror games to match." : "Nice work! Sign in as a child to save a game plan.")
                : `Check ${MIN_LETTERS_FOR_PLAN - scored.length} more to set up your games.`}
            </p>
          )}
          {plan && <p>{plan.summary}</p>}
        </div>

        {!plan && onSave && (
          <button className="sc-finish-btn" onClick={finish} disabled={!canFinish || saving || phase !== "idle"}>
            {saving ? "Setting up…" : "Set up my mouth games"}
          </button>
        )}

        {plan && params && (
          <div className="sc-plan">
            {params.focus_sounds.length > 0 && (
              <div className="sc-plan-row">
                <small>Games will focus on</small>
                <div>{plan.tricky.map((t) => <span key={t.letter} className="sc-focus">{t.letter}</span>)}</div>
              </div>
            )}
            <div className="sc-plan-row">
              <small>Rounds of</small><b>{params.round_size} sounds</b>
            </div>
            {game && (
              <button className="sc-finish-btn" onClick={() => navigate(game.path)}>
                ▶ Play {game.name}
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
