import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { PartyPopper, Sparkles, Lock, CheckCircle2, RotateCcw } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Button, Card } from '../../components/ui'
import { meAPI } from '../../api/client'

// Shown right after a kid finishes their first assessment
// (pages/kid/AssessmentGate.jsx's onFinish) -- and also whatever this kid
// lands on later once ProtectedKid's entitlement check (App.jsx) redirects
// them here for lacking an active subscription. Real gameplay routes are
// gated by GET /me/access now; this page reads the same endpoint just to
// show accurate copy (trial days left, etc.) instead of a generic nudge.
export default function AssessmentReport() {
  const navigate = useNavigate()
  const { patient } = useAuth()
  const location = useLocation()
  const routedSummary = location.state?.summary

  const [access, setAccess] = useState(null) // null = loading
  const [latest, setLatest] = useState(null) // fallback when no router state

  useEffect(() => {
    let cancelled = false
    meAPI.access()
      .then(({ data }) => { if (!cancelled) setAccess(data) })
      .catch(() => { if (!cancelled) setAccess({ has_access: false, reason: 'unknown' }) })
    return () => { cancelled = true }
  }, [])

  // No router state means we weren't routed here right after finishing an
  // assessment (e.g. tapped "My Results" from GamePicker instead) -- fetch
  // the kid's most recent result directly.
  useEffect(() => {
    if (routedSummary) return
    let cancelled = false
    meAPI.latestAssessment()
      .then(({ data }) => { if (!cancelled) setLatest(data) })
      .catch(() => { if (!cancelled) setLatest(null) })
    return () => { cancelled = true }
  }, [routedSummary])

  // wordsAttempted only exists on the just-finished-assessment path -- the
  // stored session record doesn't track it, so it's unknown on revisit.
  const wordsAttempted = routedSummary?.wordsAttempted ?? null
  const severity = routedSummary?.severityClassification ?? latest?.severity_classification

  // retake_available_at is only ever set (non-null) while still on
  // cooldown -- see assessment.py's _retake_available_at. null here means
  // either "never taken" (shouldn't reach this page) or "cooldown's
  // already lifted", both of which mean a retake is allowed right now.
  const retakeAvailableAt = location.state?.retakeAvailableAt ?? latest?.retake_available_at ?? null
  const onCooldown = retakeAvailableAt ? new Date(retakeAvailableAt) > new Date() : false
  const retakeDateLabel = onCooldown
    ? new Date(retakeAvailableAt).toLocaleDateString(undefined, { month: 'long', day: 'numeric' })
    : null

  const trialDaysLeft = access?.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(access.trial_ends_at) - new Date()) / 86400000))
    : null

  return (
    <div
      className="min-h-screen flex items-center justify-center px-6 py-12"
      style={{ background: 'linear-gradient(180deg, #12142E 0%, #241F49 45%, #3A2C5C 100%)' }}
    >
      <div className="max-w-md w-full text-center">
        <div className="flex justify-center mb-4">
          <PartyPopper className="w-10 h-10 text-brand-green" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">
          Nice work{patient?.first_name ? `, ${patient.first_name}` : ''}!
        </h1>
        <p className="text-white/50 text-sm mb-8">
          You just finished your first speech check-in.
        </p>

        <Card className="text-left mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-brand-green" />
            <span className="text-white font-semibold text-sm">Your free preview</span>
          </div>
          <div className="space-y-2 text-sm text-white/70">
            {wordsAttempted !== null && (
              <div className="flex justify-between">
                <span>Words attempted</span>
                <span className="text-white font-medium">{wordsAttempted}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Early read</span>
              <span className="text-white font-medium">{severity || 'Looking good so far'}</span>
            </div>
          </div>

          {access?.has_access ? (
            <div className="mt-4 pt-4 border-t border-white/10 flex items-start gap-2 text-brand-green text-xs">
              <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>
                {access.reason === 'trialing' && trialDaysLeft !== null
                  ? `${trialDaysLeft} day${trialDaysLeft === 1 ? '' : 's'} left on your free trial -- full report and games unlocked.`
                  : 'A plan is active on your account -- full report and games unlocked.'}
              </span>
            </div>
          ) : (
            <div className="mt-4 pt-4 border-t border-white/10 flex items-start gap-2 text-white/40 text-xs">
              <Lock className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>
                The full report -- error patterns, targeted quests, and progress tracking --
                unlocks with a parent or therapist plan.
              </span>
            </div>
          )}
        </Card>

        {access !== null && !access.has_access && (
          <Button
            variant="primary"
            size="lg"
            className="w-full mb-3"
            onClick={() => navigate('/parent/login')}
          >
            Ask a grown-up to start a free trial
          </Button>
        )}

        {onCooldown ? (
          <p className="text-white/30 text-xs mb-4">
            You can take this again on {retakeDateLabel}.
          </p>
        ) : (
          <button
            onClick={() => navigate('/assessment')}
            className="inline-flex items-center gap-1.5 text-white/50 hover:text-white text-sm
                       transition-colors mb-4"
          >
            <RotateCcw size={14} /> Take the assessment again
          </button>
        )}

        <button
          onClick={() => navigate('/play/account/history')}
          className="block mx-auto text-white/40 hover:text-white/70 text-sm transition-colors mb-2"
        >
          See my assessment &amp; game history →
        </button>
        <button
          onClick={() => navigate('/play')}
          className="text-white/40 hover:text-white/70 text-sm transition-colors"
        >
          Keep exploring the games →
        </button>
      </div>
    </div>
  )
}
