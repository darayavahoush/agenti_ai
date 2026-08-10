import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import Navbar from '../vaakmirror/components/Navbar.jsx';
import RequireAuth from '../vaakmirror/components/RequireAuth.jsx';
import Login from '../vaakmirror/pages/Login.jsx';
import PatientPicker from '../vaakmirror/pages/PatientPicker.jsx';
import Landing from '../vaakmirror/pages/Landing.jsx';
import MirrorMirror from '../vaakmirror/pages/MirrorMirror.jsx';
import TongueTamer from '../vaakmirror/pages/TongueTamer.jsx';
import LipSyncHero from '../vaakmirror/pages/LipSyncHero.jsx';
import Dashboard from '../vaakmirror/pages/Dashboard.jsx';
import Exercises from '../vaakmirror/pages/Exercises.jsx';

function VaakMirrorRoutes() {
  useEffect(() => {
    // Add vaakmirror-app class to body to isolate fonts and styles
    document.body.classList.add('vaakmirror-app');
    return () => document.body.classList.remove('vaakmirror-app');
  }, []);

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="login" element={<Login />} />
      <Route
        path="games/mirror-mirror"
        element={
          <RequireAuth kind="patient">
            <MirrorMirror />
          </RequireAuth>
        }
      />
      <Route
        path="games/tongue-tamer"
        element={
          <RequireAuth kind="patient">
            <TongueTamer />
          </RequireAuth>
        }
      />
      <Route
        path="games/lip-sync-hero"
        element={
          <RequireAuth kind="patient">
            <LipSyncHero />
          </RequireAuth>
        }
      />
      <Route
        path="patients"
        element={
          <RequireAuth kind="therapist">
            <PatientPicker />
          </RequireAuth>
        }
      />
      <Route
        path="dashboard"
        element={
          <RequireAuth kind="therapist">
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="exercises"
        element={
          <RequireAuth kind="therapist">
            <Exercises />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/vaakmirror" replace />} />
    </Routes>
  );
}

export default function VaakMirrorRouter() {
  return (
    <div className="min-h-screen bg-[#FBF7EE]">
      <a
        href="/?page=therapy"
        className="fixed top-20 right-4 z-50 rounded-full border border-[#0E2A2E]/20 bg-[#0E2A2E]/90 px-4 py-2 text-sm font-semibold text-[#FBF7EE] shadow-lg backdrop-blur transition-colors hover:border-[#2FB8A6] hover:text-[#2FB8A6]"
        aria-label="Return to the main VaaK Sudhi home page"
      >
        ← Home
      </a>
      <Navbar />
      <VaakMirrorRoutes />
    </div>
  );
}
