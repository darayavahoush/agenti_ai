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

## Database structure

23 tables across two "eras" of the codebase — a legacy `breathquest_*`-prefixed set (BreathQuest's original standalone app) and a newer unprefixed set (Assessment/therapist-portal, added during consolidation). Both eras share identity tables where it made sense (one `Patient`, one canonical `Therapist`) rather than duplicating them per-game.

**Schema is Alembic-managed** (`backend/alembic/`) as of 2026-08-13 — `alembic upgrade head` is required to bootstrap a fresh database; `Base.metadata.create_all()` alone will not, by design (see the comment block above `_ensure_patient_therapist_link_column()` in `app/main.py`).

### Identity (shared across every game)

| Table | Purpose |
|---|---|
| **`therapists`** | The canonical, going-forward therapist identity (`app/models/therapist.py`). `hashed_password` is nullable (Google-only accounts have none); `google_sub` links a Google identity. |
| **`patients`** | The canonical patient/child identity (`app/models/patient.py`), optionally linked to a registering therapist via `registered_therapist_id`. |
| **`breathquest_patients`** | BreathQuest's own patient row (`app/models/breathquest_models.py`) — the row every game actually foreign-keys against for gameplay data. Links back to the canonical `patients` row via `assessment_patient_id`, and to a `therapists` row via `therapist_id`. In effect: `patients`/`therapists` are the identity of record; `breathquest_patients` is where the games' data actually hangs. |
| **`breathquest_parents`** | Parent accounts (`Parent`), one-to-one with `breathquest_patients`. `hashed_password` nullable for the same Google-only reason as `therapists`. |

> **`breathquest_therapists`** also exists as a defined table (`Therapist` class inside `breathquest_models.py`) but is dead: nothing queries or writes it. It's still imported in `chime.py`/`voicehurdlerace.py`, but only as a (now-inaccurate) type hint on `Depends(get_current_therapist)` — the dependency itself resolves against the real `therapists` table. Safe to remove the import; the table itself can be dropped in a future migration once confirmed empty. See `app/models/therapist.py`'s own docstring, which already flags this as "retiring."

### Auth & consent

| Table | Purpose |
|---|---|
| **`breathquest_refresh_tokens`** | Revocable long-lived credentials (SHA-256-hashed, never raw) for therapist/parent/kid sessions — `owner_kind` + `owner_id` instead of three nullable FK columns, since a token belongs to exactly one of three different tables. |
| **`breathquest_kid_login_throttle`** | Brute-force tracking for kid PIN login, keyed by the lowercased identifier string attempted (name/player code), not by patient — an attempt against a nonexistent identifier still counts. |
| **`breathquest_email_verifications`**, **`breathquest_phone_verifications`** | The two consent factors backing COPPA-style verifiable parental consent on self-serve kid signup. |

### Gameplay & progress

| Table | Purpose |
|---|---|
| **`breathquest_game_sessions`** → **`breathquest_session_events`** | One row per BreathQuest play session, with granular per-event child rows (cascade-deletes with the session). |
| **`breathquest_voicehurdlerace_sessions`** | VoiceHurdleRace's own session table, FK'd to `breathquest_patients`. |
| **`vaakmirror_sessions`** → **`attempts`** | VaakMirror's session/attempt pair, same one-to-many pattern as BreathQuest's. |
| **`flashcard_attempts`**, **`flashcard_phoneme_mastery`** | Chime/PhonemeQuest's per-attempt log and rolling per-phoneme mastery, both FK'd to `breathquest_patients`. |
| **`sessions`** | A separate, older session table (`app/models/session.py`) FK'd to the canonical `patients` table rather than `breathquest_patients` — predates the BreathQuest consolidation; check before assuming it's the same thing as `breathquest_game_sessions`. |

### Therapist-facing tools

| Table | Purpose |
|---|---|
| **`breathquest_therapist_notes`** | Freeform notes per patient, optionally tagged to a specific `breathquest_game_sessions` row. |
| **`breathquest_assignments`**, **`breathquest_goals`**, **`breathquest_messages`**, **`breathquest_home_practice_logs`** | Assignment/goal tracking, therapist↔parent messaging, and home-practice logging — all FK'd to `breathquest_patients`, all `assigned_by`/`created_by` FK'd to `therapists`. |
| **`exercise_templates`** → **`exercise_assignments`** | VaakMirror's reusable exercise library and per-patient assignment of those templates. |

### Billing, assessment, and RL retraining

| Table | Purpose |
|---|---|
| **`breathquest_subscriptions`** | One row per paying parent or therapist (`owner_parent_id` XOR `owner_therapist_id`, each nullable+unique). See `billing.py`'s `PAYMENTS_LIVE` flag and the free-grant bypass note there — no real payment provider is wired in yet. |
| **`assessment_words`** | The seeded 47-word, 8-language pronunciation assessment word list (`add_images_to_db.py` seeds this). |
| **`breathquest_rl_training_events`** | Per-attempt events logged for the adaptive-difficulty RL agent's retraining pipeline, FK'd to `breathquest_patients`. |
| **`breathquest_retrain_checkpoints`** | Saved checkpoints from that retraining process. |

### A note on the two Patient tables

If you're new to this codebase, the `patients` vs. `breathquest_patients` split is the one thing worth understanding before writing a new query: `patients` is the identity a therapist creates/manages from the dashboard; `breathquest_patients` is what every game's session/attempt/mastery table actually foreign-keys against, linked back via `assessment_patient_id`. A patient can in principle exist in one without the other (a dashboard-only patient with no game history yet, or vice versa) — the dashboard's "assessment-linked patients with no game history" view (mentioned under Recent changes below) exists specifically to surface that mismatch.

<details>
<summary><strong>Full column-level schema</strong> (generated from live ORM metadata -- expand for exact types, nullability, FKs)</summary>

**Identity**

`therapists`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `email` | VARCHAR | no | unique |
| `hashed_password` | VARCHAR | yes | — |
| `full_name` | VARCHAR | no | — |
| `clinic_name` | VARCHAR | yes | — |
| `is_active` | BOOLEAN | yes | — |
| `created_at` | TIMESTAMP | yes | — |
| `last_login` | TIMESTAMP | yes | — |
| `phone` | VARCHAR | yes | — |
| `google_sub` | VARCHAR | yes | unique |

`breathquest_therapists`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `email` | VARCHAR(255) | no | indexed |
| `hashed_password` | VARCHAR(255) | no | — |
| `full_name` | VARCHAR(255) | no | — |
| `clinic_name` | VARCHAR(255) | yes | — |
| `is_active` | BOOLEAN | no | — |
| `created_at` | DATETIME | no | — |
| `last_login` | DATETIME | yes | — |

`patients`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `name` | VARCHAR | no | — |
| `age` | INTEGER | yes | — |
| `date_of_birth` | VARCHAR | yes | — |
| `language` | VARCHAR | yes | — |
| `gender` | VARCHAR | yes | — |
| `diagnosis` | VARCHAR | yes | — |
| `therapist_name` | VARCHAR | yes | — |
| `registered_therapist_id` | UUID | yes | FK → `therapists.id`, indexed |
| `parent_name` | VARCHAR | yes | — |
| `parent_contact` | VARCHAR | yes | — |
| `email` | VARCHAR | yes | — |
| `is_active` | BOOLEAN | yes | — |
| `created_at` | TIMESTAMP | yes | — |

`breathquest_patients`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `therapist_id` | UUID | yes | FK → `therapists.id`, indexed |
| `first_name` | VARCHAR(100) | no | — |
| `avatar` | VARCHAR(50) | no | — |
| `avatar_photo_url` | VARCHAR(255) | yes | — |
| `pin_hash` | VARCHAR(64) | no | — |
| `player_code` | VARCHAR(10) | no | unique |
| `age` | INTEGER | yes | — |
| `diagnosis_notes` | TEXT | yes | — |
| `is_active` | BOOLEAN | no | — |
| `assessment_patient_id` | UUID | yes | FK → `patients.id`, indexed |
| `assessment_completed` | BOOLEAN | no | — |
| `assessment_summary` | JSON | yes | — |
| `parent_email` | VARCHAR(255) | yes | — |
| `parent_consent_verified_at` | DATETIME | yes | — |
| `parent_phone` | VARCHAR(32) | yes | — |
| `parent_phone_consent_verified_at` | DATETIME | yes | — |
| `created_at` | DATETIME | no | — |

`breathquest_parents`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, unique |
| `email` | VARCHAR(255) | no | unique |
| `hashed_password` | VARCHAR(255) | yes | — |
| `full_name` | VARCHAR(255) | yes | — |
| `phone` | VARCHAR(50) | yes | — |
| `google_sub` | VARCHAR(255) | yes | unique |
| `is_active` | BOOLEAN | no | — |
| `created_at` | DATETIME | no | — |
| `last_login` | DATETIME | yes | — |

**Auth & consent**

`breathquest_refresh_tokens`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `token_hash` | VARCHAR(64) | no | indexed |
| `owner_kind` | VARCHAR(16) | no | — |
| `owner_id` | UUID | no | indexed |
| `created_at` | DATETIME | no | — |
| `expires_at` | DATETIME | no | — |
| `revoked_at` | DATETIME | yes | — |

`breathquest_kid_login_throttle`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `identifier` | VARCHAR(255) | no | unique |
| `failed_attempts` | INTEGER | no | — |
| `first_failed_at` | DATETIME | yes | — |
| `last_failed_at` | DATETIME | yes | — |
| `locked_until` | DATETIME | yes | — |

`breathquest_email_verifications`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `email` | VARCHAR(255) | no | indexed |
| `otp_code_hash` | VARCHAR(64) | no | — |
| `expires_at` | DATETIME | no | — |
| `attempts` | INTEGER | no | — |
| `verified` | BOOLEAN | no | — |
| `verified_at` | DATETIME | yes | — |
| `created_at` | DATETIME | no | — |

`breathquest_phone_verifications`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `phone` | VARCHAR(32) | no | indexed |
| `otp_code_hash` | VARCHAR(64) | no | — |
| `expires_at` | DATETIME | no | — |
| `attempts` | INTEGER | no | — |
| `verified` | BOOLEAN | no | — |
| `verified_at` | DATETIME | yes | — |
| `created_at` | DATETIME | no | — |

**Gameplay & progress**

`breathquest_game_sessions`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `level_id` | VARCHAR(11) | no | — |
| `started_at` | DATETIME | no | — |
| `ended_at` | DATETIME | yes | — |
| `duration_seconds` | FLOAT | yes | — |
| `status` | VARCHAR(11) | no | — |
| `stars_earned` | INTEGER | yes | — |
| `completed` | BOOLEAN | no | — |
| `completion_message` | VARCHAR(255) | yes | — |
| `avg_breath_strength` | FLOAT | yes | — |
| `max_breath_strength` | FLOAT | yes | — |
| `breath_consistency` | FLOAT | yes | — |
| `total_puffs` | INTEGER | yes | — |
| `lives_lost` | INTEGER | yes | — |

`breathquest_session_events`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `session_id` | UUID | no | FK → `breathquest_game_sessions.id`, indexed |
| `timestamp` | DATETIME | no | — |
| `event_type` | VARCHAR(50) | no | — |
| `breath_value` | FLOAT | yes | — |
| `event_data` | JSON | yes | — |

`breathquest_voicehurdlerace_sessions`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `level_id` | INTEGER | no | — |
| `level_name` | VARCHAR(100) | no | — |
| `score` | INTEGER | no | — |
| `time_remaining` | FLOAT | no | — |
| `pitch_accuracy` | FLOAT | no | — |
| `loudness_accuracy` | FLOAT | no | — |
| `stars` | INTEGER | no | — |
| `created_at` | DATETIME | no | — |

`vaakmirror_sessions`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `patient_id` | VARCHAR | no | indexed |
| `game` | VARCHAR(13) | no | — |
| `started_at` | DATETIME | yes | — |
| `ended_at` | DATETIME | yes | — |

`attempts`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `session_id` | INTEGER | no | FK → `vaakmirror_sessions.id` |
| `sound_id` | VARCHAR(16) | yes | — |
| `place` | VARCHAR(32) | yes | — |
| `manner` | VARCHAR(32) | yes | — |
| `voicing` | VARCHAR(16) | yes | — |
| `outcome` | VARCHAR(6) | no | — |
| `score` | FLOAT | yes | — |
| `created_at` | DATETIME | yes | — |

`flashcard_attempts`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `session_id` | VARCHAR(64) | no | indexed |
| `theme_id` | VARCHAR(50) | yes | indexed |
| `target_word` | VARCHAR(100) | no | indexed |
| `character` | VARCHAR(50) | yes | — |
| `language` | VARCHAR(20) | no | — |
| `transcript` | VARCHAR(255) | yes | — |
| `phoneme_matches` | JSON | no | — |
| `accuracy` | FLOAT | no | — |
| `composite_score` | FLOAT | no | — |
| `attempt_number` | INTEGER | no | — |
| `repeat_needed` | BOOLEAN | no | — |
| `created_at` | DATETIME | no | indexed |

`flashcard_phoneme_mastery`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `phoneme` | VARCHAR(10) | no | indexed |
| `attempts_count` | INTEGER | no | — |
| `correct_count` | INTEGER | no | — |
| `accuracy` | FLOAT | no | — |
| `last_word` | VARCHAR(100) | yes | — |
| `first_practiced_at` | DATETIME | no | — |
| `last_practiced_at` | DATETIME | no | — |

`sessions`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | yes | FK → `patients.id` |
| `f0_mean` | FLOAT | yes | — |
| `mpt` | FLOAT | yes | — |
| `jitter` | FLOAT | yes | — |
| `shimmer` | FLOAT | yes | — |
| `hnr` | FLOAT | yes | — |
| `target_word` | VARCHAR | yes | — |
| `spoken_word` | VARCHAR | yes | — |
| `accuracy` | INTEGER | yes | — |
| `feedback` | VARCHAR | yes | — |
| `stars` | INTEGER | yes | — |
| `audio_file` | VARCHAR | yes | — |
| `session_type` | VARCHAR | yes | — |
| `trs_score` | INTEGER | yes | — |
| `severity_classification` | VARCHAR | yes | — |
| `error_patterns` | JSONB | yes | — |
| `targeted_quests` | JSONB | yes | — |
| `diagnostic_report` | VARCHAR | yes | — |
| `created_at` | TIMESTAMP | yes | — |

**Therapist-facing tools**

`breathquest_therapist_notes`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `therapist_id` | UUID | no | FK → `therapists.id` |
| `created_at` | DATETIME | no | — |
| `updated_at` | DATETIME | no | — |
| `session_id` | UUID | yes | FK → `breathquest_game_sessions.id` |
| `content` | TEXT | no | — |
| `tags` | JSON | yes | — |

`breathquest_assignments`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `assigned_by` | UUID | no | FK → `therapists.id` |
| `game` | VARCHAR(50) | no | — |
| `level_id` | VARCHAR(50) | yes | — |
| `title` | VARCHAR(255) | no | — |
| `instructions` | TEXT | yes | — |
| `status` | VARCHAR(11) | no | — |
| `created_at` | DATETIME | no | — |
| `due_at` | DATETIME | yes | — |
| `completed_at` | DATETIME | yes | — |

`breathquest_goals`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `created_by` | UUID | no | FK → `therapists.id` |
| `target_metric` | VARCHAR(100) | no | — |
| `target_value` | FLOAT | no | — |
| `baseline_value` | FLOAT | yes | — |
| `target_date` | DATETIME | yes | — |
| `achieved` | BOOLEAN | no | — |
| `achieved_at` | DATETIME | yes | — |
| `created_at` | DATETIME | no | — |

`breathquest_messages`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `sender_role` | VARCHAR(9) | no | — |
| `sender_id` | UUID | yes | — |
| `body` | TEXT | no | — |
| `created_at` | DATETIME | no | — |
| `read_at` | DATETIME | yes | — |

`breathquest_home_practice_logs`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `logged_at` | DATETIME | no | — |
| `practiced_on` | DATETIME | no | — |
| `duration_minutes` | INTEGER | yes | — |
| `notes` | TEXT | yes | — |

`exercise_templates`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `title` | VARCHAR(160) | no | — |
| `description` | TEXT | no | — |
| `duration_label` | VARCHAR(32) | no | — |
| `target_categories` | ARRAY | no | — |

`exercise_assignments`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `patient_id` | VARCHAR | no | indexed |
| `exercise_id` | INTEGER | no | FK → `exercise_templates.id` |
| `status` | VARCHAR(11) | no | — |
| `assigned_at` | DATETIME | yes | — |
| `completed_at` | DATETIME | yes | — |

**Billing, assessment, RL retraining**

`breathquest_subscriptions`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `owner_parent_id` | UUID | yes | FK → `breathquest_parents.id`, unique |
| `owner_therapist_id` | UUID | yes | FK → `therapists.id`, unique |
| `plan_type` | VARCHAR(50) | no | — |
| `status` | VARCHAR(20) | no | — |
| `trial_ends_at` | DATETIME | no | — |
| `current_period_end` | DATETIME | yes | — |
| `provider` | VARCHAR(30) | yes | — |
| `provider_customer_id` | VARCHAR(255) | yes | — |
| `provider_subscription_id` | VARCHAR(255) | yes | — |
| `created_at` | DATETIME | no | — |
| `updated_at` | DATETIME | no | — |

`assessment_words`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK, indexed |
| `word` | VARCHAR(120) | no | unique |
| `image_prompt` | VARCHAR(240) | yes | — |
| `is_active` | BOOLEAN | no | — |
| `created_at` | TIMESTAMP | no | — |
| `animation_prompt` | VARCHAR(500) | yes | — |
| `animation_filename` | VARCHAR(240) | yes | — |
| `display_order` | INTEGER | no | — |
| `media_filename` | VARCHAR(240) | yes | — |
| `word_key` | VARCHAR(120) | yes | indexed |
| `english` | VARCHAR(120) | yes | — |
| `telugu` | VARCHAR(120) | yes | — |
| `hindi` | VARCHAR(120) | yes | — |
| `tamil` | VARCHAR(120) | yes | — |
| `kannada` | VARCHAR(120) | yes | — |
| `malayalam` | VARCHAR(120) | yes | — |
| `bengali` | VARCHAR(120) | yes | — |
| `marathi` | VARCHAR(120) | yes | — |

`breathquest_rl_training_events`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `child_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `timestamp` | DATETIME | no | indexed |
| `level_id` | VARCHAR | no | — |
| `attempt_number` | INTEGER | no | — |
| `score` | FLOAT | no | — |
| `is_valid_attempt` | BOOLEAN | no | — |
| `threshold_at_time` | FLOAT | yes | — |
| `action` | VARCHAR | yes | — |
| `quit_flag` | BOOLEAN | no | — |
| `raw_features` | JSON | yes | — |
| `severity_numeric` | FLOAT | no | — |
| `is_targeted_sound` | BOOLEAN | no | — |
| `policy_used` | VARCHAR | yes | — |
| `downgrade_reason` | VARCHAR | yes | — |
| `recommended_action` | VARCHAR | yes | — |
| `recommendation_message` | VARCHAR | yes | — |

`breathquest_retrain_checkpoints`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `scope` | VARCHAR | no | PK |
| `last_retrained_at` | DATETIME | no | — |
| `event_count_at_checkpoint` | INTEGER | no | — |

</details>

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

### Running tests

```bash
cd backend
uv pip install -r requirements-dev.txt
createdb vaaksudhi_test   # one-time; tests drop/recreate this schema every run
export DATABASE_URL="postgresql://postgres:password@localhost:5433/vaaksudhi_test"
pytest
```

Runs against a real Postgres database, not SQLite — several models use Postgres-native UUID columns that SQLite can't represent faithfully. Never point `DATABASE_URL` at your real dev database when running tests; the schema gets dropped and recreated. See `backend/tests/conftest.py` for the fixture design notes, including why the event-loop scope is pinned to `session` (asyncpg connections can't cross event loops, which is a sharp edge if you add fixtures of your own).

`backend/pytest.ini` scopes discovery to `backend/tests/` — the older `test_endpoints.py`, `test_db_connection.py`, `test_routes.py`, and `app/main_test.py` at the repo root are ad-hoc manual scripts (they hit a live DB / make real requests at import time), not pytest tests, and would otherwise get collected and executed too.

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
- **`epitran`/`editdistance` build failure on `pip install`**: `epitran` (used by `routers/flashcards/grapheme_to_phoneme.py`) has no prebuilt wheel and always compiles a small C extension via its `editdistance` dependency. Install Xcode Command Line Tools (macOS: `xcode-select --install`) or `build-essential` (Linux) first.

## Recent changes

- Consolidated to one frontend, one backend (previously split across `breathquest`/`vaakmirror`/standalone app trees and a port-8001 backend)
- Fixed a therapist-identity table mismatch (`therapists` vs. a retiring `breathquest_therapists` table) that silently broke patient creation
- Added kid-login rate limiting, COPPA parental consent, and phone verification as a second consent factor
- Introduced Alembic for schema migrations (previously unversioned `create_all()`)
- Fixed several live 404s: dashboard summary/session-history endpoints, VoiceHurdleRace's "my sessions," the assessment `/start` bootstrap
- Archived an orphaned, never-mounted second LangGraph pipeline (`routes/speech.py`) in favor of the one actually in use (`routes/assessment.py`)
- Added therapist-launched Assessment/Live Therapy sessions, a "today's recommendation" card driven by the adaptive-difficulty agent, and dashboard visibility for assessment-linked patients with no game history yet
- Removed dead/orphaned routes and pre-merge auth code left over from the consolidation
- Flashcards' word images now come from the same ARASAAC-backed pictogram service Assessment and VaakMirror use, replacing a smaller hand-curated Wikimedia/OpenClipart cache
- Fixed a Chime bug where the periodic "did they really make this sound" ASR verification would retract a child's already-earned progress (climb/depth/roars/fireflies/bubbles) whenever Whisper returned an empty transcript for a sustained non-lexical sound (eeee/aaaa/oooo/rrrr/ma/ya) — common even on a correct attempt — or whenever the transcription request itself failed; both cases are now treated as unverified rather than as a wrong sound, across Xylophone Tower, Rocket Launch, Submarine Dive, Wind Chime Garden, Lion's Roar, and Firefly Jar
- Fixed 7 of 35 Flashcards phoneme mouth-diagrams (`DH`, `AH`, `UH`, `OW`, `EY`, `AY`, `ER`) silently falling back to the wrong diagram (`EH`'s "half-open mouth") because their `mouth_shape` keys had never been added to the diagram library; added real diagrams for each

## Technologies

**Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, LangGraph, PyTorch, Whisper, Vosk, Librosa, Coqui TTS

**Frontend:** React, Vite, TailwindCSS, Recharts
