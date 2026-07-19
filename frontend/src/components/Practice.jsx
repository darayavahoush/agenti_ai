import { useState, useRef, useEffect } from "react";
import { T, RAINBOW, BACKEND, MODE_WORD, MODE_PHONEME } from "../constants";
import { normalizeAudio, encodeWav, playPhonemeAudio } from "../audio";
import { PHONEME_INFO, getPhonemeInfo } from "../phonemeData";
import { Particle, RainbowArc, PhonemeChip, RecordButton, CelebrationOverlay } from "../components";
import { MouthDiagram } from "../MouthDiagram";
import { Card, Button, ProgressBar, BunnyMascot } from "./UI";

export function Practice({ sessionId }) {
  const [mode, setMode] = useState(MODE_WORD);
  const [word, setWord] = useState("");
  const [language, setLanguage] = useState("english");
  const [genPhonemes, setGenPhonemes] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [focusPhoneme, setFocusPhoneme] = useState(null);
  const [phonemeResult, setPhonemeResult] = useState(null);
  const [wordResult, setWordResult] = useState(null);
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [particles, setParticles] = useState([]);
  const [celebration, setCelebration] = useState(false);
  
  const mediaRef = useRef(null);
  const pcmRef = useRef([]);
  const genTimer = useRef(null);

  // Debounced phoneme preview
  useEffect(() => {
    if (!word.trim()) { setGenPhonemes([]); return; }
    clearTimeout(genTimer.current);
    genTimer.current = setTimeout(() => fetchPhonemes(word.trim()), 480);
  }, [word, language]);

   async function fetchPhonemes(w) {
  setGenerating(true);

  try {
    const res = await fetch(
      `${BACKEND}/image/teach`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
               word: w,
               language: language === "hindi" ? "hi" : "en",
        }),
      }
    );

    const data = await res.json();

    setGenPhonemes(
      data.phonemes || []
    );

  } catch {
    setGenPhonemes([]);
  }

  finally {
    setGenerating(false);
  }
}

  async function startRecording() {
    setWordResult(null); setPhonemeResult(null); setCelebration(false); setParticles([]);
    pcmRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio:{ echoCancellation:true, noiseSuppression:true, channelCount:1 },
      });
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      
      // CRITICAL: Modern browsers start AudioContexts in a suspended state.
      // We must explicitly resume it, otherwise it records absolute silence!
      await ctx.resume();
      
      const source = ctx.createMediaStreamSource(stream);
      const proc = ctx.createScriptProcessor(4096,1,1);
      
      proc.onaudioprocess = (e) => pcmRef.current.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      
      source.connect(proc); 
      proc.connect(ctx.destination);
      
      // CRITICAL: Prevent JavaScript garbage collection from deleting the processor mid-recording!
      window.activeAudioProcessor = proc;
      
      mediaRef.current = { stream, ctx, proc, source };
      setRecording(true);
    } catch(err) {
      alert("Microphone access is required to practice.");
    }
  }

  function stopRecording() {
    const { stream, ctx, proc, source } = mediaRef.current || {};
    source?.disconnect(); proc?.disconnect();
    stream?.getTracks().forEach(t => t.stop());
    const total = pcmRef.current.reduce((s,c) => s+c.length, 0);
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of pcmRef.current) { merged.set(c, off); off += c.length; }
    
    // Dynamically grab the context's actual sample rate to prevent audio speed corruption (like playing 3x slower)
    const actualSampleRate = ctx ? ctx.sampleRate : 16000;
    const blob = encodeWav(normalizeAudio(merged), actualSampleRate);
    
    // Clear global hard reference to release memory
    window.activeAudioProcessor = null;
    
    ctx?.close();
    setRecording(false); setLoading(true);
    if (mode === MODE_WORD) sendWord(blob); else sendPhoneme(blob);
  }

  async function sendWord(blob) {

  const fd = new FormData();

  fd.append(
    "file",
    blob,
    "recording.wav"
  );

  fd.append(
    "patient_name",
    "Test Child"
  );

  fd.append(
    "target_word",
    word.trim()
  );

  fd.append(
    "therapy_mode",
    "Full Word Match"
  );
   // Include short language code for backend (en, hi, etc.)
   fd.append("language", language === "hindi" ? "hi" : "en");

  try {

    const res = await fetch(
      `${BACKEND}/speech/therapy`,
      {
        method: "POST",
        body: fd,
      }
    );

    const data = await res.json();

    const converted = {
      transcript: data.spoken_word,
      expected_phonemes: data.expected_phonemes || [],
      matches: data.phoneme_matches || [],
      accuracy: data.accuracy || 0,
      feedback: data.feedback || "",
    };

    setWordResult(converted);

    if (converted.accuracy >= 85) {
      triggerCelebration();
    }

  } catch (err) {

    console.error(err);

    setWordResult({
      error: "Backend not reachable."
    });

  } finally {

    setLoading(false);

  }
}

   async function sendPhoneme(blob) {
      const fd = new FormData();
      fd.append("file", blob, "recording.wav");
      fd.append("target_phoneme", focusPhoneme);
      // Backend expects short language codes (en, hi, te, kn, etc.)
      const langCode = language === "hindi" ? "hi" : language === "telugu" ? "te" : language === "kannada" ? "kn" : "en";
      fd.append("language", langCode);
    try {
      const res = await fetch(`${BACKEND}/speech/compare_phoneme`, { method:"POST", body:fd });
      const data = await res.json();
      if(data.success) {
        setPhonemeResult(data.data);
        if (data.data.correct) triggerCelebration();
      } else {
        setPhonemeResult({ error: data.error?.message || "Analysis failed" });
      }
    } catch { setPhonemeResult({ error:"Backend not reachable." }); }
    finally { setLoading(false); }
  }

  function triggerCelebration() {
    setCelebration(true);
    setParticles(Array.from({ length:40 }, (_, i) => ({
      id:i, x:`${Math.random()*60+20}vw`, y:`${Math.random()*40+10}vh`, color:RAINBOW[i%7],
    })));
    setTimeout(() => { setParticles([]); setCelebration(false); }, 2400);
  }

  function drillPhoneme(ph) {
    setFocusPhoneme(ph); setPhonemeResult(null); setMode(MODE_PHONEME);
  }

  function speakWord(slow = false) {
    if (!word) return;
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = language === "hindi" ? "hi-IN" : "en-IN";
    
    // For English, macOS distorts heavily below 0.6. Hindi handles 0.5 fine.
    utterance.rate = slow ? (language === "hindi" ? 0.5 : 0.6) : 0.95; 
    utterance.pitch = 1.0; // Strictly 1.0 to prevent OS-level distortion on English voices
    
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
      const preferred = voices.find(v => {
        const name = v.name.toLowerCase();
        if (name.includes("nova")) return true;
        
        if (language === "hindi") return v.lang.toLowerCase().includes("hi") && (v.name.includes("Female") || v.name.includes("Google"));
        
        // Prefer Indian English voice
        return v.lang.toLowerCase().startsWith("en-in") || name.includes("veena") || name.includes("heera") || name.includes("google en-in");
      });
      
      const fallback = voices.find(v => v.lang.toLowerCase().startsWith("en-in"));
      const fallback2 = voices.find(v => v.lang.toLowerCase().startsWith("hi-in"));
      const fallback3 = voices.find(v => v.lang.toLowerCase().startsWith("en"));
      
      if (preferred) utterance.voice = preferred;
      else if (fallback) utterance.voice = fallback;
      else if (fallback2) utterance.voice = fallback2;
      else if (fallback3) utterance.voice = fallback3;
    }
    
    window.speechSynthesis.speak(utterance);
  }

  const expectedList = wordResult?.expected_phonemes || [];
  const matches = wordResult?.matches || [];
  const chipStatuses = expectedList.map((_, i) => {
    const m = matches[i]; if (!m) return "missing";
    return m.correct ? "correct" : "wrong";
  });
  const correctCount = chipStatuses.filter(s => s === "correct").length;
   const expectedDisplay = wordResult?.expected_phonemes_display || expectedList;
   const spokenDisplay = wordResult?.spoken_phonemes_display || wordResult?.spoken_phonemes || [];
  
  const canRecord = mode === MODE_WORD
    ? (genPhonemes.length > 0 && !loading && !generating)
    : (focusPhoneme !== null && !loading);
    
  const info = focusPhoneme ? getPhonemeInfo(focusPhoneme) : null;

  return (
    <div style={{ position: "relative" }}>
      {particles.map(p => <Particle key={p.id} x={p.x} y={p.y} color={p.color} />)}
      <CelebrationOverlay show={celebration} />

      {/* Header & Mode Switcher */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "40px" }}>
         <div>
            <h1 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "36px", fontWeight: 900, color: T.text, margin: 0 }}>
               Ready to Practice?
            </h1>
            <p style={{ color: T.textMuted, fontSize: "16px", marginTop: "8px" }}>Select a mode and start speaking.</p>
         </div>

         <div style={{ display: "flex", gap: "8px", background: "#FFF5EF", padding: "8px", borderRadius: "100px", border: `1px solid ${T.border}` }}>
            {[MODE_WORD, MODE_PHONEME].map(m => {
               const active = mode === m;
               return (
                  <button key={m} onClick={() => { setMode(m); setWordResult(null); setPhonemeResult(null); }} className="clickable" style={{
                     padding: "12px 32px",
                     borderRadius: "100px",
                     border: "none",
                     background: active ? T.surface : "transparent",
                     color: active ? T.primary : T.textMuted,
                     fontFamily: "'Nunito', sans-serif",
                     fontWeight: active ? 800 : 600,
                     fontSize: "16px",
                     boxShadow: active ? T.shadowSm : "none",
                     transition: "all 0.3s ease"
                  }}>
                     {m === MODE_WORD ? "Word Mode" : "Phoneme Drill"}
                  </button>
               );
            })}
         </div>
      </div>

      {/* 2-Column Layout for Desktop */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "40px", alignItems: "start" }}>
         
         {/* LEFT COLUMN: Input & Action */}
         <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            
            {mode === MODE_WORD && (
               <Card delay="0s">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
                     <h3 style={{ margin: 0, fontFamily: "'Nunito', sans-serif", fontSize: "20px", color: T.text }}>Target Configuration</h3>
                     <div style={{ display:"flex", gap:"8px", background: "#FFF5EF", padding: "4px", borderRadius: "100px" }}>
                        {["english","hindi"].map(lang => {
                           const active = language === lang;
                           return (
                              <button key={lang} onClick={() => { setLanguage(lang); setWordResult(null); setGenPhonemes([]); }} className="clickable" style={{
                                 padding: "6px 16px", borderRadius: "100px", border: "none",
                                 background: active ? T.surface : "transparent",
                                 color: active ? T.primary : T.textMuted,
                                 fontFamily: "'Nunito', sans-serif", fontSize: "14px", fontWeight: 700,
                                 boxShadow: active ? T.shadowSm : "none", transition: "all 0.2s"
                              }}>
                                 {lang === "english" ? "EN" : "HI"}
                              </button>
                           );
                        })}
                     </div>
                  </div>

                  <label style={{ display:"block", fontSize:"12px", color:T.textMuted, fontWeight:700, textTransform:"uppercase", letterSpacing:"1px", marginBottom:"8px" }}>
                     Enter Target Word
                  </label>
                  <input value={word} onChange={e => { setWord(e.target.value); setWordResult(null); }}
                     placeholder={language === "english" ? "e.g. elephant" : "e.g. बाल"}
                     style={{
                        width: "100%", background: "#FFF5EF", border: `2px solid ${T.border}`, borderRadius: "16px",
                        padding: "16px 24px", color: T.text, fontFamily: "'Nunito', sans-serif", fontSize: "24px", fontWeight: 700,
                        outline: "none", marginBottom: "16px", transition: "all 0.3s"
                     }}
                     onFocus={e => { e.target.style.borderColor = T.primary; e.target.style.boxShadow = `0 0 0 4px ${T.primary}22`; }}
                     onBlur={e => { e.target.style.borderColor = T.border; e.target.style.boxShadow = "none"; }}
                  />

                  {/* Character TTS Example */}
                  {word && (
                     <div className="animate-pop-in" style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "16px", background: "white", padding: "12px 16px", borderRadius: "20px", border: `2px solid ${T.border}`, boxShadow: T.shadowSm }}>
                        <div style={{ flexShrink: 0 }}>
                           <BunnyMascot size={50} mood="speaking" style={{ animation: "none" }} />
                        </div>
                        <div style={{ flex: 1 }}>
                           <div style={{ fontSize: "14px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>Example</div>
                           <div style={{ fontSize: "16px", color: T.text, fontWeight: 800 }}>Listen how to say it</div>
                        </div>
                        <button onClick={() => speakWord(false)} className="clickable" style={{ width: "48px", height: "48px", borderRadius: "50%", background: T.primary, color: "white", border: "none", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: T.shadowSm }} title="Normal Speed">
                           <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                           </svg>
                        </button>
                        <button onClick={() => speakWord(true)} className="clickable" style={{ width: "48px", height: "48px", borderRadius: "50%", background: T.secondary, color: "white", border: "none", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: T.shadowSm }} title="Slow Speed">
                           <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                              <circle cx="18" cy="12" r="3" />
                              <polyline points="18 10 18 12 19 13" />
                           </svg>
                        </button>
                     </div>
                  )}

                  {generating && (
                     <div style={{ fontSize:"14px", color:T.secondary, fontFamily:"'Nunito', sans-serif", fontWeight: 700, display:"flex", alignItems:"center", gap:"8px" }}>
                        <span style={{ display:"inline-block", width:8, height:8, borderRadius:"50%", background:T.secondary, animation:"pulseSoft 1s ease infinite" }} />
                        Analyzing phonemes...
                     </div>
                  )}

                  {!generating && genPhonemes.length > 0 && (
                     <div style={{ background: "#FFF5EF", padding: "16px", borderRadius: "16px" }}>
                        <div style={{ fontSize:"12px", color:T.textMuted, fontWeight:700, textTransform:"uppercase", letterSpacing:"1px", marginBottom:"12px" }}>
                           Expected Phonemes
                        </div>
                        <div style={{ display:"flex", flexWrap:"wrap", gap:"8px" }}>
                           {genPhonemes.map((p, i) => (
                              <span key={i} style={{
                                 padding:"6px 12px", borderRadius:"10px",
                                 background:T.surface, border:`1px solid ${T.border}`,
                                 color:T.primary, fontFamily:"'JetBrains Mono', monospace", fontSize:"16px", fontWeight:700,
                                 boxShadow: T.shadowSm
                              }}>{p}</span>
                           ))}
                        </div>
                     </div>
                  )}

                  <div style={{ marginTop: "32px" }}>
                     <RecordButton recording={recording} loading={loading} disabled={!canRecord} onStart={startRecording} onStop={stopRecording} />
                  </div>
               </Card>
            )}

            {mode === MODE_PHONEME && (
               <Card delay="0s">
                  {!focusPhoneme ? (
                     <div>
                        <h3 style={{ margin: 0, fontFamily: "'Nunito', sans-serif", fontSize: "20px", color: T.text, marginBottom: "20px" }}>Select a Phoneme</h3>
                        <div style={{ display:"flex", flexWrap:"wrap", gap: "8px" }}>
                           {Object.keys(PHONEME_INFO).map(ph => (
                              <PhonemeChip key={ph} phoneme={ph} status="pending" onClick={() => drillPhoneme(ph)} />
                           ))}
                        </div>
                     </div>
                  ) : (
                     <div>
                        <div style={{ display:"flex", alignItems:"center", justifyContent: "space-between", marginBottom: "24px" }}>
                           <button onClick={() => { setFocusPhoneme(null); setPhonemeResult(null); }} className="clickable" style={{
                              background: "transparent", border: `2px solid ${T.border}`, borderRadius: "100px",
                              color: T.textMuted, padding: "8px 16px", cursor: "pointer",
                              fontFamily: "'Nunito', sans-serif", fontSize: "14px", fontWeight: 700, transition: "all 0.2s"
                           }}>
                              ← Back to List
                           </button>
                           
                           <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                              <div style={{ fontFamily:"'JetBrains Mono', monospace", fontSize:"42px", fontWeight:700, color:T.primary }}>
                                 /{focusPhoneme}/
                              </div>
                              <button onClick={() => playPhonemeAudio(info.example)} className="clickable" title={`Hear /${focusPhoneme}/`} style={{
                                 width: "48px", height: "48px", borderRadius: "50%", background: T.primary, border: "none",
                                 color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center",
                                 boxShadow: `0 8px 20px rgba(250, 93, 119, 0.4)`, cursor: "pointer", transition: "transform 0.2s"
                              }}>
                                 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                                 </svg>
                              </button>
                           </div>
                        </div>
                        
                        <div style={{ background: "#FFF5EF", padding: "20px", borderRadius: "16px", marginBottom: "24px" }}>
                           <h4 style={{ margin: "0 0 12px 0", fontSize: "14px", color: T.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>Example Word</h4>
                           <div style={{ fontSize: "20px", color: T.text, fontWeight: 800, fontStyle: "italic" }}>"{info.example}"</div>
                        </div>

                        <RecordButton recording={recording} loading={loading} disabled={!canRecord} onStart={startRecording} onStop={stopRecording} />
                     </div>
                  )}
               </Card>
            )}

         </div>

         {/* RIGHT COLUMN: Results & Feedback */}
         <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            
            {/* Word Mode Result */}
            {mode === MODE_WORD && wordResult && !wordResult.error && (
               <Card delay="0.2s" style={{ border: `2px solid ${wordResult.accuracy >= 80 ? T.correct : wordResult.accuracy >= 50 ? T.secondary : T.wrong}` }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: "32px" }}>
                     <div style={{ fontSize: "14px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", marginBottom: "16px" }}>
                        Accuracy Score
                     </div>
                     <div style={{ position: "relative" }}>
                        {/* Desktop version of the Rainbow Arc - simplified to a sleek circular progress or just the arc */}
                        <RainbowArc correctCount={correctCount} totalCount={expectedList.length} />
                        <div style={{ 
                           position: "absolute", bottom: "10px", left: "50%", transform: "translateX(-50%)",
                           fontSize: "56px", fontWeight: 900, fontFamily: "'Nunito', sans-serif",
                           color: wordResult.accuracy >= 80 ? T.correct : wordResult.accuracy >= 50 ? T.secondary : T.wrong,
                           textShadow: `0 4px 12px rgba(0,0,0,0.1)`
                        }}>
                           {wordResult.accuracy}%
                        </div>
                     </div>
                  </div>

                  <div style={{ marginBottom: "32px" }}>
                     <div style={{ fontSize:"12px", color:T.textMuted, fontWeight:700, textTransform:"uppercase", letterSpacing:"1px", marginBottom:"12px" }}>
                        Phoneme Breakdown
                     </div>
                     <div style={{ display:"flex", flexWrap:"wrap", gap:"12px" }}>
                        {expectedList.map((ph, i) => (
                           <PhonemeChip key={i} phoneme={ph} status={chipStatuses[i]} onClick={() => drillPhoneme(ph)} />
                        ))}
                     </div>
                        {expectedDisplay && expectedDisplay.length > 0 && (
                           <div style={{ marginTop: "12px", fontSize: "13px", color: T.textMuted }}>
                              Expected (native): <strong style={{ fontFamily: "'JetBrains Mono', monospace" }}>{expectedDisplay.join(' ')}</strong>
                           </div>
                        )}
                        {spokenDisplay && spokenDisplay.length > 0 && (
                           <div style={{ marginTop: "6px", fontSize: "13px", color: T.textMuted }}>
                              Detected (native): <strong style={{ fontFamily: "'JetBrains Mono', monospace" }}>{spokenDisplay.join(' ')}</strong>
                           </div>
                        )}
                  </div>

                  <div style={{ background: "#FFF5EF", padding: "24px", borderRadius: "20px" }}>
                     <div style={{ fontSize:"12px", color:T.textMuted, fontWeight:700, textTransform:"uppercase", letterSpacing:"1px", marginBottom:"8px" }}>
                        What we heard
                     </div>
                     <div style={{ fontSize: "20px", color: T.text, fontWeight: 800, fontStyle: "italic", marginBottom: "20px" }}>
                        "{wordResult.transcript || "..."}"
                     </div>

                     <div style={{ fontSize:"12px", color:T.textMuted, fontWeight:700, textTransform:"uppercase", letterSpacing:"1px", marginBottom:"8px" }}>
                        AI Therapist Feedback
                     </div>
                     <div style={{ fontSize: "16px", color: T.text, lineHeight: 1.6, paddingLeft: "16px", borderLeft: `4px solid ${T.primary}` }}>
                        {wordResult.feedback}
                     </div>
                  </div>
               </Card>
            )}

            {mode === MODE_WORD && wordResult?.error && (
               <Card delay="0.1s" style={{ borderColor: T.wrong }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "16px", color: T.wrong }}>
                     <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                        <line x1="12" x2="12" y1="9" y2="13"/>
                        <line x1="12" x2="12.01" y1="17" y2="17"/>
                     </svg>
                     <div style={{ fontSize: "18px", fontWeight: 700 }}>{wordResult.error}</div>
                  </div>
               </Card>
            )}

            {/* Word Mode empty state */}
            {mode === MODE_WORD && !wordResult && (
               <div className="animate-slide-up" style={{ 
                  height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", 
                  padding: "40px", border: `2px dashed ${T.border}`, borderRadius: "32px", color: T.textMuted 
               }}>
                  <div style={{ color: T.textMuted, marginBottom: "20px" }}>
                     <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5 }}>
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                        <line x1="12" x2="12" y1="19" y2="22" />
                     </svg>
                  </div>
                  <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "24px", color: T.text, marginBottom: "8px" }}>Waiting for audio</h3>
                  <p style={{ textAlign: "center", maxWidth: "300px", lineHeight: 1.6 }}>Type a word on the left, hit record, and we'll analyze your pronunciation here.</p>
               </div>
            )}

            {/* Phoneme Mode Instructions & Result */}
            {mode === MODE_PHONEME && focusPhoneme && info && (
               <Card delay="0.1s">
                  <div style={{ display: "flex", gap: "24px", marginBottom: "32px" }}>
                     <div style={{ flexShrink: 0, background: "#FFF5EF", borderRadius: "24px", padding: "16px", border: `1px solid ${T.border}` }}>
                        <MouthDiagram svgKey={info.svg} />
                        <div style={{ textAlign: "center", marginTop: "12px", fontSize: "12px", color: T.textMuted, fontWeight: 700, letterSpacing: "1px", textTransform: "uppercase" }}>Anatomy</div>
                     </div>
                     
                     <div>
                        <h4 style={{ margin: "0 0 12px 0", fontSize: "16px", color: T.text, fontWeight: 800 }}>How to pronounce it:</h4>
                        <ol style={{ margin: 0, paddingLeft: "20px", color: T.text, fontSize: "15px", lineHeight: 1.8 }}>
                           {info.steps.map((step, i) => (
                              <li key={i}>{step}</li>
                           ))}
                        </ol>
                     </div>
                  </div>

                  {phonemeResult && !phonemeResult.error && (
                     <div className="animate-pop-in" style={{ 
                        background: phonemeResult.correct ? T.correctBg : T.wrongBg, 
                        border: `2px solid ${phonemeResult.correct ? T.correct : T.wrong}`,
                        borderRadius: "24px", padding: "32px", textAlign: "center" 
                     }}>
                        <div style={{ marginBottom: "16px", color: phonemeResult.correct ? '#16a34a' : '#dc2626', display: "flex", justifyContent: "center" }}>
                            {phonemeResult.correct ? (
                               <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                            ) : (
                               <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><polyline points="3 3 3 8 8 8"/></svg>
                            )}
                         </div>
                        <h3 style={{ margin: "0 0 12px 0", fontFamily: "'Nunito', sans-serif", fontSize: "24px", color: phonemeResult.correct ? '#16a34a' : '#dc2626' }}>
                           {phonemeResult.correct ? "Perfect! You got it!" : "Almost there, try again!"}
                        </h3>
                        <div style={{ color: T.text, fontSize: "16px", marginBottom: "16px", opacity: 0.8 }}>
                           We heard: <strong>"{phonemeResult.transcript || "..."}"</strong>
                        </div>
                        {phonemeResult.detected_phonemes_display && (
                           <div style={{ color: T.textMuted, fontSize: "14px", marginBottom: "12px" }}>
                              Detected phoneme(s): <strong style={{ fontFamily: "'JetBrains Mono', monospace" }}>{phonemeResult.detected_phonemes_display.join(' ')}</strong>
                           </div>
                        )}
                        {!phonemeResult.correct && (
                           <div style={{ background: "rgba(255,255,255,0.7)", padding: "16px", borderRadius: "12px", fontSize: "15px", lineHeight: 1.6, textAlign: "left" }}>
                              <strong>Tip:</strong> {phonemeResult.feedback}
                           </div>
                        )}
                     </div>
                  )}

                  {phonemeResult?.error && (
                     <div style={{ background: T.wrongBg, border: `2px solid ${T.wrong}`, borderRadius: "24px", padding: "24px", color: T.wrong, display: "flex", alignItems: "center", gap: "12px" }}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                           <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                           <line x1="12" x2="12" y1="9" y2="13"/>
                           <line x1="12" x2="12.01" y1="17" y2="17"/>
                        </svg>
                        <strong>{phonemeResult.error}</strong>
                     </div>
                  )}
               </Card>
            )}

         </div>

      </div>
    </div>
  );
}
