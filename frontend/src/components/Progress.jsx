import { useState, useEffect } from "react";
import { T, BACKEND } from "../constants";
import { Card, ProgressBar } from "./PastelUI";

export function Progress({ childId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHistory() {
      try {
        const res = await fetch(`${BACKEND}/history/${childId}`);
        const json = await res.json();
        if (json.success) {
          setData(json.data);
        }
      } catch (err) {
        console.error("Failed to fetch child history:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [childId]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "400px", color: T.textMuted }}>
        <p style={{ fontFamily: "'Nunito', sans-serif", fontSize: "18px", fontWeight: 700 }}>Gathering your therapy records...</p>
      </div>
    );
  }

  // Fallback for no data
  const hasData = data && data.total_attempts > 0;

  return (
    <div className="animate-slide-up" style={{ padding: "12px 0 40px 0" }}>
      <div style={{ display: "flex", justifyContent: "between", alignItems: "center", marginBottom: "32px" }}>
        <div>
          <h1 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "36px", fontWeight: 900, color: T.text, margin: 0 }}>
             Speech Progress
          </h1>
          <p style={{ color: T.textMuted, margin: "8px 0 0 0", fontSize: "16px" }}>Real-time phoneme diagnostics and accuracy tracking</p>
        </div>
      </div>

      {!hasData ? (
        <Card style={{ textAlign: "center", padding: "80px 40px" }}>
          <div style={{ color: T.primary, marginBottom: "20px", display: "flex", justifyContent: "center" }}>
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" x2="18" y1="20" y2="10" />
              <line x1="12" x2="12" y1="20" y2="4" />
              <line x1="6" x2="6" y1="20" y2="14" />
            </svg>
          </div>
          <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "24px", color: T.text, marginBottom: "8px" }}>No recordings yet</h3>
          <p style={{ maxWidth: "320px", margin: "0 auto", color: T.textMuted, lineHeight: 1.6 }}>
            Start practicing words or phonemes in the **Practice** tab, and your analytical charts will auto-populate here!
          </p>
        </Card>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px" }}>
          
          {/* Key metrics grid */}
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <Card style={{ background: `linear-gradient(135deg, ${T.primary}, #F472B6)`, color: "#FFF", borderColor: "transparent" }}>
              <h3 style={{ fontSize: "16px", textTransform: "uppercase", letterSpacing: "1px", opacity: 0.9, margin: "0 0 12px 0", fontWeight: 800 }}>Overall Accuracy</h3>
              <div style={{ display: "flex", alignItems: "baseline", gap: "12px", marginBottom: "8px" }}>
                <span style={{ fontSize: "64px", fontWeight: 900, lineHeight: 1 }}>{Math.round(data.overall_accuracy)}%</span>
              </div>
              <p style={{ margin: 0, opacity: 0.9, fontSize: "14px", fontWeight: 600 }}>Computed from Levenshtein comparison matrices</p>
            </Card>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
              <Card style={{ padding: "24px", textAlign: "center" }}>
                <div style={{ fontSize: "32px", marginBottom: "8px" }}>🔥</div>
                <div style={{ fontSize: "28px", fontWeight: 900, color: T.text }}>{data.streak || 0}</div>
                <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase", marginTop: "4px" }}>Active Streak</div>
              </Card>
              <Card style={{ padding: "24px", textAlign: "center" }}>
                <div style={{ fontSize: "32px", marginBottom: "8px" }}>🎯</div>
                <div style={{ fontSize: "28px", fontWeight: 900, color: T.text }}>{data.total_attempts}</div>
                <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase", marginTop: "4px" }}>Attempts</div>
              </Card>
            </div>
            
            {/* diagnostic breakdown */}
            <Card>
              <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "20px", fontWeight: 800, color: T.text, margin: "0 0 20px 0" }}>Diagnostic Details</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: `1px solid ${T.border}`, paddingBottom: "12px" }}>
                  <span style={{ color: T.textMuted, fontWeight: 600 }}>Correct Matches</span>
                  <span style={{ color: T.correct, fontWeight: 800 }}>{data.correct_count}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: `1px solid ${T.border}`, paddingBottom: "12px" }}>
                  <span style={{ color: T.textMuted, fontWeight: 600 }}>Struggling Sounds</span>
                  <span style={{ color: T.wrong, fontWeight: 800 }}>{data.phonemes?.filter(p => p.accuracy < 60).length || 0}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: T.textMuted, fontWeight: 600 }}>Strong Sounds</span>
                  <span style={{ color: T.correct, fontWeight: 800 }}>{data.phonemes?.filter(p => p.accuracy >= 80).length || 0}</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Phonemes Breakdown bar charts */}
          <Card style={{ display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "20px", fontWeight: 800, color: T.text, margin: "0 0 16px 0" }}>Phoneme Breakdown</h3>
            <p style={{ color: T.textMuted, fontSize: "14px", margin: "0 0 24px 0" }}>Performance across distinct sound channels. Weakest phonemes are shown first.</p>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px", overflowY: "auto", maxHeight: "400px", paddingRight: "8px" }}>
              {data.phonemes?.map((p) => {
                const isWeak = p.accuracy < 60;
                const color = isWeak ? T.wrong : (p.accuracy >= 80 ? T.correct : T.secondary);
                return (
                  <ProgressBar 
                    key={p.phoneme} 
                    label={`Sound /${p.phoneme}/`} 
                    progress={Math.round(p.accuracy)} 
                    color={color} 
                  />
                );
              })}
            </div>
          </Card>
          
        </div>
      )}
    </div>
  );
}
