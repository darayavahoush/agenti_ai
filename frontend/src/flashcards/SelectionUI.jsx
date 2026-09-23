import { useState, useEffect, useMemo, useRef, Children } from "react";

// Shared "scrapbook page" primitives for the Flashcards selection flow
// (ThemeSelect, WordSelect in SelectionFlow.jsx; CharacterSelect in
// Flashcards.jsx). Kept in one place so the three screens read as one
// cohesive flow instead of drifting apart visually over time.
//
// Design direction: a warm paper page, not a dark-mode grid of uniform
// tiles. Cards are cream cardstock rectangles taped down at a slight
// per-card tilt (not a perfect grid of identical circles-in-boxes --
// that read as a video-call participant grid), with a torn-corner
// "photo" inset, a strip of washi tape, and a handwritten caption
// (Caveat) instead of everything sharing one body font. Matches the
// warm cream/ink palette the rest of the app (themes.js LIGHT_THEMES,
// the Chime home page) already uses, rather than the previous
// dark-purple "SaaS" background that clashed with it.

export const FUN_COLORS = ["#E8825A", "#E8B84B", "#6BBF8A", "#5B9BD5", "#B57ED5", "#E87BA8"];
const DISPLAY_FONT = "'Baloo 2', 'Nunito', sans-serif";
const HAND_FONT = "'Caveat', cursive";
// Caveat (script) reads fine as a big decorative headline, but it's the
// wrong choice for anything a kid actually has to read and recognize --
// a single cursive letter or a short word at card size loses the clear
// print shapes that make letters/words identifiable, which is the whole
// point of this screen. CONTENT_FONT (the same rounded sans as the rest
// of the app) is for real content: theme titles, word labels, the
// letter-badge fallback. HAND_FONT stays for pure flavor text.
const CONTENT_FONT = DISPLAY_FONT;
const INK = "#4A3826";
const INK_SOFT = "#9A7F68";

// Deterministic per-index tilt so the grid doesn't jitter between
// re-renders but also doesn't line up into identical rows like a
// meeting grid. A handful of hand-picked angles repeating is enough --
// real scrapbook pages don't need truly random angles, just "not zero".
const CARD_ROTATIONS = [-3, 2.5, -2, 3, -3.5, 1.5, -1.5, 2, -2.5, 3.5, -1, 2.8];
const TAPE_ROTATIONS = [-9, 7, -13, 10, -6, 12, -8, 6];
const rotFor = (i, arr) => arr[((i % arr.length) + arr.length) % arr.length];

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
// Title is handwritten (Caveat) with a highlighter-marker swipe behind
// it instead of a plain headline -- reads as a page title scrawled on
// the scrapbook page rather than app chrome. No uppercase tracked-out
// eyebrow chip -- StepDots already carries progress.
export function SectionHeader({ title, subtitle }) {
  return (
    <div style={{ textAlign: "center", marginBottom: "22px" }}>
      <h2 style={{ position: "relative", display: "inline-block", margin: 0 }}>
        <span aria-hidden style={{
          position: "absolute", left: "-6%", right: "-6%", bottom: "6%", height: "40%",
          background: "#FFD86B", opacity: 0.55, transform: "rotate(-1deg)", borderRadius: "3px", zIndex: 0,
        }} />
        <span style={{ position: "relative", zIndex: 1, color: INK, fontFamily: HAND_FONT, fontSize: "2.3rem", fontWeight: 700, letterSpacing: "0.01em" }}>
          {title}
        </span>
      </h2>
      {subtitle && <p style={{ color: INK_SOFT, fontFamily: "Quicksand, sans-serif", fontWeight: 600, fontSize: "0.88rem", margin: "8px 0 0" }}>{subtitle}</p>}
    </div>
  );
}

