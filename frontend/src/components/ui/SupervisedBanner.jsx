import { useNavigate } from 'react-router-dom'
import { Eye, LogOut } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

// Shown across /assessment* and /play/* while a therapist is running a
// session on a chosen patient's behalf (see AuthContext.jsx's
// startSupervisedSession/endSupervisedSession) -- otherwise there is no
// visual difference between a therapist-launched session and the kid
// having actually logged in themselves, which would be confusing for
// whoever's at the keyboard and makes it easy to forget you're mid-
// session as someone else's account. Mounted once in App.jsx, above the
// route tree, so it survives navigation between games/assessment/report
// without remounting.
export default function SupervisedBanner() {
  const { isSupervised, patient, supervisorName, endSupervisedSession } = useAuth()
  const navigate = useNavigate()

  if (!isSupervised) return null

  const handleExit = () => {
    const backToPatientId = patient?.patient_id
    endSupervisedSession()
    navigate(backToPatientId ? `/therapist/patients/${backToPatientId}` : '/therapist/dashboard', { replace: true })
  }

  return (
    <div className="sticky top-0 z-50 flex items-center justify-center gap-3 px-4 py-2
                     bg-amber-500/95 text-[#3a2a00] text-sm font-semibold backdrop-blur-sm
                     shadow-[0_2px_12px_-4px_rgba(0,0,0,0.4)]">
      <Eye size={15} className="shrink-0" />
      <span>
        Viewing as {patient?.first_name || 'this patient'}
        {supervisorName ? ` — supervised by ${supervisorName}` : ''}
      </span>
      <button
        onClick={handleExit}
        className="flex items-center gap-1 ml-1 px-2.5 py-0.5 rounded-lg bg-[#3a2a00]/10
                   hover:bg-[#3a2a00]/20 transition-colors"
      >
        <LogOut size={13} />
        Exit session
      </button>
    </div>
  )
}
