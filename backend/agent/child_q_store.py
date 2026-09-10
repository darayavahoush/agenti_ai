"""
Per-child tabular Q-agent persistence.

This is what "every kid gets their own model" actually means for the tabular
rung: each child gets their own small Q-table, seeded from a shared "prior"
(trained on the simulator) so a brand-new child doesn't start from nothing,
then updated online from that specific child's real transitions as they play.

Contrast with agent/train_ppo.py + retraining/scheduler.py: the deep policy
is NOT per-child (see this repo's README for why) — this file is specifically
the tabular exception.

Persisted to Azure Blob Storage (agent-state container), not local disk --
these were previously written to backend/agent/models/, which is ephemeral
on Azure Container Apps and gets wiped on every redeploy, silently resetting
every child's learned difficulty-tuning progress each time the backend
ships. Same root cause and same fix pattern as app/blob_storage.py's avatars
container (see its module docstring).
"""

import json

from .baselines import TabularQAgent

Q_TABLES_PREFIX = "q_tables/"
PRIOR_BLOB_NAME = "q_prior.json"


def _key_to_str(key: tuple) -> str:
    return ",".join(str(x) for x in key)


def _str_to_key(s: str) -> tuple:
    return tuple(int(x) for x in s.split(","))


def _container():
    from app.blob_storage import get_agent_state_container_client
    return get_agent_state_container_client()


def _save_q_table_blob(q_table: dict, blob_name: str):
    serializable = {_key_to_str(k): v for k, v in q_table.items()}
    data = json.dumps(serializable).encode("utf-8")
    _container().upload_blob(name=blob_name, data=data, overwrite=True)


def _load_q_table_blob(blob_name: str) -> dict:
    blob = _container().get_blob_client(blob_name)
    data = blob.download_blob().readall()
    serializable = json.loads(data)
    return {_str_to_key(k): v for k, v in serializable.items()}


def _blob_exists(blob_name: str) -> bool:
    return _container().get_blob_client(blob_name).exists()


def save_prior_from_agent(agent: TabularQAgent):
    """Call this after training a TabularQAgent against the simulator (see
    agent/evaluate.py) to establish the shared cold-start prior."""
    _save_q_table_blob(agent.q_table, PRIOR_BLOB_NAME)


def child_table_exists(child_id: str) -> bool:
    """Whether this child has their own persisted Q-table yet, as opposed
    to still running on the shared cold-start prior. Used by service.py to
    decide whether tabular_q is trusted for a given child."""
    return _blob_exists(f"{Q_TABLES_PREFIX}{child_id}.json")


def load_child_agent(child_id: str, **agent_kwargs) -> TabularQAgent:
    blob_name = f"{Q_TABLES_PREFIX}{child_id}.json"
    agent = TabularQAgent(**agent_kwargs)

    if _blob_exists(blob_name):
        agent.q_table = _load_q_table_blob(blob_name)
    elif _blob_exists(PRIOR_BLOB_NAME):
        agent.q_table = _load_q_table_blob(PRIOR_BLOB_NAME)

    return agent


def save_child_agent(child_id: str, agent: TabularQAgent):
    blob_name = f"{Q_TABLES_PREFIX}{child_id}.json"
    _save_q_table_blob(agent.q_table, blob_name)


def update_child_agent_from_transition(child_id: str, obs, action: int, reward: float,
                                        next_obs, done: bool) -> TabularQAgent:
    """
    The genuinely-online update path: call this once per real transition (once
    the frontend/backend logs attempts in this shape). No batch retraining
    involved — this is what makes the tabular rung different from the PPO
    rung's threshold-triggered retraining in retraining/scheduler.py.
    """
    agent = load_child_agent(child_id)
    agent.update(obs, action, reward, next_obs, done)
    save_child_agent(child_id, agent)
    return agent
