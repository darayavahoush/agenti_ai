"""
tests/conftest.py -- shared pytest fixtures for the auth test suite.

Runs against a real Postgres database, not SQLite: several models use
Postgres-native types (PGUUID columns, see app/models/breathquest_models.py
and app/models/therapist.py), so SQLite would silently diverge from
production behavior on those columns rather than give a clean signal.

Point DATABASE_URL at a *disposable* database before running these --
never your real dev database, since the schema gets dropped and recreated
on every run. Use the plain postgresql:// form (not +asyncpg) -- app's own
database.py derives the async URL from this automatically.

One-time setup:
    createdb vaaksudhi_test

Run with:
    cd backend
    export DATABASE_URL="postgresql://postgres:password@localhost:5433/vaaksudhi_test"
    pytest

Import order below matters: app/main.py runs a raw, non-Alembic
`ALTER TABLE patients ADD COLUMN IF NOT EXISTS ...` at *module import
time* (see main.py's _ensure_patient_therapist_link_column and its
siblings) -- it assumes the table already exists. On a brand-new database
that's not true yet, so every model module (and Base.metadata.create_all)
must run BEFORE `app.main` gets imported, or that import crashes here
exactly like it would on a genuinely fresh production deploy that hasn't
run `alembic upgrade head` yet. That's a real gap in the app's own
startup sequence, not just a test-fixture quirk -- worth fixing in
main.py directly at some point (guard those _ensure_*_column() calls
with a `to_regclass`/table-exists check, or move them into an Alembic
migration instead of running at import time).
"""
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5433/vaaksudhi_test"
)

# --- import app.database (safe -- no import-time side effects) first ---
from app.database import Base, engine as sync_engine, get_db

# --- import every model module so Base.metadata knows about every table,
# BEFORE app.main runs its import-time ALTER TABLE calls ---
from app.models import (  # noqa: F401
    breathquest_models,
    patient,
    voicehurdlerace_models,
    flashcards_models,
    vaakmirror_models,
    therapist,
    session,
    retraining_models,
    assessment_word,
)

# Build the full schema against the test DB now, synchronously, so the
# tables _ensure_patient_therapist_link_column() (and friends) expect to
# find already exist by the time app.main is imported below.
Base.metadata.drop_all(bind=sync_engine)
Base.metadata.create_all(bind=sync_engine)

# NOW safe to import the app -- its import-time ALTER TABLE ... IF NOT
# EXISTS calls are no-ops against the schema we just created.
from app.main import app  # noqa: E402

_async_test_url = sync_engine.url.set(drivername="postgresql+asyncpg").render_as_string(
    hide_password=False
)
test_engine = create_async_engine(_async_test_url, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _teardown_schema():
    yield
    Base.metadata.drop_all(bind=sync_engine)


@pytest_asyncio.fixture
async def client():
    """httpx AsyncClient wired to the FastAPI app. get_db is overridden to
    point at the test database instead of the real one, but otherwise
    matches app.database.get_db exactly -- a fresh AsyncSession per
    request, its own connection from the pool -- rather than sharing one
    session/connection across every request in a test. Sharing a single
    asyncpg connection across sequential-but-independent requests hits
    "another operation is in progress" the moment two sessions touch it
    without careful savepoint nesting, so this is the simpler, more
    production-faithful option: every request gets what a real request
    gets.

    Tables are truncated after each test instead of relying on a rolled-
    back transaction, for the same reason -- no shared connection to roll
    back.
    """

    async def _get_db_override():
        async with TestSessionLocal() as session_:
            try:
                yield session_
                await session_.commit()
            except Exception:
                await session_.rollback()
                raise
            finally:
                await session_.close()

    app.dependency_overrides[get_db] = _get_db_override

    from app.breathquest_core import rate_limit
    rate_limit._ip_hits.clear()
    rate_limit._failed_attempts.clear()
    rate_limit._lockout_until.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)

    # Reset state for the next test -- TRUNCATE ... CASCADE is fast and
    # avoids FK-order headaches from DELETE-ing tables one at a time.
    table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with sync_engine.begin() as conn:
        from sqlalchemy import text
        conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
