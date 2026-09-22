import axios from 'axios'
import { updateActiveAccountToken, currentAccountKey, forgetKnownAccount } from './knownAccounts'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
// routes/assessment.py is the one router mounted at plain "/assessment" in
// main.py instead of under /api/v1 (see Assessment.jsx's own API_URL, which
// already targets this same root for /assessment/analyze). Strip a trailing
// /api/v1 off BASE_URL when present so both stay derived from one env var
// instead of drifting independently.
const ROOT_URL = BASE_URL.replace(/\/api\/v1\/?$/, '')

// Deduped silent-refresh: if several requests 401 around the same moment
// (e.g. a burst of parallel calls right as the access token expires), they
// must share ONE in-flight refresh call, not each fire their own --
// /auth/refresh rotates the refresh token on every use (old one revoked),
// so a second concurrent call using the same stored token would 401 and
// force a full logout even though the session is actually still good.
let _refreshPromise = null

// Bumped on every point where the ACTIVE session identity changes under
// bq_token -- login, startSupervisedSession's swap to the patient, its
// restore back to the therapist, switchAccount, and logout (see
// bumpSessionGeneration's call sites in AuthContext.jsx). Comparing the
// exact token string (the older guard below) breaks down for a specific
// race: a background request from session A gets a legitimate 401, kicks
// off _attemptSilentRefresh, session A ends (e.g. startSupervisedSession
// swaps in session B) *while that refresh is still in flight*, and the
// refresh then resolves and writes session A's freshly-rotated token over
// session B's -- a token string comparison done *before* the refresh started
// can't catch a swap that happens *during* it. The generation captured at
// send time and re-checked after every async hop (refresh included) closes
// that gap regardless of whether the tokens involved happen to coincide.
let _sessionGeneration = 0
export function bumpSessionGeneration() {
  _sessionGeneration += 1
}

async function _attemptSilentRefresh() {
  if (_refreshPromise) return _refreshPromise
  const refreshToken = localStorage.getItem('bq_refresh_token')
  if (!refreshToken) return null
  const generationAtCall = _sessionGeneration

  // Plain axios, not the `api` instance below -- avoids recursing back
  // through this file's own interceptors, and /auth/refresh doesn't need
  // (or want) the expired access token attached as an Authorization header.
  _refreshPromise = axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
    .then(({ data }) => {
      // The session moved on (supervised-session swap, restore, switch,
      // logout) while this refresh was in flight -- the tokens it just
      // rotated belong to a session that's no longer active. Applying them
      // now would clobber whatever session actually replaced it, so drop
      // the result on the floor instead of persisting or returning it.
      if (_sessionGeneration !== generationAtCall) return null
      localStorage.setItem('bq_token', data.access_token)
      localStorage.setItem('bq_refresh_token', data.refresh_token)
      // Refresh rotates the refresh token (old one revoked server-side) --
      // without this, the profile switcher's roster would keep holding the
      // now-dead pre-rotation token and fail the next time someone tries
      // to switch back into this account after normal usage has silently
      // refreshed it in the background.
      updateActiveAccountToken(data.refresh_token)
      return data.access_token
    })
    .catch(() => null)
    .finally(() => { _refreshPromise = null })

  return _refreshPromise
}

// A pagehide-safe way to fire a final request when the kid actually closes
// the tab or navigates off-site — regular axios/fetch calls can get
// cancelled mid-flight the instant the page unloads, silently dropping
// session-end and agent-quit events. `keepalive: true` is a browser
// guarantee that the request still gets sent even after the page is gone.
// No response is read (the page may already be gone by the time it would
// arrive) — this is fire-and-forget by design.
export function beaconPost(path, body, method = 'POST') {
  const token = localStorage.getItem('bq_token')
  try {
    fetch(`${BASE_URL}${path}`, {
      method,
      keepalive: true,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    })
  } catch {
    // best-effort — nothing to do if even starting the request throws
  }
}

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach token automatically -- also stamps the session generation this
// request was sent under (see bumpSessionGeneration above), so the response
// interceptor can tell a request apart from a *later* session even in the
// (rare) case the two happen to carry the same token string.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('bq_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  config._sessionGen = _sessionGeneration
  return config
})

