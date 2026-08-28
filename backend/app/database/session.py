"""Database engine and session management.

The engine is created lazily. The API must boot and serve /health even when
PostgreSQL is unreachable, so importing this module never opens a connection.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache
def get_engine() -> Engine:
    """Create (once) and return the SQLAlchemy engine."""
    url = settings.sqlalchemy_database_uri
    is_sqlite = url.startswith("sqlite")

    engine = create_engine(
        url,
        pool_pre_ping=True,
        echo=settings.debug and settings.environment == "development",
        future=True,
        # SQLite otherwise refuses connections reused across threads, which
        # FastAPI's threadpool does routinely.
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )

    if is_sqlite:
        # SQLite ignores foreign keys unless asked, per connection. Without
        # this, referential integrity silently differs between the test
        # database and the PostgreSQL target.
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database_connection() -> tuple[bool, str | None]:
    """Ping the database. Returns (ok, error_message).

    Used by the readiness probe; never raises.
    """
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # noqa: BLE001 - probe reports, never crashes
        return False, str(exc)
