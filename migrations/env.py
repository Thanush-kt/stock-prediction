"""Alembic environment — reads DATABASE_URL from .env / Settings, uses shared Base metadata."""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Ensure project root directory is in sys.path so packages.* imports succeed
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Explicitly load .env from project root
dotenv_path = ROOT_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=False)

from packages.shared.models import Base

# Alembic Config object, which provides access to the values within alembic.ini
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve target metadata for autogenerate support
target_metadata = Base.metadata


def get_database_url() -> str:
    """Retrieve and normalize database connection URL from .env, environment, or settings."""
    # 1. Environment variable (loaded from .env above or system env)
    url = os.getenv("DATABASE_URL")

    # 2. Pydantic application settings fallback
    if not url:
        try:
            from packages.shared.config import get_settings
            url = get_settings().database_url
        except Exception:
            pass

    # 3. Fallback to alembic.ini option
    if not url:
        url = config.get_main_option("sqlalchemy.url") or ""

    # Normalize driver prefix for psycopg 3 compatibility
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


# Populate sqlalchemy.url in config so both offline and online modes pick it up
resolved_url = get_database_url()
if resolved_url:
    config.set_main_option("sqlalchemy.url", resolved_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine.
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

    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