// A 401 here means the backend has rejected the token itself (expired,
// invalid, or the patient/therapist/parent record it points to no longer
// exists) — not a per-endpoint permission issue. Before this, that state was
// invisible: AuthContext only checks whether *something* is in localStorage
// to decide isKid/isTherapist/isParent, it never re-validates the token, so
// the UI kept acting "logged in" while every real request quietly failed and
// each caller improvised its own fallback (e.g. Chime's level-unlock check
// silently treating "couldn't reach the backend" the same as "nothing
// passed yet", which looks exactly like a stuck next-level bug rather than
// what it actually is — a dead session). Handle it once, here, instead.
//
// Skip this for the auth endpoints themselves — a wrong PIN/password is a
// legitimate 401 with no session to invalidate, not a dead-session signal.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const isAuthEndpoint = originalRequest?.url?.startsWith('/auth/')

    // A 401 here can arrive long after it was sent -- PatientDetail alone
    // fires a dozen+ background requests on mount, any of which can still
    // be in flight when a therapist clicks Launch Assessment/Live Therapy.
    // startSupervisedSession swaps bq_token/bq_user_type to the patient's
    // mid-flight, so a stale therapist-scoped request that only 401s
    // *after* that swap would otherwise still read the (by then wrong)
    // bq_user_type and hard-redirect the freshly-launched patient session
    // back to /therapist/login -- exactly the "Launch Assessment kicks you
    // to the therapist login/profile switcher" symptom. If the token this
    // request was actually sent with no longer matches the live token, the
    // session has already moved on and this response is irrelevant --
    // drop it rather than acting on it.
    const sentToken = originalRequest?.headers?.Authorization
    const currentToken = localStorage.getItem('bq_token')
    const isStaleGeneration = typeof originalRequest?._sessionGen === 'number'
      && originalRequest._sessionGen !== _sessionGeneration
    const isStaleToken = sentToken && sentToken !== `Bearer ${currentToken}`
    if (isStaleGeneration || isStaleToken) {
      return Promise.reject(error)
    }

    // First 401 on a non-auth request: try one silent refresh-and-retry
    // before treating this as a dead session. _retried guards against a
    // request that 401s AGAIN even after a successful refresh (a real dead
    // session, not just an expired access token) from looping forever.
    if (error.response?.status === 401 && !isAuthEndpoint && !originalRequest._retried) {
      originalRequest._retried = true
      const newAccessToken = await _attemptSilentRefresh()
      if (newAccessToken) {
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return api(originalRequest)
      }
      // Refresh itself failed (no refresh token stored, or it's also
      // expired/revoked) -- fall through to the hard-logout path below.
      //
      // The refresh attempt just awaited is itself an async gap the session
      // could have moved on during (e.g. startSupervisedSession's swap
      // landing while this exact refresh was in flight) -- re-check rather
      // than trusting the pre-await isStaleGeneration result above.
      if (_sessionGeneration !== originalRequest._sessionGen) {
        return Promise.reject(error)
      }
    }

    if (error.response?.status === 401 && !isAuthEndpoint) {
      const userType = localStorage.getItem('bq_user_type')
      const deadKey = currentAccountKey()

      // TEMP DIAGNOSTIC (2026-09-22) -- window.__lastCrash doesn't survive
      // the window.location.href reload two lines below, so the previous
      // capture attempt always came back undefined. localStorage does
      // survive a full navigation, so stash exactly what tripped this
      // branch before clearing anything, and read it back after landing on
      // the login page. Remove once the actual 401 source is confirmed.
      try {
        localStorage.setItem('bq_debug_last_hard_logout', JSON.stringify({
          at: new Date().toISOString(),
          url: originalRequest?.url,
          method: originalRequest?.method,
          sessionGenAtSend: originalRequest?._sessionGen,
          currentSessionGen: _sessionGeneration,
          userTypeAtLogout: userType,
          retried: !!originalRequest?._retried,
          responseDetail: error.response?.data?.detail,
        }))
      } catch { /* best-effort */ }

      localStorage.removeItem('bq_token')
      localStorage.removeItem('bq_refresh_token')
      localStorage.removeItem('bq_user_type')
      localStorage.removeItem('bq_user_data')
      // This account's refresh token is dead (expired or revoked, not just
      // this one access token) -- drop it from the switcher roster too, so
      // it doesn't sit there looking switchable and failing every time.
      if (deadKey) forgetKnownAccount(deadKey)

      const loginPath = userType === 'therapist' ? '/therapist/login'
        : userType === 'parent' ? '/parent/login'
        : '/play' // kid landing — mirrors ProtectedKid's own redirect target

      // Full reload, not a router push: this file has no router context (it's
      // a plain axios instance, not a component), and a hard reload is exactly
      // what's needed anyway to clear any in-memory AuthContext/game state left
      // over from the dead session. The session_expired param lets the landing
      // page explain what happened instead of silently dumping them back at
      // login with no context -- see each login page's handling of it.
      if (window.location.pathname !== loginPath) {
        window.location.href = `${loginPath}?session_expired=1`
      }
    }
    return Promise.reject(error)
  }
)

