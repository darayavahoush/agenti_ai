import axios from 'axios'

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach token automatically
api.interceptors.request.use((config) => {
  config.headers = config.headers || {}
  const token = localStorage.getItem('bq_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  } else {
    delete config.headers.Authorization
  }
  return config
})

// ------------------------------------------------------------------ //
//  Auth                                                                //
// ------------------------------------------------------------------ //

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
  therapistCandidates: () => api.get('/auth/therapist-candidates'),
  kidRegister: (data) => api.post('/auth/kid-register', data),
  kidCandidates: () => api.get('/auth/kid-candidates'),
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
