# `_legacy/`

Code kept for historical reference, not imported by anything live. If
you're reading this because you found a broken import pointing in
here, that import is the bug — nothing in the running app is supposed
to reach into `_legacy/`.

## `speech_pipeline/`

The original LangGraph-based speech therapy pipeline from the
`lavanya2kowmar/agenti_ai` repo this project was integrated from.
Never mounted in `main.py` — `app.include_router()` was never called
for any of these three routers, so `/speech/*`, `/voice/*`, and
`/image/*` have 404'd since day one of this integrated repo. Confirmed
via grep across the whole tree (backend + frontend) before moving:
nothing outside this pipeline itself referenced any of these paths or
imported these modules, except `backend/test_routes.py` (a standalone
manual diagnostic script, not part of the app or any test suite),
which has been updated to import from here instead.

**What superseded it:** `app/routes/assessment.py`'s `/assessment/analyze`
endpoint and `app/graph/assessment_graph.py` — a *different*, smaller
LangGraph pipeline (4 nodes: speech analysis, articulation diagnostic,
vocal acoustic, diagnostic reporter) that actually is mounted and live.
The two pipelines share some building blocks (`SpeechAnalysisAgent`,
`SpeechState`, the `tools/` modules, `AudioService`/`VoiceService` for
TTS) — those stayed in their original locations in `app/`, since
they're genuinely still used by the live pipeline. Only the parts
*unique* to this dead pipeline moved here:

- `routes/speech.py`, `routes/voice.py`, `routes/image.py` — the three
  unmounted routers themselves.
- `graph/speech_graph.py` — a 6-node graph (speech analysis → progress
  evaluation → supervisor → conditionally branches to intensive
  practice or therapy recommendation → session planning) built for an
  ongoing multi-session therapy-companion product, not the one-shot
  diagnostic assessment this repo actually ships.
- `agents/supervisor_agent.py`, `therapy_recommendation_agent.py`,
  `progress_evaluation_agent.py`, `intensive_practice_agent.py`,
  `session_planning_agent.py` — the 5 agents unique to that graph.
  (`speech_analysis_agent.py` is *not* here — it's shared with the
  live pipeline and stayed in `app/agents/`.)

Internal imports between the files above were updated to point at
this new location; imports to the still-live shared modules
(`app.state.speech_state`, `app.tools.*`, `app.database`,
`app.models.*`, `app.services.*`, `app.agents.speech_analysis_agent`)
were left unchanged, since those files didn't move.

**Reviving this:** if a real multi-session therapy-companion feature
(as opposed to the one-shot assessment this repo has) gets built later,
this is a reasonable starting point — the graph structure and agent
responsibilities are sound, they're just not wired to anything today.
You'd need to: mount the router(s) in `main.py`, fix the frontend to
actually call `/speech/therapy` instead of `/assessment/analyze`, and
sort out `routes/image.py`'s dependence on `routes/speech.py`'s
`get_basic_phonemes` re-export (importing a function through an
unrelated router module rather than straight from
`app.tools.phoneme_tool` is fragile regardless of where it lives).
