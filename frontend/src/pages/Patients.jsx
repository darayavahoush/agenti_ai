import { useEffect, useState } from "react";
import { getPatientSummary } from "../services/api";

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPatientSummary()
      .then(setPatients)
      .catch((err) => console.error("Failed to load patients", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>Patients</h1>

      {loading ? (
        <p style={{ marginTop: "20px" }}>Loading patients...</p>
      ) : patients.length === 0 ? (
        <p style={{ marginTop: "20px" }}>
          No patients yet. Add a child in Live Therapy and analyze a recording.
        </p>
      ) : (
        <div style={{ marginTop: "22px", display: "grid", gap: "12px" }}>
          {patients.map((patient) => (
            <div
              key={patient.id}
              style={{
                background: "#fff",
                borderRadius: "14px",
                padding: "18px",
                boxShadow: "0 8px 22px rgba(91, 61, 177, 0.1)",
                display: "grid",
                gridTemplateColumns: "2fr 1fr 1fr 1fr",
                gap: "12px",
                alignItems: "center",
              }}
            >
              <div>
                <h3 style={{ marginBottom: "4px" }}>{patient.name}</h3>
                <p style={{ color: "#6b7280" }}>Age: {patient.age || "Not added"}</p>
              </div>
              <div>
                <strong>{patient.session_count}</strong>
                <p style={{ color: "#6b7280" }}>Sessions</p>
              </div>
              <div>
                <strong>{patient.average_accuracy}%</strong>
                <p style={{ color: "#6b7280" }}>Average</p>
              </div>
              <div>
                <strong>{patient.language || "English"}</strong>
                <p style={{ color: "#6b7280" }}>Language</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
