"""The contract every security engine implements.

Design note: a not-yet-implemented engine returns ``risk_score = None``, never
``0``. Zero is a *finding* -- it means "I looked and saw no risk". Null means "I
did not look". Conflating the two would let six unimplemented engines dilute a
genuine Authority failure of 100 down to a comfortable-looking 10, producing a
system that appears to work while assuring nothing. Risk fusion therefore
aggregates only engines that actually contributed, and every evaluation reports
its coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import ActionProposal, Agent, BankAccount, Counterparty


class EngineStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    # The engine exists as an interface but has no logic yet.
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    # The engine raised. Recorded, never silently swallowed.
    ERROR = "ERROR"


class EngineResult(BaseModel):
    """The single structure every engine returns."""

    engine: str
    status: EngineStatus
    # 0-100, or None when the engine did not produce a finding.
    risk_score: float | None = None
    flags: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    @property
    def contributes(self) -> bool:
        """Whether this result may participate in risk fusion."""
        return self.risk_score is not None

    @property
    def implemented(self) -> bool:
        return self.status is not EngineStatus.NOT_IMPLEMENTED


@dataclass
class EvaluationContext:
    """Everything an engine may read, assembled once by the orchestrator.

    Engines receive this rather than a database session alone so that the
    expensive lookups happen once, and so an engine's dependencies are visible
    in its signature rather than hidden behind ad-hoc queries.
    """

    db: Session
    proposal: ActionProposal
    # None when the proposal references an agent that no longer exists. The
    # Authority engine turns that into a BLOCK rather than the pipeline
    # erroring: an unattributable action should be refused, not left
    # unevaluated.
    agent: Agent | None
    now: datetime
    source_account: BankAccount | None = None
    counterparty: Counterparty | None = None
    # Results accumulated so far. Aggregation engines (fusion, trust,
    # governance) read this; signal engines must not.
    results: dict[str, EngineResult] = field(default_factory=dict)


@runtime_checkable
class SecurityEngine(Protocol):
    """Every engine, real or placeholder, satisfies exactly this."""

    name: str

    def evaluate(self, context: EvaluationContext) -> EngineResult: ...


class PlaceholderEngine:
    """Base for engines whose interface exists but whose logic does not.

    Deliberately returns a null risk score and a loud flag. It never invents a
    number -- a fabricated score is worse than an absent one, because it is
    indistinguishable from a real finding.
    """

    name: str = "placeholder"
    planned_phase: int = 0
    summary: str = ""

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        return EngineResult(
            engine=self.name,
            status=EngineStatus.NOT_IMPLEMENTED,
            risk_score=None,
            flags=["ENGINE_NOT_IMPLEMENTED"],
            details={
                "planned_phase": self.planned_phase,
                "summary": self.summary,
                "note": (
                    "No score produced. This engine is excluded from risk "
                    "fusion rather than contributing a neutral zero."
                ),
            },
        )
