"""
app/retraining/scheduler.py — Retraining trigger for the shared PPO/
recurrent-PPO policy, ported from retraining/scheduler.py (2026-08-20).

Ported for the same reason app.retraining.data_store exists rather than
retraining.data_store being used directly: this package's RLTrainingEvent
(app.models.retraining_models) is the one actually migrated by Alembic and
FK'd to breathquest_patients.id, which is what every real caller
(breath_agent.py/chime.py/voicehurdlerace.py/phonemequest.py/vaakmirror/
sessions.py) has always passed as child_id. The top-level retraining/
package's RLTrainingEvent is FK'd to patients.id (Assessment's separate,
disjoint patient table -- zero id overlap, confirmed 2026-08-20) and was
never part of any Alembic migration, so it can't be written to at all.

Deliberately does NOT handle the tabular Q-agent — that one is genuinely
online (see app.breathquest_agent.child_q_store) and doesn't need a batch
trigger like this at all; every real transition updates that child's table
immediately. This file is specifically for the shared deep policy, which
can only reasonably be retrained in batches.
"""

import threading

from . import data_store
from simulator.simulator_calibration import calibrate_from_events
import logging

logger = logging.getLogger(__name__)


GLOBAL_RETRAIN_THRESHOLD = 200  # pooled real events across all children


def maybe_retrain_shared_policy(db_path=None, timesteps: int = 20000, force: bool = False,
                                 recurrent: bool = False, models_dir: str = "app/breathquest_agent/models"):
    kwargs = {"db_path": db_path} if db_path else {}
    checkpoint = data_store.get_checkpoint("global", **kwargs)
    total_events = data_store.count_events(**kwargs)
    events_since = total_events - (checkpoint["event_count_at_checkpoint"] if checkpoint else 0)

    if not force and events_since < GLOBAL_RETRAIN_THRESHOLD:
        return {
            "retrained": False,
            "reason": f"only {events_since} new events since last checkpoint, need {GLOBAL_RETRAIN_THRESHOLD}",
            "events_since_checkpoint": events_since,
        }

    all_events = data_store.get_events(**kwargs)
    ranges = calibrate_from_events(all_events)

    from agent.train_ppo import train_standard_ppo, train_recurrent_ppo

    filename = "recurrent_ppo_difficulty" if recurrent else "ppo_difficulty"
    save_path = f"{models_dir}/{filename}"
    train_fn = train_recurrent_ppo if recurrent else train_standard_ppo
    train_fn(timesteps, save_path, calibrated_ranges=ranges)

    data_store.set_checkpoint("global", total_events, **kwargs)
    return {
        "retrained": True,
        "n_events_used": len(all_events),
        "calibrated_ranges": ranges,
        "model_path": save_path,
    }


_retrain_lock = threading.Lock()
_retrain_in_progress = False


def run_retrain_if_due(db_path=None):
    global _retrain_in_progress
    kwargs = {"db_path": db_path} if db_path else {}
    checkpoint = data_store.get_checkpoint("global", **kwargs)
    total = data_store.count_events(**kwargs)
    since = total - (checkpoint["event_count_at_checkpoint"] if checkpoint else 0)
    if since < GLOBAL_RETRAIN_THRESHOLD:
        return

    with _retrain_lock:
        if _retrain_in_progress:
            return
        _retrain_in_progress = True

    try:
        result = maybe_retrain_shared_policy(**kwargs)
        if result.get("retrained"):
            logger.info(f"[retraining] auto-retrain complete — {result.get('n_events_used')} events used")
    except Exception as exc:
        logger.info(f"[retraining] auto-retrain failed: {exc}")
    finally:
        _retrain_in_progress = False
