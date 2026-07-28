import { useEffect, useState } from "react";
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
  const [patients, setPatients] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/patients/`)
      .then((response) => response.ok ? response.json() : [])
      .then((data) => {
        setPatients(data);
        if (data[0]) setSelectedPatientId(data[0].id);
      })
      .catch(() => setPatients([]));
  }, []);

  const selectedPatient = patients.find((patient) => patient.id === selectedPatientId);

  const handleBreathQuest = () => {
    navigate("/breathquest");
  };

  const handleVoiceHurdleRace = () => {
    navigate("/voice-hurdle-race");
  };

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
        <div style={{ display: "flex", gap: "16px", justifyContent: "center", flexWrap: "wrap" }}>
          <button
            onClick={handleBreathQuest}
            style={{
              padding: "16px 32px",
              border: "none",
              borderRadius: "999px",
              background: "linear-gradient(90deg, #10b981, #14b8a6)",
              color: "#fff",
              fontWeight: 800,
              fontSize: "18px",
              cursor: "pointer",
              boxShadow: "0 8px 18px rgba(16, 185, 129, 0.28)",
            }}
          >
            💨 BreathQuest
          </button>
          <button
            onClick={handleVoiceHurdleRace}
            style={{
              padding: "16px 32px",
              border: "none",
              borderRadius: "999px",
              background: "linear-gradient(90deg, #f59e0b, #f97316)",
              color: "#fff",
              fontWeight: 800,
              fontSize: "18px",
              cursor: "pointer",
              boxShadow: "0 8px 18px rgba(245, 158, 11, 0.28)",
            }}
          >
            🐶 Voice Hurdle Race
          </button>
        </div>
        {/* <section style={{ marginTop: "22px", padding: "18px", borderRadius: "14px", background: "#f5f3ff", textAlign: "left" }}>
          <label style={{ display: "block", color: "#5b21b6", fontWeight: 800, marginBottom: "8px" }}>Child for this session</label>
          <select value={selectedPatientId} onChange={(event) => setSelectedPatientId(event.target.value)} style={{ width: "100%", padding: "10px", borderRadius: "10px", border: "1px solid #c4b5fd", background: "#fff" }}>
            <option value="">Select a registered child</option>
            {patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.name}</option>)}
          </select>
          {selectedPatient && (
            <p style={{ margin: "12px 0 0", color: "#475569", fontWeight: 700 }}>
              Child: {selectedPatient.name} · Therapist: {selectedPatient.therapist_name || "Not assigned"}
            </p>
          )}
        </section> */}
      </div>
    </div>
  );
}
