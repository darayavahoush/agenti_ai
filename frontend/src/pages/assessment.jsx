import { useState, useRef, useEffect } from "react";
import { MouthDiagram } from "../MouthDiagram";
import { ALPHABET_SOUNDS, KEYBOARD_ROWS, LETTER_NAME_GUIDES } from "../alphabetData";
import "./Assessment.css";

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

const INDIAN_LANGUAGES = [
  { code: "en-IN", name: "English (India)", voiceLang: "en-IN", translationKey: "english", listenText: "Listen", slowText: "Say it slowly" },
  { code: "hi-IN", name: "Hindi", voiceLang: "hi-IN", translationKey: "hindi", listenText: "सुनो", slowText: "धीरे बोलो" },
  { code: "ta-IN", name: "Tamil", voiceLang: "ta-IN", translationKey: "tamil", listenText: "கேளுங்கள்", slowText: "மெதுவாகச் சொல்லுங்கள்" },
  { code: "te-IN", name: "Telugu", voiceLang: "te-IN", translationKey: "telugu", listenText: "వినండి", slowText: "నెమ్మదిగా చెప్పండి" },
  { code: "kn-IN", name: "Kannada", voiceLang: "kn-IN", translationKey: "kannada", listenText: "ಕೇಳಿ", slowText: "ನಿಧಾನವಾಗಿ ಹೇಳಿ" },
  { code: "ml-IN", name: "Malayalam", voiceLang: "ml-IN", translationKey: "malayalam", listenText: "കേൾക്കുക", slowText: "പതുക്കെ പറയുക" },
  { code: "bn-IN", name: "Bengali", voiceLang: "bn-IN", translationKey: "bengali", listenText: "শুনুন", slowText: "আস্তে বলুন" },
  { code: "mr-IN", name: "Marathi", voiceLang: "mr-IN", translationKey: "marathi", listenText: "ऐका", slowText: "संथ बोला" },
];

function speakIndianEnglish(text, slow = false, language = "en-IN") {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = language;
  utterance.rate = slow ? 0.62 : 0.9;
  utterance.pitch = 1;

  const voices = window.speechSynthesis.getVoices();
  const indianVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith(language.toLowerCase()));
  const hindiVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("hi-in"));
  const englishVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith("en"));
  utterance.voice = indianVoice || hindiVoice || englishVoice || null;
  window.speechSynthesis.speak(utterance);
}

// Map failed phonemes to keyboard letters
function mapPhonemeToLetter(phoneme) {
  if (!phoneme) return null;
  const p = phoneme.toUpperCase().replace(/[0-9]/g, ""); // Strip stress digits
  const mapping = {
    "AA": "A", "AE": "A", "AH": "A", "AO": "O", "AW": "A", "AY": "A",
    "EH": "E", "ER": "R", "EY": "A",
    "IH": "I", "IY": "E",
    "OW": "O", "OY": "O",
    "UH": "U", "UW": "U",
    "B": "B",
    "CH": "C", "SH": "S", "JH": "J", "ZH": "S",
    "D": "D", "DH": "D",
    "F": "F",
    "G": "G",
    "HH": "H",
    "K": "K",
    "L": "L",
    "M": "M",
    "N": "N", "NG": "N",
    "P": "P",
    "R": "R",
    "S": "S", "Z": "Z",
    "T": "T", "TH": "T",
    "V": "V",
    "W": "W",
    "Y": "Y"
  };
  return mapping[p] || null;
}

