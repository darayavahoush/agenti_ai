import { useState, useEffect, useMemo } from "react";

// Shared playful/animated primitives for the Flashcards selection flow
// (ThemeSelect, WordSelect in SelectionFlow.jsx; CharacterSelect in
// Flashcards.jsx). Kept in one place so the three screens read as one
// cohesive flow instead of drifting apart visually over time.
//
// "Sticker card" design pass: solid color-tinted fills and a hard offset
// shadow instead of a near-invisible white wash + soft blur, so cards
// read as physical stickers rather than generic dark-mode SaaS cards.
// Titles use Baloo 2 (already loaded app-wide, just unused here) so
// headings carry real personality instead of sharing Nunito with every
// label and eyebrow. WordTile gives the word-select grid the same
// card weight as the theme/character screens -- it used to be a step
// down to plain pills, which is a big part of why it read as flatter
// and more "clinical" than the rest of the flow.

export const FUN_COLORS = ["#FF6F59", "#FFB238", "#4CD3A5", "#4FA8FF", "#C084FC", "#FF6FB0"];
const DISPLAY_FONT = "'Baloo 2', 'Nunito', sans-serif";

export function useCyclingEmoji(emojis, intervalMs = 1500) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI(v => (v + 1) % emojis.length), intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);
  return emojis[i];
}

// Heading + optional subtitle above every selection screen's card grid.
// No uppercase tracked-out eyebrow chip -- StepDots already carries
// progress, so a second "STEP X OF 3" label was redundant chrome. Title
// is set in Baloo 2 so it reads as a real headline, not body text at a
// bigger size.
export function SectionHeader({ title, subtitle }) {
  return (
    <div style={{ textAlign: "center", marginBottom: "24px" }}>
      <h2 style={{ color: "#FFF7ED", fontFamily: DISPLAY_FONT, fontSize: "1.7rem", fontWeight: 700, margin: 0, letterSpacing: "-0.01em" }}>
        {title}
      </h2>
      {subtitle && <p style={{ color: "rgba(255,247,237,0.5)", fontFamily: "Nunito, sans-serif", fontSize: "0.85rem", margin: "6px 0 0" }}>{subtitle}</p>}
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
              background: active ? "#C084FC" : done ? "#C084FC88" : "rgba(255,255,255,0.15)",
              transition: "all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)",
              animation: active ? "dotPulse 1.4s ease-in-out infinite" : "none",
            }}
          />
        );
      })}
    </div>
  );
}

export function PlayfulBackdrop({ tint = "#C084FC" }) {
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
      <div style={{ position: "absolute", bottom: "-15%", right: "-10%", width: "55%", height: "55%", borderRadius: "50%", background: "#4CD3A5", opacity: 0.06, filter: "blur(80px)", animation: "driftB 24s ease-in-out infinite" }} />
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
export const SELECTION_BG = "radial-gradient(ellipse 1100px 650px at 50% -10%, #251a3f 0%, #140f24 60%)";

export function GlobalSelectionStyles() {
  return (
    <style>{`
      /* Phones: the sidebar becomes a floating 44px hamburger pinned at
         top-left (16px inset, see Sidebar.jsx). Nothing on these pages
         reserved room for it, so it sat on top of the first thing in the
         corner -- the character/name in the practice header and the
         "Back to topics" button on the selection steps. Push content
         below it, and let the practice header wrap instead of squeezing
         the topic / Switch / Attempt pills into one 350px row. */
      @media (max-width: 767px) {
        .fc-clear-menu { padding-top: 68px !important; }
        .fc-head { flex-wrap: wrap; row-gap: 10px; }
        .fc-head-actions { flex-wrap: wrap; }
      }
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
        0%, 100% { box-shadow: 0 0 0 0 rgba(192,132,252,0.4); }
        50% { box-shadow: 0 0 0 5px rgba(192,132,252,0); }
      }
      @keyframes pulseGlow {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 0.85; }
      }
    `}</style>
  );
}

// Circular sticker-style badge behind the icon/emoji/letter -- solid
// color fill with a soft gloss highlight and a light ring, so it reads
// as a proper badge rather than a faint tinted outline. Static at rest;
// PlayCard/WordTile handle the hover wiggle on this element via the
// .pc-visual class.
function PlayCardBadge({ image, imageAlt, emoji, letter, title, color, size = 68 }) {
  return (
    <div
      style={{
        width: `${size}px`, height: `${size}px`, borderRadius: "50%", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: `linear-gradient(150deg, ${color} 0%, ${color}cc 100%)`,
        border: "3px solid rgba(255,255,255,0.3)",
        boxShadow: `inset 0 2px 4px rgba(255,255,255,0.35), inset 0 -6px 10px rgba(0,0,0,0.18)`,
      }}
    >
      {image ? (
        <img src={image} alt={imageAlt || title} className="pc-visual" style={{ width: `${size * 0.58}px`, height: `${size * 0.58}px`, objectFit: "contain" }} />
      ) : emoji ? (
        <span className="pc-visual" style={{ fontSize: `${size * 0.42}px`, display: "inline-block" }}>{emoji}</span>
      ) : (
        <span className="pc-visual" style={{ fontSize: `${size * 0.4}px`, fontWeight: 700, color: "#fff", fontFamily: DISPLAY_FONT, textShadow: "0 2px 2px rgba(0,0,0,0.2)" }}>{letter}</span>
      )}
    </div>
  );
}

// Hard offset "sticker" shadow instead of a soft blurred SaaS shadow --
// colored so it reads as the card's own edge lifting off the page
// rather than generic ambient elevation.
const stickerShadow = (color, lift = false) =>
  `0 ${lift ? 6 : 4}px 0 ${color}59, 0 ${lift ? 14 : 8}px ${lift ? 26 : 18}px rgba(0,0,0,0.35)`;

export function PlayCard({ emoji, image, imageAlt, title, subtitle, color = "#C084FC", index = 0, featured = false, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        position: "relative",
        display: "flex", flexDirection: "column", alignItems: "center", gap: "10px",
        background: `${color}26`,
        border: `2px solid ${color}${featured ? "cc" : "88"}`,
        borderRadius: "22px", padding: "24px 12px",
        boxShadow: stickerShadow(color),
        opacity: 0, animation: `popIn 0.4s cubic-bezier(0.22,1,0.36,1) ${index * 0.05}s forwards`,
        transition: "border-color 0.2s, box-shadow 0.15s, transform 0.15s, background 0.2s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = stickerShadow(color, true);
        e.currentTarget.style.transform = "translateY(-3px)";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "wiggle 0.5s ease-in-out";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = stickerShadow(color);
        e.currentTarget.style.transform = "translateY(0)";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "none";
      }}
      onMouseDown={e => { e.currentTarget.style.transform = "translateY(2px)"; e.currentTarget.style.boxShadow = `0 1px 0 ${color}59, 0 2px 6px rgba(0,0,0,0.3)`; }}
      onMouseUp={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = stickerShadow(color, true); }}
    >
      <PlayCardBadge image={image} imageAlt={imageAlt} emoji={emoji} title={title} color={color} />
      <span style={{ color: "#FFF7ED", fontSize: "0.95rem", fontWeight: 700, fontFamily: DISPLAY_FONT }}>{title}</span>
      {subtitle && <span style={{ color: "rgba(255,247,237,0.55)", fontSize: "0.65rem", textAlign: "center", lineHeight: 1.3, fontFamily: "Nunito, sans-serif" }}>{subtitle}</span>}
    </button>
  );
}

