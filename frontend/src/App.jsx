import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import LiveTherapy from "./pages/LiveTherapy";
import Patients from "./pages/Patients";
import Assessment from "./pages/assessment";

// BreathQuest pages
import BreathQuestLanding from "./pages/BreathQuestLanding";
import BreathQuestKidPlay from "./pages/kid/Play";
import BreathQuestLevelSelect from "./pages/kid/LevelSelect";
import BreathQuestGamePage from "./pages/kid/GamePage";
import BreathQuestTherapistLogin from "./pages/therapist/Login";
import BreathQuestTherapistDashboard from "./pages/therapist/Dashboard";
import BreathQuestPatientDetail from "./pages/therapist/PatientDetail";

import { BreathQuestAuthProvider } from "./context/BreathQuestAuth";

import { Landing } from "./components/Landing";
import Sidebar from "./components/Sidebar";

import "./App.css";

// Wrapper to completely isolate BreathQuest pages from main app styles
function BreathQuestLayout({ children }) {
  return (
    <div style={{
      width: '100vw',
      maxWidth: '100vw',
      overflowX: 'hidden',
      margin: 0,
      padding: 0,
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0
    }}>
      {children}
    </div>
  );
}

// Wrapper component to handle page state for non-BreathQuest routes
function AppContent() {
  const [page, setPage] = useState("landing");
  const location = useLocation();

  // Check if current route is a BreathQuest route
  const isBreathQuestRoute = location.pathname.startsWith('/breathquest');

  return (
    <div className="app">
      {!isBreathQuestRoute && page !== "landing" && <Sidebar setPage={setPage} page={page} />}

      <div className="content">
        {!isBreathQuestRoute && (
          <>
            {page === "landing" && <Landing onStart={() => setPage("therapy")} />}
            {page === "dashboard" && <Dashboard />}
            {page === "therapy" && <LiveTherapy setPage={setPage} />}
            {page === "patients" && <Patients />}
            {page === "assessment" && <Assessment />}
          </>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* BreathQuest routes - completely separate from main app */}
        <Route path="/breathquest" element={
          <BreathQuestLayout>
            <BreathQuestAuthProvider>
              <BreathQuestLanding />
            </BreathQuestAuthProvider>
          </BreathQuestLayout>
        } />
        <Route path="/breathquest/play" element={
          <BreathQuestLayout>
            <BreathQuestAuthProvider>
              <BreathQuestKidPlay />
            </BreathQuestAuthProvider>
          </BreathQuestLayout>
        } />
        <Route path="/breathquest/play/levels" element={
          <BreathQuestLayout>
            <BreathQuestAuthProvider>
              <BreathQuestLevelSelect />
            </BreathQuestAuthProvider>
          </BreathQuestLayout>
        } />
        <Route path="/breathquest/play/game/:levelId" element={
          <BreathQuestLayout>
            <BreathQuestAuthProvider>
              <BreathQuestGamePage />
            </BreathQuestAuthProvider>
          </BreathQuestLayout>
        } />
        <Route path="/breathquest/therapist/login" element={
          <BreathQuestLayout>
            <BreathQuestAuthProvider>
              <BreathQuestTherapistLogin />
            </BreathQuestAuthProvider>
          </BreathQuestLayout>
        } />
        <Route path="/breathquest/therapist/dashboard" element={
          <BreathQuestLayout>
            <BreathQuestAuthProvider>
              <BreathQuestTherapistDashboard />
            </BreathQuestAuthProvider>
          </BreathQuestLayout>
        } />
        <Route path="/breathquest/therapist/patients/:id" element={
          <BreathQuestLayout>
            <BreathQuestAuthProvider>
              <BreathQuestPatientDetail />
            </BreathQuestAuthProvider>
          </BreathQuestLayout>
        } />
        
        {/* Main VaakSuddhi routes */}
        <Route path="/*" element={<AppContent />} />
      </Routes>
    </BrowserRouter>
  );
}