import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { meAPI } from './api/client'
import { PageLoader, SupervisedBanner } from './components/ui'

import { Landing as AgentiLanding } from './agenti/Landing'
import TherapistLogin     from './pages/therapist/Login'
import TherapistDashboard from './pages/therapist/Dashboard'
import PatientDetail      from './pages/therapist/PatientDetail'
import AgentInsight        from './pages/therapist/AgentInsight'
import KidPlay            from './pages/kid/Play'
import AssessmentGate      from './pages/kid/AssessmentGate'
import AssessmentReport    from './pages/kid/AssessmentReport'
import LevelSelect        from './pages/kid/LevelSelect'
import GamePage           from './pages/kid/GamePage'
import GamePicker         from './pages/kid/GamePicker'
import MyAccount          from './pages/kid/MyAccount'
import VaakMirrorHome     from './vaakmirror/VaakMirrorHome'
import MirrorMirror       from './vaakmirror/MirrorMirror'
import TongueTamer        from './vaakmirror/TongueTamer'
import LipSyncHero        from './vaakmirror/LipSyncHero'
import MinimalPairDrill   from './vaakmirror/MinimalPairDrill'
import ChimeHome          from './chime/ChimeHome'
import VillageBuilder     from './chime/VillageBuilder'
import RocketLaunch       from './chime/RocketLaunch'
import SubmarineDive      from './chime/SubmarineDive'
import FireflyJar         from './chime/FireflyJar'
import WindChimeGarden    from './chime/WindChimeGarden'
import BubbleWrapPop      from './chime/BubbleWrapPop'
import XylophoneTower    from './chime/XylophoneTower'
import LionsRoar          from './chime/LionsRoar'
import RequireLevelUnlocked from './chime/lib/RequireLevelUnlocked'
import Flashcards from './pages/kid/Flashcards'
import VoiceHurdleRace    from './voiceHurdleRace/VoiceHurdleRace'
import ParentAuth         from './pages/parent/ParentAuth'
import ParentDashboard    from './pages/parent/ParentDashboard'
import Verify             from './pages/Verify'
import Billing            from './pages/Billing'
import AuthPage           from './pages/AuthPage'

// Lets Quest Hub hand off a logged-in session by linking here with
// ?token=&kind=&id=&name=&data= — adopts it into BreathQuest's OWN
// storage keys (bq_token / bq_user_type / bq_user_data), the same ones
// AuthContext reads on mount. `data` is the FULL raw response from
// BreathQuest's own /auth/login or /auth/kid-login (the hub logs in
// directly against BreathQuest, so this is real BreathQuest data, not a
// reconstruction) — using it directly means nothing gets lost, unlike
// rebuilding bq_user_data from just {kind, token, id, name}.
//
// Deliberately synchronous, NOT inside useEffect: AuthContext's own
// useEffect reads localStorage on mount to set React state. If this also
// ran in an effect, it would race AuthContext's effect with no guaranteed
// order. Running it here, in the component body, guarantees localStorage
// is populated before AuthProvider (a child of this function) ever mounts.
function adoptHubHandoffIfPresent() {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  const kind = params.get('kind')     // 'therapist' | 'patient' — matches bq_user_type values exactly
  const data = params.get('data')

  if (!token || !kind || !data) return

  try {
    const userData = JSON.parse(data)
    localStorage.setItem('bq_token', token)
    localStorage.setItem('bq_user_type', kind)
    localStorage.setItem('bq_user_data', JSON.stringify(userData))
  } catch {
    // Malformed data param — skip adoption rather than half-write storage
    return
  }

  // Strip the params from the URL/history without needing react-router
  // (this runs before BrowserRouter has mounted).
  const cleanUrl = window.location.pathname + window.location.hash
  window.history.replaceState({}, '', cleanUrl)
}