// Little brass "brads" (paper fasteners) linked by a dashed stitch line
// instead of a row of plain dots -- ties the progress indicator to the
// same tactile paper-craft language as the cards.
export function StepDots({ current, total = 3 }) {
  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", marginBottom: "16px" }}>
      {Array.from({ length: total }).map((_, i) => {
        const active = i + 1 === current;
        const done = i + 1 < current;
        const filled = active || done;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center" }}>
            <div style={{
              width: active ? "17px" : "11px", height: active ? "17px" : "11px", borderRadius: "50%",
              background: filled ? "radial-gradient(circle at 32% 28%, #F0A868, #C9662E 75%)" : "rgba(74,56,38,0.14)",
              boxShadow: active ? "0 0 0 3px rgba(201,102,46,0.22), inset 0 1px 1px rgba(255,255,255,0.5)" : filled ? "inset 0 1px 1px rgba(255,255,255,0.4)" : "none",
              transition: "all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)",
              animation: active ? "brassPulse 1.6s ease-in-out infinite" : "none",
            }} />
            {i < total - 1 && <div style={{ width: "22px", height: 0, borderTop: "2px dashed rgba(74,56,38,0.22)", margin: "0 2px" }} />}
          </div>
        );
      })}
    </div>
  );
}

// Small strip of scattered doodles + two corner washi-tape strips
// "pinning" the page content down. Replaces the previous blurred glow
// blobs + twinkling starfield, which read as ambient tech glow rather
// than anything paper-like.
const DOODLES = ["✨", "⭐", "❤️", "〰️", "✂️", "🌟"];
export function PlayfulBackdrop({ tint = "#B57ED5" }) {
  const dots = useMemo(() => Array.from({ length: 7 }).map((_, i) => ({
    id: i,
    top: 6 + Math.random() * 86,
    left: 3 + Math.random() * 92,
    rot: -25 + Math.random() * 50,
    size: 13 + Math.random() * 10,
    emoji: DOODLES[i % DOODLES.length],
  })), []);

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
      <div style={{
        position: "absolute", top: "16px", left: "6%", width: "64px", height: "22px",
        background: `repeating-linear-gradient(45deg, ${tint}99, ${tint}99 5px, ${tint}55 5px, ${tint}55 10px)`,
        transform: "rotate(-8deg)", boxShadow: "0 2px 4px rgba(74,56,38,0.18)", opacity: 0.6, borderRadius: "1px",
      }} />
      <div style={{
        position: "absolute", top: "12px", right: "7%", width: "56px", height: "20px",
        background: "repeating-linear-gradient(-45deg, #6BBF8A99, #6BBF8A99 5px, #6BBF8A55 5px, #6BBF8A55 10px)",
        transform: "rotate(7deg)", boxShadow: "0 2px 4px rgba(74,56,38,0.18)", opacity: 0.55, borderRadius: "1px",
      }} />
      {dots.map(d => (
        <span key={d.id} style={{
          position: "absolute", top: `${d.top}%`, left: `${d.left}%`,
          fontSize: `${d.size}px`, opacity: 0.16, transform: `rotate(${d.rot}deg)`,
        }}>{d.emoji}</span>
      ))}
    </div>
  );
}

