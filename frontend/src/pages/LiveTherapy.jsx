import { useState, useRef } from "react";

const cardStyle = {
  background: "linear-gradient(180deg, #fffaf0 0%, #f7f3ff 100%)",
  borderRadius: "18px",
  padding: "18px",
  boxShadow: "0 8px 22px rgba(132, 94, 194, 0.12)",
};

export default function LiveTherapy() {
  const [childName, setChildName] = useState("");
  const [word, setWord] = useState("");
  const [therapyMode, setTherapyMode] = useState("Full Word Match");
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const therapyOptions = [
    { value: "Full Word Match", label: "Full Word Match" },
    {
      value: "First Letter Match",
      label: "Alphabet",
    },
  ];

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: "audio/webm",
        });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch (err) {
      console.error(err);
      alert("Microphone access denied");
    }
  };

  const stopRecording = () => {
    if (!mediaRecorderRef.current) return;
    mediaRecorderRef.current.stop();
    setRecording(false);
  };

  const analyzeSpeech = async () => {
    if (!audioBlob) {
      alert("Please record audio first");
      return;
    }

    if (!word) {
      alert("Enter a target word");
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");
      formData.append("patient_name", childName || "Child");
      formData.append("target_word", word);
      formData.append("therapy_mode", therapyMode);

      const response = await fetch(`${import.meta.env.VITE_API_URL}/speech/therapy`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      alert("Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        padding: "24px",
        background:
          "linear-gradient(180deg, #fffaf2 0%, #f7f3ff 52%, #eefbff 100%)",
        minHeight: "100vh",
      }}
    >
      <style>{`
        @keyframes floaty {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        @keyframes sparkle {
          0% { transform: scale(0.9); opacity: 0.4; }
          50% { transform: scale(1.15); opacity: 1; }
          100% { transform: scale(1); opacity: 0.3; }
        }
        @keyframes pulseGlow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(250, 93, 119, 0.18); }
          50% { box-shadow: 0 0 0 12px rgba(250, 93, 119, 0); }
        }
      `}</style>
      <div
        style={{
          ...cardStyle,
          maxWidth: "980px",
          margin: "0 auto",
          position: "relative",
          overflow: "hidden",
          background:
            "linear-gradient(180deg, #fffef7 0%, #fff7fb 45%, #f7f7ff 100%)",
        }}
      >

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
            marginBottom: "18px",
          }}
        >
          <div>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                background: "#fff7ed",
                borderRadius: "999px",
                fontSize: "14px",
                fontWeight: 800,
                color: "#ea580c",
                marginBottom: "10px",
              }}
            >
              🎮 Speech Game Studio
            </div>
            <h1 style={{ margin: 0, fontSize: "2rem", color: "#5b21b6" }}>
              🌈 Let’s Practice Your Word!
            </h1>
          </div>
          <div
            style={{
              display: "flex",
              gap: "10px",
              flexWrap: "wrap",
            }}
          >
            <span
              style={{
                background: "#eef2ff",
                color: "#4338ca",
                padding: "8px 12px",
                borderRadius: "999px",
                fontWeight: 700,
              }}
            >
              {/* 🎯 {therapyMode} */}
            </span>
            <span
              style={{
                background: "#ecfeff",
                color: "#0f766e",
                padding: "8px 12px",
                borderRadius: "999px",
                fontWeight: 700,
              }}
            >
              {/* 🔊 Audio Ready */}
            </span>
          </div>
        </div>

        <div
          style={{
            marginTop: "18px",
            display: "grid",
            gap: "16px",
          }}
        >
          <section
            style={{
              ...cardStyle,
              background: "linear-gradient(90deg, #fff7ff 0%, #f7fbff 100%)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
              <span style={{ fontSize: "22px" }}>👶</span>
              <h2 style={{ margin: 0, color: "#7c3aed" }}>Child Name</h2>
            </div>
            <input
              value={childName}
              onChange={(e) => setChildName(e.target.value)}
              placeholder="Enter your name"
              style={{
                width: "100%",
                padding: "14px 16px",
                borderRadius: "14px",
                border: "2px solid #e9d5ff",
                fontSize: "16px",
                outline: "none",
                background: "#fff",
              }}
            />
          </section>

          <section
            style={{
              ...cardStyle,
              background: "linear-gradient(90deg, #f0fdf4 0%, #eef7ff 100%)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
              <span style={{ fontSize: "22px" }}>🎯</span>
              <h2 style={{ margin: 0, color: "#0891b2" }}>Target Word</h2>
            </div>
            <input
              value={word}
              onChange={(e) => setWord(e.target.value)}
              placeholder="banana"
              style={{
                width: "100%",
                padding: "14px 16px",
                borderRadius: "14px",
                border: "2px solid #bfdbfe",
                fontSize: "16px",
                outline: "none",
                background: "#fff",
              }}
            />
          </section>

          <section
            style={{
              ...cardStyle,
              background: "linear-gradient(90deg, #fffaf0 0%, #fff7ff 100%)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                flexWrap: "wrap",
              }}
            >
              <span style={{ fontSize: "22px" }}>🧩</span>
              <span style={{ fontWeight: 800, color: "#4338ca" }}>
                Matching Mode
              </span>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {therapyOptions.map((option) => {
                  const isActive = therapyMode === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => setTherapyMode(option.value)}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "999px",
                        border: isActive
                          ? "2px solid #7c3aed"
                          : "2px solid #ddd6fe",
                        background: isActive ? "#ede9fe" : "#f8f5ff",
                        cursor: "pointer",
                        fontWeight: isActive ? 800 : 600,
                        color: isActive ? "#4c1d95" : "#6b7280",
                        transition: "all 0.2s ease",
                      }}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </section>

          <section
            style={{
              ...cardStyle,
              background: "linear-gradient(90deg, #fff8e1 0%, #fff1f2 100%)",
            }}
          >
            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              {!recording ? (
                <button
                  onClick={startRecording}
                  style={{
                    padding: "14px 18px",
                    border: "none",
                    borderRadius: "999px",
                    background: "linear-gradient(90deg, #f97316, #fb7185)",
                    color: "#fff",
                    fontWeight: 800,
                    cursor: "pointer",
                    boxShadow: "0 8px 18px rgba(249,115,22,0.32)",
                    animation: "pulseGlow 2.4s infinite",
                  }}
                >
                  🎤 Start Recording
                </button>
              ) : (
                <button
                  onClick={stopRecording}
                  style={{
                    padding: "14px 18px",
                    border: "none",
                    borderRadius: "999px",
                    background: "linear-gradient(90deg, #ef4444, #f97316)",
                    color: "#fff",
                    fontWeight: 800,
                    cursor: "pointer",
                    boxShadow: "0 8px 18px rgba(239,68,68,0.32)",
                  }}
                >
                  ⏹ Stop Recording
                </button>
              )}

              <button
                onClick={analyzeSpeech}
                disabled={loading}
                style={{
                  padding: "14px 18px",
                  border: "none",
                  borderRadius: "999px",
                  background: loading
                    ? "#cbd5e1"
                    : "linear-gradient(90deg, #22c55e, #06b6d4)",
                  color: "#fff",
                  fontWeight: 800,
                  cursor: loading ? "not-allowed" : "pointer",
                  boxShadow: "0 8px 18px rgba(34,197,94,0.28)",
                }}
              >
                {loading ? "Analyzing..." : "🚀 Analyze Speech"}
              </button>
            </div>
          </section>

          {audioUrl && (
            <section style={{ ...cardStyle, background: "#f0fdf4" }}>
              <h3 style={{ marginTop: 0, color: "#15803d" }}>▶ Recorded Audio</h3>
              <audio controls src={audioUrl} style={{ width: "100%" }} />
            </section>
          )}

          {result && (
            <section
              style={{
                ...cardStyle,
                background: "linear-gradient(180deg, #fef2f2 0%, #f5f3ff 100%)",
                border: "2px solid #f5d0fe",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 800, color: "#a855f7", marginBottom: "6px" }}>
                    🧠 Speech Result
                  </div>
                  <h2 style={{ margin: 0, color: "#a855f7" }}>
                    Great Job! 🎉
                  </h2>
                </div>
                <div style={{ fontSize: "24px", fontWeight: 800, color: "#16a34a" }}>
                  {result.accuracy}%
                </div>
              </div>

              <div style={{ display: "grid", gap: "10px", marginTop: "16px" }}>
                <p style={{ margin: 0 }}><b>Matching Mode:</b> {therapyMode}</p>
                <p style={{ margin: 0 }}><b>Target Word:</b> {result.target_word}</p>
                <p style={{ margin: 0 }}><b>Spoken Word:</b> {result.spoken_word}</p>
                <p style={{ margin: 0 }}><b>Pitch:</b> {result.pitch}</p>
                <p style={{ margin: 0 }}><b>Loudness:</b> {result.loudness}</p>
                <p style={{ margin: 0 }}><b>Duration:</b> {result.duration}s</p>
                <p style={{ margin: 0 }}><b>Phoneme Accuracy:</b> {result.phoneme_accuracy}%</p>
                <p style={{ margin: 0 }}><b>Feedback:</b> {result.feedback}</p>
                <p style={{ margin: 0 }}><b>Stars:</b> {"⭐".repeat(result.stars)}</p>
              </div>

              <div style={{ marginTop: "18px", display: "grid", gap: "12px" }}>
                <div>
                  <h3 style={{ margin: "0 0 8px", color: "#7c3aed" }}>Expected Phonemes</h3>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {(result.expected_phonemes_display || result.expected_phonemes || []).map((p, i) => (
                      <span
                        key={`expected-${i}`}
                        style={{
                          background: "#ede9fe",
                          color: "#5b21b6",
                          padding: "6px 10px",
                          borderRadius: "999px",
                          fontWeight: 700,
                        }}
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 style={{ margin: "0 0 8px", color: "#7c3aed" }}>Detected Phonemes</h3>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {(result.spoken_phonemes_display || result.spoken_phonemes || []).map((p, i) => (
                      <span
                        key={`spoken-${i}`}
                        style={{
                          background: "#dcfce7",
                          color: "#166534",
                          padding: "6px 10px",
                          borderRadius: "999px",
                          fontWeight: 700,
                        }}
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
