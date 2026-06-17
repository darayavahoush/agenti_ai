export default function Dashboard() {
  return (
    <div>
      <h1>🏠 VaakSiddhi Dashboard</h1>

      <div style={{
        display: "flex",
        gap: "20px",
        marginTop: "20px"
      }}>
        <div className="card">
          <h3>👶 Patients</h3>
          <h2>0</h2>
        </div>

        <div className="card">
          <h3>🎤 Sessions</h3>
          <h2>0</h2>
        </div>

        <div className="card">
          <h3>⭐ Accuracy</h3>
          <h2>0%</h2>
        </div>
      </div>
    </div>
  );
}