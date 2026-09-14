"""
services/recommendations.py — "What should this kid practice today?"

Combines the three independent per-game signals this app already computes
into one kid-facing recommendation, picking whichever game/level currently
shows the strongest "needs practice" signal:

- BreathQuest: AgentService.get_status() per level (read-only, side-effect
  free by design -- see its own docstring). Uses the adaptive-difficulty
  RL agent's own success_rate/frustration read of recent attempts, so this
  reuses the agent's existing state assessment rather than recomputing one.
  Only considered when n_events_considered >= 3, matching decide()'s own
  gate for having any real signal at all.
- VoiceHurdleRace: average pitch_accuracy/loudness_accuracy per level_id
  from breathquest_voicehurdlerace_sessions. These are 0-100 (see
  GameEngine.ts's pitchAccuracy/loudnessAccuracy computation), normalized
  to 0-1 here to compare against the other two sources.
- VaakMirror: average Attempt.score per game (mirror_mirror/tongue_tamer/
  lip_sync_hero). score is already 0-1 (see sessions.py's rl_score
  fallback to 0.0/1.0).

Neither VoiceHurdleRace nor VaakMirror write to app.retraining.data_store
(confirmed -- neither router touches RLTrainingEvent), so the RL agent has
no visibility into them; this is a separate, simpler read of their own
accuracy columns, not a policy decision. That's an intentional scope split:
this module recommends WHAT to practice, it doesn't decide HOW HARD a
level should be -- that stays the RL agent's job, untouched here.
"""

from sqlalchemy import select, func

from app.models.breathquest_models import GameSession
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.vaakmirror_models import VaakMirrorSession, Attempt
from app.routers.breathquest.dashboard import LEVEL_NAMES as BQ_LEVEL_NAMES
from app.routers.breathquest.breath_agent import _agent_service

# level_id -> frontend route. BreathQuest levels deep-link to the specific
# level (routed as /play/game/:levelId); VoiceHurdleRace has no per-level
# route today (only /play/voice-hurdle-race), so it always points to the
# game entry regardless of which level_id is weakest.
BQ_PATH = "/play/game/{level_id}"
VHR_PATH = "/play/voice-hurdle-race"
VM_GAME_PATHS = {
    "mirror_mirror": "/play/vaakmirror/mirror-mirror",
    "tongue_tamer": "/play/vaakmirror/tongue-tamer",
    "lip_sync_hero": "/play/vaakmirror/lip-sync-hero",
}
VM_GAME_LABELS = {
    "mirror_mirror": "Mirror, Mirror",
    "tongue_tamer": "Tongue Tamer",
    "lip_sync_hero": "Lip Sync Hero",
}

# Below this, nothing is clearly struggling enough to call out -- avoids
# recommending a level that's merely "not perfect" every single day, which
# would make the card feel naggy rather than genuinely useful.
CONCERN_THRESHOLD = 0.35


async def get_recommended_practice(patient_id, db) -> dict | None:
    candidates = []

    # --- BreathQuest, via the RL agent's own existing per-level assessment.
    for level_id, level_name in BQ_LEVEL_NAMES.items():
        status = _agent_service.get_status(str(patient_id), level_id, policy="rule_based")
        if status["n_events_considered"] < 3:
            continue
        success_rate = status["obs"]["success_rate"]
        frustration = status["obs"]["frustration"]
        concern = (1 - success_rate) * 0.5 + frustration * 0.5
        candidates.append({
            "source": "breathquest",
            "concern": concern,
            "label": level_name,
            "path": BQ_PATH.format(level_id=level_id),
            "message": "This one's been tricky lately -- a little more practice would help!",
        })

    # --- VoiceHurdleRace, averaged per level_id.
    vhr_rows = (await db.execute(
        select(
            VoiceHurdleRaceSession.level_id,
            VoiceHurdleRaceSession.level_name,
            func.avg(VoiceHurdleRaceSession.pitch_accuracy).label("avg_pitch"),
            func.avg(VoiceHurdleRaceSession.loudness_accuracy).label("avg_loudness"),
        )
        .where(VoiceHurdleRaceSession.patient_id == patient_id)
        .group_by(VoiceHurdleRaceSession.level_id, VoiceHurdleRaceSession.level_name)
    )).all()
    for level_id, level_name, avg_pitch, avg_loudness in vhr_rows:
        avg_accuracy = ((avg_pitch or 0) + (avg_loudness or 0)) / 2 / 100
        concern = 1 - avg_accuracy
        candidates.append({
            "source": "voicehurdlerace",
            "concern": concern,
            "label": level_name,
            "path": VHR_PATH,
            "message": "Your voice control here could use a bit more practice!",
        })

    # --- VaakMirror, averaged per game. patient_id is a plain String
    # column on VaakMirrorSession (see kid_progress.py's own note on this).
    vm_rows = (await db.execute(
        select(
            VaakMirrorSession.game,
            func.avg(Attempt.score).label("avg_score"),
        )
        .join(Attempt, Attempt.session_id == VaakMirrorSession.id)
        .where(VaakMirrorSession.patient_id == str(patient_id), Attempt.score.is_not(None))
        .group_by(VaakMirrorSession.game)
    )).all()
    for game, avg_score in vm_rows:
        game_value = game.value if hasattr(game, "value") else game
        concern = 1 - (avg_score or 0)
        candidates.append({
            "source": "vaakmirror",
            "concern": concern,
            "label": VM_GAME_LABELS.get(game_value, game_value),
            "path": VM_GAME_PATHS.get(game_value, "/play/vaakmirror"),
            "message": "This game's a good one to revisit today!",
        })

    if not candidates:
        return None

    best = max(candidates, key=lambda c: c["concern"])
    if best["concern"] < CONCERN_THRESHOLD:
        return None

    return {
        "source": best["source"],
        "label": best["label"],
        "path": best["path"],
        "message": best["message"],
    }
