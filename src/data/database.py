"""Database engine and session factory.

DATABASE_URL env var selects the backend:
  - DuckDB (dev):    duckdb:///./apex_dev.duckdb
  - PostgreSQL (prod): postgresql+psycopg2://user:pass@host/dbname

NOTE: The BFF data-layer modules (scorecard_queries, spend_queries, etc.)
open their own raw DuckDB connections with read_only=True.  This module is
only used by the legacy Streamlit app.  To avoid holding a persistent
write-lock that blocks those read-only connections, we defer engine
creation until someone actually asks for a session.
"""

import os

from dotenv import load_dotenv

load_dotenv()

_default_db = os.getenv("APEX_DB_PATH", "apex_clean.duckdb")
DATABASE_URL = os.getenv("DATABASE_URL", f"duckdb:///{_default_db}")

# Lazy engine — created only when get_session() is first called.
# This prevents holding a persistent DuckDB write-lock at import time.
_engine = None
_SessionLocal = None


def _init_engine():
    global _engine, _SessionLocal
    if _engine is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        _engine = create_engine(DATABASE_URL, echo=False)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


@property
def _lazy_engine(self):
    """Accessed via the module-level `engine` attribute (see __getattr__)."""
    _init_engine()
    return _engine


def __getattr__(name: str):
    """Lazy module-level attribute: `from src.data.database import engine`
    now creates the engine on first access instead of at import time."""
    if name == "engine":
        _init_engine()
        return _engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_session():
    _init_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
