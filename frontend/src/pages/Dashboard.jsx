import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Dashboard() {
  const [patients, setPatients] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [patientsRes, sessionsRes] = await Promise.all([
          fetch(`${API}/patients/`),
          fetch(`${API}/patients/sessions/all`),
        ]);

        const patientsData = await patientsRes.json();
        const sessionsData = await sessionsRes.json();

        setPatients(Array.isArray(patientsData) ? patientsData : []);
        setSessions(Array.isArray(sessionsData) ? sessionsData : []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const avgAccuracy =
    sessions.length > 0
      ? Math.round(
        sessions.reduce((sum, s) => sum + (Number(s.accuracy) || 0), 0) /
        sessions.length
      )
      : 0;

  return (
    <div style={{ padding: "24px" }}>
      <h1 style={{ margin: 0 }}>🏠 VaakSuddhi Dashboard</h1>

      {loading ? (
        <p>Loading dashboard...</p>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "20px",
            marginTop: "20px",
          }}
        >
          <div className="card">
            <h3>👶 Patients</h3>
            <h2>{patients.length}</h2>
          </div>

          <div className="card">
            <h3>🎤 Sessions</h3>
            <h2>{sessions.length}</h2>
          </div>

          <div className="card">
            <h3>⭐ Accuracy</h3>
            <h2>{avgAccuracy}%</h2>
          </div>
        </div>
      )}
    </div>
  );
}