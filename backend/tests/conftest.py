"""Test fixtures.

Tests run against a throwaway SQLite file by default so the suite is hermetic
and needs no running services. Point TEST_DATABASE_URL at PostgreSQL to
exercise the real target:

    TEST_DATABASE_URL=postgresql+psycopg://aegis:aegis@localhost:5432/aegis_test pytest

The schema is created and dropped per test, so every test starts from the same
seeded state.
"""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# Configure the database URL before any application module reads settings.
TEST_DB_PATH = Path(__file__).parent / "test_aegis.db"
os.environ.setdefault("TEST_DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")
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

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    future=True,
)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


TestSessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


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
    """A fresh, seeded database for a single test."""
    Base.metadata.create_all(bind=engine)

    # The seeder resolves its own session factory from app settings, so point
    # that at the test engine for the duration.
    import app.database.seed as seed_module

    original_factory = seed_module.get_session_factory
    seed_module.get_session_factory = lambda: TestSessionFactory
    try:
        seed_module.seed_database(force=True)
    finally:
        seed_module.get_session_factory = original_factory

    session = TestSessionFactory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


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
