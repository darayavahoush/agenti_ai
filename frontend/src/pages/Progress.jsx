import { useEffect, useState } from "react";
import { getProgress } from "../services/api";

export default function Progress() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProgress()
      .then(setSessions)
      .catch((err) => console.error("Failed to load progress", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>Progress</h1>

      {loading ? (
        <p style={{ marginTop: "20px" }}>Loading progress...</p>
      ) : sessions.length === 0 ? (
        <p style={{ marginTop: "20px" }}>No therapy sessions yet.</p>
      ) : (
        <div style={{ marginTop: "22px", display: "grid", gap: "12px" }}>
          {sessions.map((session) => (
            <div
              key={session.id}
              style={{
                background: "#fff",
                borderRadius: "14px",
                padding: "18px",
                boxShadow: "0 8px 22px rgba(91, 61, 177, 0.1)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "12px",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <h3 style={{ marginBottom: "4px" }}>{session.child_name}</h3>
                  <p style={{ color: "#6b7280" }}>Age: {session.child_age || "Not added"}</p>
                </div>
                <strong style={{ fontSize: "24px", color: "#16a34a" }}>
                  {session.accuracy}%
                </strong>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                  gap: "12px",
                  marginTop: "14px",
                }}
              >
                <p><strong>Target:</strong> {session.target_word}</p>
                <p><strong>Spoken:</strong> {session.spoken_word}</p>
                <p><strong>Mode:</strong> {session.session_type}</p>
              </div>
              <p style={{ marginTop: "10px", color: "#6b7280" }}>{session.feedback}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