// ------------------------------------------------------------------ //
//  Auth                                                                //
// ------------------------------------------------------------------ //

export const verifyAPI = {
  request: (data) => api.post('/verify/request', data),
  confirm: (data) => api.post('/verify/confirm', data),
}

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  googleAuthTherapist: (idToken, intent = 'register') => api.post('/auth/google', { id_token: idToken, intent }),
  kidRegister: (data) => api.post('/auth/kid-register', data),
  kidLogin:    (data) => api.post('/auth/kid-login', data),
  parentRegister: (data) => api.post('/auth/parent-register', data),
  parentKidRegister: (data) => api.post('/auth/parent-kid-register', data),
  parentLogin:    (data) => api.post('/auth/parent-login', data),
  parentGoogleLogin:    (idToken) => api.post('/auth/parent-google-login', { id_token: idToken }),
  parentGoogleRegister: (data) => api.post('/auth/parent-google-register', data),
  forgotPlayerCode: (data) => api.post('/auth/forgot-player-code', data),
  forgotPin: (data) => api.post('/auth/forgot-pin', data),
  parentResetPassword: (data) => api.post('/auth/parent-reset-password', data),
  therapistResetPassword: (data) => api.post('/auth/reset-password', data),

  // Multi-child support (2026-09-10) -- see AuthContext.jsx's children
  // state / switchChild for how these get used.
  getChildren:  () => api.get('/auth/parent/children'),
  addChild:     (data) => api.post('/auth/parent/children', data),
  // Avatar-only edit for a child already in the parent's account (#68) --
  // see routers/breathquest/auth.py's update_child.
  updateChild:  (patientId, data) => api.patch(`/auth/parent/children/${patientId}`, data),
  linkChild:    (data) => api.post('/auth/parent/link-child', data),
  switchChild:  (patientId) => api.post('/auth/parent/switch-child', { patient_id: patientId }),
  // Attaches an existing therapist (by email or @username) to the
  // parent's currently active child. See routers/breathquest/auth.py's
  // link_therapist -- the reverse direction of patientsAPI.link below.
  linkTherapist: (therapistCode) => api.post('/auth/parent/link-therapist', { therapist_code: therapistCode }),

  therapistCandidates: () => api.get('/auth/therapist-candidates'),
  kidCandidates:       () => api.get('/auth/kid-candidates'),
  kidPinSetup: (data) => api.post('/auth/kid-pin-setup', data),

  deleteParentAccount: (data)    => api.delete('/auth/parent-account', { data }),
  deleteKidAccount:    (data)    => api.delete('/auth/kid-account', { data }),
  deleteTherapistAccount: (data) => api.delete('/auth/account', { data }),

  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
  logout:  (refreshToken) => api.post('/auth/logout', { refresh_token: refreshToken }),
}

// Kid-authenticated wrapper around the Assessment flow (see
// routers/breathquest/assessment.py) -- lets AssessmentGate.jsx bootstrap
// Assessment.jsx against the logged-in kid's own identity instead of its
// own separate name+DOB gate.
export const assessmentAPI = {
  start:    () => api.post('/assessment/start'),
  complete: (data) => api.post('/assessment/complete', data),
  // Sound Check (Alphabet): the VaakMirror planner agent's plan for these letter results.
  alphabetComplete: (letterResults) => api.post('/assessment/alphabet/complete', { letter_results: letterResults }),
}

// ------------------------------------------------------------------ //
//  Patients                                                            //
// ------------------------------------------------------------------ //

