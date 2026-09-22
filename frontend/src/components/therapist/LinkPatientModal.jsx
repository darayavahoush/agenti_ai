import { useState } from 'react'
import { patientsAPI, getErrorMessage } from '../../api/client'
import { Button } from '../ui'
import { useEscapeKey } from '../../hooks/useEscapeKey'

// Companion to AddPatientModal: that one creates a brand-new patient;
// this one attaches the logged-in therapist to a kid account that
// already exists -- self-registered before signups went adult-only,
// created by a parent (parent-kid-register / add-child), or previously
// linked to a different therapist. Looked up by @username or player
// code, same dual lookup kid_login supports -- most kids only ever
// hand out their @username, not their player code (that's really a
// parent-facing recovery code), so the field leads with that.
export default function LinkPatientModal({ onClose, onLinked }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEscapeKey(onClose)

  const submit = async (e) => {
    e.preventDefault()
    if (!code.trim()) { setError("Enter the child's username or player code"); return }
    setError(''); setLoading(true)
    try {
      const { data } = await patientsAPI.link(code.trim())
      onLinked(data)
    } catch (err) {
      setError(getErrorMessage(err, "Couldn't link that patient"))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true" aria-label="Link existing patient">
      <div className="bg-brand-card border border-white/10 rounded-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-bold text-white">Link an Existing Patient</h2>
          <button onClick={onClose} className="text-white/65 hover:text-white text-2xl leading-none">×</button>
        </div>
        <p className="text-white/50 text-sm mb-6">
          Already know a family whose child signed up on their own, or with a parent's account?
          Enter their @username (or player code) here to add them to your patient list --
          no need to create a second, duplicate profile.
        </p>

        <form onSubmit={submit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-white/70">Username or Player Code</label>
            <input
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. @sunny.otter or FOX4821"
              className="input tracking-wide"
            />
          </div>

          {error && (
            <div className="bg-brand-coral/10 border border-brand-coral/30 rounded-xl px-4 py-3 text-brand-coral text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 mt-2">
            <Button variant="ghost" className="flex-1" type="button" onClick={onClose}>Cancel</Button>
            <Button className="flex-1" type="submit" disabled={loading}>
              {loading ? 'Linking…' : 'Link Patient'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
