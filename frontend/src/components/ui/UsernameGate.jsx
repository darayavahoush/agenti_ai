import { useEffect, useState } from 'react'
import { AtSign, Loader2 } from 'lucide-react'
import AmbientGlow from './AmbientGlow'
import UsernamePicker from './UsernamePicker'
import { useAuth } from '../../context/AuthContext'
import { usernameAPI } from '../../api/client'

const LANDING_GRADIENT = 'linear-gradient(180deg, #12142E 0%, #241F49 38%, #6B4A8A 78%, #9A5F72 100%)'

const ROLE_COPY = {
  kid:       { title: 'Pick your username!', body: "It's how friends and your therapist will see you — you can change it any time in My Account." },
  parent:    { title: 'Choose a username', body: 'A short handle for your account. You can change it later from Settings.' },
  therapist: { title: 'Choose a username', body: 'A short handle for your account. You can change it later from Settings.' },
}

// Wraps a role's protected routes: if the signed-in account has no
// username yet, shows a full-screen picker in front of the real page, same
// render-instead-of-children pattern as SavedProfilesGate. Skipped for a
// therapist-supervised kid session -- that's the THERAPIST'S session
// temporarily wearing the kid's identity to demo/test something, not the
// kid's own first login, and a supervising therapist has no way to answer
// "does the kid have a username preference" on their behalf.
//
// "No username" is decided by the SERVER, not the locally cached account.
// The cached copy goes stale: the device's saved-profile list (see
// AuthContext's knownAccounts / switchAccount) keeps the login response from
// BEFORE the username was picked, so quick-switching back into that profile
// used to bring back an account with no username and ask again on every
// login, even though it was saved. So when the local copy has none, ask the
// server once; only a server "null" shows the picker.
export default function UsernameGate({ role, children }) {
  const { isSupervised, patient, parent, therapist, updatePatient, updateParent, updateTherapist } = useAuth()

  const skip = role === 'kid' && isSupervised
  const account = role === 'kid' ? patient : role === 'parent' ? parent : therapist
  const update = role === 'kid' ? updatePatient : role === 'parent' ? updateParent : updateTherapist
  const accountId = account ? (account.patient_id || account.parent_id || account.therapist_id || 'account') : null
  const needsCheck = !skip && !!account && !account.username

  // Which account the server has already been asked about.
  const [checkedFor, setCheckedFor] = useState(null)

  useEffect(() => {
    if (!needsCheck) return
    let cancelled = false
    usernameAPI[role].get()
      .then(({ data }) => { if (!cancelled && data?.username) update({ username: data.username }) })
      .catch(() => { /* can't verify (offline etc.): fall through to the picker, as before */ })
      .finally(() => { if (!cancelled) setCheckedFor(accountId) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [needsCheck, accountId, role])

  if (skip || !account || account.username) return children

  if (checkedFor !== accountId) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: LANDING_GRADIENT }} role="status" aria-label="Loading">
        <Loader2 size={28} className="animate-spin text-white/60" />
      </div>
    )
  }

  const copy = ROLE_COPY[role]

  return (
    <div
      className="relative min-h-screen flex flex-col items-center justify-center px-4 py-16 gap-6 overflow-hidden"
      style={{ background: LANDING_GRADIENT }}
    >
      <AmbientGlow />
      <div className="relative w-14 h-14 rounded-2xl bg-white/10 border border-white/15 flex items-center justify-center">
        <AtSign size={26} className="text-white/80" />
      </div>
      <div className="relative text-center max-w-sm">
        <h1 className="text-2xl sm:text-3xl font-display font-bold text-white mb-2">{copy.title}</h1>
        <p className="text-sm text-white/50">{copy.body}</p>
      </div>
      <div className="relative w-full max-w-xs">
        <UsernamePicker role={role} onSaved={(username) => update({ username })} />
      </div>
    </div>
  )
}
