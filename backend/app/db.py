"""Database connection module: engine, session factory, and health check."""

import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://flightuser:flightpass@db:5432/flightdb"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
"""SQLAlchemy engine: connection pool to PostgreSQL."""

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
"""Session factory. Use `db = SessionLocal()` per request, then `db.close()`."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: видає сесію БД і гарантовано закриває її після запиту.

    Використання в ендпойнті:
        def endpoint(db: Session = Depends(get_db)): ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db() -> bool:
    """Ping the database with `SELECT 1`. Returns True if reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False



"""
Host:     localhost
Port:     5432
Database: flightdb
User:     flightuser
Password: flightpass"""
