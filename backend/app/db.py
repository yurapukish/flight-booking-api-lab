"""Database connection module: engine, session factory, and health check."""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://flightuser:flightpass@db:5432/flightdb"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
"""SQLAlchemy engine: connection pool to PostgreSQL."""

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
"""Session factory. Use `db = SessionLocal()` per request, then `db.close()`."""


def check_db() -> bool:
    """Ping the database with `SELECT 1`. Returns True if reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False