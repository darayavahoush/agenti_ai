import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import LiveTherapy from "./pages/LiveTherapy";
import Patients from "./pages/Patients";
import Assessment from "./pages/assessment";

// BreathQuest App - completely isolated
import BreathQuestApp from "../breathquest/App";

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
        {/* Main VaakSuddhi routes */}
        <Route path="/*" element={<AppContent />} />
        
        {/* BreathQuest route - completely isolated app */}
        <Route path="/breathquest/*" element={<BreathQuestApp />} />
      </Routes>
    </BrowserRouter>
  );
}