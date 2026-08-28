"""Schema creation and first-run seeding.

Phase 1 uses ``Base.metadata.create_all`` rather than Alembic migrations. That
is a deliberate trade-off: the schema is still moving every phase, and
hand-maintaining migrations against a moving target costs more than it returns.
Alembic is already a dependency, so the switch is a single ``alembic init``
once the schema settles.
"""

from __future__ import annotations

import logging

from app.database.base import Base
from app.database.session import get_engine

# Importing the models package is what registers every table on
# Base.metadata. Without it create_all would produce an empty schema.
import app.models  # noqa: F401  (side-effect import)

logger = logging.getLogger(__name__)


def create_tables() -> None:
    """Create any missing tables. Idempotent; never drops or alters."""
    Base.metadata.create_all(bind=get_engine())
    logger.info("Database schema ensured (%d tables)", len(Base.metadata.tables))


def drop_tables() -> None:
    """Drop every table. Destructive -- used by tests and `seed --reset`."""
    Base.metadata.drop_all(bind=get_engine())
    logger.warning("Database schema dropped")


def init_db(*, seed: bool = True) -> None:
    from app.database.seed import seed_database

    create_tables()
    if seed:
        seed_database()
