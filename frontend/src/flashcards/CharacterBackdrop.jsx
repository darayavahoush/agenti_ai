export default function CharacterBackdrop({ character }) {
  if (!character) return null; // No motif when no character is selected — let the screen's own background carry it

  const char = character.toUpperCase();

  return (
    <div
      aria-hidden="true"
      style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden", pointerEvents: "none" }}
    >
      {char === "BOLT" && <BoltBackdrop />}
      {char === "ZARA" && <ZaraBackdrop />}
      {char === "NOVA" && <NovaBackdrop />}
      {char === "BEEP" && <BeepBackdrop />}
      {char === "ECHO" && <EchoBackdrop />}
      {char === "MIRA" && <MiraBackdrop />}
      <style>{`@media (prefers-reduced-motion: reduce) { .cb-anim { animation: none !important; } }`}</style>
    </div>
  );
}

// ---------- BOLT: starfield + radar scan pings + shooting stars ----------
function BoltBackdrop() {
  const stars = Array.from({ length: 22 }, (_, i) => ({
    x: (i * 43) % 100, y: (i * 79) % 100, size: 2 + (i % 3) * 1.5,
  }));
  const scans = [
    { x: 15, y: 20, size: 140 }, { x: 82, y: 30, size: 170 },
    { x: 25, y: 78, size: 160 }, { x: 78, y: 82, size: 130 },
  ];
  const shootingStars = [
    { top: 10, dur: 6, delay: 0 },
    { top: 45, dur: 8, delay: 3 },
    { top: 70, dur: 7, delay: 5.5 },
  ];
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {stars.map((s, i) => (
        <div key={`star-${i}`} className="cb-anim" style={{
          position: "absolute", left: `${s.x}%`, top: `${s.y}%`,
          width: s.size, height: s.size, borderRadius: "50%",
          background: "#5B9BD5", boxShadow: "0 0 6px #5B9BD5CC",
          opacity: 0.5,
          animation: `bolt-star-twinkle ${2 + (i % 4)}s ease-in-out infinite`,
          animationDelay: `${i * 0.3}s`,
        }} />
      ))}
      {scans.map((sc, i) => (
        <div key={`scan-${i}`} className="cb-anim" style={{
          position: "absolute", left: `${sc.x}%`, top: `${sc.y}%`,
          width: sc.size, height: sc.size, borderRadius: "50%",
          border: "2px solid #5B9BD5", opacity: 0,
          animation: `bolt-scan-ping ${5 + i * 1.3}s ease-out infinite`,
          animationDelay: `${i * 1.6}s`,
        }} />
      ))}
      {shootingStars.map((sh, i) => (
        <div key={`shoot-${i}`} className="cb-anim" style={{
          position: "absolute", top: `${sh.top}%`, left: "-10%",
          width: "90px", height: "2px",
          background: "linear-gradient(90deg, transparent, #5B9BD5CC, transparent)",
          animation: `bolt-shooting-star ${sh.dur}s linear infinite`,
          animationDelay: `${sh.delay}s`,
        }} />
      ))}
      <style>{`
        @keyframes bolt-star-twinkle {
          0%, 100% { opacity: 0.2; transform: scale(0.8); }
          50% { opacity: 0.9; transform: scale(1.3); }
        }
        @keyframes bolt-scan-ping {
          0% { transform: scale(0.6); opacity: 0.5; }
          80% { opacity: 0.08; }
          100% { transform: scale(1.15); opacity: 0; }
        }
        @keyframes bolt-shooting-star {
          0% { left: -10%; opacity: 0; transform: translateY(0); }
          5% { opacity: 0.8; }
          20% { opacity: 0; }
          100% { left: 110%; opacity: 0; transform: translateY(40px); }
        }
      `}</style>
    </div>
  );
}

