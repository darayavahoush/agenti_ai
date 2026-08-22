import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Make `app.*` importable when alembic is invoked from backend/ (the
# normal case) -- prepend_sys_path = . in alembic.ini already covers
# this when alembic runs from backend/, but this guards against being
# invoked from elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import every model module BEFORE reading Base.metadata below, so
# autogenerate sees the full schema. Same reasoning as the
# noqa: F401-commented imports in app/main.py -- these imports exist
# purely for their side effect of registering tables with Base.
from app.database import Base, DATABASE_URL  # noqa: E402
from app.models import patient  # noqa: E402,F401
from app.models import session  # noqa: E402,F401
from app.models import assessment_word  # noqa: E402,F401
from app.models import breathquest_models  # noqa: E402,F401
from app.models import retraining_models  # noqa: E402,F401
from app.models import vaakmirror_models  # noqa: E402,F401
from app.models import therapist  # noqa: E402,F401
from app.models import voicehurdlerace_models  # noqa: E402,F401
from app.models import flashcards_models  # noqa: E402,F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override whatever's in alembic.ini (intentionally blank) with the
# real DATABASE_URL the app itself reads from backend/.env, so there's
# one source of truth for the connection string instead of two files
# that can drift apart. Alembic always migrates via the sync
# (psycopg2) URL, never the +asyncpg one -- migrations run outside the
# app's async request lifecycle, and Alembic's own driver support is
# built around sync DBAPI connections.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
