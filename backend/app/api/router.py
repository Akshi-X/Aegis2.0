"""Aggregates every API router.

Health probes, the bank simulator, and the autonomous agent sit at the service
root. The AEGIS-X evaluation and governance routes arrive in later phases.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import accounts, actions, agent, bank, health, policy

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(accounts.router)
api_router.include_router(bank.router)
api_router.include_router(agent.router)
api_router.include_router(actions.router)
api_router.include_router(policy.router)
