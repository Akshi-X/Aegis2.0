"""Security engines.

Every engine -- implemented or not -- satisfies the ``SecurityEngine`` protocol
and returns an ``EngineResult``. Replacing a placeholder with real logic is
therefore a single-file change that the orchestrator and the API never see.

Engines run in two tiers:

* **Signal engines** produce independent risk findings and must not read each
  other's results.
* **Aggregation engines** (fusion, trust, governance) consume what the signal
  engines produced, and run afterwards in a fixed order.
"""

from app.services.engines.anomaly import AnomalyService
from app.services.engines.authority import AuthorityService
from app.services.engines.base import (
    EngineResult,
    EngineStatus,
    EvaluationContext,
    PlaceholderEngine,
    SecurityEngine,
)
from app.services.engines.blast_radius import BlastRadiusService
from app.services.engines.cascade import CascadeService
from app.services.engines.counterparty import CounterpartyService
from app.services.engines.financial_dna import FinancialDNAService
from app.services.engines.governance import GovernanceService
from app.services.engines.intent import IntentService
from app.services.engines.risk_fusion import RiskFusionService
from app.services.engines.trust import TrustService

__all__ = [
    "AnomalyService",
    "AuthorityService",
    "BlastRadiusService",
    "CascadeService",
    "CounterpartyService",
    "EngineResult",
    "EngineStatus",
    "EvaluationContext",
    "FinancialDNAService",
    "GovernanceService",
    "IntentService",
    "PlaceholderEngine",
    "RiskFusionService",
    "SecurityEngine",
    "TrustService",
]
