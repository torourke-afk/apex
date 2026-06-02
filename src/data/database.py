"""Database engine and session factory.

DATABASE_URL env var selects the backend:
  - DuckDB (dev):    duckdb:///./apex_dev.duckdb
  - PostgreSQL (prod): postgresql+psycopg2://user:pass@host/dbname
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_default_db = os.getenv("APEX_DB_PATH", "apex_clean.duckdb")
DATABASE_URL = os.getenv("DATABASE_URL", f"duckdb:///{_default_db}")

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