// Word-grid tile -- same sticker-card weight as PlayCard (badge + label,
// stacked) instead of the old flat horizontal pill, so step 2 of the
// flow doesn't read as a downgrade from steps 1 and 3.
export function WordPill({ label, color = "#C084FC", index = 0, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", flexDirection: "column", alignItems: "center", gap: "8px",
        background: `${color}26`, border: `2px solid ${color}88`,
        borderRadius: "18px", padding: "14px 8px",
        boxShadow: stickerShadow(color),
        opacity: 0, animation: `popIn 0.35s cubic-bezier(0.22,1,0.36,1) ${Math.min(index, 24) * 0.02}s forwards`,
        transition: "box-shadow 0.15s, transform 0.15s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = stickerShadow(color, true);
        e.currentTarget.style.transform = "translateY(-3px)";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "wiggle 0.5s ease-in-out";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = stickerShadow(color);
        e.currentTarget.style.transform = "translateY(0)";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "none";
      }}
      onMouseDown={e => { e.currentTarget.style.transform = "translateY(2px)"; e.currentTarget.style.boxShadow = `0 1px 0 ${color}59, 0 2px 6px rgba(0,0,0,0.3)`; }}
      onMouseUp={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = stickerShadow(color, true); }}
    >
      <PlayCardBadge letter={label[0].toUpperCase()} title={label} color={color} size={48} />
      <span style={{ color: "#FFF7ED", fontSize: "0.8rem", fontWeight: 700, fontFamily: DISPLAY_FONT, textTransform: "capitalize" }}>
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
      background: "rgba(255,255,255,0.04)", border: "2px solid rgba(255,255,255,0.07)",
      borderRadius: "22px", padding: "24px 12px",
      animation: `pulseGlow 1.6s ease-in-out ${index * 0.08}s infinite`,
    }}>
      <div style={{ width: "68px", height: "68px", borderRadius: "50%", background: "rgba(255,255,255,0.08)" }} />
      <div style={{ width: "70%", height: "10px", borderRadius: "6px", background: "rgba(255,255,255,0.08)" }} />
      <div style={{ width: "45%", height: "8px", borderRadius: "6px", background: "rgba(255,255,255,0.06)" }} />
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
      <p style={{ color: "#FFF7ED", fontWeight: 700, fontFamily: DISPLAY_FONT, fontSize: "1.05rem", margin: 0 }}>{title}</p>
      {subtitle && <p style={{ color: "rgba(255,247,237,0.5)", fontFamily: "Nunito, sans-serif", fontSize: "0.8rem", margin: 0, maxWidth: "320px" }}>{subtitle}</p>}
      {action}
    </div>
  );
}
