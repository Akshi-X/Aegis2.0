"""Cascade and sequence engine.

Interface only. Implemented in Phase 6.
"""

from __future__ import annotations

from app.services.engines.base import PlaceholderEngine


class CascadeService(PlaceholderEngine):
    name = "cascade"
    planned_phase = 6
    summary = (
        "Detects suspicious action sequences: transaction splitting, rapid repeated transfers, and sudden velocity changes."
    )
