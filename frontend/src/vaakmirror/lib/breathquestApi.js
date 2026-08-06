// Thin client for BreathQuest's own /api/v1/patients endpoint, used by
// vaakmirror's PatientPicker. Kept separate from vaakmirror/lib/api.js
// (which talks to /api/v1/vaakmirror) since this hits a different router
// entirely. Token is passed explicitly rather than via an interceptor,
// matching how PatientPicker.jsx already calls this (auth?.token).

const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/v1"

async function post(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(data?.detail || `Request failed (${res.status})`)
  }
  return data
}

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`)
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(data?.detail || `Request failed (${res.status})`)
  }
  return data
}

// Returns PatientDetailOut[]: { id, first_name, avatar, age, is_active,
// created_at, diagnosis_notes, total_sessions, total_stars, last_session_at }
export async function listPatients(token) {
  const res = await fetch(`${BASE_URL}/patients`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    throw new Error(`Failed to load patients (${res.status})`)
  }
  return res.json()
}

// --- Auth ---
// Mirrors backend/app/routers/breathquest/auth.py exactly.

// TokenResponse: { access_token, therapist_id, full_name }
export const therapistLogin = (email, password) => post("/auth/login", { email, password })

export const registerTherapist = (data) => post("/auth/register", data)

// string[] of therapist names
export const therapistCandidates = () => get("/auth/therapist-candidates")

// { id, name }[]
export const kidCandidates = () => get("/auth/kid-candidates")

// KidTokenResponse: { access_token, patient_id, first_name, avatar, player_code }
export const kidRegister = (patientId, avatar, pin) =>
  post("/auth/kid-register", { patient_id: patientId, avatar, pin })

// playerCodeOrName matches either player_code or first_name server-side
export const kidLogin = (playerCodeOrName, pin) =>
  post("/auth/kid-login", { player_code: playerCodeOrName, pin })
