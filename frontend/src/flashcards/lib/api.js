// Talks to the merged FastAPI backend's flashcards routes, mounted at
// /api/v1/flashcards/... Reuses the shared axios instance (src/api/client.js)
// the same way vaakmirror/lib/api.js does, rather than a separate fetch-based
// client — it already has the right baseURL and attaches the kid's auth
// header on every request.

import api from '../../api/client'

const FC = '/flashcards'

export function getRandomWord(language = 'english') {
  return api.get(`${FC}/random-word`, { params: { language } }).then(r => r.data)
}

export function getCharacters() {
  return api.get(`${FC}/characters`).then(r => r.data)
}

export function speakWord(word, character, speed = 1.0) {
  const form = new FormData()
  form.append('text', word)
  form.append('character', character)
  return api.post(`${FC}/speak`, form, { responseType: 'blob' }).then(r => r.data)
}

export function getImageForPhrase(phrase) {
  const form = new FormData()
  form.append('phrase', phrase)
  return api.post(`${FC}/image`, form, { responseType: 'blob' }).then(r => r.data)
}

export function evaluateAttempt({ audio, targetWord, character, language, sessionId, attemptNumber }) {
  const form = new FormData()
  form.append('audio', audio, 'attempt.wav')
  form.append('target_word', targetWord)
  form.append('character', character)
  form.append('language', language || 'english')
  form.append('attempt_number', String(attemptNumber || 1))
  if (sessionId) form.append('session_id', sessionId)
  return api.post(`${FC}/evaluate`, form).then(r => r.data)
}