// ---------- ZARA: bold glowing star sparkles ----------
function ZaraBackdrop() {
  const starPath = "M12 0 L14.6 8.5 L23 9.3 L16.5 14.8 L18.7 23 L12 18.1 L5.3 23 L7.5 14.8 L1 9.3 L9.4 8.5 Z";
  const sparkles = [
    { x: 6, y: 10, s: 26 }, { x: 88, y: 15, s: 20 }, { x: 20, y: 75, s: 24 },
    { x: 78, y: 70, s: 32 }, { x: 45, y: 22, s: 18 }, { x: 60, y: 88, s: 22 },
    { x: 12, y: 45, s: 19 }, { x: 92, y: 50, s: 24 }, { x: 35, y: 60, s: 16 },
    { x: 68, y: 35, s: 21 }, { x: 30, y: 12, s: 15 }, { x: 5, y: 60, s: 18 },
    { x: 95, y: 85, s: 20 }, { x: 55, y: 5, s: 17 }, { x: 15, y: 90, s: 22 },
    { x: 82, y: 40, s: 15 },
  ];
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {sparkles.map((sp, i) => (
        <div key={i} className="cb-anim" style={{
          position: "absolute", left: `${sp.x}%`, top: `${sp.y}%`,
          width: sp.s, height: sp.s,
          animation: `zara-twinkle ${2.5 + (i % 4) * 0.7}s ease-in-out infinite`,
          animationDelay: `${i * 0.3}s`,
        }}>
          <svg viewBox="0 0 24 23" width={sp.s} height={sp.s} style={{ filter: "drop-shadow(0 0 7px #B57ED5DD)" }}>
            <path d={starPath} fill="#B57ED5" />
          </svg>
        </div>
      ))}
      <style>{`
        @keyframes zara-twinkle {
          0%, 100% { opacity: 0.45; transform: scale(0.75) rotate(0deg); }
          50% { opacity: 1; transform: scale(1.35) rotate(35deg); }
        }
      `}</style>
    </div>
  );
}

// ---------- NOVA: falling leaves, drift + sway + rotate ----------
function NovaBackdrop() {
  const leafPath = "M10 0 C16 4, 20 12, 10 22 C0 12, 4 4, 10 0 Z M10 5 L10 20";
  const leaves = [
    { x: 5, size: 20, dur: 11, delay: 0, sway: 30 },
    { x: 18, size: 15, dur: 9, delay: 1.5, sway: 22 },
    { x: 32, size: 22, dur: 13, delay: 3, sway: 35 },
    { x: 48, size: 17, dur: 10, delay: 0.8, sway: 25 },
    { x: 62, size: 19, dur: 12, delay: 4.2, sway: 28 },
    { x: 76, size: 16, dur: 8.5, delay: 2.1, sway: 20 },
    { x: 88, size: 21, dur: 11.5, delay: 5, sway: 32 },
    { x: 95, size: 14, dur: 9.5, delay: 3.6, sway: 18 },
  ];
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {leaves.map((l, i) => (
        <div key={i} className="cb-anim" style={{
          position: "absolute", left: `${l.x}%`, top: "-30px",
          width: l.size, height: l.size,
          animation: `nova-fall ${l.dur}s linear infinite`,
          animationDelay: `${l.delay}s`,
          "--sway": `${l.sway}px`,
        }}>
          <svg viewBox="0 0 20 22" width={l.size} height={l.size} style={{ filter: "drop-shadow(0 0 4px #6BBF7A99)" }}>
            <path d={leafPath} fill="#6BBF7A" opacity="0.55" stroke="#4A9C5A" strokeWidth="0.5" />
          </svg>
        </div>
      ))}
      <style>{`
        @keyframes nova-fall {
          0% { transform: translateY(0) translateX(0) rotate(0deg); opacity: 0; }
          8% { opacity: 0.7; }
          50% { transform: translateY(50vh) translateX(var(--sway)) rotate(180deg); }
          92% { opacity: 0.6; }
          100% { transform: translateY(105vh) translateX(0) rotate(360deg); opacity: 0; }
        }
      `}</style>
    </div>
  );
}

// ---------- BEEP: bold bouncing glowing dot blips ----------
function BeepBackdrop() {
  const dots = Array.from({ length: 24 }, (_, i) => ({
    x: (i * 43) % 100, y: (i * 89) % 100, size: 7 + (i % 3) * 4,
  }));
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {dots.map((d, i) => (
        <div key={i} className="cb-anim" style={{
          position: "absolute", left: `${d.x}%`, top: `${d.y}%`,
          width: d.size, height: d.size, borderRadius: "50%",
          background: "#E8B84B", boxShadow: "0 0 14px #E8B84BCC",
          opacity: 0.5,
          animation: `beep-blip ${1.2 + (i % 3) * 0.4}s ease-in-out infinite`, animationDelay: `${i * 0.15}s`,
        }} />
      ))}
      <style>{`
        @keyframes beep-blip {
          0%, 100% { transform: translateY(0) scale(0.8); opacity: 0.3; }
          50% { transform: translateY(-26px) scale(1.3); opacity: 0.85; }
        }
      `}</style>
    </div>
  );
}

