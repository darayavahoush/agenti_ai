# Vaaksudhi — Speech Therapy Platform

A speech-therapy platform for children, combining a real LangGraph-based pronunciation assessment with four game-based practice tools (BreathQuest, VoiceHurdleRace, VaakMirror, and Chime/PhonemeQuest), a therapist dashboard, and a parent portal. One FastAPI backend, one React frontend.

## What's in here

**For kids:** a login with a player code or a chosen `@username` plus a 4-digit PIN. New kid accounts are always started by an adult — a parent (when they add a child) or a therapist (from the dashboard); kids can't self-register (`KID_SELF_SERVICE_SIGNUP_ENABLED` is off by default), and the kid-side "My Therapist Set Me Up" name picker (with its `kid-candidates` / `kid-pin-setup` routes) was retired on 2026-09-24. Once in, kids get:

- an assessment flow that scores pronunciation against a word list in 8 Indian languages (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi), including an Alphabet "Sound Check" that scores each letter's initial sound, and a "Your game plan" card (`services/game_predictor.py`) that ranks which practice games to start with based on the sounds they missed;
- four practice games — **BreathQuest**, **VoiceHurdleRace**, **VaakMirror** (shown to kids as "Orpheus": Mirror Mirror, Tongue Tamer, Lip Sync Hero, Minimal Pair Drill) and **Chime** (a rebuild of the earlier standalone PhonemeQuest mini-games, now integrated with shared kid-auth and the adaptive-difficulty agent: Rocket Launch, Submarine Dive, Firefly Jar, Wind Chime Garden, Bubble Wrap Pop, Xylophone, Lion's Roar, Village Builder). Each has its own adaptive-difficulty logic driven by a small RL agent that raises or lowers difficulty based on recent performance;
- **Flashcards**, a standalone practice section separate from the four games (phoneme mouth-diagrams, a 25-category picture vocabulary with ARASAAC pictograms, and character cards), and a cosmetic companion whose accessories unlock with practice streaks.

**For therapists:** a dashboard across all four games for each patient (with a real "Logged in" status per patient card), session history, assignments/goals/messages, home-practice logging, a home-practice-ideas library, weekly summaries, a branded PDF export, a cross-game Phoneme Command Center (one accuracy number per phoneme, pooled across Flashcards/VaakMirror/Chime, with a per-game at-a-glance strip), and an AI-generated "today's recommendation" per patient pulled from the assessment/agent data. Therapists can add a patient directly, link an existing one by player code or `@username`, launch Assessment/Live Therapy sessions, and edit a kid's avatar.

**For parents:** a tabbed dashboard (Overview / Sounds / Games / Messages) covering weekly summaries, goals/assignments, a shareable weekly recap card, a parent-facing cut of the cross-game sound summary ("going well" / "worth practicing," no clinical jargon), per-game history, and two-way messaging with their child's therapist — gated behind email verification and COPPA-style parental consent (a recently confirmed emailed code) before a kid account can be created. One parent account can hold several children and switch between them; parents can also edit a child's avatar, and the weekly progress email carries a one-click unsubscribe link.

**Accounts & sign-in:** therapists and parents sign in with email + password or Google (needs `GOOGLE_CLIENT_ID` on the backend and `VITE_GOOGLE_CLIENT_ID` on the frontend — see Environment variables). Registration verifies the email with a one-time code (SMTP). Phone numbers are collected on therapist and parent accounts but not verified — phone OTP was removed from the consent flow on 2026-08-29, leaving email as the only consent factor. Emails are case-normalized, and one email can't be registered as both a parent and a therapist — the second registration is refused with a message pointing to the right role. Kids, parents and therapists can each pick an editable, unique `@username` (unique across all three account tables; `app/breathquest_core/username.py`).

## Project structure

```
agenti_ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, all router mounts
│   │   ├── routes/assessment.py     # LangGraph-based pronunciation assessment (word list, image, TTS audio, analyze)
│   │   ├── routers/
│   │   │   ├── therapist_auth.py, therapist_patients.py, username_routes.py   # canonical therapist identity, patient CRUD, @usernames
│   │   │   ├── breathquest/         # kid/parent auth + per-game routers (breath_agent, voicehurdlerace, chime,
│   │   │   │                        #   dashboard, patients, sessions, parent, kid_progress, email_prefs,
│   │   │   │                        #   assessment_lookup, billing, access, verify)
│   │   │   ├── vaakmirror/          # VaakMirror sessions, dashboard, exercises, labeling, round size, agent, params
│   │   │   ├── flashcards/          # Flashcards: phoneme drill/eval, mastery, TTS, image lookup
│   │   │   └── phonemequest.py, audio.py, event_feedback.py
│   │   ├── models/                  # SQLAlchemy models (one Patient/Therapist identity, shared across games)
│   │   ├── services/                # phoneme summary/crosswalk, recommendations, game predictor, weekly summary/
│   │   │                            #   email, PDF report, companion unlocks, image/audio/voice helpers
│   │   ├── graph/, agents/          # LangGraph pipelines (assessment, alphabet Sound Check)
│   │   ├── breathquest_core/        # JWT auth, Google OAuth, usernames, rate limiting, parental consent,
│   │   │                            #   email provider, feature flags (config.py)
│   │   └── retraining/              # event logging + scheduler for RL retraining
│   ├── agent/                       # RL adaptive-difficulty agent (Q-tables, PPO training, baselines, safety)
│   ├── alembic/                     # schema migrations (introduced 2026-08-13; earlier tables via create_all())
│   ├── scripts/                     # one-off ops scripts (backfill assessment links, find/deactivate duplicate
│   │                                #   or orphaned patients, reset a kid PIN, demo seed data)
│   ├── tests/                       # pytest suite (needs Postgres — see Running tests)
│   └── data/, assets/audio          # assessment word images (copied into the Docker image at deploy),
│                                    #   flashcard images, static audio
├── frontend/
│   └── src/
│       ├── pages/kid/                # login, game picker, level select, gameplay, flashcards, assessment gate/report, progress
│       ├── pages/therapist/          # login, dashboard, patient detail, agent insight, settings
│       ├── pages/parent/             # auth, dashboard, settings
│       ├── assessment/               # the LangGraph-backed assessment UI, including the Alphabet Sound Check
│       ├── voiceHurdleRace/, vaakmirror/, chime/, game/, flashcards/  # practice games and Flashcards
│       └── api/client.js             # shared axios instance (bearer token, one base URL)
├── data/images/                      # assessment word images (see the deploy workflow's "Copy assessment word images" step)
├── docs/DATA_MODEL.md                # read before touching anything patient-related (Patient vs BreathQuestPatient IDs)
├── setup.sh, setup.bat               # one-shot local setup
└── .github/workflows/                # staging deploys (backend → Azure Container Apps, frontend → Azure Static Web Apps)
```

One frontend, one backend — this used to be split across separate `breathquest`/`vaakmirror`/`quest-games` app trees and a standalone port-8001 backend; those have been consolidated.

## Database structure

31 tables across two "eras" of the codebase — a legacy `breathquest_*`-prefixed set (BreathQuest's original standalone app) and a newer unprefixed set (Assessment/therapist-portal, added during consolidation). Both eras share identity tables where it made sense (one `Patient`, one canonical `Therapist`) rather than duplicating them per-game.

**Schema is Alembic-managed** (`backend/alembic/`) as of 2026-08-13 — `alembic upgrade head` is required to bootstrap a fresh database; `Base.metadata.create_all()` alone will not, by design (see the comment block above `_ensure_patient_therapist_link_column()` in `app/main.py`).

### Identity (shared across every game)

| Table | Purpose |
|---|---|
| **`therapists`** | The canonical, going-forward therapist identity (`app/models/therapist.py`). `hashed_password` is nullable (Google-only accounts have none); `google_sub` links a Google identity. |
| **`patients`** | The canonical patient/child identity (`app/models/patient.py`), optionally linked to a registering therapist via `registered_therapist_id`. |
| **`breathquest_patients`** | BreathQuest's own patient row (`app/models/breathquest_models.py`) — the row every game actually foreign-keys against for gameplay data. Links back to the canonical `patients` row via `assessment_patient_id`, and to a `therapists` row via `therapist_id`. In effect: `patients`/`therapists` are the identity of record; `breathquest_patients` is where the games' data actually hangs. |
| **`breathquest_parents`** | Parent accounts (`Parent`). `patient_id` is the parent's currently active child. `hashed_password` nullable for the same Google-only reason as `therapists`. |
| **`breathquest_parent_children`** | The set of children a parent may switch between (multi-child support, 2026-09-10). Only `POST /auth/parent/switch-child` ever reassigns `Parent.patient_id`, and it checks membership here first. |

> **`breathquest_therapists`** also exists as a defined table (`Therapist` class inside `breathquest_models.py`) but is dead: nothing queries or writes it. It's still imported in `routers/flashcards/router.py`, but only as a (now-inaccurate) type hint on `Depends(get_current_therapist)` — the dependency itself resolves against the real `therapists` table. Safe to remove the import; the table itself can be dropped in a future migration once confirmed empty. See `app/models/therapist.py`'s own docstring, which already flags this as "retiring."

### Auth & consent

| Table | Purpose |
|---|---|
| **`breathquest_refresh_tokens`** | Revocable long-lived credentials (SHA-256-hashed, never raw) for therapist/parent/kid sessions — `owner_kind` + `owner_id` instead of three nullable FK columns, since a token belongs to exactly one of three different tables. |
| **`breathquest_kid_login_throttle`** | Brute-force tracking for kid PIN login, keyed by the lowercased identifier string attempted (name/player code), not by patient — an attempt against a nonexistent identifier still counts. |
| **`breathquest_email_verifications`** | Emailed one-time codes; a code confirmed within the consent window is the COPPA-style verifiable-consent factor, and it also gates therapist/parent registration. |
| **`breathquest_phone_verifications`** | Legacy: the former second consent factor. Phone OTP was removed on 2026-08-29 and no route reads or writes this table now (nor is `breathquest_core/phone_provider.py`'s Azure SMS provider called anywhere). Safe to drop in a future migration. |

### Gameplay & progress

| Table | Purpose |
|---|---|
| **`breathquest_companion_unlocks`** | Permanent record of each cosmetic companion accessory a kid has earned (unique per patient + item), so an unlock survives a later streak reset. |
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
| **`vaakmirror_round_size_settings`** | Per-patient, per-game round size for VaakMirror (unique per patient + game; defaults to 10). |

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
| `username` | VARCHAR(30) | yes | unique |

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
| `equipped_companion_item` | VARCHAR(50) | yes | — |
| `avatar_photo_url` | VARCHAR(255) | yes | — |
| `pin_hash` | VARCHAR(64) | no | — |
| `player_code` | VARCHAR(10) | no | unique |
| `age` | INTEGER | yes | — |
| `diagnosis_notes` | TEXT | yes | — |
| `is_active` | BOOLEAN | no | — |
| `assessment_patient_id` | UUID | yes | FK → `patients.id`, indexed |
| `assessment_completed` | BOOLEAN | no | — |
| `assessment_summary` | JSON | yes | — |
| `assessment_completed_at` | DATETIME | yes | — |
| `last_seen_at` | DATETIME | yes | — |
| `username` | VARCHAR(30) | yes | unique |
| `parent_email` | VARCHAR(255) | yes | — |
| `parent_consent_verified_at` | DATETIME | yes | — |
| `parent_phone` | VARCHAR(32) | yes | — |
| `parent_phone_consent_verified_at` | DATETIME | yes | — |
| `last_weekly_email_sent_at` | DATETIME | yes | — |
| `weekly_email_opt_out` | BOOLEAN | no | — |
| `archived_at` | DATETIME | yes | — |
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
| `username` | VARCHAR(30) | yes | unique |

`breathquest_parent_children`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `parent_id` | UUID | no | FK → `breathquest_parents.id`, indexed |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `is_primary` | BOOLEAN | no | — |
| `created_at` | DATETIME | no | — |

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
| `shape` | VARCHAR(32) | yes | — |
| `openness` | FLOAT | yes | — |
| `spread` | FLOAT | yes | — |
| `predicted_tier` | VARCHAR(8) | yes | — |
| `therapist_label` | VARCHAR(9) | yes | — |
| `labeled_at` | DATETIME | yes | — |
| `labeled_by` | VARCHAR | yes | — |

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

`breathquest_companion_unlocks`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `breathquest_patients.id`, indexed |
| `item_id` | VARCHAR(50) | no | — |
| `unlocked_at` | DATETIME | no | — |

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

`vaakmirror_round_size_settings`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | no | PK |
| `patient_id` | VARCHAR | no | indexed |
| `game` | VARCHAR(13) | no | — |
| `round_size` | INTEGER | no | — |
| `updated_at` | DATETIME | yes | — |

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
| `feedback` | VARCHAR | yes | — |
| `feedback_at` | DATETIME | yes | — |

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

cp .env.example .env   # set DATABASE_URL at minimum; see Environment variables below for the rest

# Schema: Alembic-managed as of 2026-08-13
alembic upgrade head

# Seed the assessment word list (47 words, 8-language translations)
python add_images_to_db.py

uvicorn app.main:app --reload   # http://localhost:8000
```

### Environment variables

`backend/.env.example` only lists a handful of these, so use this table as the reference. Everything except `DATABASE_URL` has a default, and empty SMTP settings mean dev mode: OTP codes are logged to the server output instead of emailed.

**Backend** (`backend/.env`, or the Container App's env vars in production)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string (sync `postgresql://` or `postgresql+asyncpg://` both work) |
| `SECRET_KEY` | JWT signing secret — **must be overridden outside local dev** |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `API_BASE_URL` | Public backend URL, used for links inside emails (e.g. unsubscribe) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID; Google sign-in fails with a 500 if unset. Same value as the frontend's `VITE_GOOGLE_CLIENT_ID` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Email OTP codes + weekly progress emails (Gmail SMTP with an app password works) |
| `AZURE_COMMUNICATION_CONNECTION_STRING`, `AZURE_COMMUNICATION_FROM_NUMBER` | Only read by `phone_provider.py`, which nothing calls today (phone OTP was removed) — safe to leave unset |
| `OPENAI_API_KEY` | Optional, for enhanced features |
| `ASSESSMENT_SERVICE_API_KEY` | `X-API-Key` for the service-to-service assessment routes |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob storage (`app/blob_storage.py`) |
| `PIXABAY_API_KEY` | Optional image-lookup fallback |
| `CHIME_WHISPER_MODEL` | Whisper model size for Chime verification (default `base`) |
| `TTS_FALLBACK_TO_DUMMY` | Default `true`: if Coqui TTS fails, write a placeholder tone instead of erroring. Set `false` to fail loudly |
| `KID_SELF_SERVICE_SIGNUP_ENABLED` | Default `false`: only adults create new kid accounts |
| `PAYMENTS_LIVE` | Default `false`: no real payment provider is wired in yet (see `billing.py`) |

**Frontend** (`frontend/.env.development`, `frontend/.env.production`): `VITE_API_URL` and `VITE_GOOGLE_CLIENT_ID` (a public identifier, safe to expose client-side).

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

## Deployment

Pushing to `staging` triggers two GitHub Actions workflows: `deploy-staging.yml` (builds the backend Docker image, pushes it to Azure Container Registry, updates the `vaaksudhi-backend` Container App) and `deploy-frontend-staging.yml` (builds the frontend and deploys it to the `vaaksudhi-frontend` Static Web App; only runs when `frontend/**` changes).

Both repos (`darayavahoush/agenti_ai` and `lavanya2kowmar/agenti_ai`) carry the same workflows and receive the same `staging` pushes, so each workflow is gated to run the real deploy in **one** canonical repo, currently **`darayavahoush/agenti_ai`** (moved back on 2026-09-21 because the other repo's Actions billing was blocked). The other repo's run shows "Skipped" by design. Actions secrets don't carry over between repos, so every secret the workflow references (Azure IDs, `SMTP_*`, `GOOGLE_CLIENT_ID`) must exist in the canonical repo. If the canonical repo ever changes, update the `if: github.repository == ...` line in both workflows. (The explanatory comments above that line in both workflow files still describe the earlier 2026-09-18 switch to `lavanya2kowmar` and are out of date.)

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
- Added a cross-game Phoneme Command Center (`services/phoneme_summary.py`) that pools Flashcards + VaakMirror + Chime attempts into one accuracy number per phoneme, with a per-game at-a-glance totals strip; wired into the therapist dashboard, the PDF report, and (parent-scoped, reframed without clinical jargon) the parent dashboard's new Sounds tab
- Redesigned the ICF-style PDF report (cover band, KPI cards, color-coded severity badges, paginated footers) and gave it an actual brand identity — a wordmark/logo mark on the cover and the product name + site URL in the footer of every page, not just a generic export
- Restructured the parent dashboard from one long scroll into four tabs (Overview / Sounds / Games / Messages), pulling messaging onto its own tab with an unread badge instead of burying it below goals/assignments
- Corrected the staging-deploy note: after briefly switching to `lavanya2kowmar/agenti_ai` (2026-09-18), the canonical deploy repo moved back to `darayavahoush/agenti_ai` on 2026-09-21 because the other repo's Actions billing was blocked; the non-canonical repo's workflow run shows "Skipped" by design (see Deployment)
- Added editable, unique `@username`s for kids, parents and therapists; the dashboard shows a kid's username instead of the player code once set, and therapists can link an existing patient by player code or `@username`
- Added Google sign-in for therapists and parents
- Removed phone OTP as a second consent factor (2026-08-29): parental consent is now email-only, and the phone-verification table and SMS provider are dormant
- Multi-child parent accounts (`breathquest_parent_children`, `POST /auth/parent/switch-child`), plus a weekly progress email with a one-click unsubscribe link
- Closed an account-takeover hole in kid PIN setup, removed the "New child, no therapist" parent signup option, and turned off kid self-registration by default (adults now create every new kid account)
- Blocked the same email from being registered as both a parent and a therapist, normalized email case across auth, added a confirm-password field, and validate therapist registration before the OTP is sent
- Removed the kid login screen's "My Therapist Set Me Up" name picker (2026-09-24) and retired its unauthenticated backend routes, `GET /auth/kid-candidates` (which listed unlinked children's names to anyone, and never actually populated the picker) and `POST /auth/kid-pin-setup`, plus the unused `GET /auth/therapist-candidates` (which listed therapist names to anyone); all three now return 410. New kid accounts are created only by a parent or therapist, who sets the PIN
- Added an assessment game-prediction agent ("Your game plan" card) and an Alphabet Sound Check LangGraph agent with VaakMirror parameters
- Flashcards: expanded to a 25-category / 776-word vocabulary with real pictures in the word-select tiles, full-portrait character cards, and a redesign of the theme/word select screens; fixed Flashcards history entries showing up labeled as Chime
- Chime: 3-2-1-Go countdown before scoring, Xylophone redrawn and renamed, and fixes for games freezing at full progress when the browser can't record, Rocket sound spelling, Village Builder word-match scoring, and Lion's Roar replay/win confirmation
- VaakMirror: brighter low-light camera frames for detection, personalized openness calibration, and a per-patient round-size setting
- Fixed `/parent/progress` returning a 500 for parents whose child had two or more Chime plays on the same sound; fixed stale-session 401s and login bounces in the SPA (session-generation counter, auto-reload after a deploy)

## Technologies

**Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, LangGraph, PyTorch (PPO training for the RL agent), Whisper, Vosk, Librosa, Coqui TTS, Google OAuth

**Frontend:** React, Vite, TailwindCSS, Recharts

**Hosting / CI:** Azure Container Apps + Container Registry (backend), Azure Static Web Apps (frontend), GitHub Actions
