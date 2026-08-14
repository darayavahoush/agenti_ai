import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { assessmentAPI, getErrorMessage } from '../../api/client'
import { PageLoader } from '../../components/ui'
import Assessment from '../../assessment/Assessment'

// Bootstraps a logged-in kid into the standalone Assessment flow
// (frontend/src/assessment/Assessment.jsx) without its own separate
// name+DOB login screen: POST /assessment/start auto-links or creates the
// Assessment-side Patient row for this kid, then Assessment renders
// straight into its "home" section via authedPatientId/authedPatientName.
// On finish, marks the kid's account assessment_completed and routes to
// the report/paywall screen.
export default function AssessmentGate() {
  const navigate = useNavigate()
  const { markAssessmentComplete } = useAuth()
  const [state, setState] = useState({ status: 'loading' }) // loading | ready | error

  useEffect(() => {
    let cancelled = false
    assessmentAPI.start()
      .then(({ data }) => {
        if (cancelled) return
        if (data.already_completed) {
          navigate('/assessment/report', { replace: true })
          return
        }
        setState({ status: 'ready', data })
      })
      .catch((err) => { if (!cancelled) setState({ status: 'error', message: getErrorMessage(err) }) })
    return () => { cancelled = true }
  }, [navigate])

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
      // Navigate regardless — the summary is a nice-to-have for the report
      // screen's teaser, not a gate; a failed PATCH shouldn't strand the
      // kid mid-assessment with no way forward.
      navigate('/assessment/report', { state: { summary }, replace: true })
    }
  }

  return (
    <Assessment
      authedPatientId={state.data.assessment_patient_id}
      authedPatientName={state.data.first_name}
      onFinish={handleFinish}
    />
  )
}
