# VaakSuddhi Data Model — Patient Identity & IDs

Read this before touching anything patient-related. The #1 source of
"Patient not found" bugs in this codebase is passing the wrong ID to
the wrong table.

## Two patient tables, one database

**Updated 2026-09-23: this used to describe two separate Postgres
databases connected only over HTTP. That's no longer true as of the
2026-08-11/08-12 agenti_ai <-> quest-games merge** — `Patient` and
`BreathQuestPatient` are two tables in the *same* database now, both
declared on the same SQLAlchemy `Base` in `app/database.py`, which has
exactly one `DATABASE_URL` / one `engine` / one `async_engine`.
`assessment_client.py` (the old HTTP client) no longer exists; the
lookup it used to do over HTTP is now `services/assessment_lookup.py`'s
in-process query. If you're reading this because something referenced
"two databases" or `assessment_client`, that's stale — don't go
looking for a second Postgres instance or a network hop, there isn't
one.

| Table | Primary key means | Owns |
|---|---|---|
| `Patient` (`patients` table) | The "real" patient — created via assessment/onboarding flow | Assessment data, `EmailVerification` records |
| `BreathQuestPatient` (`breathquest_patients` table) | A kid's login/play identity — created via kid-register / parent flow | Game sessions, PIN auth, agent training state |

These are linked by a **real SQL foreign key** (migration
`a9f3c7d2e1b4`), not an application-level convention:
`BreathQuestPatient.assessment_patient_id --> Patient.id` (nullable!)

If `assessment_patient_id` is `NULL`, that BreathQuestPatient has never
been linked to an assessment record, and anything that requires the
assessment side (agent status, diagnostic context) will 404 — this is
expected, not a bug, for a patient who hasn't been assessed yet.

## Which ID do I use where?

- **Gameplay routes** (logging sessions, in-game events): use
  `BreathQuestPatient.id` (the "bq_id"). This is what kid-token auth
  (`get_current_patient`) resolves to.
- **Agent status / diagnostic routes** (`/breath/agent/status/{id}`,
  Chime and Voice Hurdle Race equivalents): the path param is
  `Patient.assessment_patient_id`, NOT `BreathQuestPatient.id`. The
  route internally re-looks-up the `BreathQuestPatient` row by that
  assessment ID + `therapist_id` ownership check, then uses
  `patient_row.id` (the bq_id) for the actual `AgentService` call.
  **Do not assume the frontend route param `id` is either of these
  directly** — see `AgentInsight.jsx`, which resolves the real
  assessment ID from the patient record before calling any
  agent-status endpoint.
- **Therapist-facing patient list / dashboard**: keyed by
  `BreathQuestPatient.therapist_id` (ownership) — every patient a
  therapist can see must have this set at creation.

## Ownership check pattern

Every therapist-facing route filters by BOTH:
```python
BreathQuestPatient.assessment_patient_id == patient_id,
BreathQuestPatient.therapist_id == therapist.id,
```
and returns **404** (not 403) on failure, deliberately — so a
therapist probing random IDs can't learn which patient IDs exist.
This means a patient missing *either* field looks identical, from the
API's perspective, to a patient that doesn't exist at all. When
debugging a mystery 404, check both fields before assuming the ID is
wrong.

## Known data debt (as of Sep 2026)

A number of `BreathQuestPatient` rows predate one or both of
`assessment_patient_id` and `therapist_id` being populated at write
time (pre-dates the FK migration / quest-games merge). These rows
will 404 on agent-status routes even though the patient "exists" and
plays fine in-game. `scripts/backfill_assessment_links.py` (2026-09-23)
backfills `assessment_patient_id` in bulk for every row that has a
`therapist_id` set — run it (dry-run by default, `--confirm` to apply)
before assuming a specific patient's 404 is a new bug rather than legacy
data. Rows missing `therapist_id` entirely can't be auto-fixed (nothing
in the schema says which therapist should own them) and the script only
reports those for manual resolution via `POST /patients/link`.

## Other things worth knowing

- Two dev servers: agenti_ai frontend on 5173, quest-games on 5174,
  proxied together via `vite.config.js` (`/quest-app/*` -> 5174).
- SMTP sender is `manaslearning.com@gmail.com` (Gmail SMTP, app
  password stored as the `smtp-password` Container App secret —
  never as a plain env var value).
- `AUTO_VERIFY_CONSENT` flag exists as a temporary bypass for parent
  consent gating (PR #9) — don't assume consent is actually verified
  in current data.
