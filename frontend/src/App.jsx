import { useState } from "react";

import Dashboard from "./pages/Dashboard";
import LiveTherapy from "./pages/LiveTherapy";
import Patients from "./pages/Patients";
import Progress from "./pages/Progress";
import Assessment from "./pages/Assessment";

import { Landing } from "./components/Landing";
import Sidebar from "./components/Sidebar";

import "./App.css";

export default function App() {
  const [page, setPage] = useState("landing");

  return (
    <div className="app">
      {page !== "landing" && <Sidebar setPage={setPage} page={page} />}

      <div className="content">
        {page === "landing" && <Landing onStart={() => setPage("therapy")} />}

        {page === "dashboard" && <Dashboard />}

        {page === "therapy" && <LiveTherapy />}

        {page === "patients" && <Patients />}

        {page === "progress" && <Progress />}

        {page === "assessment" && <Assessment />}
      </div>
    </div>
  );
}