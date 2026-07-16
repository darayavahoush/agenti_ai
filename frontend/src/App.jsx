import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import LiveTherapy from "./pages/LiveTherapy";
import Patients from "./pages/Patients";
import Assessment from "./pages/assessment";

// BreathQuest pages
import BreathQuestLanding from "../breathquest/pages/Landing";
import BreathQuestKidPlay from "../breathquest/pages/kid/Play";
import BreathQuestLevelSelect from "../breathquest/pages/kid/LevelSelect";
import BreathQuestGamePage from "../breathquest/pages/kid/GamePage";
import BreathQuestTherapistLogin from "../breathquest/pages/therapist/Login";
import BreathQuestTherapistDashboard from "../breathquest/pages/therapist/Dashboard";
import BreathQuestPatientDetail from "../breathquest/pages/therapist/PatientDetail";

import { BreathQuestAuthProvider } from "../breathquest/context/AuthContext";

import { Landing } from "./components/Landing";
import Sidebar from "./components/Sidebar";

import "./App.css";

// Wrapper component to handle page state for non-BreathQuest routes
function AppContent() {
  const [page, setPage] = useState("landing");
  const location = useLocation();

  // Check if current route is a BreathQuest route
  const isBreathQuestRoute = location.pathname.startsWith('/breathquest');

  // Return null for BreathQuest routes to let them take full viewport
  if (isBreathQuestRoute) {
    return null;
  }

  return (
    <div className="app">
      {page !== "landing" && <Sidebar setPage={setPage} page={page} />}

      <div className="content">
        <>
          {page === "landing" && <Landing onStart={() => setPage("therapy")} />}
          {page === "dashboard" && <Dashboard />}
          {page === "therapy" && <LiveTherapy setPage={setPage} />}
          {page === "patients" && <Patients />}
          {page === "assessment" && <Assessment />}
        </>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* BreathQuest routes */}
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