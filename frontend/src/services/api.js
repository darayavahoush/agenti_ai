const API = "http://127.0.0.1:8000";

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