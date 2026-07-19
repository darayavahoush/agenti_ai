from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    pg_user = os.getenv("PGUSER") or "postgres"
    pg_password = os.getenv("PGPASSWORD") or ""
    pg_host = os.getenv("PGHOST") or "localhost"
    pg_port = os.getenv("PGPORT") or "5433"
    pg_database = os.getenv("PGDATABASE") or "postgres"
    DATABASE_URL = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

# Convert to async URL for BreathQuest
_async_db_url = DATABASE_URL
if _async_db_url.startswith("postgresql://"):
    _async_db_url = _async_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_engine(
    DATABASE_URL,
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
