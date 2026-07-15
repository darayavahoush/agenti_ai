from sqlalchemy import create_engine, inspect, text
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

def ensure_database_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if not inspector.has_table("assessment_words"):
        return
    columns = {column["name"] for column in inspector.get_columns("assessment_words")}
    if "word_key" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE assessment_words ADD COLUMN word_key VARCHAR(120)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_assessment_words_word_key ON assessment_words (word_key)"))
