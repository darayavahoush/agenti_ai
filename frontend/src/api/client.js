import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach token automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('bq_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ------------------------------------------------------------------ //
//  Auth                                                                //
// ------------------------------------------------------------------ //

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  kidRegister: (data) => api.post('/auth/kid-register', data),
  kidLogin:    (data) => api.post('/auth/kid-login', data),
}

// ------------------------------------------------------------------ //
//  Patients                                                            //
// ------------------------------------------------------------------ //

export const patientsAPI = {
  list:   ()           => api.get('/patients'),
  get:    (id)         => api.get(`/patients/${id}`),
  create: (data)       => api.post('/patients', data),
  update: (id, data)   => api.patch(`/patients/${id}`, data),
  delete: (id)         => api.delete(`/patients/${id}`),
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
  createNote:  (patientId, data) => api.post(`/dashboard/patients/${patientId}/notes`, data),
  listNotes:   (patientId)       => api.get(`/dashboard/patients/${patientId}/notes`),
  updateNote:  (noteId, data)    => api.patch(`/dashboard/notes/${noteId}`, data),
  deleteNote:  (noteId)          => api.delete(`/dashboard/notes/${noteId}`),
}

export default api

// ------------------------------------------------------------------ //
//  Beacon (fire-and-forget, page-unload-safe request)
// ------------------------------------------------------------------ //

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

// ------------------------------------------------------------------ //
//  Verify
// ------------------------------------------------------------------ //

export const verifyAPI = {
  request: (data) => api.post('/verify/request', data),
  confirm: (data) => api.post('/verify/confirm', data),
  phoneRequest: (data) => api.post('/verify/phone/request', data),
  phoneConfirm: (data) => api.post('/verify/phone/confirm', data),
}

// Kid-authenticated wrapper around the Assessment flow — lets
// AssessmentGate.jsx bootstrap Assessment.jsx against the logged-in kid's
// own identity instead of its own separate name+DOB gate.
export const assessmentAPI = {
  start:    () => api.post('/assessment/start'),
  complete: (data) => api.post('/assessment/complete', data),
}

// ------------------------------------------------------------------ //
//  Chime (therapist-facing)
// ------------------------------------------------------------------ //

export const chimeAPI = {
  getPatientEvents: (patientId, levelId) =>
    api.get(`/chime/patients/${patientId}/events`, { params: levelId ? { level_id: levelId } : {} }),
}

// ------------------------------------------------------------------ //
//  VaakMirror (therapist-facing)
// ------------------------------------------------------------------ //

export const vaakmirrorAPI = {
  getPatientDashboard: (patientId) => api.get(`/vaakmirror/patients/${patientId}/dashboard`),
  getGameSettingsSuggestion: (patientId, game) =>
    api.get(`/vaakmirror/patients/${patientId}/game-settings/${game}/suggestion`),
  updateGameSettings: (patientId, game, payload) =>
    api.patch(`/vaakmirror/patients/${patientId}/game-settings/${game}`, payload),
}

// ------------------------------------------------------------------ //
//  Kid-facing "my progress"
// ------------------------------------------------------------------ //

export const meAPI = {
  progress: () => api.get('/me/progress'),
  access:   () => api.get('/me/access'),
}

// ------------------------------------------------------------------ //
//  Parent-facing
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
}

// FastAPI's `detail` field is a plain string for most HTTPExceptions, but
// automatic Pydantic request-validation failures (422s) return an *array*
// of {type, loc, msg, input, ctx} objects instead. Normalize once, here.
export function getErrorMessage(err, fallback = 'Something went wrong') {
  const detail = err?.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map(d => d?.msg).filter(Boolean)
    return messages.length ? messages.join('; ') : fallback
  }
  return fallback
}
