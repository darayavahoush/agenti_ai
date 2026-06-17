import { useState } from "react";
import { T } from "../constants";
import { Card, Button } from "./UI";

export function Profile({ childId, activeSessionId, onResetSession }) {
  const [profile] = useState({
    name: "Gagan",
    id: childId,
    avatar: "🐰",
    level: 4,
    points: 1240,
    goals: [
      "Master the Hindi /r/ (र) sound in isolation",
      "Improve word accuracy above 85% for English words starting with 's'",
      "Maintain a 5-day daily practice streak"
    ],
    therapist: {
      name: "Dr. Ananya Malhotra, SLP",
      clinic: "VaakSuddhi Speech & Phonology Center",
      email: "contact@VaakSuddhi.in"
    }
  });

  return (
    <div className="animate-slide-up" style={{ padding: "12px 0 40px 0" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "36px", fontWeight: 900, color: T.text, margin: 0 }}>
           Student Profile
        </h1>
        <p style={{ color: T.textMuted, margin: "8px 0 0 0", fontSize: "16px" }}>Child diagnostic file, goals, and therapist connection</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px" }}>
        
        {/* Child avatar card */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <Card style={{ textAlign: "center", padding: "40px 24px" }}>
            <div style={{ 
              width: "100px", 
              height: "100px", 
              borderRadius: "50%", 
              background: `linear-gradient(135deg, ${T.primaryBg}, ${T.secondaryBg})`,
              display: "flex", 
              justifyContent: "center", 
              alignItems: "center", 
              fontSize: "48px", 
              margin: "0 auto 16px auto",
              boxShadow: T.shadowSm
            }}>
              {profile.avatar}
            </div>
            <h2 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "28px", fontWeight: 900, color: T.text, margin: "0 0 4px 0" }}>{profile.name}</h2>
            <p style={{ margin: 0, color: T.textMuted, fontSize: "14px", fontWeight: 700, textTransform: "uppercase" }}>Child ID: {profile.id}</p>
            
            <div style={{ display: "flex", justifyContent: "center", gap: "12px", marginTop: "24px" }}>
              <div style={{ background: T.primaryBg, padding: "8px 16px", borderRadius: "12px", fontSize: "14px", fontWeight: 800, color: T.primary }}>
                 Lv. {profile.level}
              </div>
              <div style={{ background: T.secondaryBg, padding: "8px 16px", borderRadius: "12px", fontSize: "14px", fontWeight: 800, color: T.secondary }}>
                 ⭐ {profile.points} pts
              </div>
            </div>
          </Card>

          {/* Active Session Card */}
          <Card>
            <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "18px", fontWeight: 800, color: T.text, margin: "0 0 16px 0" }}>Active Database Session</h3>
            {activeSessionId ? (
              <div>
                <p style={{ fontSize: "14px", color: T.textMuted, marginBottom: "8px" }}>Your practice metrics are currently writing to database session:</p>
                <div style={{ fontFamily: "monospace", padding: "12px", background: T.border, borderRadius: "12px", fontSize: "12px", wordBreak: "break-all", color: T.text, marginBottom: "20px" }}>
                  {activeSessionId}
                </div>
                <Button variant="outline" onClick={onResetSession} style={{ width: "100%", padding: "12px", fontSize: "14px" }}>
                  Reset & Start New Session
                </Button>
              </div>
            ) : (
              <div>
                <p style={{ fontSize: "14px", color: T.textMuted, margin: "0 0 16px 0" }}>No active session found. Practice actions are currently stateless.</p>
                <Button variant="primary" onClick={onResetSession} style={{ width: "100%", padding: "12px", fontSize: "14px" }}>
                  Initialize Active Session
                </Button>
              </div>
            )}
          </Card>
        </div>

        {/* Therapy Goals & Therapist Details */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <Card style={{ flex: 1 }}>
            <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "20px", fontWeight: 800, color: T.text, margin: "0 0 16px 0" }}>Active Speech Goals</h3>
            <ul style={{ paddingLeft: "20px", margin: 0, display: "flex", flexDirection: "column", gap: "16px", color: T.text, lineHeight: 1.6 }}>
              {profile.goals.map((g, index) => (
                <li key={index} style={{ fontWeight: 600, fontSize: "15px" }}>{g}</li>
              ))}
            </ul>
          </Card>

          <Card>
            <h3 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "20px", fontWeight: 800, color: T.text, margin: "0 0 4px 0" }}>Therapist Connection</h3>
            <p style={{ color: T.textMuted, fontSize: "14px", margin: "0 0 20px 0" }}>Connected clinical provider files</p>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase" }}>Primary Practitioner</div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: T.text, marginTop: "2px" }}>{profile.therapist.name}</div>
              </div>
              <div>
                <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase" }}>Clinic / facility</div>
                <div style={{ fontSize: "15px", fontWeight: 700, color: T.text, marginTop: "2px" }}>{profile.therapist.clinic}</div>
              </div>
              <div>
                <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase" }}>Contact email</div>
                <div style={{ fontSize: "15px", fontWeight: 700, color: T.primary, marginTop: "2px" }}>{profile.therapist.email}</div>
              </div>
            </div>
          </Card>
        </div>

      </div>
    </div>
  );
}
