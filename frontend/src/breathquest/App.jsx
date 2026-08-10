import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { PageLoader } from './components/ui'

import Landing            from './pages/Landing'
import TherapistLogin     from './pages/therapist/Login'
import TherapistDashboard from './pages/therapist/Dashboard'
import PatientDetail      from './pages/therapist/PatientDetail'
import KidPlay            from './pages/kid/Play'
import LevelSelect        from './pages/kid/LevelSelect'
import GamePage           from './pages/kid/GamePage'

function ProtectedTherapist({ children }) {
  const { isTherapist, loading } = useAuth()
  if (loading) return <PageLoader />
  if (!isTherapist) return <Navigate to="/breathquest/therapist/login" replace />
  return children
}

function ProtectedKid({ children }) {
  const { isKid, loading } = useAuth()
  if (loading) return <PageLoader />
  if (!isKid) return <Navigate to="/breathquest/play" replace />
  return children
}

function AppRoutes() {
  const { isTherapist, isKid, loading } = useAuth()
  if (loading) return <PageLoader />

  return (
    <Routes>
      <Route path="/" element={<Landing />} />

      {/* Therapist */}
      <Route path="/therapist/login" element={
        isTherapist ? <Navigate to="/breathquest/therapist/dashboard" replace /> : <TherapistLogin />
      } />
      <Route path="/therapist/dashboard" element={
        <ProtectedTherapist><TherapistDashboard /></ProtectedTherapist>
      } />
      <Route path="/therapist/patients/:id" element={
        <ProtectedTherapist><PatientDetail /></ProtectedTherapist>
      } />

      {/* Kid */}
      <Route path="/play" element={
        isKid ? <Navigate to="/breathquest/play/levels" replace /> : <KidPlay />
      } />
      <Route path="/play/register" element={
        isKid ? <Navigate to="/breathquest/play/levels" replace /> : <KidPlay />
      } />
      <Route path="/play/login" element={
        isKid ? <Navigate to="/breathquest/play/levels" replace /> : <KidPlay />
      } />
      <Route path="/play/levels" element={
        <ProtectedKid><LevelSelect /></ProtectedKid>
      } />
      <Route path="/play/game/:levelId" element={
        <ProtectedKid><GamePage /></ProtectedKid>
      } />

      <Route path="*" element={<Navigate to="/breathquest" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
