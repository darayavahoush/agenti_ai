# Vaaksudhi — Speech Therapy Platform

A speech-therapy platform for children, combining a real LangGraph-based pronunciation assessment with four game-based practice tools (BreathQuest, VoiceHurdleRace, VaakMirror, and Chime/PhonemeQuest), a therapist dashboard, and a parent portal. One FastAPI backend, one React frontend.

## What's in here

**For kids:** a PIN-based login, an assessment flow that scores pronunciation against a word list in 8 Indian languages (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi), and four practice games — BreathQuest, VoiceHurdleRace, VaakMirror, and Chime (a rebuild of the earlier standalone PhonemeQuest mini-games — Bubble Wrap Pop, Drum Island, Rocket Launch — now integrated with shared kid-auth and the adaptive-difficulty agent instead of static HTML pages). Each game has its own adaptive-difficulty logic driven by a small RL agent that raises or lowers difficulty based on recent performance.

**For therapists:** a dashboard across all four games for each patient, session history, assignments/goals/messages, home-practice logging, a home-practice-ideas library, weekly summaries, PDF export, and an AI-generated "today's recommendation" per patient pulled from the assessment/agent data.

**For parents:** a lighter read-only view of their child's cross-game progress, gated behind email + phone verification and COPPA-style parental consent before a kid account can be created.

## Project structure

```
agenti_ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, all router mounts
│   │   ├── routes/assessment.py     # LangGraph-based pronunciation assessment (word list, image, TTS audio, analyze)
│   │   ├── routers/
│   │   │   ├── therapist_auth.py, therapist_patients.py   # canonical therapist identity + patient CRUD
│   │   │   └── breathquest/         # kid auth, per-game routers (breath_agent, voicehurdlerace,
│   │   │                            #   chime, dashboard, patients, sessions, billing, access, verify)
│   │   ├── models/                  # SQLAlchemy models (one Patient/Therapist identity, shared across games)
│   │   ├── breathquest_core/        # JWT auth, rate limiting, parental consent, phone/SMS + email providers
│   │   └── agent/, retraining/      # RL adaptive-difficulty agent (Q-tables) + event logging for retraining
│   ├── alembic/                     # schema migrations (introduced 2026-08-13; earlier tables via create_all())
│   └── data/images, assets/audio    # (unused by the live assessment flow — images and TTS audio are
│                                     #  generated on demand, not served from disk; kept for reference)
├── frontend/
│   └── src/
│       ├── pages/kid/                # login, game picker, level select, gameplay, assessment gate/report, progress
│       ├── pages/therapist/          # login, dashboard, patient detail, agent insight
│       ├── pages/parent/             # auth, dashboard
│       ├── assessment/Assessment.jsx # the LangGraph-backed assessment UI
│       ├── voiceHurdleRace/, vaakmirror/, chime/, game/  # the four practice games
│       └── api/client.js             # shared axios instance (bearer token, one base URL)
└── data/images/                      # legacy seed assets for app/routes/assessment.py's AssessmentWord table
```

One frontend, one backend — this used to be split across separate `breathquest`/`vaakmirror`/`quest-games` app trees and a standalone port-8001 backend; those have been consolidated.

## Prerequisites

- Python 3.10+, Node.js 18+, PostgreSQL, Git
- `pip install uv` (fast Python package installer)

## Setup

### Backend

```bash
cd backend
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

cp .env.example .env   # set DATABASE_URL and provider keys (email/SMS) as needed

# Schema: Alembic-managed as of 2026-08-13
alembic upgrade head

# Seed the assessment word list (47 words, 8-language translations)
python add_images_to_db.py

uvicorn app.main:app --reload   # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Database

```sql
CREATE DATABASE vaaksudhi;
```
Then `alembic upgrade head` from `backend/` as above.

## Troubleshooting

- **`passlib`/`bcrypt` error on registration** (`password cannot be longer than 72 bytes`): a known incompatibility between `passlib` and `bcrypt>=4.1`. Pin with `pip install "bcrypt==4.0.1" --force-reinstall`.
- **Port already in use**: `uvicorn app.main:app --port 8001` for the backend, or edit `vite.config.js` for the frontend.
- **Database connection issues**: confirm PostgreSQL is running and `DATABASE_URL` in `backend/.env` is correct.

## Recent changes

- Consolidated to one frontend, one backend (previously split across `breathquest`/`vaakmirror`/standalone app trees and a port-8001 backend)
- Fixed a therapist-identity table mismatch (`therapists` vs. a retiring `breathquest_therapists` table) that silently broke patient creation
- Added kid-login rate limiting, COPPA parental consent, and phone verification as a second consent factor
- Introduced Alembic for schema migrations (previously unversioned `create_all()`)
- Fixed several live 404s: dashboard summary/session-history endpoints, VoiceHurdleRace's "my sessions," the assessment `/start` bootstrap
- Archived an orphaned, never-mounted second LangGraph pipeline (`routes/speech.py`) in favor of the one actually in use (`routes/assessment.py`)
- Added therapist-launched Assessment/Live Therapy sessions, a "today's recommendation" card driven by the adaptive-difficulty agent, and dashboard visibility for assessment-linked patients with no game history yet
- Removed dead/orphaned routes and pre-merge auth code left over from the consolidation

## Technologies

**Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, LangGraph, PyTorch, Whisper, Vosk, Librosa, Coqui TTS

**Frontend:** React, Vite, TailwindCSS, Recharts
