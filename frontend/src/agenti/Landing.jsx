import { T } from "../assessment/constants";
import { Button, BunnyMascot } from "./UI";
import { PartyPopper, Gamepad2, Globe, Brain, Flame, PawPrint, Mic2, Bell, Layers, Sparkles, Sparkle, Target } from "lucide-react";

export function Landing({ onStart }) {
  return (
    <div
      style={{
        width: "100%",
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
        position: "relative",
        overflow: "hidden",
        background:
          "radial-gradient(circle at top, rgba(255, 245, 186, 0.8), transparent 18%), linear-gradient(180deg, #fff9f1 0%, #f7fbff 100%)",
      }}
    >
      <style>{`
        @keyframes float-slow {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-12px); }
        }
        @keyframes float-fast {
          0%, 100% { transform: translateY(0px) scale(1); }
          50% { transform: translateY(-18px) scale(1.04); }
        }
        @keyframes bubble-drift {
          0% { transform: translateX(0) translateY(0); opacity: 0.5; }
          50% { opacity: 0.95; }
          100% { transform: translateX(25px) translateY(-20px); opacity: 0; }
        }
        @keyframes pulse-ring {
          0% { transform: scale(0.95); opacity: 0.6; }
          50% { transform: scale(1.05); opacity: 0.9; }
          100% { transform: scale(1.15); opacity: 0; }
        }
      `}</style>

      <div className="bg-blob-1" />
      <div className="bg-blob-2" />
      <div
        style={{
          position: "absolute", top: "12%", left: "10%", width: "14px", height: "14px",
          background: T.primary, borderRadius: "50%", opacity: 0.7,
          animation: "float-slow 3.5s ease-in-out infinite",
        }}
      />
      <div
        style={{
          position: "absolute", top: "20%", right: "18%", width: "18px", height: "18px",
          background: T.secondary, borderRadius: "50%", opacity: 0.7,
          animation: "float-slow 4s ease-in-out infinite 0.5s",
        }}
      />
      <div
        style={{
          position: "absolute", bottom: "10%", left: "22%", width: "10px", height: "10px",
          background: "#60a5fa", borderRadius: "50%", opacity: 0.75,
          animation: "float-slow 3s ease-in-out infinite 1s",
        }}
      />

      <div
        style={{
          maxWidth: "1220px", width: "100%", display: "flex", alignItems: "center",
          justifyContent: "space-between", gap: "48px", zIndex: 1,
        }}
      >
        <div className="animate-slide-up" style={{ flex: 1, maxWidth: "560px" }}>
          <div
            style={{
              display: "inline-flex", alignItems: "center", gap: "10px", padding: "10px 16px",
              background: "rgba(255, 255, 255, 0.78)", border: `1px solid ${T.border}`,
              borderRadius: "999px", boxShadow: T.shadowSm, marginBottom: "18px",
            }}
          >
            <PartyPopper size={18} color={T.primary} />
            <span style={{ fontSize: "15px", fontWeight: 800, color: T.primary }}>
              Speech Adventure Time
            </span>
          </div>

          <h1
            style={{
              fontFamily: "'Nunito', sans-serif", fontSize: "clamp(48px, 6vw, 72px)",
              fontWeight: 900, lineHeight: 1, color: T.text, margin: "0 0 18px 0",
            }}
          >
            Blow, speak, and <br />
            <span style={{ color: T.primary }}>watch the world move</span>
          </h1>

          <p
            style={{
              fontSize: "19px", color: T.textMuted, lineHeight: 1.6,
              marginBottom: "24px", fontWeight: 600,
            }}
          >
            Five games that turn real speech practice into play — breath, voice, and pronunciation, each adapting in real time to how your child is doing.
          </p>

          <div style={{ display: "flex", gap: "14px", flexWrap: "wrap", marginBottom: "22px" }}>
            <Button onClick={() => onStart("play-select")} variant="primary" style={{ padding: "18px 32px", fontSize: "18px" }}>
              Start Assessment
            </Button>
            <Button onClick={() => onStart("play-select?mode=signin")} variant="secondary" style={{ padding: "18px 28px", fontSize: "18px" }}>
              Sign in
            </Button>
          </div>

          <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "22px" }}>
            <div style={{ background: "#fff", borderRadius: "18px", padding: "12px 14px", boxShadow: T.shadowSm, minWidth: "130px" }}>
              <div style={{ fontSize: "18px", fontWeight: 800, color: T.primary, display: "flex", alignItems: "center", gap: "6px" }}><Gamepad2 size={18} /> 5</div>
              <div style={{ fontSize: "13px", color: T.textMuted }}>games, one login</div>
            </div>
            <div style={{ background: "#fff", borderRadius: "18px", padding: "12px 14px", boxShadow: T.shadowSm, minWidth: "130px" }}>
              <div style={{ fontSize: "18px", fontWeight: 800, color: T.secondary, display: "flex", alignItems: "center", gap: "6px" }}><Globe size={18} /> 8</div>
              <div style={{ fontSize: "13px", color: T.textMuted }}>languages</div>
            </div>
            <div style={{ background: "#fff", borderRadius: "18px", padding: "12px 14px", boxShadow: T.shadowSm, minWidth: "130px" }}>
              <div style={{ fontSize: "18px", fontWeight: 800, color: "#60a5fa", display: "flex", alignItems: "center", gap: "6px" }}><Brain size={18} /> AI</div>
              <div style={{ fontSize: "13px", color: T.textMuted }}>adapts difficulty live</div>
            </div>
          </div>

          {/* What's inside -- the real breadth (5 mechanically different
              games, not one app skinned five ways), stated plainly rather
              than left implicit until someone signs up. */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {[
              [Flame, "BreathQuest"], [PawPrint, "Voice Hurdle Race"], [Mic2, "VaakMirror"],
              [Bell, "Chime"], [Layers, "Flashcards"],
            ].map(([Icon, name]) => (
              <span key={name} style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "rgba(255,255,255,0.7)", border: `1px solid ${T.border}`,
                borderRadius: "999px", padding: "6px 12px", fontSize: "13px",
                fontWeight: 700, color: T.text,
              }}>
                <Icon size={14} /> {name}
              </span>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center" }}>
          <div style={{ position: "relative", width: "520px", maxWidth: "100%", display: "flex", justifyContent: "center" }}>
            <div
              style={{
                position: "absolute", inset: "12% 8%",
                background: "radial-gradient(circle, rgba(250, 93, 119, 0.18), rgba(255,255,255,0))",
                borderRadius: "50%", animation: "pulse-ring 5s ease-out infinite",
              }}
            />
            <div
              style={{
                position: "absolute", top: "18%", right: "4%", background: "#fff",
                borderRadius: "18px 18px 6px 18px", padding: "10px 14px", boxShadow: T.shadowSm,
                fontWeight: 800, color: T.text, animation: "float-fast 4s ease-in-out infinite",
              }}
            >
              YAY! <Sparkles size={14} style={{ verticalAlign: "-2px" }} />
            </div>
            <div
              style={{
                position: "absolute", bottom: "8%", left: "2%", width: "140px", background: "#fff",
                borderRadius: "18px", padding: "12px", boxShadow: T.shadowSm,
                animation: "float-slow 3.5s ease-in-out infinite 0.8s",
              }}
            >
              <div style={{ fontSize: "12px", fontWeight: 800, color: T.primary, marginBottom: "4px" }}>Today's Goal</div>
              <div style={{ fontSize: "14px", color: T.text, fontWeight: 700, display: "flex", alignItems: "center", gap: "4px" }}>Say "apple" <Target size={14} /></div>
            </div>
            <div style={{ position: "absolute", top: "0%", left: "8%", display: "flex", gap: "8px" }}>
              {[0, 1, 2].map((index) => (
                <Sparkle
                  key={index}
                  size={index === 1 ? 24 : 18}
                  color={T.primary}
                  style={{
                    animation: `bubble-drift ${3 + index}s ease-out infinite ${index * 0.6}s`,
                  }}
                />
              ))}
            </div>
            <BunnyMascot size={430} mood="happy" style={{ position: "relative", zIndex: 2 }} />
          </div>
        </div>
      </div>

      <div style={{
        position: "absolute", bottom: "18px", left: 0, right: 0,
        display: "flex", justifyContent: "center", gap: "20px", zIndex: 1,
      }}>
        {[["Pricing", "/pricing"], ["Privacy", "/privacy"], ["Terms", "/terms"]].map(([label, href]) => (
          <a key={href} href={href} style={{
            fontSize: "13px", fontWeight: 700, color: T.textMuted,
            textDecoration: "none",
          }}>
            {label}
          </a>
        ))}
      </div>
    </div>
  );
}
