import { AtSign } from 'lucide-react'
import AmbientGlow from './AmbientGlow'
import UsernamePicker from './UsernamePicker'
import { useAuth } from '../../context/AuthContext'

const LANDING_GRADIENT = 'linear-gradient(180deg, #12142E 0%, #241F49 38%, #6B4A8A 78%, #9A5F72 100%)'

const ROLE_COPY = {
  kid:       { title: 'Pick your username!', body: "It's how friends and your therapist will see you — you can change it any time in My Account." },
  parent:    { title: 'Choose a username', body: 'A short handle for your account. You can change it later from Settings.' },
  therapist: { title: 'Choose a username', body: 'A short handle for your account. You can change it later from Settings.' },
}

// Wraps a role's protected routes: if the signed-in account has no
// username yet (null until they pick one -- see UsernameOut on the
// backend), shows a full-screen picker in front of the real page, same
// render-instead-of-children pattern as SavedProfilesGate. Skipped for a
// therapist-supervised kid session -- that's the THERAPIST'S session
// temporarily wearing the kid's identity to demo/test something, not the
// kid's own first login, and a supervising therapist has no way to answer
// "does the kid have a username preference" on their behalf.
export default function UsernameGate({ role, children }) {
  const { isSupervised, patient, parent, therapist, updatePatient, updateParent, updateTherapist } = useAuth()

  if (role === 'kid' && isSupervised) return children

  const account = role === 'kid' ? patient : role === 'parent' ? parent : therapist
  if (!account || account.username) return children

  const update = role === 'kid' ? updatePatient : role === 'parent' ? updateParent : updateTherapist
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
