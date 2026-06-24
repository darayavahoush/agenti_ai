import { useState } from "react";

import { MouthDiagram } from "../MouthDiagram";
import { ALPHABET_SOUNDS, KEYBOARD_ROWS } from "../alphabetData";
import "./Assessment.css";

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function speakIndianEnglish(text, slow = false) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN";
  utterance.rate = slow ? 0.62 : 0.9;
  utterance.pitch = 1;

  const voices = window.speechSynthesis.getVoices();
  const indianVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("en-in"));
  const hindiVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("hi-in"));
  const englishVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("en"));
  utterance.voice = indianVoice || hindiVoice || englishVoice || null;
  window.speechSynthesis.speak(utterance);
}

export default function Assessment() {
  const [section, setSection] = useState("home");
  const [word, setWord] = useState(null);
  const [wordLoading, setWordLoading] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [error, setError] = useState("");
  const [letter, setLetter] = useState("A");

  const selectedSound = ALPHABET_SOUNDS[letter];
  const letterGuide = LETTER_NAME_GUIDES[selectedSound.guide];

  async function loadRandomWord() {
    setSection("word");
    setWordLoading(true);
    setImageLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/assessment/words/random`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load a word");
      setWord(data);
    } catch (requestError) {
      setWord(null);
      setImageLoading(false);
      setError(requestError.message);
    } finally {
      setWordLoading(false);
    }
  }

  function openAlphabet() {
    setSection("alphabet");
    setError("");
  }

  return (
    <main className="assessment-page">
      <div className="assessment-heading">
        <div>
          <span className="assessment-eyebrow">Learn · Listen · Explore</span>
          <h1>Assessment Playground</h1>
          <p>Choose a word challenge or explore how every alphabet sound is formed.</p>
        </div>
        {section !== "home" && (
          <button className="assessment-back" onClick={() => setSection("home")}>
            ← All activities
          </button>
        )}
      </div>

      {section === "home" && (
        <div className="assessment-choice-grid">
          <button className="assessment-choice word-choice" onClick={loadRandomWord}>
            <span className="choice-icon">🖼️</span>
            <span className="choice-copy">
              <strong>Say a Word</strong>
              <small>See it, hear it in an Indian accent, then say it aloud.</small>
            </span>
            <span className="choice-arrow">→</span>
          </button>

          <button className="assessment-choice alphabet-choice" onClick={openAlphabet}>
            <span className="choice-icon">⌨️</span>
            <span className="choice-copy">
              <strong>Alphabet</strong>
              <small>Explore tongue, mouth, airflow and stress positions.</small>
            </span>
            <span className="choice-arrow">→</span>
          </button>
        </div>
      )}

      {section === "word" && (
        <section className="word-assessment-card">
          {wordLoading && <div className="assessment-loader">Picking a word for you…</div>}

          {!wordLoading && error && (
            <div className="assessment-empty">
              <span>🌱</span>
              <h2>Your word box is empty</h2>
              <p>{error}</p>
              <code>POST /assessment/words {`{ "word": "mango" }`}</code>
              <button onClick={loadRandomWord}>Try again</button>
            </div>
          )}

          {!wordLoading && word && (
            <>
              <div className="word-picture-wrap">
                {imageLoading && <div className="picture-placeholder">Creating picture…</div>}
                <img
                  key={word.id}
                  src={`${API_URL}${word.image_url}`}
                  alt={`Illustration of ${word.word}`}
                  className={imageLoading ? "loading" : ""}
                  onLoad={() => setImageLoading(false)}
                  onError={() => setImageLoading(false)}
                />
              </div>
              <div className="word-practice-panel">
                <span className="word-label">Your word is</span>
                <h2>{word.word}</h2>
                <p>Listen carefully, then try saying the word yourself.</p>
                <div className="listen-actions">
                  <button onClick={() => speakIndianEnglish(word.word)}>
                    🔊 Listen
                  </button>
                  <button className="slow" onClick={() => speakIndianEnglish(word.word, true)}>
                    🐢 Say it slowly
                  </button>
                </div>
                <button className="next-word" onClick={loadRandomWord}>Next word →</button>
              </div>
            </>
          )}
        </section>
      )}

      {section === "alphabet" && (
        <section className="alphabet-assessment">
          <div className="keyboard-card">
            <div className="keyboard-title">
              <div>
                <span>Interactive keyboard</span>
                <h2>Choose an alphabet</h2>
              </div>
              <div className="selected-letter-mini">{letter}</div>
            </div>
            <div className="alphabet-keyboard">
              {KEYBOARD_ROWS.map((row, rowIndex) => (
                <div className={`keyboard-row row-${rowIndex + 1}`} key={row.join("")}>
                  {row.map((key) => (
                    <button
                      key={key}
                      className={letter === key ? "active" : ""}
                      onClick={() => setLetter(key)}
                      aria-label={`Show articulation for ${key}`}
                    >
                      {key}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>

          <article className="articulation-card">
            <div className="sound-header">
              <div className="big-letter">{letter}</div>
              <div>
                <span>Letter name</span>
                <h2>{selectedSound.ipa}</h2>
                <p>say <strong>“{selectedSound.spoken}”</strong></p>
              </div>
              <button onClick={() => speakIndianEnglish(selectedSound.spoken)} aria-label={`Hear the letter ${letter}`}>
                🔊
              </button>
            </div>

            <div className="articulation-content">
              <div className="mouth-visual">
                <MouthDiagram svgKey={letterGuide.svg} />
                <span>Side view of tongue and mouth</span>
              </div>
              <div className="position-guide">
                <div className="position-summary">
                  <span>👄 Shape & position</span>
                  <strong>{letterGuide.anatomy}</strong>
                </div>
                <h3>Make the sound correctly</h3>
                <ol>
                  <li className="letter-transition">{selectedSound.transition}</li>
                  {letterGuide.steps.map((step) => <li key={step}>{step}</li>)}
                
                </ol>
                <div className="stress-tip">
                  <span>💨 Stress, voice & airflow</span>
                  <p>{letterGuide.steps[letterGuide.steps.length - 1]}</p>
                </div>
              </div>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}