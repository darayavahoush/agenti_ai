import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";

const cardStyle = {
  background: "linear-gradient(180deg, #fffaf0 0%, #f7f3ff 100%)",
  borderRadius: "16px",
  padding: "14px",
  boxShadow: "0 8px 22px rgba(132, 94, 194, 0.12)",
};

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const INDIAN_LANGUAGES = [
  { code: "en-IN", name: "English (India)", voiceLang: "en-IN" },
  { code: "hi-IN", name: "Hindi", voiceLang: "hi-IN" },
  { code: "te-IN", name: "Telugu", voiceLang: "te-IN" },
  { code: "kn-IN", name: "Kannada", voiceLang: "kn-IN" },
  { code: "ta-IN", name: "Tamil", voiceLang: "ta-IN" },
  { code: "ml-IN", name: "Malayalam", voiceLang: "ml-IN" },
  { code: "bn-IN", name: "Bengali", voiceLang: "bn-IN" },
  { code: "mr-IN", name: "Marathi", voiceLang: "mr-IN" },
];

export default function LiveTherapy({ setPage }) {
  const navigate = useNavigate();

  return (
    <div
      style={{
        padding: "0 24px 16px",
        background:
          "linear-gradient(180deg, #fffaf2 0%, #f7f3ff 52%, #eefbff 100%)",
        minHeight: "calc(100vh - 80px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          ...cardStyle,
          maxWidth: "980px",
          margin: "0 auto",
          position: "relative",
          overflow: "hidden",
          background:
            "linear-gradient(180deg, #fffef7 0%, #fff7fb 45%, #f7f7ff 100%)",
          textAlign: "center",
        }}
      >
        <h1 style={{ margin: "0 0 20px 0", fontSize: "1.75rem", color: "#5b21b6" }}>
          🌈 Live Therapy
        </h1>
        <button
          onClick={() => navigate('/assessment')}
          style={{
            padding: "16px 32px",
            border: "none",
            borderRadius: "999px",
            background: "linear-gradient(90deg, #8b5cf6, #ec4899)",
            color: "#fff",
            fontWeight: 800,
            fontSize: "18px",
            cursor: "pointer",
            boxShadow: "0 8px 18px rgba(139, 92, 246, 0.28)",
          }}
        >
          🎮 Assessment
        </button>
      </div>
    </div>
  );
}
