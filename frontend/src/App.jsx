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
          <BreathQuestAuthProvider>
            <BreathQuestLanding />
          </BreathQuestAuthProvider>
        } />
        <Route path="/breathquest/play" element={
          <BreathQuestAuthProvider>
            <BreathQuestKidPlay />
          </BreathQuestAuthProvider>
        } />
        <Route path="/breathquest/play/levels" element={
          <BreathQuestAuthProvider>
            <BreathQuestLevelSelect />
          </BreathQuestAuthProvider>
        } />
        <Route path="/breathquest/play/game/:levelId" element={
          <BreathQuestAuthProvider>
            <BreathQuestGamePage />
          </BreathQuestAuthProvider>
        } />
        <Route path="/breathquest/therapist/login" element={
          <BreathQuestAuthProvider>
            <BreathQuestTherapistLogin />
          </BreathQuestAuthProvider>
        } />
        <Route path="/breathquest/therapist/dashboard" element={
          <BreathQuestAuthProvider>
            <BreathQuestTherapistDashboard />
          </BreathQuestAuthProvider>
        } />
        <Route path="/breathquest/therapist/patients/:id" element={
          <BreathQuestAuthProvider>
            <BreathQuestPatientDetail />
          </BreathQuestAuthProvider>
        } />
        
        {/* Main VaakSuddhi routes */}
        <Route path="/*" element={<AppContent />} />
      </Routes>
    </BrowserRouter>
  );
}