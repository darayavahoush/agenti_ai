// Reads the same localStorage keys BreathQuest's AuthContext.jsx already
// writes on login (bq_token / bq_user_type / bq_user_data) — vaakmirror
// shares that login rather than running a second, parallel auth system.
// See breathquest/context/AuthContext.jsx for the writing side.

function parseJwt(token) {
  try {
    const payload = token.split(".")[1]
    if (!payload) return null
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
    return JSON.parse(decodeURIComponent(escape(json)))
  } catch {
    return null
  }
}

function isJwtValid(token) {
  const payload = parseJwt(token)
  if (!payload || !payload.exp) return false
  return Date.now() / 1000 < payload.exp
}

// Returns { token, kind, ...userData } or null if not logged in / expired.
// kind matches the "therapist" | "patient" values Navbar.jsx and friends
// check against directly. userData is whatever the login response
// contained:
//   therapist -> { access_token, therapist_id, full_name }
//   patient   -> { access_token, patient_id, first_name, avatar, player_code }
export function getAuth() {
  const token = localStorage.getItem("bq_token")
  const kind = localStorage.getItem("bq_user_type")
  const rawUserData = localStorage.getItem("bq_user_data")

  if (!token || !kind || !rawUserData || !isJwtValid(token)) return null

  let userData
  try {
    userData = JSON.parse(rawUserData)
  } catch {
    return null
  }

  // Raw fields (therapist_id/full_name or patient_id/first_name/avatar)
  // are kept as-is for cross-app compatibility with BreathQuest's own
  // AuthContext.jsx, plus a normalized id/name on top so VaakMirror's own
  // components don't need to branch on kind just to show a name.
  const normalized =
    kind === "therapist"
      ? { id: userData.therapist_id, name: userData.full_name }
      : { id: userData.patient_id, name: userData.first_name }

  return { token, kind, ...userData, ...normalized }
}

export function isTherapist() {
  return getAuth()?.kind === "therapist"
}

export function isPatient() {
  return getAuth()?.kind === "patient"
}

// Writes auth in the SAME shape BreathQuest's own AuthContext.jsx uses,
// under the same bq_* keys — VaakMirror's Login.jsx and BreathQuest's
// login both feed the same shared session, so someone who logs in through
// one and later lands on a page belonging to the other still works
// correctly (e.g. the therapist dashboard reading therapist.full_name).
// Accepts the convenience shape Login.jsx already builds:
//   { kind, token, id, name, avatar?, player_code? }
export function setAuth({ kind, token, id, name, avatar, player_code }) {
  const userData =
    kind === "therapist"
      ? { access_token: token, therapist_id: id, full_name: name }
      : { access_token: token, patient_id: id, first_name: name, avatar, player_code }

  localStorage.setItem("bq_token", token)
  localStorage.setItem("bq_user_type", kind)
  localStorage.setItem("bq_user_data", JSON.stringify(userData))
}

// Full logout — clears BreathQuest's own auth keys (shared with vaakmirror)
// plus vaakmirror's active-patient selection, since that selection belongs
// to whoever was just logged in and shouldn't leak into the next session.
export function clearAuth() {
  localStorage.removeItem("bq_token")
  localStorage.removeItem("bq_user_type")
  localStorage.removeItem("bq_user_data")
  clearActivePatientId()
}

// --- Active patient (vaakmirror-only concept) ---
// A therapist can have many patients; this tracks which one they're
// currently viewing across vaakmirror's dashboard/exercises pages. Kept in
// its own key, separate from bq_* auth keys, since it's not part of login
// state and shouldn't be cleared/touched by BreathQuest's own auth logic.
const ACTIVE_PATIENT_KEY = "vm_active_patient_id"

export function getActivePatientId() {
  const auth = getAuth()
  // A logged-in patient (kid) only ever has one patient to view: themself.
  if (auth?.kind === "patient") return auth.patient_id
  return localStorage.getItem(ACTIVE_PATIENT_KEY)
}

export function setActivePatientId(patientId) {
  localStorage.setItem(ACTIVE_PATIENT_KEY, patientId)
}

export function clearActivePatientId() {
  localStorage.removeItem(ACTIVE_PATIENT_KEY)
}
