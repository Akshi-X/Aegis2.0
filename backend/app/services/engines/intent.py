"""Intent alignment engine.

Interface only. Implemented in Phase 5.
"""

from __future__ import annotations

from app.services.engines.base import PlaceholderEngine


class IntentService(PlaceholderEngine):
    name = "intent"
    planned_phase = 5
    summary = (
        "Compares the proposed action against the agent's assigned objective, scoring semantic alignment."
    )
