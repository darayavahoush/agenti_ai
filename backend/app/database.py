from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    pg_user = os.getenv("PGUSER") or "postgres"
    pg_password = os.getenv("PGPASSWORD") or ""
    pg_host = os.getenv("PGHOST") or "localhost"
    pg_port = os.getenv("PGPORT") or "5432"
    pg_database = os.getenv("PGDATABASE") or "postgres"
    DATABASE_URL = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()