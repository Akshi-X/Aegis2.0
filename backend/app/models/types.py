"""Shared column types.

Kept in one place so every model agrees on how money and structured data are
stored, and so no model has to import another purely for a type.
"""

from __future__ import annotations

from sqlalchemy import JSON, Numeric
from sqlalchemy.dialects.postgresql import JSONB

# Money is NUMERIC, never FLOAT. Binary floating point cannot represent decimal
# currency amounts exactly, and the error compounds across a ledger.
MoneyType = Numeric(18, 2, asdecimal=True)

# JSONB on PostgreSQL (indexable, the real target), plain JSON on SQLite.
PortableJSON = JSON().with_variant(JSONB, "postgresql")
