import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import { AuthProvider, useAuth } from '../breathquest/context/AuthContext';
import { PageLoader } from '../breathquest/components/ui';

import Landing from '../breathquest/pages/Landing';
import TherapistLogin from '../breathquest/pages/therapist/Login';
import TherapistDashboard from '../breathquest/pages/therapist/Dashboard';
import PatientDetail from '../breathquest/pages/therapist/PatientDetail';
import KidPlay from '../breathquest/pages/kid/Play';
import LevelSelect from '../breathquest/pages/kid/LevelSelect';
import GamePage from '../breathquest/pages/kid/GamePage';

function ProtectedTherapist({ children }) {
  const { isTherapist, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!isTherapist) return <Navigate to="/breathquest/therapist/login" replace />;
  return children;
}

function ProtectedKid({ children }) {
  const { isKid, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!isKid) return <Navigate to="/breathquest/play" replace />;
  return children;
}

function BreathQuestRoutes() {
  const { isTherapist, isKid, loading } = useAuth();

  useEffect(() => {
    document.body.classList.add('breathquest');
    return () => document.body.classList.remove('breathquest');
  }, []);

  if (loading) return <PageLoader />;

  return (
    <Routes>
      <Route index element={<Landing />} />

      <Route
        path="therapist/login"
        element={isTherapist ? <Navigate to="/breathquest/therapist/dashboard" replace /> : <TherapistLogin />}
      />
      <Route
        path="therapist/dashboard"
        element={
          <ProtectedTherapist>
            <TherapistDashboard />
          </ProtectedTherapist>
        }
      />
      <Route
        path="therapist/patients/:id"
        element={
          <ProtectedTherapist>
            <PatientDetail />
          </ProtectedTherapist>
        }
      />

      <Route
        path="play"
        element={isKid ? <Navigate to="/breathquest/play/levels" replace /> : <KidPlay />}
      />
      <Route
        path="play/register"
        element={isKid ? <Navigate to="/breathquest/play/levels" replace /> : <KidPlay />}
      />
      <Route
        path="play/login"
        element={isKid ? <Navigate to="/breathquest/play/levels" replace /> : <KidPlay />}
      />
      <Route
        path="play/levels"
        element={
          <ProtectedKid>
            <LevelSelect />
          </ProtectedKid>
        }
      />
      <Route
        path="play/game/:levelId"
        element={
          <ProtectedKid>
            <GamePage />
          </ProtectedKid>
        }
      />

      <Route path="*" element={<Navigate to="/breathquest" replace />} />
    </Routes>
  );
}

export default function BreathQuestRouter() {
  return (
    <AuthProvider>
      <BreathQuestRoutes />
    </AuthProvider>
  );
}
