import { useState, useEffect, useMemo } from "react";

// Shared playful/animated primitives for the Flashcards selection flow
// (ThemeSelect, WordSelect in SelectionFlow.jsx; CharacterSelect in
// Flashcards.jsx). Kept in one place so the three screens read as one
// cohesive flow instead of drifting apart visually over time.

export const FUN_COLORS = ["#FF6B6B", "#FFB84C", "#FFE066", "#8CE99A", "#5FD0F3", "#B197FC", "#FF8FE0"];

export function useCyclingEmoji(emojis, intervalMs = 900) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI(v => (v + 1) % emojis.length), intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);
  return emojis[i];
}

export function StepDots({ current, total = 3 }) {
  return (
    <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginBottom: "18px" }}>
      {Array.from({ length: total }).map((_, i) => {
        const active = i + 1 === current;
        const done = i + 1 < current;
        return (
          <div
            key={i}
            style={{
              width: active ? "22px" : "8px",
              height: "8px",
              borderRadius: "999px",
              background: active ? "#A78BFA" : done ? "#A78BFA88" : "rgba(255,255,255,0.15)",
              transition: "all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)",
              animation: active ? "dotPulse 1.4s ease-in-out infinite" : "none",
            }}
          />
        );
      })}
    </div>
  );
}

export function PlayfulBackdrop({ tint = "#A78BFA" }) {
  const stars = useMemo(() => Array.from({ length: 28 }).map((_, i) => ({
    id: i,
    top: Math.random() * 100,
    left: Math.random() * 100,
    size: 1 + Math.random() * 2,
    delay: Math.random() * 4,
    duration: 2 + Math.random() * 3,
  })), []);

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      <div style={{ position: "absolute", top: "-10%", left: "-10%", width: "50%", height: "50%", borderRadius: "50%", background: tint, opacity: 0.10, filter: "blur(70px)", animation: "driftA 14s ease-in-out infinite" }} />
      <div style={{ position: "absolute", bottom: "-15%", right: "-10%", width: "55%", height: "55%", borderRadius: "50%", background: "#4ABFBF", opacity: 0.08, filter: "blur(80px)", animation: "driftB 18s ease-in-out infinite" }} />
      {stars.map(s => (
        <div key={s.id} style={{
          position: "absolute", top: `${s.top}%`, left: `${s.left}%`,
          width: `${s.size}px`, height: `${s.size}px`, borderRadius: "50%",
          background: "#fff", animation: `twinkle ${s.duration}s ease-in-out ${s.delay}s infinite`,
        }} />
      ))}
    </div>
  );
}

export function GlobalSelectionStyles() {
  return (
    <style>{`
      @keyframes popIn {
        0% { opacity: 0; transform: scale(0.4) translateY(14px) rotate(-4deg); }
        60% { opacity: 1; transform: scale(1.08) translateY(-2px) rotate(1deg); }
        100% { opacity: 1; transform: scale(1) translateY(0) rotate(0deg); }
      }
      @keyframes floatY {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
      }
      @keyframes wiggle {
        0%, 100% { transform: rotate(0deg); }
        25% { transform: rotate(-4deg); }
        75% { transform: rotate(4deg); }
      }
      @keyframes twinkle {
        0%, 100% { opacity: 0.15; }
        50% { opacity: 0.9; }
      }
      @keyframes driftA {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(30px, 20px); }
      }
      @keyframes driftB {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(-25px, -15px); }
      }
      @keyframes dotPulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(167,139,250,0.5); }
        50% { box-shadow: 0 0 0 6px rgba(167,139,250,0); }
      }
    `}</style>
  );
}

export function PlayCard({ emoji, image, imageAlt, title, subtitle, color = "#A78BFA", index = 0, dashed = false, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        position: "relative",
        display: "flex", flexDirection: "column", alignItems: "center", gap: "8px",
        background: dashed ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.05)",
        border: dashed ? `2px dashed ${color}66` : `2px solid ${color}44`,
        borderRadius: "18px", padding: "18px 10px", cursor: "pointer",
        opacity: 0, animation: `popIn 0.5s cubic-bezier(0.34,1.56,0.64,1) ${index * 0.06}s forwards`,
        transition: "border-color 0.2s, box-shadow 0.2s, transform 0.15s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = color;
        e.currentTarget.style.boxShadow = `0 8px 24px ${color}33`;
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "wiggle 0.5s ease-in-out";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = dashed ? `${color}66` : `${color}44`;
        e.currentTarget.style.boxShadow = "none";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = `floatY 2.4s ease-in-out ${index * 0.15}s infinite`;
      }}
      onMouseDown={e => { e.currentTarget.style.transform = "scale(0.93)"; }}
      onMouseUp={e => { e.currentTarget.style.transform = "scale(1.04)"; }}
    >
      {image ? (
        <img
          src={image} alt={imageAlt || title} className="pc-visual"
          style={{ width: "56px", height: "56px", objectFit: "contain", animation: `floatY 2.4s ease-in-out ${index * 0.15}s infinite` }}
        />
      ) : (
        <span
          className="pc-visual"
          style={{ fontSize: "2.4rem", display: "inline-block", animation: `floatY 2.4s ease-in-out ${index * 0.15}s infinite` }}
        >
          {emoji}
        </span>
      )}
      <span style={{ color: "#fff", fontSize: "0.82rem", fontWeight: 800, fontFamily: "Nunito, sans-serif" }}>{title}</span>
      {subtitle && <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.62rem", textAlign: "center", lineHeight: 1.3 }}>{subtitle}</span>}
    </button>
  );
}

