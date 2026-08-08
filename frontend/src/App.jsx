import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import LiveTherapy from "./pages/LiveTherapy";
import Patients from "./pages/Patients";
import Assessment from "./pages/assessment";

import { Landing } from "./components/Landing";
import Sidebar from "./components/Sidebar";

import "./App.css";

// Wrapper component to handle page state
function AppContent({ page, setPage }) {

  return (
    <div className="app">
      {page !== "landing" && page !== "therapy" && <Sidebar setPage={setPage} page={page} />}

      <div className="content">
        <>
          {page === "landing" && <Landing onStart={(target) => setPage(target || "therapy")} />}
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
  const [page, setPage] = useState(() => new URLSearchParams(window.location.search).get("page") || "landing");

  return (
    <BrowserRouter>
      <Routes>
        {/* breathquest, vaakmirror, and voice-hurdle-race moved to the
            standalone quest-games apps -- see the frontend merge plan. */}
        <Route path="/*" element={<AppContent page={page} setPage={setPage} />} />
      </Routes>
    </BrowserRouter>
  );
}