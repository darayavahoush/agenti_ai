from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
from pathlib import Path
from dotenv import load_dotenv

# Explicit path, not the bare load_dotenv() this used to be -- that
# searches from the CURRENT PROCESS's cwd, which silently breaks now
# that this module gets cross-imported from quest-games' backend (see
# the 2026-08-11 agenti_ai <-> quest-games merge). A bare load_dotenv()
# call from that context loaded QUEST-GAMES' .env into this process's
# os.environ instead, corrupting SECRET_KEY resolution anywhere else in
# the process that also reads os.environ (discovered via
# core/deps.py's therapist-token verification silently using the wrong
# secret). Always load this file's own .env, regardless of caller.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    pg_user = os.getenv("PGUSER") or "postgres"
    pg_password = os.getenv("PGPASSWORD") or ""
    pg_host = os.getenv("PGHOST") or "localhost"
    pg_port = os.getenv("PGPORT") or "5433"
    pg_database = os.getenv("PGDATABASE") or "postgres"
    DATABASE_URL = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

# The sync engine must use a regular psycopg2-compatible PostgreSQL URL,
# while the async engine needs the asyncpg driver. Reusing the same
# asyncpg URL for both creates the import-time `MissingGreenlet` crash
# seen when app.main connects during startup. Azure/.env values also use
# the asyncpg form (`ssl=require`), which psycopg2 rejects outright; convert
# that query flag to `sslmode=require` for the sync engine.
_sync_db_url = DATABASE_URL
if _sync_db_url.startswith("postgresql+asyncpg://"):
    _sync_db_url = _sync_db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
if "ssl=" in _sync_db_url:
    _sync_db_url = _sync_db_url.replace("ssl=", "sslmode=", 1)

_async_db_url = DATABASE_URL
if _async_db_url.startswith("postgresql://"):
    _async_db_url = _async_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_engine(
    _sync_db_url,
    pool_pre_ping=True
)

# Async engine for BreathQuest
async_engine = create_async_engine(
    _async_db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

# Async get_db for BreathQuest routers
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
