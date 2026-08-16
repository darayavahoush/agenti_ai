import { useState, useEffect } from "react";
import { T, BACKEND } from "../constants";
import { Card, Button } from "./PastelUI";

export function Journal({ childId }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedSession, setExpandedSession] = useState(null);
  const [sessionDetail, setSessionDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    async function fetchSessions() {
      try {
        const res = await fetch(`${BACKEND}/history/${childId}/sessions`);
        const json = await res.json();
        if (json.success) {
          setSessions(json.data.sessions || []);
        }
      } catch (err) {
        console.error("Failed to fetch sessions:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchSessions();
  }, [childId]);

  const loadSessionDetails = async (sessionId) => {
    if (expandedSession === sessionId) {
      setExpandedSession(null);
      setSessionDetail(null);
      return;
    }
    setExpandedSession(sessionId);
    setDetailLoading(true);
    try {
      const res = await fetch(`${BACKEND}/sessions/${sessionId}`);
      const json = await res.json();
      if (json.success) {
        setSessionDetail(json.data);
      }
    } catch (err) {
      console.error("Failed to load session details:", err);
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "400px", color: T.textMuted }}>
        <p style={{ fontFamily: "'Nunito', sans-serif", fontSize: "18px", fontWeight: 700 }}>Reading your speech journal...</p>
      </div>
    );
  }

  return (
    <div className="animate-slide-up" style={{ padding: "12px 0 40px 0" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "36px", fontWeight: 900, color: T.text, margin: 0 }}>
           Therapy Journal
        </h1>
        <p style={{ color: T.textMuted, margin: "8px 0 0 0", fontSize: "16px" }}>Historical play sessions and word-by-word clinical summaries</p>
      </div>

      {sessions.length === 0 ? (
        <Card style={{ textAlign: "center", padding: "80px 40px" }}>
          <div style={{ color: T.secondary, marginBottom: "20px", display: "flex", justifyContent: "center" }}>
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6 2v20H4.5A2.5 2.5 0 0 1 2 19.5v-15A2.5 2.5 0 0 1 4.5 2H6Z" />
              <path d="M16 6H8" />
              <path d="M16 10H8" />
            </svg>
          </div>
          <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "24px", color: T.text, marginBottom: "8px" }}>Your journal is empty</h3>
          <p style={{ maxWidth: "320px", margin: "0 auto", color: T.textMuted, lineHeight: 1.6 }}>
             Complete a speech session by practicing a series of words, and they will be documented right here for review!
          </p>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {sessions.map((s) => {
            const date = new Date(s.started_at).toLocaleDateString("en-US", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            });
            const isExpanded = expandedSession === s.id;

            return (
              <Card key={s.id} style={{ padding: "24px", borderLeft: `6px solid ${T.primary}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
                  <div>
                    <span style={{ 
                      display: "inline-block", 
                      padding: "4px 12px", 
                      borderRadius: "100px", 
                      fontSize: "12px", 
                      fontWeight: 800, 
                      textTransform: "uppercase",
                      background: s.language === "hindi" ? "#FEF3C7" : "#DBEAFE",
                      color: s.language === "hindi" ? "#D97706" : "#2563EB",
                      marginBottom: "8px"
                    }}>
                      {s.language === "hindi" ? "🇮🇳 Hindi Session" : "🇺🇸 English Session"}
                    </span>
                    <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "20px", fontWeight: 800, color: T.text, margin: "0 0 4px 0" }}>{date}</h3>
                    <p style={{ margin: 0, color: T.textMuted, fontSize: "14px" }}>Session ID: <span style={{ fontFamily: "monospace" }}>{s.id.substring(0, 8)}...</span></p>
                  </div>
                  <Button variant="flat" onClick={() => loadSessionDetails(s.id)} style={{ padding: "10px 20px", fontSize: "14px" }}>
                    {isExpanded ? "Hide Details" : "View Analytics"}
                  </Button>
                </div>

                {isExpanded && (
                  <div style={{ marginTop: "24px", borderTop: `1px solid ${T.border}`, paddingTop: "24px" }}>
                    {detailLoading ? (
                      <p style={{ color: T.textMuted, fontWeight: 700 }}>Extracting database telemetry...</p>
                    ) : sessionDetail ? (
                      <div>
                        {/* Session stats overview */}
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "24px" }}>
                          <div style={{ background: T.surface, padding: "16px", borderRadius: "16px", border: `1px solid ${T.border}` }}>
                            <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase" }}>Total Practices</div>
                            <div style={{ fontSize: "24px", fontWeight: 800, color: T.text, marginTop: "4px" }}>{sessionDetail.session.total_analyses}</div>
                          </div>
                          <div style={{ background: T.surface, padding: "16px", borderRadius: "16px", border: `1px solid ${T.border}` }}>
                            <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase" }}>Average Accuracy</div>
                            <div style={{ fontSize: "24px", fontWeight: 800, color: T.correct, marginTop: "4px" }}>{Math.round(sessionDetail.session.avg_accuracy)}%</div>
                          </div>
                          <div style={{ background: T.surface, padding: "16px", borderRadius: "16px", border: `1px solid ${T.border}` }}>
                            <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase" }}>Status</div>
                            <div style={{ fontSize: "18px", fontWeight: 800, color: "#10B981", marginTop: "8px", textTransform: "capitalize" }}>{sessionDetail.session.status}</div>
                          </div>
                        </div>

                        {/* Words list */}
                        <h4 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "16px", fontWeight: 800, color: T.text, margin: "0 0 12px 0" }}>Practiced Words Summary</h4>
                        {sessionDetail.summary.words_attempted?.length === 0 ? (
                          <p style={{ color: T.textMuted, fontStyle: "italic" }}>No words attempted during this session.</p>
                        ) : (
                          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                            {sessionDetail.summary.words_attempted.map((w, index) => (
                              <div key={index} style={{ padding: "16px", background: T.surface, borderRadius: "16px", border: `1px solid ${T.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <div>
                                  <span style={{ fontSize: "18px", fontWeight: 800, color: T.text }}>{w.word}</span>
                                  <span style={{ marginLeft: "8px", color: T.textMuted, fontSize: "14px" }}>🗣 "{w.transcript}"</span>
                                </div>
                                <span style={{ 
                                  fontWeight: 800, 
                                  color: w.accuracy >= 80 ? T.correct : (w.accuracy >= 50 ? T.secondary : T.wrong),
                                  background: w.accuracy >= 80 ? T.correctBg : (w.accuracy >= 50 ? "#FEF3C7" : T.wrongBg),
                                  padding: "4px 10px",
                                  borderRadius: "8px",
                                  fontSize: "14px"
                                }}>
                                  {w.accuracy}%
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p style={{ color: T.wrong }}>Failed to retrieve session data.</p>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
