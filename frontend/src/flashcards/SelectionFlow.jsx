import { useState, useEffect } from "react";
import { getThemes, getWordsForTheme, getWordImage } from "./lib/api";
import { PlayCard, WordPill, StepDots, SectionHeader, PlayfulBackdrop, GlobalSelectionStyles, useCyclingEmoji, FUN_COLORS, SkeletonCard, EmptyState, SELECTION_BG } from "./SelectionUI";

// Selection flow -- staggered pop-in cards, twinkling starfield, per-card
// color cycling, wiggle-on-hover. Shared primitives live in SelectionUI.jsx
// so this file and Flashcards.jsx's CharacterSelect stay visually
// consistent instead of drifting apart.

// Fetches each word's picture with a capped number of requests in
// flight -- a 30-40 word theme firing that many image lookups at once
// (several of which fall through to ARASAAC/Pixabay/DuckDuckGo on a
// cache miss, see matcher.py) would both hammer the backend and not
// actually render any faster than a handful at a time. `isStale` lets
// an in-flight batch bail out once the theme changes again rather than
// racing its results into the next theme's word list.
function loadWordImages(words, concurrency, onImage, isStale) {
  let next = 0;
  async function worker() {
    while (next < words.length) {
      const word = words[next++];
      if (isStale()) return;
      const image = await getWordImage(word);
      if (isStale()) return;
      onImage(word, image);
    }
  }
  Array.from({ length: Math.min(concurrency, words.length) }, worker);
}

export function ThemeSelect({ onPick }) {
  const [themeList, setThemeList] = useState(null);
  const [themeLoadFailed, setThemeLoadFailed] = useState(false);
  const surpriseEmoji = useCyclingEmoji(["🎲", "✨", "🎉", "🌈"]);

  const loadThemes = () => {
    setThemeList(null);
    setThemeLoadFailed(false);
    getThemes().then(d => setThemeList(d.themes)).catch(() => { setThemeList([]); setThemeLoadFailed(true); });
  };

  useEffect(() => { loadThemes(); }, []);

  return (
    <div className="flex-1 flex items-center justify-center" style={{ background: SELECTION_BG, position: "relative", overflow: "hidden" }}>
      <PlayfulBackdrop tint="#C084FC" />
      <GlobalSelectionStyles />
      <div className="fc-clear-menu" style={{ maxWidth: "580px", width: "100%", padding: "24px", position: "relative", zIndex: 1 }}>
        <StepDots current={1} total={3} />
        <SectionHeader title="What do you want to practice? 🎯" subtitle="Pick a topic for your cards" />
        {themeList === null ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" }}>
            {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} index={i} />)}
          </div>
        ) : themeList.length === 0 ? (
          <EmptyState
            emoji={themeLoadFailed ? "😕" : "📭"}
            title={themeLoadFailed ? "Couldn't load topics" : "No topics yet"}
            subtitle={themeLoadFailed ? "Check your connection and try again." : "Ask your therapist to add some!"}
            action={themeLoadFailed && (
              <button
                onClick={loadThemes}
                style={{ background: "#C9662E", border: "none", borderRadius: "14px", padding: "10px 22px", color: "#FFF8EC", fontWeight: 800, cursor: "pointer", fontFamily: "Quicksand, sans-serif", marginTop: "4px" }}
              >
                Try again
              </button>
            )}
          />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" }}>
            {themeList.map((t, i) => (
              <PlayCard
                key={t.id}
                emoji={t.emoji}
                title={t.name}
                subtitle={`${t.word_count} cards`}
                color={FUN_COLORS[i % FUN_COLORS.length]}
                index={i}
                onClick={() => onPick(t.id)}
              />
            ))}
            <PlayCard
              emoji={surpriseEmoji}
              title="Surprise me"
              subtitle="Any topic"
              color="#C084FC"
              index={themeList.length}
              featured
              onClick={() => onPick(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export function WordSelect({ theme, onPick, onBack }) {
  const [words, setWords] = useState(null);
  const [images, setImages] = useState({});
  const surpriseEmoji = useCyclingEmoji(["🎲", "✨", "🎉", "🌈"]);

  useEffect(() => {
    if (!theme) { setWords([]); return; }
    setWords(null);
    setImages({});
    getWordsForTheme(theme).then(d => setWords(d.words)).catch(() => setWords([]));
  }, [theme]);

  // Separate from the word-list load above so a fast re-render (e.g.
  // switching themes twice quickly) doesn't restart the image batch
  // before `words` has actually settled.
  useEffect(() => {
    if (!words || words.length === 0) return;
    let stale = false;
    loadWordImages(words, 5, (word, image) => {
      setImages(prev => (prev[word] === image ? prev : { ...prev, [word]: image }));
    }, () => stale);
    return () => { stale = true; };
  }, [words]);

  return (
    <div className="flex-1 flex items-center justify-center" style={{ background: SELECTION_BG, position: "relative", overflow: "hidden" }}>
      <PlayfulBackdrop tint="#4CD3A5" />
      <GlobalSelectionStyles />
      <div className="fc-clear-menu" style={{ maxWidth: "580px", width: "100%", padding: "24px", position: "relative", zIndex: 1 }}>
        <button onClick={onBack} style={{ background: "none", border: "none", color: "#9A7F68", fontSize: "0.8rem", cursor: "pointer", marginBottom: "12px", fontFamily: "Quicksand, sans-serif", fontWeight: 700 }}>
          ← Back to topics
        </button>
        <StepDots current={2} total={3} />
        <SectionHeader title="Pick a word, or let us choose ✨" />
        {words === null ? (
          <p style={{ color: "#9A7F68", textAlign: "center", fontFamily: "Quicksand, sans-serif" }}>Loading words…</p>
        ) : (
          <>
            <button
              onClick={() => onPick(null)}
              style={{
                width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                background: "#FFFDF7", border: "1.5px solid #B57ED5",
                borderRadius: "4px 12px 4px 12px", padding: "14px", cursor: "pointer", marginBottom: "14px",
                color: "#4A3826", fontWeight: 700, fontFamily: "'Caveat', cursive", fontSize: "1.05rem",
                boxShadow: "0 5px 11px rgba(74,56,38,0.15), 0 2px 4px rgba(74,56,38,0.10)",
                opacity: 0, animation: "popIn 0.35s cubic-bezier(0.22,1,0.36,1) forwards",
              }}
            >
              <span>{surpriseEmoji}</span>
              Surprise me within this topic
            </button>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px", maxHeight: "420px", overflowY: "auto", padding: "4px" }}>
              {words.map((w, i) => (
                <WordPill key={w} label={w} image={images[w] ? `data:image/png;base64,${images[w]}` : undefined} color={FUN_COLORS[i % FUN_COLORS.length]} index={i} onClick={() => onPick(w)} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
