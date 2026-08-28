"""Behavioural anomaly engine.

Interface only. Implemented in Phase 4.
"""

from __future__ import annotations

from app.services.engines.base import PlaceholderEngine


class AnomalyService(PlaceholderEngine):
    name = "anomaly"
    planned_phase = 4
    summary = (
        "Isolation Forest inference over transaction features, with scores calibrated to a percentile rank against the training distribution."
    )