// Warm cream paper gradient (matches themes.js LIGHT_THEMES.DEFAULT) with
// a faint dotted grain layered on top, so it reads as paper texture
// rather than a flat fill -- and, critically, isn't the near-black
// purple background that made the sticker cards read as dark-mode
// SaaS/video-call tiles.
export const SELECTION_BG = `radial-gradient(circle at 1px 1px, rgba(74,56,38,0.07) 1px, transparent 0) 0 0/24px 24px, linear-gradient(160deg, #FDEDEA 0%, #FDF3DD 30%, #FBFAE0 55%, #E9F6EA 75%, #E2F5F2 100%)`;

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
        0% { opacity: 0; transform: scale(0.92) translateY(10px) rotate(var(--pop-rot, 0deg)); }
        100% { opacity: 1; transform: scale(1) translateY(0) rotate(var(--pop-rot, 0deg)); }
      }
      @keyframes wiggle {
        0%, 100% { transform: rotate(0deg); }
        25% { transform: rotate(-6deg); }
        75% { transform: rotate(6deg); }
      }
      @keyframes brassPulse {
        0%, 100% { box-shadow: 0 0 0 3px rgba(201,102,46,0.22), inset 0 1px 1px rgba(255,255,255,0.5); }
        50% { box-shadow: 0 0 0 6px rgba(201,102,46,0), inset 0 1px 1px rgba(255,255,255,0.5); }
      }
      @keyframes pulseGlow {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 0.85; }
      }
      /* Smooths the dock-magnify effect below -- both the card wrapper
         and the photo inset ease into their scaled/glowing state
         instead of snapping, since DockMagnifyGrid drives them via
         direct style writes on every mousemove for performance rather
         than React state. */
      .dock-item { transition: transform 0.16s cubic-bezier(0.22,1,0.36,1); }
      .pc-badge { transition: transform 0.16s cubic-bezier(0.22,1,0.36,1), box-shadow 0.16s ease-out; }
      .pc-visual { transition: filter 0.16s ease-out; }
      @media (hover: none) {
        /* Touch devices have no cursor to magnify toward -- don't reserve
           any transition budget for an effect that never fires. */
        .dock-item, .pc-badge, .pc-visual { transition: none; }
      }
    `}</style>
  );
}

// macOS-dock-style magnification: cards near the cursor grow smoothly
// (falling off with distance) instead of the grid sitting at one flat
// size, and the photo inset on the nearest card gets an extra pop plus
// a warm glow -- "bigger and shine" -- rather than just scaling
// everything uniformly. Wraps a plain CSS grid of PlayCard/WordPill
// children; each gets its own scaling wrapper div so PlayCard's own
// rotate/translateY hover transform (set directly via onMouseEnter)
// keeps working unmodified on the inner element while this component
// only ever touches the outer wrapper's transform.
//
// Driven by direct DOM style writes (not React state) inside a
// rAF-throttled mousemove handler -- re-rendering the whole grid on
// every pixel of mouse movement would be needlessly expensive for a
// purely cosmetic effect.
export function DockMagnifyGrid({ children, columns = 3, gap = "14px", radius = 150, maxScale = 1.3, style }) {
  const itemRefs = useRef([]);
  const rafRef = useRef(null);
  const kids = Children.toArray(children);
  itemRefs.current.length = kids.length;

  const applyScales = (mouseX, mouseY) => {
    itemRefs.current.forEach((el) => {
      if (!el) return;
      const badge = el.querySelector(".pc-badge");
      const visual = el.querySelector(".pc-visual");
      if (mouseX == null) {
        el.style.transform = "scale(1)";
        el.style.zIndex = 0;
        if (badge) { badge.style.transform = "scale(1)"; badge.style.boxShadow = ""; }
        if (visual) visual.style.filter = "none";
        return;
      }
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dist = Math.hypot(mouseX - cx, mouseY - cy);
      const t = Math.max(0, 1 - dist / radius);
      const eased = t * t * (3 - 2 * t); // smoothstep -- dock icons ease in/out, don't snap
      const scale = 1 + eased * (maxScale - 1);
      el.style.transform = `scale(${scale})`;
      el.style.zIndex = eased > 0.04 ? 5 : 0;
      if (badge) {
        badge.style.transform = `scale(${1 + eased * 0.2})`;
        badge.style.boxShadow = eased > 0.04
          ? `inset 0 1px 3px rgba(74,56,38,0.12), 0 0 ${Math.round(6 + eased * 20)}px ${Math.round(2 + eased * 6)}px rgba(255,216,107,${(0.18 + eased * 0.55).toFixed(2)})`
          : "";
      }
      if (visual) {
        visual.style.filter = eased > 0.04 ? `brightness(${(1 + eased * 0.22).toFixed(2)})` : "none";
      }
    });
  };

  const handleMouseMove = (e) => {
    const x = e.clientX, y = e.clientY;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => applyScales(x, y));
  };

  const handleMouseLeave = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    applyScales(null, null);
  };

  useEffect(() => () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); }, []);

  return (
    <div
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ display: "grid", gridTemplateColumns: `repeat(${columns}, 1fr)`, gap, ...style }}
    >
      {kids.map((child, i) => (
        <div key={child.key ?? i} ref={(el) => (itemRefs.current[i] = el)} className="dock-item" style={{ transformOrigin: "center center" }}>
          {child}
        </div>
      ))}
    </div>
  );
}

// Small diagonal-stripe washi-tape strip, tilted independently of the
// card it sits on -- the detail that most says "stuck onto a page"
// rather than "rendered in a component library".
function Tape({ color, index, width = 46 }) {
  const rot = rotFor(index, TAPE_ROTATIONS);
  return (
    <div aria-hidden style={{
      position: "absolute", top: "-9px", left: "50%", width: `${width}px`, height: "17px",
      background: `repeating-linear-gradient(45deg, ${color}cc, ${color}cc 4px, ${color}70 4px, ${color}70 8px)`,
      transform: `translateX(-50%) rotate(${rot}deg)`,
      boxShadow: "0 1px 2px rgba(74,56,38,0.25)",
      opacity: 0.92, borderRadius: "2px", zIndex: 2,
    }} />
  );
}

// Small folded-corner "dog ear" for the smaller word tiles, standing in
// for the tape on the bigger cards without crowding a denser grid.
function FoldedCorner({ color }) {
  return (
    <div aria-hidden style={{
      position: "absolute", top: 0, right: 0, width: 0, height: 0,
      borderStyle: "solid", borderWidth: "0 18px 18px 0",
      borderColor: `transparent ${color}77 transparent transparent`,
      filter: "drop-shadow(-1px 1px 1px rgba(74,56,38,0.2))",
    }} />
  );
}

// "Photo" inset behind the icon/emoji/letter -- a soft-cornered square
// with a tinted background and a real border, like a small photo tucked
// into a scrapbook slot, rather than a circular avatar (the circle was
// most of what made the grid read as video-call participant tiles).
function PlayCardBadge({ image, imageAlt, emoji, letter, title, color, size = 72 }) {
  return (
    <div
      className="pc-badge"
      style={{
        width: `${size}px`, height: `${size}px`, borderRadius: "10px", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: `${color}2e`,
        border: `2px solid ${color}`,
        boxShadow: "inset 0 1px 3px rgba(74,56,38,0.12)",
      }}
    >
      {image ? (
        <img src={image} alt={imageAlt || title} className="pc-visual" style={{ width: `${size * 0.62}px`, height: `${size * 0.62}px`, objectFit: "contain" }} />
      ) : emoji ? (
        <span className="pc-visual" style={{ fontSize: `${size * 0.44}px`, display: "inline-block" }}>{emoji}</span>
      ) : (
        <span className="pc-visual" style={{ fontSize: `${size * 0.4}px`, fontWeight: 800, color: INK, fontFamily: CONTENT_FONT }}>{letter}</span>
      )}
    </div>
  );
}

// Soft warm "paper lifted off the page" shadow instead of a hard SaaS
// drop shadow -- ink-brown tinted rather than pure black, so it reads
// as a shadow cast on cream paper.
const paperShadow = (lift = false) => lift
  ? "0 12px 20px rgba(74,56,38,0.22), 0 3px 7px rgba(74,56,38,0.14)"
  : "0 5px 11px rgba(74,56,38,0.15), 0 2px 4px rgba(74,56,38,0.10)";

export function PlayCard({ emoji, image, imageAlt, title, subtitle, color = "#B57ED5", index = 0, featured = false, onClick }) {
  const rot = rotFor(index, CARD_ROTATIONS);
  return (
    <button
      onClick={onClick}
      style={{
        position: "relative",
        display: "flex", flexDirection: "column", alignItems: "center", gap: "10px",
        background: "#FFFDF7",
        border: `1.5px solid ${featured ? color : "rgba(74,56,38,0.14)"}`,
        borderRadius: "6px 16px 6px 16px",
        padding: "24px 12px 16px",
        boxShadow: paperShadow(),
        transform: `rotate(${rot}deg)`,
        "--pop-rot": `${rot}deg`,
        opacity: 0, animation: `popIn 0.4s cubic-bezier(0.22,1,0.36,1) ${index * 0.05}s forwards`,
        transition: "box-shadow 0.18s, transform 0.18s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = paperShadow(true);
        e.currentTarget.style.transform = "rotate(0deg) translateY(-4px) scale(1.03)";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "wiggle 0.5s ease-in-out";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = paperShadow();
        e.currentTarget.style.transform = `rotate(${rot}deg)`;
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "none";
      }}
      onMouseDown={e => { e.currentTarget.style.transform = `rotate(${rot * 0.4}deg) translateY(1px) scale(0.98)`; }}
      onMouseUp={e => { e.currentTarget.style.transform = "rotate(0deg) translateY(-4px) scale(1.03)"; }}
    >
      <Tape color={color} index={index} />
      <PlayCardBadge image={image} imageAlt={imageAlt} emoji={emoji} title={title} color={color} />
      <span style={{ color: INK, fontSize: "1.1rem", fontWeight: 800, fontFamily: CONTENT_FONT, lineHeight: 1.15, letterSpacing: "0.01em" }}>{title}</span>
      {subtitle && <span style={{ color: INK_SOFT, fontSize: "0.68rem", textAlign: "center", lineHeight: 1.3, fontFamily: "Quicksand, sans-serif", fontWeight: 600 }}>{subtitle}</span>}
    </button>
  );
}

// Word-grid tile -- a smaller sticky-note sibling of PlayCard (badge +
// handwritten label, same tilt language, folded corner instead of
// tape) so step 2 of the flow carries the same weight as steps 1 and 3
// instead of downgrading to bare pills.
export function WordPill({ label, image, color = "#B57ED5", index = 0, onClick }) {
  const rot = rotFor(index, CARD_ROTATIONS);
  return (
    <button
      onClick={onClick}
      style={{
        position: "relative", overflow: "hidden",
        display: "flex", flexDirection: "column", alignItems: "center", gap: "8px",
        background: `${color}20`, border: `1.5px solid ${color}70`,
        borderRadius: "4px 12px 4px 12px", padding: "14px 8px 10px",
        boxShadow: paperShadow(),
        transform: `rotate(${rot}deg)`,
        "--pop-rot": `${rot}deg`,
        opacity: 0, animation: `popIn 0.35s cubic-bezier(0.22,1,0.36,1) ${Math.min(index, 24) * 0.02}s forwards`,
        transition: "box-shadow 0.15s, transform 0.15s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = paperShadow(true);
        e.currentTarget.style.transform = "rotate(0deg) translateY(-3px) scale(1.03)";
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "wiggle 0.5s ease-in-out";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = paperShadow();
        e.currentTarget.style.transform = `rotate(${rot}deg)`;
        const visual = e.currentTarget.querySelector(".pc-visual");
        if (visual) visual.style.animation = "none";
      }}
      onMouseDown={e => { e.currentTarget.style.transform = `rotate(${rot * 0.4}deg) translateY(1px) scale(0.98)`; }}
      onMouseUp={e => { e.currentTarget.style.transform = "rotate(0deg) translateY(-3px) scale(1.03)"; }}
    >
      <FoldedCorner color={color} />
      <PlayCardBadge image={image} imageAlt={label} letter={label[0].toUpperCase()} title={label} color={color} size={44} />
      <span style={{ color: INK, fontSize: "0.92rem", fontWeight: 800, fontFamily: CONTENT_FONT, letterSpacing: "0.01em", textTransform: "capitalize" }}>
        {label}
      </span>
    </button>
  );
}

// Pulsing placeholder tile shaped like a real PlayCard, so the grid
// doesn't visually jump when real data arrives -- used in place of a
// bare "Loading…" line. Warm paper-neutral tones instead of white-on-
// dark, to match the new light background.
export function SkeletonCard({ index = 0 }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", gap: "10px",
      background: "rgba(74,56,38,0.05)", border: "1.5px solid rgba(74,56,38,0.08)",
      borderRadius: "6px 16px 6px 16px", padding: "24px 12px 16px",
      animation: `pulseGlow 1.6s ease-in-out ${index * 0.08}s infinite`,
    }}>
      <div style={{ width: "72px", height: "72px", borderRadius: "10px", background: "rgba(74,56,38,0.09)" }} />
      <div style={{ width: "70%", height: "10px", borderRadius: "6px", background: "rgba(74,56,38,0.09)" }} />
      <div style={{ width: "45%", height: "8px", borderRadius: "6px", background: "rgba(74,56,38,0.07)" }} />
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
      <p style={{ color: INK, fontWeight: 700, fontFamily: HAND_FONT, fontSize: "1.3rem", margin: 0 }}>{title}</p>
      {subtitle && <p style={{ color: INK_SOFT, fontFamily: "Quicksand, sans-serif", fontSize: "0.8rem", margin: 0, maxWidth: "320px" }}>{subtitle}</p>}
      {action}
    </div>
  );
}
