import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API}/patients/dashboard/summary`);
        const data = await res.json();
        setSummary(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

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
            <h3>👶 Total Patients</h3>
            <h2>{summary?.total_patients || 0}</h2>
          </div>

          <div className="card">
            <h3>🎤 Total Sessions</h3>
            <h2>{summary?.total_sessions || 0}</h2>
          </div>

          <div className="card">
            <h3>⭐ Avg Accuracy</h3>
            <h2>{summary?.avg_accuracy ? `${summary.avg_accuracy.toFixed(1)}%` : '—'}</h2>
          </div>
        </div>
      )}
    </div>
  );
}