from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql://{os.getenv('PGUSER')}:"
    f"{os.getenv('PGPASSWORD')}@"
    f"{os.getenv('PGHOST')}:"
    f"{os.getenv('PGPORT')}/"
    f"{os.getenv('PGDATABASE')}"
)

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