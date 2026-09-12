import { useState } from 'react'
import { ArrowRight, LogIn, X } from 'lucide-react'
import { Avatar } from './Avatar'
import AmbientGlow from './AmbientGlow'
import { useAuth } from '../../context/AuthContext'
import { ROLE_HOME_PATH } from '../../api/knownAccounts'

// Same vertical gradient as the landing page / Sidebar.jsx, so this reads
// as part of the app's chrome rather than a bolted-on interstitial.
const LANDING_GRADIENT = 'linear-gradient(180deg, #12142E 0%, #241F49 38%, #6B4A8A 78%, #9A5F72 100%)'

// A saved account's userType doesn't literally say "kid" (it's "patient",
// matching the backend's own naming) -- this maps the role prop each page
// passes in to the userType knownAccounts actually stores.
const ROLE_USER_TYPE = { kid: 'patient', therapist: 'therapist', parent: 'parent' }

function displayName(a) {
  return a.userData?.first_name || a.userData?.full_name || a.userData?.email || 'Account'
}

function ProfileTile({ account, busy, onSelect, onForget }) {
  const name = displayName(account)
  const initials = name.slice(0, 2).toUpperCase()
  return (
    <button
      type="button"
      onClick={() => onSelect(account.key)}
      disabled={busy}
      className="group relative flex flex-col items-center gap-3 w-28 disabled:opacity-50
                 transition-transform duration-300 hover:-translate-y-1.5"
    >
      {account.userType === 'patient' ? (
        <div className="rounded-2xl border border-white/15 bg-white/[0.03] group-hover:border-white/40
                         group-hover:shadow-[0_8px_30px_rgba(255,255,255,0.08)] transition-all p-1.5">
          <Avatar avatar={account.userData?.avatar} photoUrl={account.userData?.avatar_photo_url} size="xl" name={name} />
        </div>
      ) : (
        <span className="w-20 h-20 rounded-2xl border border-white/15 bg-white/10 flex items-center justify-center
                          text-2xl font-semibold text-white/90 group-hover:border-white/40 group-hover:bg-white/15
                          transition-all">
          {initials}
        </span>
      )}
      <span className="text-sm text-white/80 font-medium truncate w-full text-center">{name}</span>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onForget(account.key) }}
        className="absolute -top-1.5 -right-1.5 w-6 h-6 rounded-full bg-black/60 border border-white/20
                   text-white/50 hover:text-white hover:bg-black/80 opacity-0 group-hover:opacity-100
                   flex items-center justify-center transition-opacity"
        aria-label={`Remove ${name} from this device`}
        title="Remove from this device"
      >
        <X size={12} />
      </button>
    </button>
  )
}

// Wraps a role's login page: if this device already remembers an account
// of that role (added via a real login at some point -- see
// AuthContext.jsx's knownAccounts/_persistSession), shows a Netflix-style
// "who's continuing" picker in front of the actual login form, so
// returning to a login route doesn't mean re-entering credentials every
// time. Renders the wrapped page as-is when there's nothing saved for
// this role, or once the person picks "Log in as someone else".
//
// Deliberately scoped by role (not "every saved account on this device")
// -- each of these pages IS a single role's login flow, so a parent
// hitting /parent/login should only see saved PARENT profiles here, not
// a therapist or kid profile that happens to share the device; picking
// among those already lives in Sidebar.jsx's device-level switcher, once
// actually logged in.
export default function SavedProfilesGate({ role, children }) {
  const { knownAccounts, switchAccount, forgetAccount, loading } = useAuth()
  const [showForm, setShowForm] = useState(false)
  const [busyKey, setBusyKey] = useState(null)
  const [error, setError] = useState(null)

  const userType = ROLE_USER_TYPE[role]
  const matching = knownAccounts.filter((a) => a.userType === userType)

  // Avoid a flash of "who's continuing" before AuthContext has even
  // finished reading localStorage, and skip straight to the real form
  // once there's nothing saved (first-ever visit) or the person asked to
  // log in as someone else.
  if (loading) return null
  if (showForm || matching.length === 0) return children

  const handleSelect = async (key) => {
    setBusyKey(key)
    setError(null)
    const result = await switchAccount(key)
    if (result.ok) {
      // Full reload rather than a router push -- same reasoning as
      // Sidebar.jsx's ProfileSwitcherModal: this device may have fetched
      // and cached data for a different session in memory, and a reload
      // is the simplest way to guarantee none of it lingers under the
      // newly active one.
      window.location.href = ROLE_HOME_PATH[userType] || '/'
    } else {
      // switchAccount already drops the dead entry from knownAccounts
      // itself on an expired/revoked refresh token -- nothing further to
      // clean up here, just surface why and let them log in fresh.
      setBusyKey(null)
      setError("That session has expired — log in again below.")
      setShowForm(true)
    }
  }

  const handleForget = async (key) => {
    await forgetAccount(key)
  }

  return (
    <div
      className="relative min-h-screen flex flex-col items-center justify-center px-4 py-16 gap-10 overflow-hidden"
      style={{ background: LANDING_GRADIENT }}
    >
      <AmbientGlow />
      <div className="relative text-center">
        <h1 className="text-2xl sm:text-3xl font-display font-bold text-white mb-2">Who's continuing?</h1>
        {error && <p className="text-sm text-amber-300">{error}</p>}
      </div>

      <div className="relative flex flex-wrap justify-center gap-6 max-w-lg">
        {matching.map((a) => (
          <ProfileTile
            key={a.key}
            account={a}
            busy={busyKey === a.key}
            onSelect={handleSelect}
            onForget={handleForget}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={() => setShowForm(true)}
        className="group relative flex items-center gap-2 px-5 py-2.5 rounded-full border border-white/15
                   bg-white/[0.04] text-white/70 hover:text-white hover:border-white/30 hover:bg-white/[0.08]
                   transition-all text-sm font-medium"
      >
        <LogIn size={16} />
        Log in as someone else
        <ArrowRight size={14} className="transition-transform group-hover:translate-x-1" />
      </button>
    </div>
  )
}
