"""Audit log helper.

``record`` only stages the row; the caller commits. That lets a successful
transfer and its audit entry share one transaction, so the log can never claim
a transfer happened that was actually rolled back.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    *,
    event_type: str,
    message: str = "",
    entity_type: str | None = None,
    entity_id: int | None = None,
    agent_id: int | None = None,
    actor: str = "system",
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        agent_id=agent_id,
        actor=actor,
        payload=payload or {},
    )
    db.add(entry)
    return entry


def list_recent(db: Session, *, limit: int = 100) -> list[AuditLog]:
    statement = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    return list(db.execute(statement).scalars())
