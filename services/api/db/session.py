"""Database session management — E02 Persistence.

Uses SQLAlchemy 2.x async engine when DATABASE_URL is configured;
falls back to a SQLite in-memory engine for local single-developer mode.

Engine/SessionLocal are LAZY and RESETTABLE so test modules can safely
change DATABASE_URL between test runs without cross-module pollution.
"""
from __future__ import annotations

import os
from collections.abc import Generator
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _sync_database_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "sqlite:///./advocate_chambers_local.db",
    )
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def get_engine() -> Engine:
    """Return the current engine, creating it lazily from env if needed."""
    global _engine
    if _engine is None:
        _build_engine_from_env()
    assert _engine is not None
    return _engine


def _build_engine_from_env() -> None:
    global _engine, _SessionLocal
    url = _sync_database_url()
    if "sqlite" in url:
        from sqlalchemy.pool import StaticPool
        pool_kwargs = {"poolclass": StaticPool}
        conn_args = {"check_same_thread": False}
    else:
        pool_kwargs = {"pool_pre_ping": True}
        conn_args = {}
    _engine = create_engine(url, connect_args=conn_args, **pool_kwargs)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_session_factory() -> sessionmaker:
    """Return the current SessionLocal, creating it lazily if needed."""
    global _SessionLocal
    if _SessionLocal is None:
        _build_engine_from_env()
    assert _SessionLocal is not None
    return _SessionLocal


def reset_session_singletons(dispose: bool = True) -> None:
    """Reset engine + SessionLocal so the next call re-reads DATABASE_URL.

    Used by test suites to eliminate cross-module ordering dependencies.
    """
    global _engine, _SessionLocal
    if dispose and _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine = None
    _SessionLocal = None


SessionLocal: sessionmaker  # type: ignore[assignment]
# Forward-compat alias — code that imports SessionLocal gets a lazy proxy.


def __getattr__(name: str):
    if name == "SessionLocal":
        return get_session_factory()
    if name == "engine":
        return get_engine()
    if name == "DATABASE_URL":
        return _sync_database_url()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session and closes it after the request."""
    factory = get_session_factory()
    session = factory()
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

    Base.metadata.create_all(bind=get_engine())
