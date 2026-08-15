// Talks to the merged FastAPI backend's flashcards routes, mounted at
// /api/v1/flashcards/... Reuses the shared axios instance (src/api/client.js)
// the same way vaakmirror/lib/api.js does, rather than a separate fetch-based
// client — it already has the right baseURL and attaches the kid's auth
// header on every request.

import api from '../../api/client'

const FC = '/flashcards'

export function getThemes() {
  return api.get(`${FC}/themes`).then(r => r.data)
}

export function getWordsForTheme(theme) {
  return api.get(`${FC}/words`, { params: { theme } }).then(r => r.data)
}

export function getMastery() {
  return api.get(`${FC}/mastery`).then(r => r.data)
}

// Accepts either the old positional string ('english') or an options
// object ({ language, theme, word }) so every existing call site keeps
// working unchanged.
export function getRandomWord(arg = 'english') {
  const opts = typeof arg === 'string' ? { language: arg } : (arg || {})
  const { language = 'english', theme, word } = opts
  return api.get(`${FC}/random-word`, { params: { language, theme, word } }).then(r => r.data)
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

export function evaluateAttempt({ audio, targetWord, character, language, sessionId, attemptNumber, theme }) {
  const form = new FormData()
  form.append('audio', audio, 'attempt.wav')
  form.append('target_word', targetWord)
  form.append('character', character)
  form.append('language', language || 'english')
  form.append('attempt_number', String(attemptNumber || 1))
  if (sessionId) form.append('session_id', sessionId)
  if (theme) form.append('theme', theme)
  return api.post(`${FC}/evaluate`, form).then(r => r.data)
}