export const patientsAPI = {
  list:   ()           => api.get('/breathquest/patients'),
  get:    (id)         => api.get(`/breathquest/patients/${id}`),
  create: (data)       => api.post('/breathquest/patients', data),
  update: (id, data)   => api.patch(`/breathquest/patients/${id}`, data),
  delete: (id)         => api.delete(`/breathquest/patients/${id}`),
  generateParentInviteCode: (id) => api.post(`/breathquest/patients/${id}/parent-invite-code`),
  // Attaches the calling therapist to an existing kid account by
  // @username or player code -- for a child who self/parent-registered
  // before this therapist was in the picture. See
  // routers/breathquest/patients.py's link_existing_patient -- the
  // reverse direction of authAPI.linkTherapist.
  link: (identifier) => api.post('/breathquest/patients/link', { identifier }),
  // Therapist-launched entry point into Assessment/Live Therapy (see
  // AuthContext.jsx's startSupervisedSession) -- mints a real kid token
  // for this patient without needing their PIN.
  startSession: (id)   => api.post(`/breathquest/patients/${id}/start-session`),
}

// ------------------------------------------------------------------ //
//  Sessions                                                            //
// ------------------------------------------------------------------ //

export const sessionsAPI = {
  start:     (data)              => api.post('/sessions', data),
  logEvents: (id, events)        => api.post(`/sessions/${id}/events`, { events }),
  end:       (id, data)          => api.post(`/sessions/${id}/end`, data),
  get:       (id)                => api.get(`/sessions/${id}`),
}

// ------------------------------------------------------------------ //
//  Dashboard                                                           //
// ------------------------------------------------------------------ //

