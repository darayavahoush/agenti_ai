const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function teachWord(word) {
  const response = await fetch(`${API}/image/teach`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      word,
    }),
  });

  return response.json();
}

export async function getPatients() {
  const response = await fetch(`${API}/patients/`);
  return response.json();
}

export async function getPatientSummary() {
  const response = await fetch(`${API}/patients/summary`);
  return response.json();
}

export async function getDashboardStats() {
  const response = await fetch(`${API}/patients/stats`);
  return response.json();
}

export async function getProgress() {
  const response = await fetch(`${API}/patients/progress`);
  return response.json();
}

export async function createPatient(data) {
  const response = await fetch(`${API}/patients/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return response.json();
}

export async function analyzeSpeech(formData) {
  const response = await fetch(`${API}/speech/therapy`, {
    method: "POST",
    body: formData,
  });

  return response.json();
}

export async function generateVoice(therapistId, text, language = "en-IN") {
  const response = await fetch(`${API}/api/audio/words/${encodeURIComponent(text)}?language=${encodeURIComponent(language)}`);
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.detail || "Speech generation failed."); }
  return response.json();
}
