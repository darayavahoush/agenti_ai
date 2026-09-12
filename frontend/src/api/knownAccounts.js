// "Known accounts on this device" -- backs the profile switcher so kids,
// parents, and therapists sharing one tablet/computer can flip between
// whichever profiles have logged in here before without re-entering a
// PIN or password each time, the same way picking a different Netflix
// profile doesn't ask for the account password again.
//
// This is deliberately a SEPARATE localStorage key from the "active
// session" keys (bq_token/bq_refresh_token/bq_user_type/bq_user_data) --
// those still represent whichever one profile is live right now; this is
// the roster of everyone remembered on this device, switchable instantly
// as long as their own refresh token hasn't expired (14-30 days idle,
// see backend REFRESH_TOKEN_EXPIRE_DAYS).
//
// Used from two places that must stay in sync: AuthContext.jsx (adds an
// entry on every real login, drives the switcher UI) and client.js's
// silent-refresh interceptor (keeps the CURRENT entry's refresh token
// current as it rotates on every use, so it doesn't go stale and start
// failing the next time someone tries to switch back into it).

const KEY = 'bq_known_accounts'

// A stable per-account identity for the switcher list, independent of
// whatever access/refresh token happens to be active right now -- so the
// same person logging in again later updates their existing entry rather
// than duplicating it. Different account types use different id fields
// in their user-data blob, hence the fallback chain.
//
// parent_id is checked before id/patient_id specifically because a Parent
// payload has no top-level `id` field -- without this, a parent's key
// would fall through to patient_id, which is the CURRENTLY ACTIVE CHILD,
// not the parent's own identity. That was harmless before multi-child
// support (patient_id never changed for a given parent), but switchChild
// (see AuthContext.jsx) reassigns it, which would otherwise silently
// fragment one parent account into a new roster entry every time they
// switched active child.
export function accountKey(userType, userData) {
  const id = userData?.parent_id ?? userData?.id ?? userData?.patient_id ?? userData?.player_code ?? userData?.email
  return `${userType}:${id}`
}

export function listKnownAccounts() {
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveAll(accounts) {
  localStorage.setItem(KEY, JSON.stringify(accounts))
}

// Adds or updates a remembered account. Returns the new full list so
// callers can set React state from it directly without a second read.
export function upsertKnownAccount(userType, userData, refreshToken) {
  const key = accountKey(userType, userData)
  const accounts = listKnownAccounts().filter((a) => a.key !== key)
  accounts.unshift({ key, userType, userData, refreshToken, lastActiveAt: Date.now() })
  saveAll(accounts)
  return accounts
}

// Keeps just the refresh token current for whichever account is ACTIVE
// right now, without touching its cached display info -- the silent
// -refresh interceptor only ever gets a fresh token pair back, never a
// full user-data blob, so it can't do a full upsert.
export function updateActiveAccountToken(refreshToken) {
  const userType = localStorage.getItem('bq_user_type')
  const userDataRaw = localStorage.getItem('bq_user_data')
  if (!userType || !userDataRaw) return
  try {
    upsertKnownAccount(userType, JSON.parse(userDataRaw), refreshToken)
  } catch {
    // corrupt stored user data -- nothing to key this update against
  }
}

export function forgetKnownAccount(key) {
  saveAll(listKnownAccounts().filter((a) => a.key !== key))
}

export function currentAccountKey() {
  const userType = localStorage.getItem('bq_user_type')
  const userDataRaw = localStorage.getItem('bq_user_data')
  if (!userType || !userDataRaw) return null
  try {
    return accountKey(userType, JSON.parse(userDataRaw))
  } catch {
    return null
  }
}

// Where each account type lands after a successful login OR a quick
// profile-switch -- shared by Sidebar.jsx's ProfileSwitcherModal and
// SavedProfilesGate.jsx so the two switchers can't drift out of sync
// with each other (or with each login form's own post-login navigate()
// target).
export const ROLE_HOME_PATH = { patient: '/play/levels', therapist: '/therapist/dashboard', parent: '/parent/dashboard' }
