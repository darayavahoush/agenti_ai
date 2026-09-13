import { useState, useEffect, useMemo } from "react";

// Shared playful/animated primitives for the Flashcards selection flow
// (ThemeSelect, WordSelect in SelectionFlow.jsx; CharacterSelect in
// Flashcards.jsx). Kept in one place so the three screens read as one
// cohesive flow instead of drifting apart visually over time.
//
// Design pass (calmer + more polished on purpose): no continuous idle
// motion on cards -- animation happens on entrance and on hover only.
// Palette is a small cohesive set rather than a clashing rainbow. Cards
// get real neutral elevation (shadow) instead of relying on colored glow
// for depth, and SectionHeader/WordPill give the flow a consistent,
// slightly more designed feel instead of plain headings and bare buttons.

export const FUN_COLORS = ["#7C9CFF", "#4ABFBF", "#F2A65A", "#8FD694", "#E58FA0"];

export function useCyclingEmoji(emojis, intervalMs = 1500) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI(v => (v + 1) % emojis.length), intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);
  return emojis[i];
}

// Small tracked-out label + heading + optional subtitle, used above every
// selection screen's card grid so the step dots aren't the only sense of
// progress, and so all three screens share one heading treatment.
export function SectionHeader({ eyebrow, title, subtitle }) {
  return (
    <div style={{ textAlign: "center", marginBottom: "22px" }}>
      {eyebrow && (
        <span style={{
          display: "inline-block", fontSize: "0.65rem", fontWeight: 800,
          letterSpacing: "0.12em", textTransform: "uppercase",
          color: "#A78BFA", marginBottom: "8px", fontFamily: "Nunito, sans-serif",
        }}>
          {eyebrow}
        </span>
      )}
      <h2 style={{ color: "#fff", fontFamily: "Nunito, sans-serif", fontSize: "1.5rem", fontWeight: 900, margin: 0, letterSpacing: "-0.01em" }}>
        {title}
      </h2>
      {subtitle && <p style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.85rem", margin: "6px 0 0" }}>{subtitle}</p>}
    </div>
  );
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
  const stars = useMemo(() => Array.from({ length: 10 }).map((_, i) => ({
    id: i,
    top: Math.random() * 100,
    left: Math.random() * 100,
    size: 1 + Math.random() * 2,
    delay: Math.random() * 4,
    duration: 3 + Math.random() * 3,
  })), []);

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      <div style={{ position: "absolute", top: "-10%", left: "-10%", width: "50%", height: "50%", borderRadius: "50%", background: tint, opacity: 0.07, filter: "blur(70px)", animation: "driftA 20s ease-in-out infinite" }} />
      <div style={{ position: "absolute", bottom: "-15%", right: "-10%", width: "55%", height: "55%", borderRadius: "50%", background: "#4ABFBF", opacity: 0.06, filter: "blur(80px)", animation: "driftB 24s ease-in-out infinite" }} />
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

// Subtle radial gradient instead of flat black -- adds depth at zero
// motion cost. Shared so all three selection screens use one background
// definition rather than each hardcoding '#0d0d1a'.
export const SELECTION_BG = "radial-gradient(ellipse 1100px 650px at 50% -10%, #1c1c3a 0%, #0d0d1a 60%)";

export function GlobalSelectionStyles() {
  return (
    <style>{`
      @keyframes popIn {
        0% { opacity: 0; transform: scale(0.92) translateY(10px); }
        100% { opacity: 1; transform: scale(1) translateY(0); }
      }
      @keyframes wiggle {
        0%, 100% { transform: rotate(0deg); }
        25% { transform: rotate(-3deg); }
        75% { transform: rotate(3deg); }
      }
      @keyframes twinkle {
        0%, 100% { opacity: 0.12; }
        50% { opacity: 0.7; }
      }
      @keyframes driftA {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(24px, 16px); }
      }
      @keyframes driftB {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(-20px, -12px); }
      }
      @keyframes dotPulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(167,139,250,0.4); }
        50% { box-shadow: 0 0 0 5px rgba(167,139,250,0); }
      }
      @keyframes pulseGlow {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 0.85; }
      }
    `}</style>
  );
}

// Circular colored badge behind the icon/emoji -- reads as a proper app
// icon rather than a floating character. Static at rest; PlayCard handles
// the hover wiggle directly on this element via the .pc-visual class.
function PlayCardBadge({ image, imageAlt, emoji, title, color }) {
  return (
    <div
      style={{
        width: "68px", height: "68px", borderRadius: "50%",
        display: "flex", alignItems: "center", justifyContent: "center",
        background: `linear-gradient(145deg, ${color}2b, ${color}0f)`,
        border: `2px solid ${color}44`,
      }}
    >
      {image ? (
        <img src={image} alt={imageAlt || title} className="pc-visual" style={{ width: "40px", height: "40px", objectFit: "contain" }} />
      ) : (
        <span className="pc-visual" style={{ fontSize: "2rem", display: "inline-block" }}>{emoji}</span>
      )}
    </div>
  );
}

const CARD_SHADOW = "0 4px 16px rgba(0,0,0,0.22)";
const CARD_SHADOW_HOVER = "0 8px 24px rgba(0,0,0,0.3)";

export function PlayCard({ emoji, image, imageAlt, title, subtitle, color = "#A78BFA", index = 0, featured = false, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        position: "relative",
        display: "flex", flexDirection: "column", alignItems: "center", gap: "10px",
        background: featured ? `${color}14` : "rgba(255,255,255,0.045)",
        border: featured ? `1.5px solid ${color}66` : `1.5px solid ${color}33`,
        borderRadius: "22px", padding: "24px 12px",
        boxShadow: CARD_SHADOW,
        opacity: 0, animation: `popIn 0.4s cubic-bezier(0.22,1,0.36,1) ${index * 0.05}s forwards`,
        transition: "border-color 0.2s, box-shadow 0.2s, transform 0.15s, background 0.2s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = color;
        e.currentTarget.style.boxShadow = CARD_SHADOW_HOVER;
        e.currentTarget.style.transform = "translateY(-2px)";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "wiggle 0.5s ease-in-out";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = featured ? `${color}66` : `${color}33`;
        e.currentTarget.style.boxShadow = CARD_SHADOW;
        e.currentTarget.style.transform = "translateY(0)";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "none";
      }}
      onMouseDown={e => { e.currentTarget.style.transform = "scale(0.96) translateY(-2px)"; }}
      onMouseUp={e => { e.currentTarget.style.transform = "translateY(-2px)"; }}
    >
      <PlayCardBadge image={image} imageAlt={imageAlt} emoji={emoji} title={title} color={color} />
      <span style={{ color: "#fff", fontSize: "0.88rem", fontWeight: 800, fontFamily: "Nunito, sans-serif" }}>{title}</span>
      {subtitle && <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.65rem", textAlign: "center", lineHeight: 1.3 }}>{subtitle}</span>}
    </button>
  );
}

// Compact pill for word-grid selection -- small circular letter badge +
// label, so the word screen matches the production value of the
// theme/character screens instead of being a step down to plain rectangles.
export function WordPill({ label, color = "#A78BFA", index = 0, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: "8px",
        background: "rgba(255,255,255,0.045)", border: `1.5px solid ${color}33`,
        borderRadius: "14px", padding: "8px 12px", cursor: "pointer",
        boxShadow: CARD_SHADOW,
        opacity: 0, animation: `popIn 0.35s cubic-bezier(0.22,1,0.36,1) ${Math.min(index, 24) * 0.02}s forwards`,
        transition: "border-color 0.2s, box-shadow 0.2s, transform 0.15s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = color;
        e.currentTarget.style.boxShadow = CARD_SHADOW_HOVER;
        e.currentTarget.style.transform = "translateY(-2px)";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = `${color}33`;
        e.currentTarget.style.boxShadow = CARD_SHADOW;
        e.currentTarget.style.transform = "translateY(0)";
      }}
    >
      <span style={{
        width: "22px", height: "22px", borderRadius: "50%", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: `${color}33`, color: "#fff", fontSize: "0.7rem", fontWeight: 800,
        fontFamily: "Nunito, sans-serif", textTransform: "uppercase",
      }}>
        {label[0]}
      </span>
      <span style={{ color: "#fff", fontSize: "0.75rem", fontWeight: 700, fontFamily: "Nunito, sans-serif", textTransform: "capitalize" }}>
        {label}
      </span>
    </button>
  );
}

