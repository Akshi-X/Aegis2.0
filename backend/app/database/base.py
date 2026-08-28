"""Declarative base for ORM models.

Models are introduced in a later phase; they will subclass ``Base`` and be
imported here so Alembic autogenerate can discover them.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common base class for all AEGIS-X ORM models."""
