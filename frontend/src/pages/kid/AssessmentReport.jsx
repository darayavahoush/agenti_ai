import { useLocation, useNavigate } from 'react-router-dom'
import { PartyPopper, Sparkles, Lock } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Button, Card } from '../../components/ui'

// Shown right after a kid finishes their first assessment
// (pages/kid/AssessmentGate.jsx's onFinish). This is a soft nudge, not an
// enforcement gate -- nothing here blocks the "Keep exploring" link below
// from reaching real games. Real enforcement (checking a parent/
// therapist's subscription status before letting a kid into gameplay
// routes) is a separate, deliberately scoped-out follow-up.
export default function AssessmentReport() {
  const navigate = useNavigate()
  const { patient } = useAuth()
  const location = useLocation()
  const summary = location.state?.summary || {}
  const wordsAttempted = summary.wordsAttempted ?? 0
  const severity = summary.severityClassification

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
            <div className="flex justify-between">
              <span>Words attempted</span>
              <span className="text-white font-medium">{wordsAttempted}</span>
            </div>
            <div className="flex justify-between">
              <span>Early read</span>
              <span className="text-white font-medium">{severity || 'Looking good so far'}</span>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-white/10 flex items-start gap-2 text-white/40 text-xs">
            <Lock className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            <span>
              The full report -- error patterns, targeted quests, and progress tracking --
              unlocks with a parent or therapist plan.
            </span>
          </div>
        </Card>

        <Button
          variant="primary"
          size="lg"
          className="w-full mb-3"
          onClick={() => navigate('/parent/login')}
        >
          Ask a grown-up to start a free trial
        </Button>
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