// Pulsing placeholder tile shaped like a real PlayCard, so the grid
// doesn't visually jump when real data arrives -- used in place of a
// bare "Loading…" line.
export function SkeletonCard({ index = 0 }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", gap: "10px",
      background: "rgba(255,255,255,0.03)", border: "1.5px solid rgba(255,255,255,0.06)",
      borderRadius: "22px", padding: "24px 12px",
      animation: `pulseGlow 1.6s ease-in-out ${index * 0.08}s infinite`,
    }}>
      <div style={{ width: "68px", height: "68px", borderRadius: "50%", background: "rgba(255,255,255,0.06)" }} />
      <div style={{ width: "70%", height: "10px", borderRadius: "6px", background: "rgba(255,255,255,0.06)" }} />
      <div style={{ width: "45%", height: "8px", borderRadius: "6px", background: "rgba(255,255,255,0.04)" }} />
    </div>
  );
}

// Distinguishes "nothing here yet" from "couldn't load" -- an empty
// theme list used to render identically for both cases.
export function EmptyState({ emoji = "🔍", title, subtitle, action }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", gap: "10px",
      padding: "32px 20px", textAlign: "center",
      animation: "popIn 0.4s cubic-bezier(0.22,1,0.36,1) forwards",
    }}>
      <span style={{ fontSize: "2.2rem" }}>{emoji}</span>
      <p style={{ color: "#fff", fontWeight: 800, fontFamily: "Nunito, sans-serif", fontSize: "0.95rem", margin: 0 }}>{title}</p>
      {subtitle && <p style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.8rem", margin: 0, maxWidth: "320px" }}>{subtitle}</p>}
      {action}
    </div>
  );
}
