"""Test fixtures.

Each test gets its own **in-memory** SQLite database, created and destroyed
with the test. That makes isolation structural rather than dependent on a
teardown succeeding: an earlier version shared one SQLite *file* and relied on
``drop_all`` to clean up, so any test that left a connection open leaked its
tables into the next test and produced UNIQUE-constraint cascades. The suite
passed or failed depending on ordering and timing.

``StaticPool`` is what makes an in-memory database usable here -- it keeps a
single connection for the engine's lifetime, so every session (including the
ones FastAPI's threadpool opens) sees the same database.

Point TEST_DATABASE_URL at PostgreSQL to exercise the real target instead:

    TEST_DATABASE_URL=postgresql+psycopg://aegis:aegis@localhost:5432/aegis_test pytest
"""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Configure the database URL before any application module reads settings.
os.environ.setdefault("TEST_DATABASE_URL", "sqlite://")  # in-memory
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["AUTO_INIT_DB"] = "false"  # fixtures own schema lifecycle
os.environ["DEBUG"] = "false"

# SQLite cannot store Decimal natively, so SQLAlchemy warns that it round-trips
# through float. Irrelevant here (PostgreSQL is the real target and stores
# NUMERIC exactly) and it drowns the test output.
warnings.filterwarnings("ignore", r".*support Decimal objects natively.*")

from app.database.base import Base  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import BankAccount  # noqa: E402

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
_is_sqlite = TEST_DATABASE_URL.startswith("sqlite")


def _build_engine() -> Engine:
    """A brand-new engine, and therefore a brand-new database, per test."""
    if _is_sqlite:
        engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            # One connection for the engine's lifetime, so the in-memory
            # database survives between sessions instead of vanishing when the
            # first connection is returned to the pool.
            poolclass=StaticPool,
            future=True,
        )

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
            # Without this SQLite ignores foreign keys, so referential
            # integrity would differ between tests and the PostgreSQL target.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    return create_engine(TEST_DATABASE_URL, future=True)


@pytest.fixture(autouse=True)
def _isolate_policy_cache() -> Iterator[None]:
    """Stop policy state leaking between tests.

    ``get_policy`` is lru_cached, so a test that points the loader at a
    temporary policy file would otherwise leave that policy cached for every
    test that follows.
    """
    from app.core.policy import get_policy

    get_policy.cache_clear()
    yield
    get_policy.cache_clear()


@pytest.fixture
def db() -> Iterator[Session]:
    """A fresh, seeded database for a single test.

    The engine is built and disposed per test, so cleanup cannot fail: the
    database ceases to exist with the connection rather than being emptied by
    a teardown that a lingering transaction could block.
    """
    engine = _build_engine()
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )

    # The seeder resolves its own session factory from app settings, so point
    # that at the test engine for the duration.
    import app.database.seed as seed_module

    original_factory = seed_module.get_session_factory
    seed_module.get_session_factory = lambda: session_factory
    try:
        seed_module.seed_database(force=True)
    finally:
        seed_module.get_session_factory = original_factory

    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        if not _is_sqlite:
            # A real database outlives the engine, so it does need emptying.
            Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """API client bound to the same session the test can inspect."""

    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def accounts(db: Session) -> dict[str, BankAccount]:
    """Seeded accounts keyed by a short, readable name."""
    rows = db.query(BankAccount).order_by(BankAccount.id).all()
    by_number = {row.account_number: row for row in rows}
    return {
        "company": by_number["ACC1000000001"],
        "abc": by_number["ACC2000000001"],
        "xyz": by_number["ACC2000000002"],
        "unknown": by_number["ACC9000000001"],
    }