// ---------- ECHO: bold, random glitchy scan-lines + fragments ----------
function EchoBackdrop() {
  const fragments = Array.from({ length: 16 }, (_, i) => ({
    x: (i * 61) % 100, y: (i * 137) % 100, w: 25 + (i % 4) * 25,
    dur: 1.2 + (i % 5) * 0.5, delay: (i * 0.37) % 3,
  }));
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <div className="cb-anim" style={{
        position: "absolute", inset: 0,
        background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(232,123,90,0.18) 2px, rgba(232,123,90,0.18) 4px)",
        animation: "echo-scan 4s linear infinite",
      }} />
      {fragments.map((f, i) => (
        <div key={i} className="cb-anim" style={{
          position: "absolute", left: `${f.x}%`, top: `${f.y}%`,
          width: f.w, height: 3, background: "#E87B5A",
          boxShadow: "0 0 12px #E87B5ACC", opacity: 0.5,
          animation: `echo-flicker ${f.dur}s steps(1) infinite`, animationDelay: `${f.delay}s`,
        }} />
      ))}
      <style>{`
        @keyframes echo-scan { 0% { transform: translateY(0); } 100% { transform: translateY(4px); } }
        @keyframes echo-flicker { 0%, 70%, 100% { opacity: 0.1; } 15%, 25% { opacity: 0.8; } 40% { opacity: 0.2; } 55% { opacity: 0.6; } }
      `}</style>
    </div>
  );
}

// ---------- MIRA: bubbles + swimming fish ----------
function MiraBackdrop() {
  const bubbles = Array.from({ length: 16 }, (_, i) => ({
    x: (i * 61) % 100, size: 10 + (i % 4) * 7, dur: 7 + (i % 5) * 1.6, delay: i * 0.7,
  }));
  const fishPath = "M0 8 C4 0, 16 0, 22 8 C16 16, 4 16, 0 8 Z M22 8 L28 3 L28 13 Z";
  const fish = [
    { y: 15, size: 34, dur: 22, delay: 0, dir: 1 },
    { y: 38, size: 26, dur: 17, delay: 4, dir: -1 },
    { y: 60, size: 40, dur: 26, delay: 8, dir: 1 },
    { y: 78, size: 22, dur: 15, delay: 2, dir: -1 },
  ];
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {bubbles.map((b, i) => (
        <div key={i} className="cb-anim" style={{
          position: "absolute", left: `${b.x}%`, bottom: "-40px",
          width: b.size, height: b.size, borderRadius: "50%",
          border: "2px solid #4ABFBF", boxShadow: "0 0 10px #4ABFBFAA",
          opacity: 0, animation: `mira-rise ${b.dur}s ease-in infinite`, animationDelay: `${b.delay}s`,
        }} />
      ))}
      {fish.map((f, i) => (
        <div key={`f${i}`} className="cb-anim" style={{
          position: "absolute", top: `${f.y}%`,
          left: f.dir === 1 ? "-60px" : "auto",
          right: f.dir === -1 ? "-60px" : "auto",
          width: f.size, height: f.size * 0.6,
          animation: `${f.dir === 1 ? "mira-swim-right" : "mira-swim-left"} ${f.dur}s linear infinite`,
          animationDelay: `${f.delay}s`,
        }}>
          <svg viewBox="0 0 28 16" width={f.size} height={f.size * 0.6}
               style={{ filter: "drop-shadow(0 0 5px #4ABFBF99)", transform: f.dir === -1 ? "scaleX(-1)" : "none" }}>
            <path d={fishPath} fill="#4ABFBF" opacity="0.5" />
          </svg>
        </div>
      ))}
      <style>{`
        @keyframes mira-rise {
          0% { transform: translateY(0) translateX(0); opacity: 0; }
          10% { opacity: 0.5; }
          90% { opacity: 0.4; }
          100% { transform: translateY(-110vh) translateX(25px); opacity: 0; }
        }
        @keyframes mira-swim-right {
          0% { left: -60px; opacity: 0; }
          8% { opacity: 0.55; }
          92% { opacity: 0.5; }
          100% { left: 105%; opacity: 0; }
        }
        @keyframes mira-swim-left {
          0% { right: -60px; opacity: 0; }
          8% { opacity: 0.55; }
          92% { opacity: 0.5; }
          100% { right: 105%; opacity: 0; }
        }
      `}</style>
    </div>
  );
}
