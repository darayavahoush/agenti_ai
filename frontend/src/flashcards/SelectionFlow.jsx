import { useState, useEffect } from "react";
import { getThemes, getWordsForTheme } from "./lib/api";
import { PlayCard, StepDots, PlayfulBackdrop, GlobalSelectionStyles, useCyclingEmoji, FUN_COLORS } from "./SelectionUI";

// Playful, animated space-themed selection flow -- staggered pop-in cards,
// twinkling starfield, per-card color cycling, wiggle-on-hover. Shared
// primitives live in SelectionUI.jsx so this file and Flashcards.jsx's
// CharacterSelect stay visually consistent instead of drifting apart.

export function ThemeSelect({ onPick }) {
  const [themeList, setThemeList] = useState(null);
  const surpriseEmoji = useCyclingEmoji(["🎲", "✨", "🎉", "🌈"]);

  useEffect(() => {
    getThemes().then(d => setThemeList(d.themes)).catch(() => setThemeList([]));
  }, []);

  return (
    <div className="flex-1 flex items-center justify-center" style={{ background: '#0d0d1a', position: "relative", overflow: "hidden" }}>
      <PlayfulBackdrop tint="#A78BFA" />
      <GlobalSelectionStyles />
      <div style={{ maxWidth: "580px", width: "100%", padding: "24px", position: "relative", zIndex: 1 }}>
        <StepDots current={1} total={3} />
        <h2 style={{ color: "#fff", fontFamily: "Nunito, sans-serif", fontSize: "1.5rem", fontWeight: 900, textAlign: "center", marginBottom: "6px" }}>
          What do you want to practice? 🎯
        </h2>
        <p style={{ color: "rgba(255,255,255,0.4)", textAlign: "center", fontSize: "0.85rem", marginBottom: "24px" }}>
          Pick a topic for your cards
        </p>
        {themeList === null ? (
          <p style={{ color: "rgba(255,255,255,0.4)", textAlign: "center" }}>Loading topics…</p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
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
              color="#A78BFA"
              index={themeList.length}
              dashed
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
  const surpriseEmoji = useCyclingEmoji(["🎲", "✨", "🎉", "🌈"]);

  useEffect(() => {
    if (!theme) { setWords([]); return; }
    setWords(null);
    getWordsForTheme(theme).then(d => setWords(d.words)).catch(() => setWords([]));
  }, [theme]);

  return (
    <div className="flex-1 flex items-center justify-center" style={{ background: '#0d0d1a', position: "relative", overflow: "hidden" }}>
      <PlayfulBackdrop tint="#4ABFBF" />
      <GlobalSelectionStyles />
      <div style={{ maxWidth: "580px", width: "100%", padding: "24px", position: "relative", zIndex: 1 }}>
        <button onClick={onBack} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", fontSize: "0.8rem", cursor: "pointer", marginBottom: "12px", fontFamily: "Nunito, sans-serif" }}>
          ← Back to topics
        </button>
        <StepDots current={2} total={3} />
        <h2 style={{ color: "#fff", fontFamily: "Nunito, sans-serif", fontSize: "1.5rem", fontWeight: 900, textAlign: "center", marginBottom: "14px" }}>
          Pick a word, or let us choose ✨
        </h2>
        {words === null ? (
          <p style={{ color: "rgba(255,255,255,0.4)", textAlign: "center" }}>Loading words…</p>
        ) : (
          <>
            <button
              onClick={() => onPick(null)}
              style={{
                width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                background: "rgba(167,139,250,0.12)", border: "2px dashed #A78BFA66",
                borderRadius: "14px", padding: "14px", cursor: "pointer", marginBottom: "14px",
                color: "#A78BFA", fontWeight: 800, fontFamily: "Nunito, sans-serif", fontSize: "0.85rem",
                animation: "popIn 0.4s cubic-bezier(0.34,1.56,0.64,1) forwards",
              }}
            >
              <span style={{ display: "inline-block", animation: "floatY 1.8s ease-in-out infinite" }}>{surpriseEmoji}</span>
              Surprise me within this topic
            </button>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px", maxHeight: "320px", overflowY: "auto" }}>
              {words.map((w, i) => {
                const color = FUN_COLORS[i % FUN_COLORS.length];
                return (
                  <button
                    key={w}
                    onClick={() => onPick(w)}
                    style={{
                      background: "rgba(255,255,255,0.05)", border: `1.5px solid ${color}44`,
                      borderRadius: "12px", padding: "10px 6px", cursor: "pointer",
                      color: "#fff", fontSize: "0.75rem", fontWeight: 700, fontFamily: "Nunito, sans-serif",
                      textTransform: "capitalize", transition: "border-color 0.2s, transform 0.15s, box-shadow 0.2s",
                      opacity: 0, animation: `popIn 0.4s cubic-bezier(0.34,1.56,0.64,1) ${Math.min(i, 24) * 0.02}s forwards`,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = color; e.currentTarget.style.boxShadow = `0 6px 16px ${color}33`; e.currentTarget.style.transform = "translateY(-2px)"; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = `${color}44`; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "translateY(0)"; }}
                  >
                    {w}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

