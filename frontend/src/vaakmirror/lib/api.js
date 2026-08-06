import axios from "axios"

const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/v1/vaakmirror"

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
})

// Reuses the same patient token BreathQuest's login flow already stores —
// vaakmirror's backend auth (get_current_patient_id) checks the same
// breathquest_patients table, so there's one login for both game suites,
// not a second parallel auth system.
api.interceptors.request.use((config) => {
  config.headers = config.headers || {}
  const token = localStorage.getItem("bq_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  } else {
    delete config.headers.Authorization
  }
  return config
})

// game must be one of the backend's GameName enum values:
// "mirror_mirror" | "tongue_tamer" | "lip_sync_hero"
export async function createGameSession(game) {
  const res = await api.post("/sessions", { game })
  return res.data // SessionOut: { id, patient_id, game, started_at, ended_at }
}

// attempt fields map 1:1 to the backend's AttemptCreate schema.
// outcome must be one of: "passed" | "caught" | "missed"
export async function logAttempt(sessionId, attempt) {
  const res = await api.post(`/sessions/${sessionId}/attempts`, attempt)
  return res.data // AttemptOut
}

export async function endGameSession(sessionId) {
  const res = await api.patch(`/sessions/${sessionId}/end`)
  return res.data // SessionOut with ended_at set
}

// --- Exercises ---
// list_exercise_library has no auth requirement server-side, but the
// interceptor above attaches the token automatically anyway — harmless.
export async function getExerciseLibrary() {
  const res = await api.get("/exercises")
  return res.data // ExerciseTemplateOut[]
}

// Accepts either a therapist or patient token server-side
// (get_current_identity) — enforces the caller owns/is the patient.
export async function getChildExercises(patientId) {
  const res = await api.get(`/patients/${patientId}/exercises`)
  return res.data // ExerciseAssignmentOut[]
}

// Therapist-only server-side (get_current_therapist_id) — a patient token
// will get a 401/403 here, which is correct: only therapists assign.
export async function assignExercise(exerciseId, patientId) {
  const res = await api.post(`/patients/${patientId}/exercises/${exerciseId}/assign`)
  return res.data // ExerciseAssignmentOut
}

// Accepts either identity type, same ownership check as getChildExercises.
export async function updateAssignmentStatus(assignmentId, status) {
  const res = await api.patch(`/exercise-assignments/${assignmentId}`, { status })
  return res.data // ExerciseAssignmentOut
}

// --- Dashboard ---
// Therapist-only server-side (get_current_therapist_id) — matches how it's
// called: a therapist viewing whichever patient is currently active.
export async function getDashboard(patientId) {
  const res = await api.get(`/patients/${patientId}/dashboard`)
  return res.data // DashboardOut
}

export default api
