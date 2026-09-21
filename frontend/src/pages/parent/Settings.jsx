import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, TrendingUp, CreditCard, Eye, EyeOff, Mail, Pencil } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Sidebar, ChildSwitcher, AboutModal, UsernamePicker } from '../../components/ui'
import { parentAPI, getErrorMessage } from '../../api/client'
import toast from 'react-hot-toast'

export default function ParentSettings() {
  const { parent, logout, deleteParentAccount, updateParent } = useAuth()
  const navigate = useNavigate()
  const [editingUsername, setEditingUsername] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [weeklyEmails, setWeeklyEmails] = useState(true)
  const [emailPrefLoading, setEmailPrefLoading] = useState(true)
  const [emailPrefSaving, setEmailPrefSaving] = useState(false)

  useEffect(() => {
    parentAPI.getEmailPreferences()
      .then(({ data }) => setWeeklyEmails(!data.weekly_email_opt_out))
      .catch(() => {}) // non-critical -- toggle just stays at its default if this fails
      .finally(() => setEmailPrefLoading(false))
  }, [])

  const handleToggleWeeklyEmails = async () => {
    const next = !weeklyEmails
    setWeeklyEmails(next) // optimistic -- this is a simple boolean flip, worth not blocking on
    setEmailPrefSaving(true)
    try {
      await parentAPI.updateEmailPreferences(!next)
    } catch (err) {
      setWeeklyEmails(!next) // revert on failure
      toast.error(getErrorMessage(err, "Couldn't save that — try again"))
    } finally {
      setEmailPrefSaving(false)
    }
  }

  return (
    <div className="min-h-dvh bg-ink relative flex">
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
        extraFooter={<><ChildSwitcher /><AboutModal role="parent" /></>}
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
            <div className="flex justify-between items-center">
              <span className="text-paper/40">Username</span>
              {editingUsername ? null : (
                <span className="flex items-center gap-1.5">
                  <span className="text-paper/80">@{parent?.username || 'not set'}</span>
                  <button onClick={() => setEditingUsername(true)} className="text-paper/40 hover:text-paper transition-colors" aria-label="Edit username">
                    <Pencil size={12} />
                  </button>
                </span>
              )}
            </div>
            {editingUsername && (
              <UsernamePicker
                role="parent"
                currentUsername={parent?.username}
                onSaved={(username) => { updateParent({ username }); setEditingUsername(false); toast.success('Username saved!') }}
                onCancel={() => setEditingUsername(false)}
              />
            )}
          </div>
        </div>

        <div className="rounded-2xl p-6 border border-white/10 bg-white/5 mb-6">
          <h2 className="text-paper/80 text-sm font-semibold mb-1 flex items-center gap-2">
            <Mail size={14} className="text-paper/40" /> Weekly emails
          </h2>
          <p className="text-paper/40 text-xs mb-4">
            A short progress update (or a gentle nudge if there's been no practice) once a week.
          </p>
          <button
            onClick={handleToggleWeeklyEmails}
            disabled={emailPrefLoading || emailPrefSaving}
            className={`relative w-11 h-6 rounded-full transition-colors disabled:opacity-50
                       ${weeklyEmails ? 'bg-mint' : 'bg-white/15'}`}
            role="switch"
            aria-checked={weeklyEmails}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform
                         ${weeklyEmails ? 'translate-x-5' : 'translate-x-0'}`}
            />
          </button>
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
              <div className="relative mb-2">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => { setCurrentPassword(e.target.value); setDeleteError('') }}
                  placeholder="Enter your current password to confirm"
                  className="w-full px-4 py-2.5 pr-10 rounded-xl bg-white/5 border border-white/10 text-paper text-sm
                             placeholder:text-paper/30 focus:outline-none focus:border-coral/40"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(s => !s)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-paper/30 hover:text-paper/60 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
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
                      setDeleteError(getErrorMessage(err, 'Could not delete account — check your password and try again.'))
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

        <p className="text-paper/25 text-[11px] text-center mt-6">
          Flashcard icons by{' '}
          <a href="https://openmoji.org" target="_blank" rel="noopener noreferrer"
             className="underline hover:text-paper/40 transition-colors">
            OpenMoji
          </a>{' '}
          — the open-source emoji and icon project (CC BY-SA 4.0)
        </p>
      </div>
    </div>
  )
}
