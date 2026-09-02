import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, LayoutDashboard, CreditCard, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Sidebar, AmbientGlow } from '../../components/ui'
import { getErrorMessage } from '../../api/client'

export default function TherapistSettings() {
  const { therapist, logout, deleteTherapistAccount } = useAuth()
  const navigate = useNavigate()
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  return (
    <div className="min-h-screen relative flex"
         style={{ background: 'radial-gradient(ellipse 1400px 800px at 15% -10%, #1D9E75 0%, #16332D 35%, #12122A 70%)' }}>
      <AmbientGlow />

      <Sidebar
        role="therapist"
        items={[
          { label: 'Dashboard', icon: LayoutDashboard, to: '/therapist/dashboard' },
        ]}
        name={therapist?.full_name}
        subtitle={therapist?.clinic_name}
        onLogout={logout}
      />

      <div className="relative flex-1 min-w-0 max-w-2xl mx-auto px-6 py-10">
        <h1 className="font-vm-display text-2xl font-bold text-white mb-1">Account settings</h1>
        <p className="text-white/50 text-sm mb-10">{therapist?.email}</p>

        <div className="rounded-2xl p-6 border border-white/10 bg-white/5">
          <h2 className="text-white/80 text-sm font-semibold mb-1">Danger zone</h2>
          <p className="text-white/40 text-xs mb-4">
            This can't be undone.
          </p>

          {!confirmingDelete ? (
            <button onClick={() => setConfirmingDelete(true)}
                    className="text-white/40 hover:text-brand-coral text-sm flex items-center gap-1.5 transition-colors">
              <Trash2 className="w-3.5 h-3.5" /> Delete my account
            </button>
          ) : (
            <div>
              <p className="text-white/60 text-sm mb-3">
                This deletes your login and your notes on patients. Patients themselves, and their game
                progress, are kept — they'll just no longer be assigned to you. Are you sure?
              </p>
              <div className="relative mb-2">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => { setCurrentPassword(e.target.value); setDeleteError('') }}
                  placeholder="Enter your current password to confirm (skip if you sign in with Google)"
                  className="w-full px-4 py-2.5 pr-10 rounded-xl bg-white/5 border border-white/10 text-white text-sm
                             placeholder:text-white/30 focus:outline-none focus:border-brand-coral/40"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(s => !s)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {deleteError && <p className="text-brand-coral text-xs mb-3">{deleteError}</p>}
              <div className="flex items-center gap-3">
                <button onClick={() => { setConfirmingDelete(false); setCurrentPassword(''); setDeleteError('') }}
                        className="text-white/40 hover:text-white/70 text-sm px-4 py-2 transition-colors">
                  Never mind
                </button>
                <button
                  disabled={deleting}
                  onClick={async () => {
                    setDeleting(true)
                    setDeleteError('')
                    try {
                      await deleteTherapistAccount(currentPassword)
                      navigate('/therapist/login')
                    } catch (err) {
                      setDeleteError(getErrorMessage(err, 'Could not delete account — check your password and try again.'))
                      setDeleting(false)
                    }
                  }}
                  className="text-brand-coral hover:text-white text-sm font-semibold px-4 py-2 rounded-xl
                             bg-brand-coral/10 hover:bg-brand-coral border border-brand-coral/30 transition-colors disabled:opacity-50">
                  {deleting ? 'Deleting…' : 'Yes, delete it'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
