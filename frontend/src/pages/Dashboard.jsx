import { useEffect, useState } from "react";
import { getDashboardStats } from "../services/api";

const statStyle = {
  background: "#ffffff",
  borderRadius: "14px",
  padding: "20px",
  minWidth: "180px",
  boxShadow: "0 8px 22px rgba(91, 61, 177, 0.1)",
};

export default function Dashboard() {
  const [stats, setStats] = useState({ patients: 0, sessions: 0, accuracy: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch((err) => console.error("Failed to load dashboard stats", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1>VaakSuddhi Dashboard</h1>

      <div
        style={{
          display: "flex",
          gap: "20px",
          marginTop: "20px",
          flexWrap: "wrap",
        }}
      >
        <div className="card" style={statStyle}>
          <h3>Patients</h3>
          <h2>{loading ? "..." : stats.patients}</h2>
        </div>

        <div className="card" style={statStyle}>
          <h3>Sessions</h3>
          <h2>{loading ? "..." : stats.sessions}</h2>
        </div>

        <div className="card" style={statStyle}>
          <h3>Accuracy</h3>
          <h2>{loading ? "..." : `${stats.accuracy}%`}</h2>
        </div>
      </div>
    </div>
  );
}
