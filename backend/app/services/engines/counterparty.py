"""Counterparty intelligence engine.

Interface only. Implemented in Phase 6.
"""

from __future__ import annotations

from app.services.engines.base import PlaceholderEngine


class CounterpartyService(PlaceholderEngine):
    name = "counterparty"
    planned_phase = 6
    summary = (
        "Graph analysis over the transaction network (NetworkX): fan-in, fan-out, rapid forwarding, and proximity to flagged nodes."
    )