function ProtectedTherapist({ children }) {
  const { isTherapist, loading } = useAuth()
  if (loading) return <PageLoader />
  if (!isTherapist) return <Navigate to="/therapist/login" replace />
  return children
}

function ProtectedKid({ children, requireEntitlement = true }) {
  const { isKid, loading, patient } = useAuth()
  const location = useLocation()
  const [access, setAccess] = useState(null) // null = not yet checked this route

  const needsEntitlementCheck = requireEntitlement && isKid && !!patient?.assessment_completed

  useEffect(() => {
    if (!needsEntitlementCheck) { setAccess(null); return }
    let cancelled = false
    meAPI.access()
      .then(({ data }) => { if (!cancelled) setAccess(data) })
      // Fail open on a network/server error rather than locking a kid out
      // of games they may have already paid for over a flaky connection --
      // this is a soft-nudge product, not a high-security paywall. A real
      // "no subscription" response (has_access: false) still gates below.
      .catch(() => { if (!cancelled) setAccess({ has_access: true, reason: 'check_failed' }) })
    return () => { cancelled = true }
  }, [needsEntitlementCheck, location.pathname])

  if (loading) return <PageLoader />
  if (!isKid) return <Navigate to="/play" replace />
  // First-login gate: a kid who hasn't finished their assessment yet gets
  // routed there before anything else in /play/* -- except the assessment
  // routes themselves, which would otherwise redirect to themselves.
  if (!patient?.assessment_completed && !location.pathname.startsWith('/assessment')) {
    return <Navigate to="/assessment" replace />
  }
  if (needsEntitlementCheck) {
    if (access === null) return <PageLoader />
    if (!access.has_access) return <Navigate to="/assessment/report" replace />
  }
  return children
}

function ProtectedParent({ children }) {
  const { isParent, loading } = useAuth()
  if (loading) return <PageLoader />
  if (!isParent) return <Navigate to="/parent/login" replace />
  return children
}

