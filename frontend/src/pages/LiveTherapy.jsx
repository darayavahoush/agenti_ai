const QUEST_GAMES_URL = import.meta.env.VITE_QUEST_GAMES_URL || "https://quest-games.onrender.com";

export default function LiveTherapy({ setPage }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "#000" }}>
      <button
        onClick={() => setPage("dashboard")}
        style={{
          position: "fixed",
          top: "16px",
          left: "16px",
          zIndex: 10,
          padding: "10px 20px",
          border: "none",
          borderRadius: "999px",
          background: "rgba(15, 15, 20, 0.85)",
          color: "#fff",
          fontWeight: 700,
          fontSize: "14px",
          cursor: "pointer",
          backdropFilter: "blur(6px)",
          boxShadow: "0 4px 14px rgba(0,0,0,0.35)",
        }}
        aria-label="Back to dashboard"
      >
        ← Back
      </button>
      <iframe
        src={QUEST_GAMES_URL}
        title="Quest Games"
        style={{ width: "100%", height: "100%", border: "none" }}
        allow="camera; microphone; autoplay"
      />
    </div>
  );
}
