"""ActionEvaluation: the immutable record of one pass through the pipeline.

One row per evaluation, holding every engine's raw output. Re-evaluating a
proposal writes a new row rather than overwriting -- an audit trail that can be
edited is not an audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.types import PortableJSON


def _new_evaluation_id() -> str:
    return f"ev_{uuid.uuid4().hex[:16]}"


class ActionEvaluation(Base):
    __tablename__ = "action_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evaluation_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=_new_evaluation_id
    )

    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("action_proposals.id"), index=True
    )
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)

    decision: Mapped[str] = mapped_column(String(16), index=True)
    decision_reason: Mapped[str] = mapped_column(Text, default="")
    # True when the decision rests on incomplete evidence, i.e. some engines
    # have not been implemented yet.
    provisional: Mapped[bool] = mapped_column(default=False)

    # None when no engine produced a score -- distinct from a score of zero.
    overall_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_score_at_evaluation: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Every engine's result, exactly as returned.
    engine_results: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)
    # Which engines contributed, which are stubs, and the fusion arithmetic.
    coverage: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)
    fusion_detail: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)
    top_factors: Mapped[list] = mapped_column(PortableJSON, default=list)

    engines_run: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    proposal = relationship("ActionProposal", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<ActionEvaluation {self.evaluation_id} {self.decision} "
            f"risk={self.overall_risk_score}>"
        )
