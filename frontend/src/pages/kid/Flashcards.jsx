import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { Sidebar, StarRating } from "../../components/ui";
import { KID_SIDEBAR_ITEMS } from "../../lib/kidSidebarItems";
import { CHARACTERS } from "../../flashcards/characters";
import CharacterBackdrop from "../../flashcards/CharacterBackdrop";
import { ThemeSelect, WordSelect } from "../../flashcards/SelectionFlow";
import { PlayCard, StepDots, PlayfulBackdrop, GlobalSelectionStyles, useCyclingEmoji } from "../../flashcards/SelectionUI";
import { useAudio } from "../../flashcards/hooks/useAudio";
import { evaluateAttempt, speakWord, getRandomWord, getThemes, getPhonemeCard } from "../../flashcards/lib/api";
import { getErrorMessage } from "../../api/client";
import { speak as speakBrowserTTS } from "../../lib/speech";
import { friendlyPhoneme, phonemeExample } from "../../flashcards/utils/phonemeMap";
import { mouthShapeForArpabet } from "../../flashcards/utils/mouthShapeFromPhoneme";
import MouthShapeGuide from "../../vaakmirror/components/MouthShapeGuide";
import { getTheme, getSurface } from "../../flashcards/utils/themes";
import PhonemeHelp from "../../flashcards/PhonemeHelp";