export default function Assessment() {
  const [section, setSection] = useState("home");
  const [word, setWord] = useState(null);
  const [wordLoading, setWordLoading] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [error, setError] = useState("");
  const [letter, setLetter] = useState("A");
  const [selectedLanguage, setSelectedLanguage] = useState("en-IN");

  // Audio Recording & Analysis States
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // Custom Audio Recording for Word Pronunciation
  const [customRecording, setCustomRecording] = useState(false);
  const [customAudioBlob, setCustomAudioBlob] = useState(null);
  const [customAudioUrl, setCustomAudioUrl] = useState(null);
  const [audioExists, setAudioExists] = useState(false);
  const [checkingAudio, setCheckingAudio] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [playingAudio, setPlayingAudio] = useState(false);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const customMediaRecorderRef = useRef(null);
  const customChunksRef = useRef([]);

  const selectedSound = ALPHABET_SOUNDS[letter];
  const letterGuide = LETTER_NAME_GUIDES[selectedSound.guide];

  async function loadRandomWord() {
    setSection("word");
    setWordLoading(true);
    setImageLoading(true);
    setError("");
    setAudioBlob(null);
    setAudioUrl(null);
    setAnalysisResult(null);
    setCustomAudioBlob(null);
    setCustomAudioUrl(null);
    setAudioExists(false);

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

  // Check if audio exists for current word and language
  const checkAudioExistence = async (wordKey, languageCode) => {
    if (!wordKey || !languageCode) return;
    
    setCheckingAudio(true);
    try {
      const langCode = languageCode.split('-')[0]; // Extract 'en' from 'en-IN'
      const response = await fetch(`${API_URL}/assessment/audio/${wordKey}/${langCode}/exists`);
      const data = await response.json();
      if (response.ok) {
        setAudioExists(data.exists);
      }
    } catch (err) {
      console.error("Failed to check audio existence:", err);
      setAudioExists(false);
    } finally {
      setCheckingAudio(false);
    }
  };

  // Check audio when word or language changes
  useEffect(() => {
    if (word && selectedLanguage) {
      const langCode = selectedLanguage.split('-')[0];
      checkAudioExistence(word.word, langCode);
    }
  }, [word, selectedLanguage]);

  // Custom audio recording functions
  const startCustomRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      customChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          customChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(customChunksRef.current, { type: "audio/webm" });
        setCustomAudioBlob(blob);
        setCustomAudioUrl(URL.createObjectURL(blob));
      };

      customMediaRecorderRef.current = recorder;
      recorder.start();
      setCustomRecording(true);
    } catch (err) {
      console.error(err);
      alert("Microphone access denied");
    }
  };

  const stopCustomRecording = () => {
    if (!customMediaRecorderRef.current) return;
    customMediaRecorderRef.current.stop();
    setCustomRecording(false);
  };

  // Auto-upload when recording stops
  useEffect(() => {
    if (customAudioBlob && !customRecording) {
      uploadCustomAudio();
    }
  }, [customAudioBlob, customRecording]);

  const uploadCustomAudio = async () => {
    if (!customAudioBlob || !word) {
      return;
    }

    setUploading(true);
    try {
      const langCode = selectedLanguage.split('-')[0];
      const formData = new FormData();
      formData.append("file", customAudioBlob, `${word.word}_${langCode}.webm`);

      const response = await fetch(`${API_URL}/assessment/audio/${word.word}/${langCode}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Upload failed");

      setCustomAudioBlob(null);
      setCustomAudioUrl(null);
      setAudioExists(true);
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  const playCachedAudio = async (slow = false) => {
    if (!word || !selectedLanguage) return;
    
    const langCode = selectedLanguage.split('-')[0];
    
    if (!audioExists) {
      alert(`No audio found for ${word.word} in ${INDIAN_LANGUAGES.find(l => l.code === selectedLanguage)?.name}. Please record it first.`);
      return;
    }

    setPlayingAudio(true);
    try {
      const response = await fetch(`${API_URL}/assessment/audio/${word.word}/${langCode}`);
      if (!response.ok) {
        throw new Error("Failed to fetch audio");
      }
      
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      if (slow) {
        audio.playbackRate = 0.7;
      }
      
      audio.onended = () => {
        setPlayingAudio(false);
        URL.revokeObjectURL(audioUrl);
      };
      
      audio.onerror = () => {
        setPlayingAudio(false);
        URL.revokeObjectURL(audioUrl);
        alert("Failed to play audio");
      };
      
      audio.play();
    } catch (err) {
      console.error(err);
      setPlayingAudio(false);
      alert("Failed to play audio: " + err.message);
    }
  };

  function openAlphabet() {
    setSection("alphabet");
    setError("");
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch (err) {
      console.error(err);
      alert("Microphone access denied");
    }
  };

  const stopRecording = () => {
    if (!mediaRecorderRef.current) return;
    mediaRecorderRef.current.stop();
    setRecording(false);
  };

  const analyzeSpeech = async () => {
    if (!audioBlob || !word) {
      alert("Please record audio first");
      return;
    }
    setLoading(true);
    setError("");
    setAnalysisResult(null);

    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");
      formData.append("patient_name", "Student");
      formData.append("target_word", word.word);
      const response = await fetch(`${API_URL}/assessment/analyze`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok || data.error || data.detail) {
        throw new Error(data.error || JSON.stringify(data.detail || data));
      }

      setAnalysisResult(data);
    } catch (err) {
      console.error(err);
      setError("Speech analysis failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Find incorrect phonemes and link them to Alphabet cards
  const getLinkableLetters = () => {
    if (!analysisResult || !analysisResult.phoneme_matches) return [];
    const incorrectPhonemes = analysisResult.phoneme_matches
      .filter(m => !m.correct)
      .map(m => m.expected);
    const uniqueIncorrect = [...new Set(incorrectPhonemes)];
    return uniqueIncorrect
      .map(p => ({ phoneme: p, letter: mapPhonemeToLetter(p) }))
      .filter(item => item.letter && ALPHABET_SOUNDS[item.letter]);
  };

  const linkableLetters = getLinkableLetters();

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
        <section className="word-assessment-card" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {wordLoading && <div className="assessment-loader">Picking a word for you…</div>}

          {!wordLoading && error && (
            <div className="assessment-empty">
              <span>🌱</span>
              <h2>Something went wrong</h2>
              <p>{error}</p>
              <button onClick={loadRandomWord}>Try again</button>
            </div>
          )}

          {!wordLoading && word && (
            <>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "20px", width: "100%" }}>
                <div className="word-picture-wrap" style={{ flex: "1 1 300px" }}>
                  {imageLoading && <div className="picture-placeholder">Creating picture…</div>}
                  <img
                    key={word.id}
                    src={`${API_URL}${word.image_url}`}
                    alt={`Illustration of ${word.word}`}
                    className={imageLoading ? "loading" : ""}
                    style={{ width: "100%", height: "auto", maxHeight: "350px", objectFit: "contain" }}
                    onLoad={() => setImageLoading(false)}
                    onError={() => setImageLoading(false)}
                  />
                </div>
                <div className="word-practice-panel" style={{ flex: "1 1 300px", display: "flex", flexDirection: "column", gap: "10px", padding: "12px" }}>
                  <span className="word-label">Your word is</span>
                  <h2 style={{ fontSize: "2rem", margin: 0, color: "#5b21b6" }}>{word.word}</h2>
                  <p style={{ margin: 0, fontSize: "14px" }}>Listen carefully, then try saying the word yourself.</p>
                  
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    <label style={{ fontSize: "14px", fontWeight: 700, color: "#6d28d9", whiteSpace: "nowrap" }}>🌐</label>
                    <select
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                      style={{
                        padding: "8px 12px",
                        borderRadius: "8px",
                        border: "2px solid #a855f7",
                        background: "#faf5ff",
                        color: "#6d28d9",
                        fontWeight: 600,
                        fontSize: "14px",
                        cursor: "pointer",
                        minWidth: "160px"
                      }}
                    >
                      {INDIAN_LANGUAGES.map((lang) => (
                        <option key={lang.code} value={lang.code}>
                          {lang.name}
                        </option>
                      ))}
                    </select>

                    {customRecording ? (
                      <button
                        onClick={stopCustomRecording}
                        style={{
                          padding: "10px",
                          border: "2px solid #a855f7",
                          borderRadius: "50%",
                          background: "#faf5ff",
                          color: "#6d28d9",
                          cursor: "pointer",
                          boxShadow: "0 4px 6px rgba(168,85,247,0.1)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          width: "48px",
                          height: "48px"
                        }}
                        title="Stop Recording"
                      >
                        ⏹
                      </button>
                    ) : (
                      <>
                        {!audioExists && (
                          <button
                            onClick={startCustomRecording}
                            disabled={uploading}
                            style={{
                              padding: "10px",
                              border: "2px solid #a855f7",
                              borderRadius: "50%",
                              background: uploading ? "#e9d5ff" : "#faf5ff",
                              color: "#6d28d9",
                              cursor: uploading ? "not-allowed" : "pointer",
                              boxShadow: "0 4px 6px rgba(168,85,247,0.1)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              width: "48px",
                              height: "48px",
                              opacity: uploading ? 0.6 : 1
                            }}
                            title="Record Pronunciation"
                          >
                            🎤
                          </button>
                        )}

                        {audioExists && (
                          <>
                            <button
                              onClick={startCustomRecording}
                              disabled={uploading}
                              style={{
                                padding: "10px",
                                border: "2px solid #a855f7",
                                borderRadius: "50%",
                                background: uploading ? "#e9d5ff" : "#faf5ff",
                                color: "#6d28d9",
                                cursor: uploading ? "not-allowed" : "pointer",
                                boxShadow: "0 4px 6px rgba(168,85,247,0.1)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                width: "48px",
                                height: "48px",
                                opacity: uploading ? 0.6 : 1
                              }}
                              title="Edit Pronunciation"
                            >
                              ✏️
                            </button>
                            <button
                              onClick={() => playCachedAudio(false)}
                              disabled={playingAudio || checkingAudio}
                              style={{
                                padding: "10px",
                                border: "2px solid #a855f7",
                                borderRadius: "50%",
                                background: (playingAudio || checkingAudio) ? "#e9d5ff" : "#faf5ff",
                                color: "#6d28d9",
                                cursor: (playingAudio || checkingAudio) ? "not-allowed" : "pointer",
                                boxShadow: "0 4px 6px rgba(168,85,247,0.1)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                width: "48px",
                                height: "48px",
                                opacity: (playingAudio || checkingAudio) ? 0.6 : 1
                              }}
                              title="Play Audio"
                            >
                                {playingAudio ? "⏳" : "▶️"}
                            </button>
                            <button
                              onClick={() => playCachedAudio(true)}
                              disabled={playingAudio || checkingAudio}
                              style={{
                                padding: "10px",
                                border: "2px solid #a855f7",
                                borderRadius: "50%",
                                background: (playingAudio || checkingAudio) ? "#e9d5ff" : "#faf5ff",
                                color: "#6d28d9",
                                cursor: (playingAudio || checkingAudio) ? "not-allowed" : "pointer",
                                boxShadow: "0 4px 6px rgba(168,85,247,0.1)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                width: "48px",
                                height: "48px",
                                opacity: (playingAudio || checkingAudio) ? 0.6 : 1
                              }}
                              title="Play Slow"
                            >
                                🐢
                            </button>
                          </>
                        )}
                      </>
                    )}
                  </div>

                  <div style={{ borderTop: "1px solid #eee", marginTop: "12px", paddingTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                    <h4 style={{ margin: 0, color: "#6d28d9", fontSize: "15px" }}>🎙️ Try Pronouncing It:</h4>
                    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                      {!recording ? (
                        <button
                          onClick={startRecording}
                          style={{
                            padding: "10px 18px",
                            border: "none",
                            borderRadius: "999px",
                            background: "linear-gradient(90deg, #f97316, #fb7185)",
                            color: "#fff",
                            fontWeight: 700,
                            fontSize: "14px",
                            cursor: "pointer",
                            boxShadow: "0 4px 10px rgba(249,115,22,0.2)"
                          }}
                        >
                          🎤 Record
                        </button>
                      ) : (
                        <button
                          onClick={stopRecording}
                          style={{
                            padding: "10px 18px",
                            border: "none",
                            borderRadius: "999px",
                            background: "linear-gradient(90deg, #ef4444, #f97316)",
                            color: "#fff",
                            fontWeight: 700,
                            fontSize: "14px",
                            cursor: "pointer",
                            boxShadow: "0 4px 10px rgba(239,68,68,0.2)"
                          }}
                        >
                          ⏹ Stop
                        </button>
                      )}

                      <button
                        onClick={analyzeSpeech}
                        disabled={loading || !audioBlob}
                        style={{
                          padding: "10px 18px",
                          border: "none",
                          borderRadius: "999px",
                          background: loading
                            ? "#cbd5e1"
                            : !audioBlob
                            ? "#e2e8f0"
                            : "linear-gradient(90deg, #22c55e, #06b6d4)",
                          color: loading || !audioBlob ? "#94a3b8" : "#fff",
                          fontWeight: 700,
                          fontSize: "14px",
                          cursor: loading || !audioBlob ? "not-allowed" : "pointer",
                          boxShadow: !audioBlob ? "none" : "0 4px 10px rgba(34,197,94,0.2)"
                        }}
                      >
                        {loading ? "Analyzing..." : "🚀 Analyze"}
                      </button>
                    </div>
                  </div>

                  {audioUrl && (
                    <div style={{ marginTop: "10px" }}>
                      <audio controls src={audioUrl} style={{ width: "100%", height: "36px" }} />
                    </div>
                  )}

                  <button className="next-word" onClick={loadRandomWord} style={{ marginTop: "auto", alignSelf: "flex-start", padding: "10px 20px", background: "#7c3aed", color: "#fff", border: "none", borderRadius: "12px", fontWeight: 700, fontSize: "14px", cursor: "pointer" }}>Next word →</button>
                </div>
              </div>

              {/* 🧙‍♂️ Wizard's Magic Speech Board */}
              {analysisResult && (
                <div
                  style={{
                    padding: "14px",
                    borderRadius: "14px",
                    background: "linear-gradient(135deg, #fffbeb 0%, #fff1f2 100%)",
                    border: "3px dashed #f472b6",
                    boxShadow: "0 10px 25px rgba(244, 114, 182, 0.15)",
                    width: "100%"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
                    <h3 style={{ margin: 0, color: "#db2777", display: "flex", alignItems: "center", gap: "8px", fontSize: "1.1rem", fontWeight: 900 }}>
                      🪄 Wizard's Speech Magic! ✨
                    </h3>
                    <div style={{ fontSize: "20px", fontWeight: 900, color: "#16a34a" }}>
                      {analysisResult.accuracy ?? 0}% Match
                    </div>
                  </div>

                  {analysisResult.reasoning && (
                    <div style={{ marginBottom: "10px", padding: "10px 12px", background: "#ffffff", borderRadius: "10px", border: "2px solid #c084fc" }}>
                      <div style={{ fontSize: "11px", color: "#a855f7", fontWeight: 800, textTransform: "uppercase", marginBottom: "4px" }}>
                        🗣️ Voice Helper's Advice
                      </div>
                      <p style={{ margin: 0, fontSize: "13px", color: "#374151", fontWeight: 600 }}>
                        {analysisResult.reasoning}
                      </p>
                    </div>
                  )}

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px" }}>
                    {analysisResult.diagnostic_report && (
                      <div style={{ padding: "10px", background: "#faf5ff", borderRadius: "10px", borderTop: "4px solid #c084fc" }}>
                        <span style={{ fontSize: "13px", fontWeight: 800, color: "#7e22ce" }}>🩺 Clinician Diagnostic Report</span>
                        <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "#4b5563", fontWeight: 500, lineHeight: 1.3 }}>{analysisResult.diagnostic_report}</p>
                      </div>
                    )}

                    <div style={{ padding: "10px", background: "#f0fdf4", borderRadius: "10px", borderTop: "4px solid #4ade80" }}>
                      <span style={{ fontSize: "13px", fontWeight: 800, color: "#15803d" }}>📊 Articulation Diagnostics</span>
                      <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "#4b5563", fontWeight: 500, lineHeight: 1.3 }}>
                        <b>Status:</b> {analysisResult.severity_score || "Normal"} <br />
                        <b>Patterns:</b> {analysisResult.error_patterns && analysisResult.error_patterns.length > 0
                          ? analysisResult.error_patterns.join(", ")
                          : "No phonological errors detected."}
                      </p>
                    </div>

                    {analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
                      <div style={{ padding: "10px", background: "#f0f9ff", borderRadius: "10px", borderTop: "4px solid #38bdf8" }}>
                        <span style={{ fontSize: "13px", fontWeight: 800, color: "#0369a1" }}>💨 Acoustic cord check</span>
                        <ul style={{ margin: "4px 0 0 0", paddingLeft: "14px", fontSize: "12px", color: "#4b5563", fontWeight: 500 }}>
                          {analysisResult.recommendations.map((metric, i) => (
                            <li key={i}>{metric}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {linkableLetters.length > 0 && (
                    <div style={{ marginTop: "12px", padding: "10px 12px", background: "#f0f9ff", borderRadius: "10px", border: "2px solid #0ea5e9" }}>
                      <h4 style={{ margin: "0 0 6px 0", color: "#0369a1", fontSize: "13px", fontWeight: 800 }}>✨ Listen & Learn Practice Board:</h4>
                      <p style={{ margin: "0 0 10px 0", fontSize: "12px", color: "#0284c7", fontWeight: 500 }}>
                        We found some sounds to practice. Click any button below to open the interactive keyboard and see how to position your mouth!
                      </p>
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                        {linkableLetters.map((item, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setLetter(item.letter);
                              setSection("alphabet");
                            }}
                            style={{
                              padding: "6px 12px",
                              borderRadius: "999px",
                              border: "none",
                              background: "#0284c7",
                              color: "#fff",
                              fontWeight: 700,
                              fontSize: "12px",
                              cursor: "pointer",
                              boxShadow: "0 4px 8px rgba(2, 132, 199, 0.25)",
                              transition: "all 0.2s ease"
                            }}
                          >
                            🗣️ Learn sound /{item.phoneme}/ (Letter {item.letter})
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
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
            <div style={{ padding: "0 20px 20px 20px" }}>
              <label style={{ fontSize: "13px", fontWeight: 700, color: "#6d28d9" }}>🌐 Select Language:</label>
              <select 
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                style={{
                  padding: "8px 12px",
                  borderRadius: "8px",
                  border: "2px solid #a855f7",
                  background: "#faf5ff",
                  color: "#6d28d9",
                  fontWeight: 600,
                  fontSize: "14px",
                  cursor: "pointer",
                  marginTop: "8px"
                }}
              >
                {INDIAN_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
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
              <button onClick={() => speakIndianEnglish(selectedSound.spoken, false, selectedLanguage)} aria-label={`Hear the letter ${letter}`}>
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