function AppRoutes() {
  const { isTherapist, isKid, isParent, loading } = useAuth()
  const navigate = useNavigate()
  if (loading) return <PageLoader />

  return (
    <>
      <SupervisedBanner />
      <Routes>
        <Route path="/" element={<AgentiLanding onStart={(target) => {
          // target is "play-select" or "play-select?mode=signin" -- carry
          // mode through to the unified page, same as before.
          const mode = target.includes('mode=signin') ? '&mode=signin' : ''
          navigate(`/auth?role=kid${mode}`)
        }} />} />
        <Route path="/auth" element={<AuthPage />} />
        {/* Old deep link -- still works, lands on the unified page, kid tab preset */}
        <Route path="/play-select" element={<AuthPage initialRole="kid" />} />
        <Route path="/verify" element={<Verify />} />

        {/* Therapist */}
        <Route path="/therapist/login" element={
          isTherapist ? <Navigate to="/therapist/dashboard" replace /> : <TherapistLogin />
        } />
        <Route path="/therapist/dashboard" element={
          <ProtectedTherapist><TherapistDashboard /></ProtectedTherapist>
        } />
        <Route path="/therapist/patients/:id" element={
          <ProtectedTherapist><PatientDetail /></ProtectedTherapist>
        } />
        <Route path="/therapist/patients/:id/agent" element={
          <ProtectedTherapist><AgentInsight /></ProtectedTherapist>
        } />
        <Route path="/therapist/billing" element={
          <ProtectedTherapist><Billing role="therapist" /></ProtectedTherapist>
        } />

        {/* Kid */}
        <Route path="/play" element={
          isKid ? <ProtectedKid requireEntitlement={false}><GamePicker /></ProtectedKid> : <KidPlay />
        } />
        <Route path="/assessment" element={
          <ProtectedKid requireEntitlement={false}><AssessmentGate /></ProtectedKid>
        } />
        <Route path="/assessment/report" element={
          <ProtectedKid requireEntitlement={false}><AssessmentReport /></ProtectedKid>
        } />
        <Route path="/play/levels" element={
          <ProtectedKid><LevelSelect /></ProtectedKid>
        } />
        <Route path="/play/account" element={
          <ProtectedKid requireEntitlement={false}><MyAccount /></ProtectedKid>
        } />
        <Route path="/play/game/:levelId" element={
          <ProtectedKid><GamePage /></ProtectedKid>
        } />
        <Route path="/play/vaakmirror" element={
          <ProtectedKid><VaakMirrorHome /></ProtectedKid>
        } />
        <Route path="/play/vaakmirror/mirror-mirror" element={
          <ProtectedKid><MirrorMirror /></ProtectedKid>
        } />
        <Route path="/play/vaakmirror/tongue-tamer" element={
          <ProtectedKid><TongueTamer /></ProtectedKid>
        } />
        <Route path="/play/vaakmirror/lip-sync-hero" element={
          <ProtectedKid><LipSyncHero /></ProtectedKid>
        } />
        <Route path="/play/vaakmirror/minimal-pair-drill" element={
          <ProtectedKid><MinimalPairDrill /></ProtectedKid>
        } />
        <Route path="/play/chime" element={
          <ProtectedKid><ChimeHome /></ProtectedKid>
        } />
        <Route path="/play/chime/rocket-launch" element={
          <ProtectedKid><RequireLevelUnlocked levelId="aa"><RocketLaunch /></RequireLevelUnlocked></ProtectedKid>
        } />
        <Route path="/play/chime/submarine-dive" element={
          <ProtectedKid><RequireLevelUnlocked levelId="oo"><SubmarineDive /></RequireLevelUnlocked></ProtectedKid>
        } />
        <Route path="/play/chime/firefly-jar" element={
          <ProtectedKid><RequireLevelUnlocked levelId="ma"><FireflyJar /></RequireLevelUnlocked></ProtectedKid>
        } />
        <Route path="/play/chime/wind-chime-garden" element={
          <ProtectedKid><RequireLevelUnlocked levelId="fa"><WindChimeGarden /></RequireLevelUnlocked></ProtectedKid>
        } />
        <Route path="/play/chime/bubble-wrap-pop" element={
          <ProtectedKid><RequireLevelUnlocked levelId="ha"><BubbleWrapPop /></RequireLevelUnlocked></ProtectedKid>
        } />
        <Route path="/play/chime/xylophone-tower" element={
          <ProtectedKid><RequireLevelUnlocked levelId="ee"><XylophoneTower /></RequireLevelUnlocked></ProtectedKid>
        } />
        <Route path="/play/chime/lions-roar" element={
          <ProtectedKid><RequireLevelUnlocked levelId="r"><LionsRoar /></RequireLevelUnlocked></ProtectedKid>
        } />
        <Route path="/play/chime/village-builder" element={
          <ProtectedKid><RequireLevelUnlocked levelId="village-builder"><VillageBuilder /></RequireLevelUnlocked></ProtectedKid>
        } />
        <Route path="/play/voice-hurdle-race" element={
          <ProtectedKid><VoiceHurdleRace /></ProtectedKid>
        } />
        <Route path="/play/flashcards" element={
          <ProtectedKid><Flashcards /></ProtectedKid>
        } />

        {/* Parent */}
        <Route path="/parent/login" element={<ParentAuth />} />
        <Route path="/parent/dashboard" element={
          <ProtectedParent><ParentDashboard /></ProtectedParent>
        } />
        <Route path="/parent/billing" element={
          <ProtectedParent><Billing role="parent" /></ProtectedParent>
        } />

        <Route path="*" element={
          <Navigate to={
            isTherapist ? '/therapist/dashboard'
              : isParent  ? '/parent/dashboard'
              : isKid     ? '/play'
              : '/'
          } replace />
        } />
        </Routes>
    </>
  )
}

export default function App() {
  adoptHubHandoffIfPresent()

  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
