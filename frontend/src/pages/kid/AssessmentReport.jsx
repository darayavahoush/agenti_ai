import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { PartyPopper, Sparkles, Lock, CheckCircle2, RotateCcw, NotebookText } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Button, Card } from '../../components/ui'
import { meAPI } from '../../api/client'
import GamePlanCard from '../../components/kid/GamePlanCard'
import NextStepsWalkthrough from '../../components/kid/NextStepsWalkthrough'

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
  const [gamePlan, setGamePlan] = useState(null) // game-prediction agent's plan for these words

  useEffect(() => {
    let cancelled = false
    meAPI.access()
      .then(({ data }) => { if (!cancelled) setAccess(data) })
      .catch(() => { if (!cancelled) setAccess({ has_access: false, reason: 'unknown' }) })
    return () => { cancelled = true }
  }, [])

  // No router state means we weren't routed here right after finishing an
  // assessment (e.g. tapped "My Results" from GamePicker instead) -- fetch
  // the kid's most recent result directly. Fetched either way (not just as
  // a fallback) because it's also the only source for alphabet_completed,
  // which the walkthrough below needs even right after finishing the word
  // assessment.
  useEffect(() => {
    let cancelled = false
    meAPI.latestAssessment()
      .then(({ data }) => { if (!cancelled) setLatest(data) })
      .catch(() => { if (!cancelled) setLatest(null) })
    return () => { cancelled = true }
  }, [])

  // The plan is computed server-side when the assessment is completed, so
  // it is always fetched rather than carried in router state.
  useEffect(() => {
    let cancelled = false
    meAPI.gamePlan()
      .then(({ data }) => { if (!cancelled) setGamePlan(data) })
      .catch(() => { if (!cancelled) setGamePlan(null) })
    return () => { cancelled = true }
  }, [])

  // wordsAttempted only exists on the just-finished-assessment path -- the
  // stored session record doesn't track it, so it's unknown on revisit.
  const wordsAttempted = routedSummary?.wordsAttempted ?? null
  const severity = routedSummary?.severityClassification ?? latest?.severity_classification

  // Per-word breakdown for the unlocked "detailed results" view below --
  // present on the just-finished path via router state, and on a later
  // revisit via /assessment/me/latest's word_results (assessment_summary,
  // stamped by POST /assessment/complete). Empty on a patient with no
  // assessment_summary yet (e.g. one taken before this field existed).
  const wordResults = routedSummary?.wordResults ?? latest?.word_results ?? []
  const avgAccuracy = wordResults.length
    ? Math.round(wordResults.reduce((sum, w) => sum + (w.accuracy || 0), 0) / wordResults.length)
    : null
  // Tally how often each error pattern string shows up across every word
  // this run, so the card can surface the handful that came up most
  // instead of dumping every raw pattern from every word.
  const topErrorPatterns = Object.entries(
    wordResults
      .flatMap((w) => w.errorPatterns || [])
      .reduce((counts, p) => ({ ...counts, [p]: (counts[p] || 0) + 1 }), {})
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([pattern]) => pattern)

  // A plain-language aggregate summary -- separate from the per-word
  // diagnostic_report text below (each of those is written about ONE
  // word, e.g. "practicing 'apple'"), this is the whole-session read so
  // the report opens with something that actually reads like a summary
  // rather than only a scorecard.
  const sessionNarrative = wordResults.length
    ? `Across ${wordResults.length} word${wordResults.length === 1 ? '' : 's'}, ${patient?.first_name || 'the check-in'} averaged ${avgAccuracy}% accuracy` +
      (severity ? `, landing in the "${severity}" range` : '') +
      (topErrorPatterns.length
        ? `. The patterns that showed up most: ${topErrorPatterns.join(', ')}.`
        : '. No pattern stood out more than the others.')
    : null

  const alphabetCompleted = Boolean(latest?.alphabet_completed)

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

  // Only celebrate the very first time this page renders for a
  // just-finished assessment -- not on every later revisit (e.g. tapping
  // "My Results" from GamePicker), where a confetti burst would feel odd.
  const isFreshResult = Boolean(routedSummary)

  return (
    <div
      className="min-h-screen flex items-center justify-center px-6 py-12 overflow-hidden"
      style={{ background: 'linear-gradient(180deg, #12142E 0%, #241F49 45%, #3A2C5C 100%)' }}
    >
      <div className="relative max-w-md w-full text-center">
        {isFreshResult && (
          <div className="pointer-events-none absolute inset-x-0 -top-6 flex justify-center gap-6 z-10">
            {['🎉', '✨', '⭐️', '🎊'].map((e, i) => (
              <span
                key={i}
                className="text-xl animate-[confettiFall_1.6s_ease-in_forwards]"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                {e}
              </span>
            ))}
          </div>
        )}

        <div className="flex justify-center mb-4">
          <PartyPopper className={`w-10 h-10 text-brand-green ${isFreshResult ? 'animate-[popIn_0.5s_ease-out]' : ''}`} />
        </div>
        <h1 className="text-2xl font-bold text-white mb-2 animate-[fadeIn_0.5s_ease-out]">
          Nice work{patient?.first_name ? `, ${patient.first_name}` : ''}!
        </h1>
        <p className="text-white/50 text-sm mb-8 animate-[fadeIn_0.5s_ease-out_0.1s_backwards]">
          You just finished your first speech check-in.
        </p>

        <Card className="text-left mb-6 animate-[cardIn_0.5s_ease-out_0.15s_backwards]">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-brand-green animate-[spin_4s_linear_infinite]" />
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
            <div className="mt-4 pt-4 border-t border-white/10">
              <div className="flex items-start gap-2 text-brand-green text-xs mb-3">
                <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span>
                  {access.reason === 'trialing' && trialDaysLeft !== null
                    ? `${trialDaysLeft} day${trialDaysLeft === 1 ? '' : 's'} left on your free trial.`
                    : 'A plan is active on your account.'}
                </span>
              </div>

              {sessionNarrative && (
                <p className="text-white/70 text-xs leading-relaxed mb-3 flex items-start gap-1.5">
                  <NotebookText className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-brand-green" />
                  <span>{sessionNarrative}</span>
                </p>
              )}

              {wordResults.length > 0 ? (
                <>
                  {avgAccuracy !== null && (
                    <div className="flex justify-between text-sm mb-3">
                      <span className="text-white/70">Average accuracy</span>
                      <span className="text-white font-medium">{avgAccuracy}%</span>
                    </div>
                  )}

                  <div className="space-y-2.5 mb-3">
                    {wordResults.map((w, i) => (
                      <div key={i} className="text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-white/70 capitalize">{w.targetWord}</span>
                          <div className="flex items-center gap-2 flex-1 mx-3">
                            <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${Math.max(0, Math.min(100, w.accuracy || 0))}%`,
                                  background: (w.accuracy || 0) >= 75 ? '#A8FF6F' : (w.accuracy || 0) >= 45 ? '#FF9B54' : '#FF6F6F',
                                }}
                              />
                            </div>
                          </div>
                          <span className="text-white/50 w-9 text-right">{w.accuracy ?? '--'}%</span>
                        </div>
                        {w.diagnosticReport && (
                          <p className="text-white/40 text-[11px] leading-snug mt-1 pl-0.5">{w.diagnosticReport}</p>
                        )}
                      </div>
                    ))}
                  </div>

                  {topErrorPatterns.length > 0 && (
                    <div className="text-xs text-white/50">
                      <span className="text-white/70 font-medium">Watch for: </span>
                      {topErrorPatterns.join(', ')}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-white/50 text-xs">
                  No per-word breakdown on file for this check-in yet -- it'll show up next time.
                </p>
              )}
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

        <GamePlanCard plan={gamePlan} className="mb-6 animate-[cardIn_0.5s_ease-out_0.25s_backwards]" />

        <NextStepsWalkthrough
          plan={gamePlan}
          alphabetCompleted={alphabetCompleted}
          severity={severity}
          firstName={patient?.first_name}
          className="mb-6 animate-[cardIn_0.5s_ease-out_0.3s_backwards]"
        />

        {access !== null && !access.has_access && (
          <Button
            variant="primary"
            size="lg"
            className="w-full mb-3 animate-[cardIn_0.5s_ease-out_0.2s_backwards]"
            onClick={() => navigate(`/parent/login?from=kid_trial&kid=${encodeURIComponent(patient?.first_name || '')}`)}
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

      <style>{`
        @keyframes popIn {
          0% { opacity: 0; transform: scale(0.6) rotate(-8deg); }
          60% { transform: scale(1.12) rotate(4deg); }
          100% { opacity: 1; transform: scale(1) rotate(0deg); }
        }
        @keyframes fadeIn {
          0% { opacity: 0; transform: translateY(-6px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes cardIn {
          0% { opacity: 0; transform: translateY(12px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes confettiFall {
          0% { opacity: 0; transform: translateY(-10px) rotate(0deg); }
          20% { opacity: 1; }
          100% { opacity: 0; transform: translateY(50px) rotate(180deg); }
        }
      `}</style>
    </div>
  )
}
