// Talks to the merged FastAPI backend's Chime routes, mounted at
// /api/v1/chime/... (see breathquest/backend/main.py, routers/chime.py).
//
// Reuses BreathQuest's own axios instance (src/api/client.js), same as
// vaakmirror/lib/api.js — it already attaches the bq_token header, so a
// kid can only ever log events/scores against themself (backend derives
// child identity from the token, not from any id in the request body).

import api from '../../api/client'

const CHIME = '/chime'

export function scoreWord(transcript, targetWord, asrConfidence = 1.0) {
  return api.post(`${CHIME}/village-builder/score-word`, {
    transcript,
    target_word: targetWord,
    asr_confidence: asrConfidence,
  }).then(r => r.data)
}

export function transcribeAudio(audioBlob, filename = 'recording.webm') {
  const form = new FormData()
  form.append('audio', audioBlob, filename)

  // Override the instance's default 'Content-Type: application/json' —
  // multipart uploads need the browser to set the boundary itself, so we
  // explicitly clear it here rather than let axios send JSON headers with
  // a FormData body (which the backend's UploadFile param would reject).
  return api.post(`${CHIME}/village-builder/transcribe`, form, {
    headers: { 'Content-Type': undefined },
  }).then(r => r.data)
}

export function scorePhoneme(levelId, audioBlob, filename = 'recording.webm') {
  const form = new FormData()
  form.append('audio', audioBlob, filename)

  // Same Content-Type override as transcribeAudio above -- multipart upload,
  // let the browser set the boundary itself.
  return api.post(`${CHIME}/phoneme/score/${levelId}`, form, {
    headers: { 'Content-Type': undefined },
  }).then(r => r.data)
}

export function logEvent(event) {
  return api.post(`${CHIME}/events`, event).then(r => r.data)
}

export function getEvents(levelId) {
  const params = levelId ? { level_id: levelId } : {}
  return api.get(`${CHIME}/events`, { params }).then(r => r.data)
}

// Shared across every game (Chime, VaakMirror, etc.) -- unlike the rest
// of this file, this hits /api/v1/events/... directly, not /api/v1/chime/...,
// since feedback keys off the RL training event's own id and isn't
// Chime-specific. See backend/app/routers/event_feedback.py.
export function submitEventFeedback(eventId, feedback) {
  return api.patch(`/events/${eventId}/feedback`, { feedback }).then(r => r.data)
}

export function getDifficulty(levelId) {
  return api.get(`${CHIME}/difficulty/${levelId}`).then(r => r.data)
}

export function getAgentDecision(levelId, policy = 'tabular_q') {
  return api.get(`${CHIME}/agent/decide/${levelId}`, { params: { policy } }).then(r => r.data)
}
