"""
app/retraining/data_store.py — Postgres-backed store for real session data
(RL training events). Ported from quest-games' retraining/data_store.py,
retargeted at agenti_ai's existing sync engine (app.database.SessionLocal)
instead of a separate retraining/db.py -- agenti_ai's database.py already
has a sync engine alongside its async one, so no second engine is needed
here the way quest-games needed (its async engine was asyncpg-only).

Deliberately still sync (not async def) -- callers are a mix of sync def
endpoints and async endpoints using asyncio.to_thread, and keeping this
sync means neither call style needs to change.
"""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import DATABASE_URL

# Small dedicated engine, separate from database.py's shared `engine` --
# this file's traffic (RL event logging, checkpoints) is low-volume and
# doesn't need to compete for headroom in the shared pool. Capped total
# of 5 connections (pool_size + max_overflow).
_retraining_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=3,
    connect_args={
        "options": "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=30000"
    },
)
RetrainingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_retraining_engine,
)
from app.models.retraining_models import RLTrainingEvent, RetrainCheckpoint

# Vestigial -- kept only because ported call sites (chime.py, breath_agent.py,
# dashboard.py, kid_progress.py) do `DB_PATH = data_store.DEFAULT_DB_PATH` at
# import time and pass it through as db_path=... on every call. All
# data_store functions here ignore db_path entirely -- it exists purely so
# those import-time references don't AttributeError.
DEFAULT_DB_PATH = None


def add_event(child_id, level_id: str, attempt_number: int, score: float,
              is_valid_attempt: bool, threshold_at_time: float = None, action: str = None,
              quit_flag: bool = False, raw_features: dict = None,
              severity_numeric: float = 0.0, is_targeted_sound: bool = False,
              policy_used: str = None, downgrade_reason: str = None,
              recommended_action: str = None, recommendation_message: str = None,
              db_path=None):
    with RetrainingSessionLocal() as session:
        event = RLTrainingEvent(
            child_id=child_id,
            timestamp=datetime.now(timezone.utc),
            level_id=level_id,
            attempt_number=attempt_number,
            score=score,
            is_valid_attempt=is_valid_attempt,
            threshold_at_time=threshold_at_time,
            action=action,
            quit_flag=quit_flag,
            raw_features=raw_features or {},
            severity_numeric=severity_numeric,
            is_targeted_sound=is_targeted_sound,
            policy_used=policy_used,
            downgrade_reason=downgrade_reason,
            recommended_action=recommended_action,
            recommendation_message=recommendation_message,
        )
        session.add(event)
        session.commit()


def get_events(child_id=None, since_id: int = None, db_path=None):
    with RetrainingSessionLocal() as session:
        query = select(RLTrainingEvent)
        if child_id is not None:
            query = query.where(RLTrainingEvent.child_id == child_id)
        if since_id is not None:
            query = query.where(RLTrainingEvent.id > since_id)
        query = query.order_by(RLTrainingEvent.id.asc())
        rows = session.execute(query).scalars().all()
        return [
            {c.name: getattr(r, c.name) for c in RLTrainingEvent.__table__.columns}
            for r in rows
        ]


def get_latest_decision(child_id, db_path=None):
    with RetrainingSessionLocal() as session:
        query = (
            select(RLTrainingEvent)
            .where(RLTrainingEvent.child_id == child_id)
            .where(RLTrainingEvent.recommended_action.isnot(None))
            .order_by(RLTrainingEvent.id.desc())
            .limit(1)
        )
        row = session.execute(query).scalars().first()
        if row is None:
            return None
        return {c.name: getattr(row, c.name) for c in RLTrainingEvent.__table__.columns}


def count_events(child_id=None, db_path=None) -> int:
    with RetrainingSessionLocal() as session:
        query = select(func.count()).select_from(RLTrainingEvent)
        if child_id is not None:
            query = query.where(RLTrainingEvent.child_id == child_id)
        return session.execute(query).scalar_one()


def count_events_since(child_ids: list, since_iso: str, db_path=None) -> int:
    if not child_ids:
        return 0
    since_dt = datetime.fromisoformat(since_iso)
    with RetrainingSessionLocal() as session:
        query = select(func.count()).select_from(RLTrainingEvent).where(
            RLTrainingEvent.timestamp >= since_dt,
            RLTrainingEvent.child_id.in_(child_ids),
        )
        return session.execute(query).scalar_one()


def last_event_time(child_id, db_path=None):
    with RetrainingSessionLocal() as session:
        query = select(func.max(RLTrainingEvent.timestamp)).where(
            RLTrainingEvent.child_id == child_id
        )
        result = session.execute(query).scalar_one_or_none()
        if result is None:
            return None
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def get_checkpoint(scope: str, db_path=None):
    with RetrainingSessionLocal() as session:
        query = select(RetrainCheckpoint).where(RetrainCheckpoint.scope == scope)
        row = session.execute(query).scalar_one_or_none()
        if row is None:
            return None
        return {
            "scope": row.scope,
            "last_retrained_at": row.last_retrained_at.isoformat(),
            "event_count_at_checkpoint": row.event_count_at_checkpoint,
        }


def set_checkpoint(scope: str, event_count: int, db_path=None):
    with RetrainingSessionLocal() as session:
        stmt = pg_insert(RetrainCheckpoint).values(
            scope=scope,
            last_retrained_at=datetime.now(timezone.utc),
            event_count_at_checkpoint=event_count,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["scope"],
            set_={
                "last_retrained_at": stmt.excluded.last_retrained_at,
                "event_count_at_checkpoint": stmt.excluded.event_count_at_checkpoint,
            },
        )
        session.execute(stmt)
        session.commit()
