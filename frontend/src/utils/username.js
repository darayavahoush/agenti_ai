// utils/username.js -- client-side mirror of
// backend/app/breathquest_core/username.py's validate_username_format().
// Kept in sync by hand (small, stable rule set) so the picker can give
// instant feedback before firing the debounced /check network call, which
// still has the final say (reserved list, and cross-table taken/available).

export const USERNAME_MIN = 3
export const USERNAME_MAX = 20

const ALLOWED = /^[a-z0-9._]+$/

export function normalizeUsername(raw) {
  return (raw || '').trim().replace(/^@+/, '').toLowerCase()
}

// Returns { normalized, error }. error is null when the format is fine --
// mirrors the backend's (normalized, error) tuple. Does NOT know the
// reserved-word list or whether the name is taken; those only come back
// from usernameAPI.*.check(), since they need the database.
export function validateUsernameFormat(raw) {
  const name = normalizeUsername(raw)

  if (!name) return { normalized: name, error: 'Pick a username to continue.' }
  if (name.length < USERNAME_MIN) {
    return { normalized: name, error: `Too short — use at least ${USERNAME_MIN} characters.` }
  }
  if (name.length > USERNAME_MAX) {
    return { normalized: name, error: `Too long — use ${USERNAME_MAX} characters or fewer.` }
  }
  if (!ALLOWED.test(name)) {
    return { normalized: name, error: 'Only letters, numbers, dots (.) and underscores (_) are allowed — no spaces.' }
  }
  if (!/[a-z]/.test(name)) {
    return { normalized: name, error: 'Add at least one letter.' }
  }
  if (name.startsWith('.') || name.endsWith('.')) {
    return { normalized: name, error: "A username can't start or end with a dot." }
  }
  if (name.includes('..')) {
    return { normalized: name, error: 'No two dots in a row.' }
  }
  return { normalized: name, error: null }
}
