"""Blast radius engine.

Interface only. Implemented in Phase 6.
"""

from __future__ import annotations

from app.services.engines.base import PlaceholderEngine


class BlastRadiusService(PlaceholderEngine):
    name = "blast_radius"
    planned_phase = 6
    summary = (
        "Estimates the damage if this action is wrong or malicious, from amount, account balance, remaining authority, and counterparty risk."
    )
