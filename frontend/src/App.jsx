import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import LiveTherapy from "./pages/LiveTherapy";
import Patients from "./pages/Patients";
import Progress from "./pages/Progress";
import Assessment from "./pages/assessment";

// BreathQuest pages
import BreathQuestLandingNew from "./pages/BreathQuestLandingNew";
import BreathQuestKidPlay from "./pages/BreathQuestKidPlay";
import BreathQuestLevelSelect from "./pages/BreathQuestLevelSelect";
import BreathQuestGamePage from "./pages/BreathQuestGamePage";

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
            {page === "progress" && <Progress />}
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
      <BreathQuestAuthProvider>
        <Routes>
          {/* Main VaakSuddhi routes */}
          <Route path="/*" element={<AppContent />} />
          
          {/* BreathQuest routes */}
          <Route path="/breathquest" element={<BreathQuestLandingNew />} />
          <Route path="/breathquest/play" element={<BreathQuestKidPlay />} />
          <Route path="/breathquest/play/levels" element={<BreathQuestLevelSelect />} />
          <Route path="/breathquest/play/game/:levelId" element={<BreathQuestGamePage />} />
        </Routes>
      </BreathQuestAuthProvider>
    </BrowserRouter>
  );
}