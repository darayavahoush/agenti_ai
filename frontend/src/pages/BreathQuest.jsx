const BREATHQUEST_URL = import.meta.env.VITE_BREATHQUEST_URL || "/breathquest/index.html";

export default function BreathQuest({ setPage }) {
  return (
    <div
      style={{
        height: "100%",
        minHeight: "100dvh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        background: "#12122a",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "14px",
          padding: "10px 18px",
          minHeight: "56px",
          color: "#fff",
          background: "#181836",
          borderBottom: "1px solid rgba(255, 255, 255, 0.12)",
          flexShrink: 0,
        }}
      >
        <strong style={{ fontSize: "1.05rem" }}>BreathQuest</strong>
        {setPage && (
          <button
            onClick={() => setPage("assessment")}
            style={{
              padding: "9px 14px",
              borderRadius: "999px",
              border: "1px solid rgba(255, 255, 255, 0.18)",
              background: "#4f46e5",
              color: "#fff",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            &larr; Back to Live Therapy
          </button>
        )}
      </div>

      <iframe
        title="BreathQuest"
        src={BREATHQUEST_URL}
        style={{ width: "100%", flex: 1, minHeight: 0, border: "0", display: "block" }}
        allow="clipboard-read; clipboard-write; microphone; camera; fullscreen"
      />
    </div>
  );
}