export const dashboardAPI = {
  summary:     ()           => api.get('/dashboard/summary'),
  progress:    (patientId)  => api.get(`/dashboard/patients/${patientId}/progress`),
  // game: 'breathquest' | 'chime' | 'voicehurdlerace' -- each has its own
  // AgentService-backed router (see backend/app/routers/breathquest/
  // breath_agent.py, chime.py, voicehurdlerace.py agent/status routes).
  agentStatus: (patientId, levelId, policy = 'tabular_q', game = 'breathquest') => {
    if (game === 'assessment') {
      // routes/assessment.py's router is mounted at plain prefix="/assessment"
      // in main.py -- not under /api/v1 like every other game's router --
      // same root Assessment.jsx's own API_URL already targets for
      // /assessment/analyze. `api`'s baseURL bakes in /api/v1, so this one
      // goes through axios directly against the un-prefixed root instead,
      // manually attaching the same bearer token `api`'s interceptor would.
      const token = localStorage.getItem('bq_token')
      return axios.get(`${ROOT_URL}/assessment/agent/status/${patientId}`, {
        params: { level_id: levelId, policy },
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
    }
    const prefix = { breathquest: '/breath', chime: '/chime', voicehurdlerace: '/voicehurdlerace', vaakmirror: '/vaakmirror', flashcards: '/flashcards' }[game]
    return api.get(`${prefix}/agent/status/${patientId}`, { params: { level_id: levelId, policy } })
  },
  // Same un-prefixed-root rationale as agentStatus above. Assessment has no
  // fixed level list (phonemes depend on which words/languages this child
  // has actually been given), so AgentInsight.jsx fetches it per-patient
  // instead of reading a static GAMES[...].levels array.
  assessmentAgentLevels: (patientId) => {
    const token = localStorage.getItem('bq_token')
    return axios.get(`${ROOT_URL}/assessment/agent/levels/${patientId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
  },
  createNote:  (patientId, data) => api.post(`/dashboard/patients/${patientId}/notes`, data),
  listNotes:   (patientId)       => api.get(`/dashboard/patients/${patientId}/notes`),
  updateNote:  (noteId, data)    => api.patch(`/dashboard/notes/${noteId}`, data),
  deleteNote:  (noteId)          => api.delete(`/dashboard/notes/${noteId}`),

  // Assignments ("homework")
  createAssignment: (patientId, data) => api.post(`/dashboard/patients/${patientId}/assignments`, data),
  listAssignments:  (patientId)       => api.get(`/dashboard/patients/${patientId}/assignments`),
  updateAssignment: (assignmentId, data) => api.patch(`/dashboard/assignments/${assignmentId}`, data),
  deleteAssignment: (assignmentId)       => api.delete(`/dashboard/assignments/${assignmentId}`),

  // Goals
  createGoal: (patientId, data) => api.post(`/dashboard/patients/${patientId}/goals`, data),
  listGoals:   (patientId)      => api.get(`/dashboard/patients/${patientId}/goals`),
  updateGoal:  (goalId, data)   => api.patch(`/dashboard/goals/${goalId}`, data),
  deleteGoal:  (goalId)         => api.delete(`/dashboard/goals/${goalId}`),
  goalHistory: (goalId)         => api.get(`/dashboard/goals/${goalId}/history`),
  matchingSessions: (assignmentId) => api.get(`/dashboard/assignments/${assignmentId}/matching-sessions`),

  // Messages (therapist <-> parent log)
  createMessage:    (patientId, data) => api.post(`/dashboard/patients/${patientId}/messages`, data),
  listMessages:     (patientId)       => api.get(`/dashboard/patients/${patientId}/messages`),
  markMessageRead:  (messageId)       => api.post(`/dashboard/messages/${messageId}/read`),

  // Home practice log (manual, parent-reported)
  createHomePractice: (patientId, data) => api.post(`/dashboard/patients/${patientId}/home-practice`, data),
  listHomePractice:   (patientId)       => api.get(`/dashboard/patients/${patientId}/home-practice`),

  // Multi-child alert view
  listAlerts: (inactiveDays) => api.get('/dashboard/alerts', { params: inactiveDays ? { inactive_days: inactiveDays } : {} }),

  // Weekly summary (rule-based, no LLM calls)
  weeklySummary: (patientId, weekOffset) =>
    api.get(`/dashboard/patients/${patientId}/weekly-summary`, { params: weekOffset ? { week_offset: weekOffset } : {} }),

  // ICF-style PDF report export
  getReport: (patientId) => api.get(`/dashboard/patients/${patientId}/report`, { responseType: 'blob' }),

  // Sound-accuracy-over-time (real data only — no vocab/fluency tracking exists in this app)
  getSoundProgress: (patientId, weeks) =>
    api.get(`/dashboard/patients/${patientId}/sound-progress`, { params: weeks ? { weeks } : {} }),

  // Flashcards phoneme-mastery summary (strongest/weakest, full list, recent words)
  getFlashcardsProgress: (patientId) => api.get(`/dashboard/patients/${patientId}/flashcards`),

  // Cross-game phoneme summary — one merged accuracy number per phoneme,
  // pooled across Flashcards + VaakMirror + Chime, plus a category rollup
  // and a weakest-phonemes priority list.
  getPhonemeSummary: (patientId) => api.get(`/dashboard/patients/${patientId}/phoneme-summary`),

  // 50-item home practice ideas library, filterable by condition/goal
  listHomePracticeIdeas: (condition, goal) =>
    api.get('/dashboard/home-practice-ideas', { params: { ...(condition && { condition }), ...(goal && { goal }) } }),
}

// ------------------------------------------------------------------ //
//  Chime (therapist-facing) — chime.py itself is otherwise entirely
//  kid-token-gated; get_patient_events is the one therapist endpoint.
// ------------------------------------------------------------------ //

export const chimeAPI = {
  getPatientEvents: (patientId, levelId) =>
    api.get(`/chime/patients/${patientId}/events`, { params: levelId ? { level_id: levelId } : {} }),
}

// ------------------------------------------------------------------ //
//  VaakMirror (therapist-facing)                                      //
// ------------------------------------------------------------------ //

export const vaakmirrorAPI = {
  getPatientDashboard: (patientId) => api.get(`/vaakmirror/patients/${patientId}/dashboard`),
  getPatientAttempts: (patientId, params) => api.get(`/vaakmirror/patients/${patientId}/attempts`, { params }),
  labelAttempt: (attemptId, label) => api.post(`/vaakmirror/attempts/${attemptId}/label`, { label }),
  getGameSettingsSuggestion: (patientId, game) =>
    api.get(`/vaakmirror/patients/${patientId}/game-settings/${game}/suggestion`),
  updateGameSettings: (patientId, game, payload) =>
    api.patch(`/vaakmirror/patients/${patientId}/game-settings/${game}`, payload),
}

// ------------------------------------------------------------------ //
//  Kid-facing "my progress" — deliberately minimal endpoint, no scores //
// ------------------------------------------------------------------ //

export const meAPI = {
  profile:         () => api.get('/me'),
  progress:        () => api.get('/me/progress'),
  calendar:        () => api.get('/me/calendar'),
  quests:          () => api.get('/me/quests'),
  companion:       () => api.get('/me/companion'),
  equipCompanion:  (itemId) => api.post('/me/companion/equip', { item_id: itemId }),
  goal:            () => api.get('/me/goal'),
  history:         () => api.get('/me/history'),
  breathquestLevelScores: () => api.get('/me/breathquest/level-scores'),
  gamesSummary:    () => api.get('/me/games-summary'),
  dailyGreeting:   () => api.get('/me/greeting'),
  recommendedPractice: () => api.get('/me/recommended-practice'),
  access:          () => api.get('/me/access'),
  latestAssessment: () => api.get('/assessment/me/latest'),
  gamePlan:        () => api.get('/assessment/me/game-plan'),
  updateProfile:   (data) => api.patch('/breathquest/patients/me/profile', data),
  changePin:       (data) => api.patch('/breathquest/patients/me/change-pin', data),
  uploadProfilePhoto: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/breathquest/patients/me/profile/photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// ------------------------------------------------------------------ //
//  Parent-facing                                                      //
// ------------------------------------------------------------------ //

export const billingAPI = {
  getSubscription:       () => api.get('/billing/subscription'),
  getParentSubscription: () => api.get('/billing/parent-subscription'),
  checkout:       () => api.post('/billing/checkout'),
  parentCheckout: () => api.post('/billing/parent-checkout'),
}

export const parentAPI = {
  progress: () => api.get('/parent/progress'),
  guidedActivity: () => api.get('/parent/guided-activity'),
  listMessages: () => api.get('/parent/messages'),
  sendMessage: (body) => api.post('/parent/messages', { body, sender_role: 'parent' }),
  markMessageRead: (messageId) => api.post(`/parent/messages/${messageId}/read`),
  history: (category, item) => api.get(`/parent/history/${category}/${encodeURIComponent(item)}`),
  chimeWeeklyBreakdown: () => api.get('/parent/weekly-breakdown/chime'),
  phonemeSummary: () => api.get('/parent/phoneme-summary'),
  getEmailPreferences: () => api.get('/parent/email-preferences'),
  updateEmailPreferences: (weekly_email_opt_out) => api.put('/parent/email-preferences', { weekly_email_opt_out }),
}

// ------------------------------------------------------------------ //
//  Editable @username (kid / parent / therapist) -- one shared factory
//  server-side (routers/username_routes.py), one shared client-side call
//  set here. Every route is auth'd as the account itself, so there's no
//  "look up someone else's username" call -- just get/check/suggestions/
//  set for whoever is currently logged in.
// ------------------------------------------------------------------ //

function makeUsernameAPI(base) {
  return {
    get:         () => api.get(base),
    check:       (username) => api.get(`${base}/check`, { params: { username } }),
    suggestions: () => api.get(`${base}/suggestions`),
    set:         (username) => api.patch(base, { username }),
  }
}

export const usernameAPI = {
  kid:       makeUsernameAPI('/breathquest/patients/me/username'),
  parent:    makeUsernameAPI('/parent/username'),
  therapist: makeUsernameAPI('/auth/therapist/username'),
}

// FastAPI's `detail` field is a plain string for most HTTPExceptions (e.g.
// "Invalid email or password"), but automatic Pydantic request-validation
// failures (422s — e.g. an email that fails EmailStr's format check) return
// an *array* of {type, loc, msg, input, ctx} objects instead. Every login/
// register form does `setError(err.response?.data?.detail || fallback)` and
// renders `error` directly as JSX text; when detail is that array, React
// tries to render objects as children and the whole page crashes (React
// error #31), not just the form. Normalize once, here, instead of leaving
// every call site to assume detail is always a string.
export function getErrorMessage(err, fallback = 'Something went wrong') {
  // No response at all means the request never reached the server --
  // offline, DNS failure, server down, CORS block, etc. -- as opposed to
  // the server responding with an actual error status. The generic
  // caller-supplied fallback ("please try again") is actively misleading
  // here, since retrying immediately won't help if there's no connection.
  if (!err?.response) {
    return "Can't reach the server — check your connection and try again."
  }
  const detail = err.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map(d => d?.msg).filter(Boolean)
    return messages.length ? messages.join('; ') : fallback
  }
  return fallback
}

export default api
