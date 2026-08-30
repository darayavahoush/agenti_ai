import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, TrendingUp, CreditCard } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Sidebar } from '../../components/ui'

export default function ParentSettings() {
  const { parent, logout, deleteParentAccount } = useAuth()
  const navigate = useNavigate()
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [deleteError, setDeleteError] = useState('')

  return (
    <div className="min-h-screen bg-ink relative flex">
      <div className="absolute top-0 left-0 w-full h-80 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-24 w-[28rem] h-[28rem] rounded-full bg-coral/[0.08] blur-[100px]" />
        <div className="absolute -top-40 right-0 w-[26rem] h-[26rem] rounded-full bg-mint/[0.06] blur-[100px]" />
      </div>

      <Sidebar
        role="parent"
        items={[
          { label: 'Progress', icon: TrendingUp, to: '/parent/dashboard' },
        ]}
        name={parent?.child_first_name ? `${parent.child_first_name}'s Progress` : undefined}
        onLogout={logout}
      />

      <div className="relative flex-1 min-w-0 max-w-2xl mx-auto px-6 py-10">
        <h1 className="font-vm-display text-2xl font-bold text-paper mb-8">Account settings</h1>

        <div className="rounded-2xl p-6 border border-white/10 bg-white/5 mb-6">
          <h2 className="text-paper/80 text-sm font-semibold mb-4">Contact info</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-paper/40">Email</span>
              <span className="text-paper/80">{parent?.email || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-paper/40">Phone</span>
              <span className="text-paper/80">{parent?.phone || '—'}</span>
            </div>
          </div>
        </div>

        <div className="rounded-2xl p-6 border border-white/10 bg-white/5">
          <h2 className="text-paper/80 text-sm font-semibold mb-1">Danger zone</h2>
          <p className="text-paper/40 text-xs mb-4">
            This can't be undone.
          </p>

          {!confirmingDelete ? (
            <button onClick={() => setConfirmingDelete(true)}
                    className="text-paper/40 hover:text-coral-light text-sm flex items-center gap-1.5 transition-colors">
              <Trash2 className="w-3.5 h-3.5" /> Delete my account
            </button>
          ) : (
            <div>
              <p className="text-paper/60 text-sm mb-3">
                This deletes your account and your child's account — all progress, all history. This can't be undone.
              </p>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => { setCurrentPassword(e.target.value); setDeleteError('') }}
                placeholder="Enter your current password to confirm"
                className="w-full mb-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-paper text-sm
                           placeholder:text-paper/30 focus:outline-none focus:border-coral/40"
              />
              {deleteError && <p className="text-coral-light text-xs mb-3">{deleteError}</p>}
              <div className="flex items-center gap-3">
                <button onClick={() => { setConfirmingDelete(false); setCurrentPassword(''); setDeleteError('') }}
                        className="text-paper/40 hover:text-paper/70 text-sm px-4 py-2 transition-colors">
                  Never mind
                </button>
                <button
                  disabled={deleting || !currentPassword}
                  onClick={async () => {
                    setDeleting(true)
                    setDeleteError('')
                    try {
                      await deleteParentAccount(currentPassword)
                      navigate('/')
                    } catch (err) {
                      setDeleteError(err?.response?.data?.detail || 'Could not delete account — check your password and try again.')
                      setDeleting(false)
                    }
                  }}
                  className="text-coral-light hover:text-paper text-sm font-semibold px-4 py-2 rounded-xl
                             bg-coral/15 hover:bg-coral border border-coral/30 transition-colors disabled:opacity-50">
                  {deleting ? 'Deleting…' : 'Yes, delete everything'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
