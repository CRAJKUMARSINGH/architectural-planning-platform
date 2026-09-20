"""Database session management — E02 Persistence.

Uses SQLAlchemy 2.x async engine when DATABASE_URL is configured;
falls back to a SQLite in-memory engine for local single-developer mode.
"""
from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./advocate_chambers_local.db",
)

# Convert asyncpg URL to sync psycopg for simplicity; swap for async in E04+
_sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")

engine = create_engine(
    _sync_url,
    pool_pre_ping=True,
    # SQLite-specific: allow same connection across threads in tests
    connect_args={"check_same_thread": False} if "sqlite" in _sync_url else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session and closes it after the request."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables() -> None:
    """Create all tables (for SQLite dev / test; production uses Alembic)."""
    from services.api.models.base import Base  # noqa: PLC0415

    Base.metadata.create_all(bind=engine)