function CharacterSelect({ onPick }) {
  return (
    <div className="flex-1 flex items-center justify-center" style={{ background: '#0d0d1a', position: "relative", overflow: "hidden" }}>
      <PlayfulBackdrop tint="#A78BFA" />
      <GlobalSelectionStyles />
      <div style={{ maxWidth: "480px", width: "100%", padding: "24px", position: "relative", zIndex: 1 }}>
        <StepDots current={3} total={3} />
        <h2 style={{ color: "#fff", fontFamily: "Nunito, sans-serif", fontSize: "1.5rem", fontWeight: 900, textAlign: "center", marginBottom: "6px" }}>
          Who's helping you today? 🚀
        </h2>
        <p style={{ color: "rgba(255,255,255,0.4)", textAlign: "center", fontSize: "0.85rem", marginBottom: "24px" }}>
          Pick a friend to practice words with
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" }}>
          {Object.values(CHARACTERS).map((c, i) => (
            <PlayCard
              key={c.id}
              image={c.image}
              imageAlt={c.name}
              title={c.name}
              subtitle={c.tagline}
              color={c.color}
              index={i}
              onClick={() => onPick(c.id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// Tiered kid-facing framing for a composite_score, replacing a bare percentage
// with a label/emoji/star-count a child can read at a glance.
function resultTier(score) {
  if (score >= 85) return { label: "Amazing!", emoji: "🎉", stars: 3, confetti: true };
  if (score >= 60) return { label: "Nice job!", emoji: "🌟", stars: 2, confetti: false };
  return { label: "Keep practicing!", emoji: "💪", stars: 1, confetti: false };
}

const CONFETTI_BITS = ["🎉", "✨", "⭐", "🎊", "💫"];

export default function Flashcards() {
  const { patient, logout } = useAuth();

  // Setup flow: 'theme' -> 'word' -> 'character' -> 'practice'. Picking
  // "Surprise me" at the theme step skips straight to 'character' with
  // theme/word left null (random.random-word already handles that).
  const [stage, setStage] = useState("theme");
  const [selectedTheme, setSelectedTheme] = useState(null);   // theme id or null (any topic)
  const [character, setCharacter] = useState(null);
  const [themeNames, setThemeNames] = useState({});           // { id: {name, emoji} } for header display

  const [wordData, setWordData] = useState(null);
  const [loadingWord, setLoadingWord] = useState(false);
  const [wordError, setWordError] = useState(null);
  const [themeError, setThemeError] = useState(null);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [attemptNumber, setAttemptNumber] = useState(1);
  const [attemptHistory, setAttemptHistory] = useState([]);
  const [result, setResult] = useState(null);
  const [submitError, setSubmitError] = useState(null);

  const [phase, setPhase] = useState("listen");
  const [playingChar, setPlayingChar] = useState(false);
  const [playingChild, setPlayingChild] = useState(false);
  const [playingInstructions, setPlayingInstructions] = useState(false);
  const [speed, setSpeed] = useState(1.0);  // slidable playback speed, 0.5-1.5x (matches backend atempo range)
  const { isRecording, audioBlob, audioUrl, startRecording, stopRecording, reset } = useAudio();
  const [showSwitcher, setShowSwitcher] = useState(false);      // character switcher (existing)
  const [showTopicSwitcher, setShowTopicSwitcher] = useState(false); // NEW: topic switcher
  const [exploredPhoneme, setExploredPhoneme] = useState(null);  // phoneme badge tapped for learn-before-attempt
  const [exploredCard, setExploredCard] = useState(undefined);   // undefined=loading, null=no card, object=loaded

  const th = character ? getTheme(character, false) : null;
  const loadingEmoji = useCyclingEmoji(["🔍", "🎴", "✨"]);

  const fetchThemeNames = () => {
    setThemeError(null);
    getThemes().then(d => {
      const map = {};
      d.themes.forEach(t => { map[t.id] = t; });
      setThemeNames(map);
    }).catch(() => setThemeError("Couldn't load topics."));
  };
  useEffect(() => { fetchThemeNames(); }, []);

  useEffect(() => {
    if (th) {
      document.body.style.background = th.bg;
      document.body.style.transition = "background 0.5s ease";
    }
  }, [th]);

  const loadNextWord = async (wordOverride) => {
    setLoadingWord(true);
    setWordError(null);
    setResult(null);
    setPhase("listen");
    reset();
    try {
      const data = await getRandomWord({ language: "english", theme: selectedTheme || undefined, word: wordOverride || undefined });
      setWordData(data);
    } catch (err) {
      console.error("Failed to load word", err);
      // Don't leave a stale word on screen while silently failing to
      // refresh it -- clear it so the error state below is unambiguous
      // about needing a retry, rather than looking like nothing happened.
      setWordData(null);
      setWordError("Couldn't load a card. Check your connection and try again.");
    } finally {
      setLoadingWord(false);
    }
  };

  // Runs once, right when the setup flow finishes and character gets set
  // for the first time. `pendingFirstWord` (closed over via ref-like state
  // below) is only honoured for this very first card.
  const [pendingFirstWord, setPendingFirstWord] = useState(null);
  useEffect(() => {
    if (character && stage === "practice") {
      loadNextWord(pendingFirstWord);
      setPendingFirstWord(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [character, stage]);

  const playWord = async (speed = 1.0) => {
    if (!wordData) return;
    setPlayingChar(true);
    try {
      const blob = await speakWord(wordData.word, character, speed);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
      audio.onended = () => setPlayingChar(false);
    } catch (err) {
      console.error('Flashcards: backend speakWord failed, falling back to browser TTS', err);
      // Without a per-character pitch here, every character sounded
      // identical whenever this fallback fired (browser TTS has one voice) --
      // pass the same pitch backend TTS uses so BOLT/ZARA/etc. stay
      // distinguishable even when the real per-character audio is down.
      speakBrowserTTS(wordData.word, { rate: speed >= 1 ? 0.95 : 0.75, pitch: CHARACTERS[character]?.pitch ?? 1.0 });
      setPlayingChar(false);
    }
  };

  const playChildAudio = () => {
    if (!audioUrl) return;
    setPlayingChild(true);
    const audio = new Audio(audioUrl);
    audio.play();
    audio.onended = () => setPlayingChild(false);
  };

  // Speaks the phoneme-card tip text ("Put your top teeth on your bottom
  // lip...") -- same speakWord endpoint the word/phoneme audio already
  // uses, just with the tip's sentence as the text instead of a single
  // word. Mirrors playWord's browser-TTS fallback so this doesn't go
  // silent if the backend voice endpoint is down.
  const playInstructions = async () => {
    if (!exploredCard?.tip) return;
    setPlayingInstructions(true);
    try {
      const blob = await speakWord(exploredCard.tip, character, 0.95);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
      audio.onended = () => setPlayingInstructions(false);
    } catch (err) {
      console.error('Flashcards: backend speakWord failed for instructions, falling back to browser TTS', err);
      speakBrowserTTS(exploredCard.tip, { rate: 0.9, pitch: CHARACTERS[character]?.pitch ?? 1.0 });
      setPlayingInstructions(false);
    }
  };

  const handleRecord = async () => {
    setSubmitError(null);
    setPhase("record");
    await startRecording();
  };

  const handleSubmit = async () => {
    if (!audioBlob || !wordData) return;
    setSubmitError(null);
    setPhase("loading");
    try {
      const res = await evaluateAttempt({
        audio: audioBlob,
        targetWord: wordData.word,
        character,
        language: "english",
        sessionId,
        attemptNumber,
        theme: selectedTheme || wordData?.theme || undefined,
      });
      setAttemptHistory(h => [...h, res]);
      setResult(res);
      setPhase("result");
    } catch (err) {
      console.error(err);
      // The backend now distinguishes "couldn't process this recording"
      // (422, e.g. a broken/empty upload) from a real connectivity failure
      // (no response at all) -- surface whichever actually happened instead
      // of always blaming the connection, which was misleading and made
      // this look like a network bug even when the mic input was the issue.
      setSubmitError(getErrorMessage(err, "Couldn't check that recording. Check your connection and try again."));
      setPhase("record");
    }
  };

  const handleNextCard = () => {
    setAttemptNumber(1);
    setAttemptHistory([]);
    loadNextWord();
  };

  const handleRetry = () => {
    setAttemptNumber(n => n + 1);
    setResult(null);
    setPhase("listen");
    reset();
  };

  // --- Setup flow handlers ---
  const handleThemePick = (themeId) => {
    setSelectedTheme(themeId);
    setStage(themeId ? "word" : "character"); // "Surprise me" (null) skips word-select
  };
  const handleWordPick = (word) => {
    setPendingFirstWord(word); // null = surprise within theme
    setStage("character");
  };

  const handleCharacterPick = (id) => {
    setCharacter(id);
    setStage("practice");
  };
  // --- In-session topic switcher (mirrors the existing character Switch) ---
  const handleSwitchTheme = (themeId) => {
    setSelectedTheme(themeId);
    setShowTopicSwitcher(false);
    loadNextWord(); // fresh random word in the new (or cleared) topic
  };

  const imageUrl = wordData?.image_base64 ? `data:image/png;base64,${wordData.image_base64}` : null;
  const char = character ? CHARACTERS[character] : null;
  const currentThemeLabel = selectedTheme && themeNames[selectedTheme]
    ? `${themeNames[selectedTheme].emoji} ${themeNames[selectedTheme].name}`
    : "🎲 Any topic";

  return (
    <div className="flex min-h-screen" data-fc-root>
      <Sidebar role="kid" items={KID_SIDEBAR_ITEMS} name={patient?.first_name} onLogout={logout} />
      <div className="flex-1 flex flex-col" style={{ background: th?.bg || '#0d0d1a' }}>
        {/* Keyframes (floatY, wiggle, ...) also live inside CharacterSelect/
            ThemeSelect/WordSelect, but those unmount once practice starts --
            mounted here too so the loading/error states below can use them. */}
        <GlobalSelectionStyles />

        {stage === "theme" ? (
          <ThemeSelect onPick={handleThemePick} />
        ) : stage === "word" ? (
          <WordSelect theme={selectedTheme} onPick={handleWordPick} onBack={() => setStage("theme")} />
        ) : stage === "character" ? (
          <CharacterSelect onPick={handleCharacterPick} />
        ) : loadingWord ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "14px" }}>
            <div style={{ fontSize: "2.5rem", animation: "floatY 1.6s ease-in-out infinite" }}>{loadingEmoji}</div>
            <p style={{ color: th.text, fontFamily: "Nunito, sans-serif", opacity: 0.7 }}>Loading a card…</p>
          </div>
        ) : wordError ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "14px", padding: "24px", textAlign: "center" }}>
            <div style={{ fontSize: "2.5rem", animation: "wiggle 2.2s ease-in-out infinite" }}>😕</div>
            <p style={{ color: th?.text || "#fff", fontFamily: "Nunito, sans-serif", fontSize: "1rem" }}>{wordError}</p>
            <button onClick={() => loadNextWord()} style={{ background: th?.accent || "#A78BFA", border: "none", borderRadius: "14px", padding: "12px 24px", color: "#fff", fontWeight: 800, cursor: "pointer", fontFamily: "Nunito, sans-serif" }}>
              Try again
            </button>
          </div>
        ) : !wordData ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "14px" }}>
            <div style={{ fontSize: "2.5rem", animation: "floatY 1.6s ease-in-out infinite" }}>{loadingEmoji}</div>
            <p style={{ color: th?.text || "#fff", fontFamily: "Nunito, sans-serif", opacity: 0.7 }}>Loading a card…</p>
          </div>
        ) : (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "24px 20px", position: "relative" }}>
            <CharacterBackdrop character={character} />
            <div style={{ width: "100%", maxWidth: "980px", display: "flex", flexDirection: "column", gap: "16px", position: "relative", zIndex: 1 }}>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <img src={char.image} alt={char.name} style={{ width: "40px", height: "40px", objectFit: "contain" }} />
                  <span style={{ color: th.text, fontWeight: 800, fontSize: "0.95rem", fontFamily: "Nunito, sans-serif" }}>{char.name}</span>
                </div>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <button onClick={() => { setShowTopicSwitcher(!showTopicSwitcher); setShowSwitcher(false); }} style={{ background: th.card, border: `1.5px solid ${th.accent}44`, borderRadius: "10px", padding: "5px 12px", color: th.sub, fontSize: "0.7rem", fontWeight: 700, cursor: "pointer", fontFamily: "Nunito, sans-serif" }}>
                    {currentThemeLabel}
                  </button>
                  <button onClick={() => { setShowSwitcher(!showSwitcher); setShowTopicSwitcher(false); }} style={{ background: th.card, border: `1.5px solid ${th.accent}44`, borderRadius: "10px", padding: "5px 12px", color: th.sub, fontSize: "0.7rem", fontWeight: 700, cursor: "pointer", fontFamily: "Nunito, sans-serif" }}>Switch</button>
                  <div style={{ background: th.card, border: `1px solid ${th.accent}44`, borderRadius: "20px", padding: "4px 14px", fontSize: "0.75rem", color: th.sub, fontWeight: 700 }}>Attempt {attemptNumber}</div>
                </div>
              </div>

              {showTopicSwitcher && (
                <div style={{ background: getSurface(false, 0.9), border: `1.5px solid ${th.accent}33`, borderRadius: "16px", padding: "14px", boxShadow: `0 4px 20px ${th.accent}18` }}>
                  <p style={{ color: th.sub, fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", margin: "0 0 10px 0" }}>Switch topic</p>
                  {themeError && Object.keys(themeNames).length === 0 && (
                    <div style={{ marginBottom: "10px" }}>
                      <p style={{ color: "#FF6B6B", fontSize: "0.7rem", margin: "0 0 6px 0" }}>{themeError}</p>
                      <button onClick={fetchThemeNames} style={{ background: "transparent", border: `1px solid ${th.accent}66`, borderRadius: "8px", padding: "4px 10px", color: th.accent, fontSize: "0.68rem", cursor: "pointer", fontWeight: 700, fontFamily: "Nunito, sans-serif" }}>
                        Retry
                      </button>
                    </div>
                  )}
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <button onClick={() => handleSwitchTheme(null)} style={{ display: "flex", alignItems: "center", gap: "6px", background: !selectedTheme ? th.card : "transparent", border: `1.5px solid ${!selectedTheme ? th.accent : "rgba(0,0,0,0.08)"}`, borderRadius: "10px", padding: "8px 12px", cursor: "pointer", fontSize: "0.72rem", fontWeight: 700, color: th.text, fontFamily: "Nunito, sans-serif" }}>
                      🎲 Any topic
                    </button>
                    {Object.values(themeNames).map(t => (
                      <button key={t.id} onClick={() => handleSwitchTheme(t.id)} style={{ display: "flex", alignItems: "center", gap: "6px", background: selectedTheme === t.id ? th.card : "transparent", border: `1.5px solid ${selectedTheme === t.id ? th.accent : "rgba(0,0,0,0.08)"}`, borderRadius: "10px", padding: "8px 12px", cursor: "pointer", fontSize: "0.72rem", fontWeight: 700, color: th.text, fontFamily: "Nunito, sans-serif" }}>
                        {t.emoji} {t.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {showSwitcher && (
                <div style={{ background: getSurface(false, 0.9), border: `1.5px solid ${th.accent}33`, borderRadius: "16px", padding: "14px", boxShadow: `0 4px 20px ${th.accent}18` }}>
                  <p style={{ color: th.sub, fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", margin: "0 0 10px 0" }}>Switch character</p>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {Object.values(CHARACTERS).map(c => (
                      <button key={c.id} onClick={() => { setCharacter(c.id); setShowSwitcher(false); }} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px", background: c.id === character ? getTheme(c.id, false).card : "transparent", border: `1.5px solid ${c.id === character ? getTheme(c.id, false).accent : "rgba(0,0,0,0.08)"}`, borderRadius: "10px", padding: "8px 10px", cursor: "pointer" }}>
                        <img src={c.image} alt={c.name} style={{ width: "32px", height: "32px", objectFit: "contain" }} />
                        <span style={{ fontSize: "0.62rem", fontWeight: 700, color: getTheme(c.id, false).text, fontFamily: "Nunito, sans-serif" }}>{c.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: "flex", gap: "16px", alignItems: "flex-start", flexWrap: "wrap", justifyContent: "center", width: "100%" }}>
              <div style={{ flex: "1 1 380px", maxWidth: "480px", background: getSurface(false, 0.7), border: `1.5px solid ${th.accent}33`, borderRadius: "24px", padding: "28px 24px", display: "flex", flexDirection: "column", alignItems: "center", gap: "16px", boxShadow: `0 4px 24px ${th.accent}18` }}>
                {imageUrl ? (
                  <img src={imageUrl} alt={wordData.word} style={{ width: "180px", height: "180px", objectFit: "contain", borderRadius: "16px" }} />
                ) : (
                  <div style={{ width: "140px", height: "140px", background: th.card, borderRadius: "16px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "3rem" }}>🖼️</div>
                )}

                <div style={{ textAlign: "center" }}>
                  <p style={{ color: th.sub, fontSize: "0.65rem", letterSpacing: "0.12em", margin: "0 0 6px 0", fontWeight: 700, textTransform: "uppercase" }}>Target Word</p>
                  <p style={{ fontFamily: "Nunito, sans-serif", fontSize: "2.4rem", fontWeight: 900, color: th.text, margin: 0 }}>{wordData?.word}</p>
                </div>

                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", justifyContent: "center" }}>
                  {(wordData?.phonemes || []).map((p, i) => (
                    <div key={i} title={`Tap to hear more about /${p}/${phonemeExample(p) ? ` — ${phonemeExample(p)}` : ""}`}
                      onClick={async () => {
                        if (exploredPhoneme === p) { setExploredPhoneme(null); return; }
                        setExploredPhoneme(p);
                        setExploredCard(undefined);
                        try {
                          const card = await getPhonemeCard(p);
                          setExploredCard(card);
                        } catch {
                          setExploredCard(null);
                        }
                      }}
                      style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "2px", background: exploredPhoneme === p ? `${th.accent}22` : th.card, border: `1px solid ${th.accent}${exploredPhoneme === p ? "" : "55"}`, borderRadius: "10px", padding: "6px 10px", cursor: "pointer" }}>
                      <span style={{ color: th.accent, fontFamily: "Nunito, sans-serif", fontSize: "0.95rem", fontWeight: 900, lineHeight: 1 }}>
                        {friendlyPhoneme(p)}
                      </span>
                      <span style={{ color: th.sub, fontFamily: "JetBrains Mono, monospace", fontSize: "0.55rem", opacity: 0.6 }}>{p}</span>
                    </div>
                  ))}
                </div>
                <p style={{ color: th.sub, fontSize: "0.65rem", textAlign: "center", margin: "-8px 0 0 0", opacity: 0.7 }}>Tap a sound to learn how to make it</p>
              </div>

              {exploredPhoneme && (
                <div style={{ flex: "1 1 380px", maxWidth: "460px", alignSelf: "stretch", background: getSurface(false, 0.7), border: `1.5px solid ${th.accent}33`, borderRadius: "16px", padding: "24px 20px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "18px" }}>
                  {exploredCard === undefined && <p style={{ color: th.sub, fontSize: "0.8rem", margin: 0, textAlign: "center" }}>Loading...</p>}
                  {exploredCard === null && <p style={{ color: th.sub, fontSize: "0.8rem", margin: 0, textAlign: "center" }}>No tip available for this sound yet.</p>}
                  {exploredCard && (
                    <>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "1.1rem", color: th.accent, fontWeight: 700 }}>{friendlyPhoneme(exploredPhoneme)}</span>
                        <span style={{ color: th.sub, fontFamily: "JetBrains Mono, monospace", fontSize: "0.65rem", opacity: 0.7 }}>/{exploredPhoneme}/</span>
                      </div>
                      {(() => {
                        // Same real illustrated mouth-shape photos Assessment's
                        // alphabet screen and every vaakmirror game use, instead
                        // of the backend's abstract line-art SVG -- only for
                        // phonemes the shared taxonomy actually covers (see
                        // mouthShapeFromPhoneme.js for why vowels fall back).
                        const realShape = mouthShapeForArpabet(exploredPhoneme)
                        if (realShape) {
                          return (
                            <div style={{ width: "180px", height: "180px", flexShrink: 0 }}>
                              <MouthShapeGuide shape={realShape.shape} manner={realShape.manner} className="w-full h-full" />
                            </div>
                          )
                        }
                        return exploredCard.mouth_svg ? (
                          <div style={{ width: "220px", height: "180px", flexShrink: 0 }} dangerouslySetInnerHTML={{ __html: exploredCard.mouth_svg }} />
                        ) : null
                      })()}
                      {exploredCard.tip && (
                        <p style={{ color: th.sub, fontSize: "0.95rem", margin: 0, lineHeight: 1.6, textAlign: "center" }}>
                          {exploredCard.tip}
                        </p>
                      )}
                      {exploredCard.name && (
                        <p style={{ color: th.text, fontWeight: 800, fontSize: "1.1rem", margin: 0, fontFamily: "Nunito, sans-serif", textAlign: "center" }}>{exploredCard.name}</p>
                      )}
                      {exploredCard.example_word && (
                        <p style={{ color: th.sub, fontSize: "0.75rem", margin: 0 }}>
                          Example: <span style={{ color: th.text, fontFamily: "Nunito, sans-serif", fontWeight: 700 }}>{exploredCard.example_word}</span>
                        </p>
                      )}
                      {exploredCard.tip && (
                        <button onClick={playInstructions} disabled={playingInstructions} style={{ background: `${th.accent}22`, border: `1.5px solid ${th.accent}44`, borderRadius: "12px", padding: "12px 20px", color: th.accent, fontSize: "0.9rem", fontWeight: 700, cursor: "pointer", fontFamily: "Nunito, sans-serif" }}>
                          {playingInstructions ? "Playing..." : "🔊 Hear instructions"}
                        </button>
                      )}
                    </>
                  )}
                </div>
              )}
              </div>

              <div style={{ width: "100%", maxWidth: "480px", alignSelf: "center", display: "flex", flexDirection: "column", gap: "16px" }}>
              {phase !== "result" && (
                <>
                  <div style={{ background: getSurface(false, 0.7), border: `1.5px solid ${th.accent}44`, borderRadius: "14px", padding: "14px 16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: th.sub, fontSize: "0.7rem", letterSpacing: "0.08em", fontWeight: 700, textTransform: "uppercase", fontFamily: "Nunito, sans-serif" }}>🐢 Slow &nbsp;·&nbsp; Fast 🐇</span>
                      <span style={{ color: th.accent, fontSize: "0.8rem", fontFamily: "Nunito, sans-serif", fontWeight: 900 }}>{speed.toFixed(2)}x</span>
                    </div>
                    <input
                      type="range" min="0.5" max="1.5" step="0.05" value={speed}
                      onChange={(e) => setSpeed(parseFloat(e.target.value))}
                      onMouseUp={() => playWord(speed)}
                      onTouchEnd={() => playWord(speed)}
                      style={{ width: "100%", accentColor: th.accent, cursor: "pointer" }}
                    />
                    <button onClick={() => playWord(speed)} disabled={playingChar} style={{ background: th.accent, border: "none", borderRadius: "10px", padding: "10px", cursor: "pointer", color: "#fff", fontWeight: 700, fontSize: "0.85rem", fontFamily: "Nunito, sans-serif" }}>
                      {playingChar ? "Playing..." : `🔊 Play at ${speed.toFixed(2)}x`}
                    </button>
                  </div>
                </>
              )}

              {phase === "listen" && (
                <button onClick={handleRecord} style={{ background: th.accent, border: "none", borderRadius: "18px", padding: "22px", fontFamily: "Nunito, sans-serif", fontSize: "1.15rem", fontWeight: 900, color: "#fff", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", boxShadow: `0 4px 20px ${th.accent}44` }}>
                  <span style={{ fontSize: "1.4rem" }}>🎙️</span>
                  Now you try!
                </button>
              )}

              {phase === "record" && isRecording && (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
                  <div style={{ position: "relative", width: "88px", height: "88px" }}>
                    <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "#FF6B6B", opacity: 0.25, animation: "ping 1.2s ease-in-out infinite" }} />
                    <button onClick={stopRecording} style={{ position: "relative", width: "88px", height: "88px", borderRadius: "50%", background: "#FF6B6B", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 20px #FF6B6B44" }}>
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
                        <path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4z"/>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2" fill="none" stroke="white" strokeWidth="2"/>
                        <line x1="12" y1="19" x2="12" y2="23" stroke="white" strokeWidth="2"/>
                        <line x1="8" y1="23" x2="16" y2="23" stroke="white" strokeWidth="2"/>
                      </svg>
                    </button>
                  </div>
                  <p style={{ color: th.sub, fontSize: "0.85rem", fontWeight: 600 }}>Recording... tap to stop</p>
                </div>
              )}

              {phase === "record" && !isRecording && audioBlob && (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {submitError && (
                    <p style={{ color: "#FF6B6B", fontSize: "0.8rem", textAlign: "center", margin: 0, fontWeight: 600 }}>
                      {submitError}
                    </p>
                  )}
                  <div style={{ background: getSurface(false, 0.7), border: `1.5px solid ${th.accent}33`, borderRadius: "16px", padding: "14px", display: "flex", gap: "10px" }}>
                    <button onClick={playChildAudio} disabled={playingChild} style={{ flex: 1, background: "transparent", border: `1.5px solid ${th.accent}44`, borderRadius: "10px", padding: "10px", color: th.sub, fontSize: "0.8rem", cursor: "pointer", fontWeight: 700, fontFamily: "Nunito, sans-serif" }}>
                      {playingChild ? "Playing..." : "Hear yourself"}
                    </button>
                    <button onClick={() => playWord(1.0)} disabled={playingChar} style={{ flex: 1, background: "transparent", border: `1.5px solid ${th.accent}66`, borderRadius: "10px", padding: "10px", color: th.accent, fontSize: "0.8rem", cursor: "pointer", fontWeight: 700, fontFamily: "Nunito, sans-serif" }}>
                      {playingChar ? "Playing..." : `🔊 Hear ${char.name}`}
                    </button>
                  </div>
                  <button onClick={handleSubmit} style={{ background: th.accent, border: "none", borderRadius: "16px", padding: "20px", fontFamily: "Nunito, sans-serif", fontSize: "1.1rem", fontWeight: 900, color: "#fff", cursor: "pointer", boxShadow: `0 4px 20px ${th.accent}44` }}>
                    Check my answer! ✨
                  </button>
                  <button onClick={() => { setSubmitError(null); reset(); setPhase("record"); startRecording(); }} style={{ background: "transparent", border: `1.5px solid ${th.accent}44`, borderRadius: "12px", padding: "12px", color: th.sub, fontSize: "0.85rem", cursor: "pointer", fontFamily: "Nunito, sans-serif", fontWeight: 600 }}>
                    Try again
                  </button>
                  {submitError && (
                    // The scoring backend was unreachable, so there's no result and
                    // the normal "Next card" button (only rendered in phase ===
                    // "result") never appears. Without this, a network hiccup
                    // strands the child on one word with no way forward.
                    <button onClick={handleNextCard} style={{ background: "transparent", border: `1.5px solid ${th.accent}66`, borderRadius: "12px", padding: "12px", color: th.accent, fontSize: "0.85rem", cursor: "pointer", fontFamily: "Nunito, sans-serif", fontWeight: 700 }}>
                      Skip to next word →
                    </button>
                  )}
                </div>
              )}

              {phase === "loading" && (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px", padding: "32px" }}>
                  <div style={{ width: "44px", height: "44px", border: `3px solid ${th.accent}33`, borderTop: `3px solid ${th.accent}`, borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                  <p style={{ color: th.sub, fontSize: "0.85rem", fontWeight: 600 }}>Analysing your voice...</p>
                </div>
              )}

              {phase === "result" && result && (() => {
                const tier = resultTier(result.composite_score);
                const matches = result.phoneme_scores?.matches || [];
                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <div style={{ position: "relative", overflow: "hidden", background: getSurface(false, 0.7), border: `1.5px solid ${th.accent}44`, borderRadius: "20px", padding: "24px 20px", textAlign: "center" }}>
                      {tier.confetti && (
                        <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
                          {CONFETTI_BITS.map((bit, i) => (
                            <span key={i} style={{
                              position: "absolute", left: `${8 + i * 20}%`, top: "-10%",
                              fontSize: "1.4rem", animation: `confettiFall 1.4s ease-in ${i * 0.09}s 1`,
                            }}>{bit}</span>
                          ))}
                        </div>
                      )}

                      {char?.image && (
                        <img src={char.image} alt={char.name} style={{ width: "64px", height: "64px", objectFit: "contain", margin: "0 auto 8px", display: "block", animation: "resultBounce 0.6s ease-out" }} />
                      )}

                      <p style={{ fontSize: "1.35rem", fontWeight: 900, color: th.text, margin: "0 0 2px 0", fontFamily: "Nunito, sans-serif" }}>
                        {tier.emoji} {tier.label}
                      </p>
                      <div style={{ display: "flex", justifyContent: "center", margin: "6px 0" }}>
                        <StarRating stars={tier.stars} max={3} size="lg" />
                      </div>
                      <p style={{ fontSize: "2.2rem", fontWeight: 900, color: th.accent, margin: "4px 0", fontFamily: "Nunito, sans-serif" }}>
                        {Math.round(result.composite_score)}%
                      </p>
                      <p style={{ color: th.sub, fontSize: "0.85rem", margin: "0 0 4px 0" }}>{result.feedback}</p>

                      {matches.length > 0 && (
                        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", justifyContent: "center", marginTop: "12px" }}>
                          {matches.map((m, i) => (
                            <span key={i} title={m.detected || "?"} style={{
                              display: "inline-flex", alignItems: "center", gap: "4px",
                              background: m.correct ? `${th.accent}22` : "rgba(255,107,107,0.15)",
                              border: `1px solid ${m.correct ? th.accent + "55" : "#FF6B6B55"}`,
                              borderRadius: "999px", padding: "4px 10px", fontSize: "0.8rem", fontWeight: 800,
                              color: m.correct ? th.accent : "#FF6B6B", fontFamily: "Nunito, sans-serif",
                            }}>
                              {friendlyPhoneme(m.expected)} {m.correct ? "✓" : "✗"}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {result.acoustic_tips?.length > 0 && result.composite_score < 80 && (
                      <div style={{ background: getSurface(false, 0.8), border: `1.5px solid ${th.accent}33`, borderRadius: "16px", padding: "16px" }}>
                        <p style={{ color: th.sub, fontSize: "0.65rem", letterSpacing: "0.12em", margin: "0 0 10px 0", fontWeight: 700, textTransform: "uppercase" }}>Voice Tips</p>
                        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                          {result.acoustic_tips.map((tip, i) => (
                            <p key={i} style={{ color: th.text, fontSize: "0.85rem", margin: 0, lineHeight: 1.6, paddingLeft: "12px", borderLeft: `3px solid ${th.accent}` }}>{tip.tip}</p>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.composite_score < 80 && matches.some(m => !m.correct) && (
                      <PhonemeHelp matches={matches} th={th} />
                    )}

                    <div style={{ display: "flex", gap: "10px" }}>
                      {result.repeat_needed && attemptNumber < 3 && (
                        <button onClick={handleRetry} style={{ flex: 1, background: "transparent", border: `1.5px solid ${th.accent}66`, borderRadius: "14px", padding: "16px", color: th.accent, fontWeight: 800, cursor: "pointer", fontFamily: "Nunito, sans-serif" }}>
                          Try again
                        </button>
                      )}
                      <button onClick={handleNextCard} style={{ flex: 1, background: th.accent, border: "none", borderRadius: "14px", padding: "16px", color: "#fff", fontWeight: 800, cursor: "pointer", fontFamily: "Nunito, sans-serif" }}>
                        Next card →
                      </button>
                    </div>
                  </div>
                );
              })()}
              </div>
            </div>

            <style>{`
              @keyframes spin { to { transform: rotate(360deg); } }
              @keyframes ping { 75%, 100% { transform: scale(2.2); opacity: 0; } }
              @keyframes confettiFall {
                0%   { transform: translateY(0) rotate(0deg); opacity: 1; }
                100% { transform: translateY(140px) rotate(200deg); opacity: 0; }
              }
              @keyframes resultBounce {
                0%   { transform: scale(0.3) translateY(-10px); opacity: 0; }
                60%  { transform: scale(1.1) translateY(0); opacity: 1; }
                100% { transform: scale(1) translateY(0); opacity: 1; }
              }
              @media (prefers-reduced-motion: reduce) {
                * { animation: none !important; }
              }
            `}</style>
          </div>
        )}
      </div>
    </div>
  );
}
