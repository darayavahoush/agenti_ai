import { useState } from "react";
import { T } from "../constants";
import { BunnyMascot } from "./UI";

export function DashboardLayout({ children, currentTab, setTab }) {
  const tabs = [
    { 
      id: "practice", 
      label: "Practice", 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" x2="12" y1="19" y2="22" />
        </svg>
      ) 
    },
    { 
      id: "progress", 
      label: "Progress", 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" x2="18" y1="20" y2="10" />
          <line x1="12" x2="12" y1="20" y2="4" />
          <line x1="6" x2="6" y1="20" y2="14" />
        </svg>
      ) 
    },
    { 
      id: "journal", 
      label: "Journal", 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
          <path d="M6 6h10" />
          <path d="M6 10h10" />
        </svg>
      ) 
    },
    { 
      id: "profile", 
      label: "Profile", 
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      ) 
    },
  ];

  return (
    <div style={{ width: "100%", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Top Navigation */}
      <header style={{
        width: "100%",
        padding: "24px 60px",
        background: "rgba(255,255,255,0.7)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: `1px solid ${T.border}`,
        position: "sticky",
        top: 0,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between"
      }}>
        {/* Logo area */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px", cursor: "pointer" }} onClick={() => setTab("practice")} className="clickable">
          <BunnyMascot size={40} mood="happy" style={{ animation: "none" }} />
          <h2 style={{ fontFamily: "'Nunito', sans-serif", fontSize: "28px", fontWeight: 900, color: T.primary, margin: 0, letterSpacing: "-0.5px" }}>
            VaakSiddhi
          </h2>
        </div>

        {/* Desktop Tabs */}
        <nav style={{ display: "flex", gap: "12px", background: "#FFF5EF", padding: "6px", borderRadius: "100px", border: `1px solid ${T.border}` }}>
          {tabs.map(tab => {
            const active = currentTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setTab(tab.id)}
                className="clickable"
                style={{
                  padding: "10px 24px",
                  borderRadius: "100px",
                  border: "none",
                  background: active ? T.surface : "transparent",
                  color: active ? T.primary : T.textMuted,
                  fontFamily: "'Nunito', sans-serif",
                  fontWeight: active ? 800 : 600,
                  fontSize: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  boxShadow: active ? T.shadowSm : "none",
                  transition: "all 0.3s ease"
                }}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            )
          })}
        </nav>

        {/* User Profile Mini */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ textAlign: "right", display: "none" /* hidden on very small screens, though this is desktop */ }}>
            <div style={{ fontSize: "12px", color: T.textMuted, fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px" }}>Welcome Back,</div>
            <div style={{ fontSize: "16px", color: T.text, fontWeight: 800 }}>Dr. Therapist</div>
          </div>
          <div className="clickable" style={{ width: "48px", height: "48px", borderRadius: "50%", background: T.secondary, display: "flex", alignItems: "center", justifyContent: "center", color: "#FFF", fontSize: "20px", fontWeight: "bold", boxShadow: T.shadowSm }}>
            DT
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: "40px 60px", position: "relative" }}>
         {/* Very subtle background blobs for the dashboard */}
         <div className="bg-blob-1" style={{ opacity: 0.5, top: "-20%" }} />
         <div className="bg-blob-2" style={{ opacity: 0.5, bottom: "-20%" }} />
         
         <div style={{ maxWidth: "1200px", margin: "0 auto", position: "relative", zIndex: 1 }}>
            {children}
         </div>
      </main>
    </div>
  );
}
