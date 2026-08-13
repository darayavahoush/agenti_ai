# 🗣️ VaakSiddhi

**AI-powered speech therapy for children — making practice feel like play.**

VaakSiddhi is a web app designed to support children with autism in developing speech and pronunciation skills. A child picks a fun robot character, sees a flashcard with an image and hears the word spoken in that character's voice, then speaks it themselves — and gets instant, encouraging feedback.

---

## ✨ How It Works

1. **Choose a character** — BOLT, ZARA, NOVA, BEEP, ECHO, or MIRA, each with a unique voice and personality
2. **Get a word** — entered by a therapist or parent as text, or spoken aloud
3. **See & hear** — a flashcard shows an image of the word while the chosen character says it aloud in an Indian-accented English voice
4. **Practice** — the child repeats the word
5. **Get feedback** — the app evaluates pronunciation at the phoneme level and gives encouraging, character-specific feedback

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | FastAPI (Python) |
| Speech Recognition | faster-whisper |
| Text-to-Speech | Kokoro ONNX (`if_sara`, `im_nicola` — Indian English voices) |
| Phoneme Analysis | g2p-en, epitran |
| Deployment | Vercel (frontend) + Hugging Face Spaces (backend) |

---

## 🚀 Live Demo

🌐 **[vaaksiddhi.vercel.app](https://vaaksiddhi.vercel.app)**  
⚙️ **Backend:** [anabaena-vaaksiddhi.hf.space](https://anabaena-vaaksiddhi.hf.space)

---

## 🏃 Running Locally

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 👾 Characters

| Character | Personality |
|---|---|
| BOLT | Brave space robot |
| ZARA | Friendly alien from planet Zorb |
| NOVA | Calm and wise guide |
| BEEP | Tiny, enthusiastic helper robot |
| ECHO | Ancient computer from a distant galaxy |
| MIRA | Cheerful underwater robot |

---

## 🎯 Purpose

Built as a tool to make speech therapy more engaging for children with autism. Traditional repetition drills can be difficult to sustain — VaakSiddhi wraps the same practice in character-driven interactions that feel fun rather than clinical.

---

## 📄 License

MIT
