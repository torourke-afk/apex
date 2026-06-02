"""Alembic env.py — supports DuckDB (dev) and PostgreSQL (prod) via DATABASE_URL."""

import os
import sys
from logging.config import fileConfig

from alembic import context
from alembic.ddl.impl import DefaultImpl
from sqlalchemy import engine_from_config, pool

# Register a DuckDB DDL implementation so Alembic's migration context works.
# duckdb_engine provides the SQLAlchemy dialect but not the Alembic DDL impl.
class DuckDBImpl(DefaultImpl):
    __dialect__ = "duckdb"


# Ensure project root is on sys.path so src.data.orm is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.data.orm import Base  # noqa: E402 — import after path fix

# Alembic Config object (gives access to alembic.ini values).
config = context.config

# Override sqlalchemy.url from DATABASE_URL env var if present.
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
