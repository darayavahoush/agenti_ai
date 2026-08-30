import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { History, RotateCcw, Sparkles, Star } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { assessmentAPI, getErrorMessage } from '../../api/client'
import { PageLoader, Button, Avatar, Sidebar } from '../../components/ui'
import { KID_SIDEBAR_ITEMS } from '../../lib/kidSidebarItems'
import Assessment from '../../assessment/Assessment'

// Bootstraps a logged-in kid into the standalone Assessment flow
// (frontend/src/assessment/Assessment.jsx) without its own separate
// name+DOB login screen: POST /assessment/start auto-links or creates the
// Assessment-side Patient row for this kid.
//
// Shows a welcome screen first with a choice: retake/start the assessment,
// or go look at history -- rather than auto-redirecting either way. On
// finish, marks the kid's account assessment_completed and routes to the
// report/paywall screen as before.
export default function AssessmentGate() {
  const navigate = useNavigate()
  const { patient, markAssessmentComplete, logout } = useAuth()
  const [state, setState] = useState({ status: 'loading' }) // loading | choice | assessment | error
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    let cancelled = false
    assessmentAPI.start()
      .then(({ data }) => {
        if (cancelled) return
        setState({ status: 'choice', data })
      })
      .catch((err) => { if (!cancelled) setState({ status: 'error', message: getErrorMessage(err) }) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (state.status !== 'choice') return
    const t = setTimeout(() => setMounted(true), 30)
    return () => clearTimeout(t)
  }, [state.status])

  if (state.status === 'loading') return <PageLoader />

  if (state.status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#12142E' }}>
        <div className="text-center text-white/60 max-w-sm px-6">
          <p className="mb-4">{state.message || "Couldn't start the assessment."}</p>
          <button onClick={() => window.location.reload()} className="text-white underline">
            Try again
          </button>
        </div>
      </div>
    )
  }

  const handleFinish = async (summary) => {
    try {
      await markAssessmentComplete(summary)
    } finally {
      navigate('/assessment/report', { state: { summary }, replace: true })
    }
  }

  if (state.status === 'assessment') {
    return (
      <div className="flex min-h-screen">
        <Sidebar role="kid" items={KID_SIDEBAR_ITEMS} name={patient?.first_name} onLogout={logout} />
        <div className="flex-1">
          <Assessment
            authedPatientId={state.data.assessment_patient_id}
            authedPatientName={state.data.first_name}
            onFinish={handleFinish}
          />
        </div>
      </div>
    )
  }

  // status === 'choice'
  const { data } = state
  const alreadyCompleted = !!data.already_completed
  const onCooldown = data.retake_available_at ? new Date(data.retake_available_at) > new Date() : false
  const retakeDateLabel = onCooldown
    ? new Date(data.retake_available_at).toLocaleDateString(undefined, { month: 'long', day: 'numeric' })
    : null

  return (
    <div className="flex min-h-screen">
      <Sidebar role="kid" items={KID_SIDEBAR_ITEMS} name={patient?.first_name} onLogout={logout} />
      <div
        className="flex-1 flex items-center justify-center px-6 py-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(160deg, #2A1F5C 0%, #4A2E6E 45%, #6B3A5E 100%)' }}
      >
      {/* Playful floating stickers scattered around the screen */}
      <div className="absolute top-[12%] left-[10%] text-5xl opacity-70 motion-safe:animate-float pointer-events-none select-none">⭐</div>
      <div className="absolute top-[20%] right-[12%] text-4xl opacity-60 motion-safe:animate-float pointer-events-none select-none" style={{ animationDelay: '0.8s' }}>🎈</div>
      <div className="absolute bottom-[18%] left-[8%] text-4xl opacity-60 motion-safe:animate-float pointer-events-none select-none" style={{ animationDelay: '1.4s' }}>🌟</div>
      <div className="absolute bottom-[25%] right-[9%] text-5xl opacity-70 motion-safe:animate-float pointer-events-none select-none" style={{ animationDelay: '0.4s' }}>✨</div>
      <div className="absolute top-[45%] left-[5%] text-3xl opacity-50 motion-safe:animate-float pointer-events-none select-none" style={{ animationDelay: '1.8s' }}>🎵</div>
      <div className="absolute top-[50%] right-[6%] text-3xl opacity-50 motion-safe:animate-float pointer-events-none select-none" style={{ animationDelay: '1s' }}>🎶</div>

      {/* Soft color glows behind everything */}
      <div className="absolute top-10 left-16 w-72 h-72 bg-[#A8FF6F]/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-16 w-72 h-72 bg-[#FF9B54]/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-brand-teal/10 rounded-full blur-3xl pointer-events-none" />

      <div
        className={`max-w-md w-full text-center relative transition-all duration-700 ${
          mounted ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-8 scale-95'
        }`}
      >
        <div className="relative inline-block mb-4">
          <div
            className="absolute inset-0 rounded-full blur-xl motion-safe:animate-pulse-slow"
            style={{ background: 'radial-gradient(circle, #A8FF6F55 0%, transparent 70%)' }}
          />
          <div className="relative motion-safe:animate-float">
            <Avatar avatar={patient?.avatar} photoUrl={patient?.avatar_photo_url} size="xl" />
          </div>
        </div>

        <div
          className="text-7xl mb-2 motion-safe:animate-bounce inline-block"
          style={{ animationDuration: '1.6s' }}
        >
          🎤
        </div>

        <h1 className="font-vm-display text-4xl font-black text-white mb-2 drop-shadow-lg">
          Hi, {patient?.first_name || 'friend'}! 🎉
        </h1>
        <p className="text-white/70 text-base mb-8 font-medium">
          {alreadyCompleted
            ? "Ready to check in again, or want to see how far you've come?"
            : 'Ready for a quick speech check-in?'}
        </p>

        <div
          className={`rounded-3xl p-6 mb-6 text-left border-2 transition-all duration-700 delay-150 ${
            mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{
            background: 'linear-gradient(160deg, rgba(168,255,111,0.16) 0%, rgba(30,30,63,0.6) 70%)',
            borderColor: 'rgba(168,255,111,0.3)',
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-5 h-5 text-[#A8FF6F]" />
            <span className="text-white font-bold text-base">
              {alreadyCompleted ? "You've done this before!" : 'First time here!'}
            </span>
            <Star className="w-4 h-4 text-[#A8FF6F] motion-safe:animate-pulse-slow ml-auto" fill="#A8FF6F" />
          </div>
          <p className="text-sm text-white/70 leading-relaxed">
            {alreadyCompleted
              ? onCooldown
                ? `You can take it again on ${retakeDateLabel}. 📅`
                : "You can retake the assessment whenever you're ready. 💪"
              : "You'll answer a few speaking prompts into the mic -- about 5 minutes, no wrong answers. It's totally free, no payment needed. 🚀"}
          </p>
        </div>

        <div
          className={`transition-all duration-700 delay-300 ${
            mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          {(!alreadyCompleted || !onCooldown) && (
            <Button
              variant="primary"
              size="lg"
              className="w-full mb-4 hover:scale-105 active:scale-95 transition-transform duration-200
                         text-lg font-black shadow-[0_8px_24px_-4px_rgba(168,255,111,0.5)]"
              onClick={() => setState({ status: 'assessment', data })}
            >
              <RotateCcw size={18} className="inline mr-1.5 -mt-0.5" />
              {alreadyCompleted ? 'Retake Assessment' : 'Start Assessment'}
            </Button>
          )}

          {/* No "back to games" affordance here on purpose -- assessment
              is mandatory before any gameplay (ProtectedKid in App.jsx
              redirects any non-/assessment route straight back here while
              assessment_completed is false), so a button implying a kid
              could skip ahead and play was misleading: tapping it just
              bounced them right back to this same screen. */}
          <button
            onClick={() => navigate('/play/account/history')}
            className="w-full flex items-center justify-center gap-2 text-white/70 hover:text-white
                       hover:scale-105 text-base font-semibold transition-all mb-3 py-2"
          >
            <History size={17} /> View my history
          </button>
        </div>
      </div>
      </div>
    </div>
  )
}
