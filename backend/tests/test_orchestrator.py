"""Orchestrator and engine tests.

The properties that matter most here are architectural rather than numeric:
placeholders must not be scored as harmless, a crashing engine must not take
down an evaluation, and nothing may execute as a side effect of deciding.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ActionEvaluation,
    ActionProposal,
    Agent,
    AgentStatus,
    AuditLog,
    BankAccount,
    Transaction,
)
from app.services.engines import EngineResult, EngineStatus
from app.services.engines.risk_fusion import fuse
from app.services.engines.trust import autonomy_tier
from app.services.orchestrator import AegisOrchestrator

NORMAL_TASK = "Pay ₹50,000 to ABC Technologies for invoice INV-204"
OVER_LIMIT_TASK = "Transfer ₹15,00,000 to XYZ Cloud for infrastructure renewal"


def propose(client: TestClient, task: str = NORMAL_TASK) -> str:
    response = client.post("/agent/task", json={"agent_id": 1, "task": task})
    assert response.status_code == 201, response.text
    return response.json()["proposal"]["action_id"]


def evaluate(client: TestClient, action_id: str):
    response = client.post(f"/actions/{action_id}/evaluate")
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# Pipeline shape
# --------------------------------------------------------------------------- #

def test_all_ten_engines_run(client: TestClient) -> None:
    body = evaluate(client, propose(client))
    results = body["evaluation"]["engine_results"]

    assert set(results) == {
        "authority",
        "intent",
        "financial_dna",
        "anomaly",
        "cascade",
        "counterparty",
        "blast_radius",
        "risk_fusion",
        "trust",
        "governance",
    }
    assert body["evaluation"]["engines_run"] == 10


def test_every_engine_returns_the_standard_structure(client: TestClient) -> None:
    results = evaluate(client, propose(client))["evaluation"]["engine_results"]

    for name, result in results.items():
        assert set(result) == {"engine", "status", "risk_score", "flags", "details"}
        assert result["engine"] == name
        assert isinstance(result["flags"], list)
        assert isinstance(result["details"], dict)


def test_placeholders_return_null_not_zero(client: TestClient) -> None:
    """The load-bearing property of this phase.

    A placeholder scoring 0 would be indistinguishable from an engine that
    looked and found nothing, letting six stubs dilute a real finding.
    """
    results = evaluate(client, propose(client))["evaluation"]["engine_results"]

    for name in ("blast_radius",):
        assert results[name]["status"] == "NOT_IMPLEMENTED"
        assert results[name]["risk_score"] is None, f"{name} invented a score"
        assert "ENGINE_NOT_IMPLEMENTED" in results[name]["flags"]


def test_coverage_is_reported_honestly(client: TestClient) -> None:
    coverage = evaluate(client, propose(client))["evaluation"]["coverage"]

    assert coverage["complete"] is False
    assert set(coverage["not_implemented"]) == {"blast_radius"}
    assert "authority" in coverage["implemented"]
    assert "financial_dna" in coverage["implemented"]
    assert "intent" in coverage["implemented"]
    assert "anomaly" in coverage["implemented"]
    assert "counterparty" in coverage["implemented"]
    assert "cascade" in coverage["implemented"]
    assert coverage["errored"] == []


# --------------------------------------------------------------------------- #
# Authority engine (the only real signal engine)
# --------------------------------------------------------------------------- #

def test_authority_passes_a_compliant_payment(client: TestClient) -> None:
    authority = evaluate(client, propose(client))["evaluation"]["engine_results"][
        "authority"
    ]

    assert authority["status"] == "PASS"
    assert authority["risk_score"] == 0
    assert authority["flags"] == []
    assert authority["details"]["daily_spend_before"] == "0.00"


def test_authority_fails_when_over_the_transaction_limit(client: TestClient) -> None:
    body = evaluate(client, propose(client, OVER_LIMIT_TASK))
    authority = body["evaluation"]["engine_results"]["authority"]

    # 1,500,000 against a 100,000 limit.
    assert authority["status"] == "FAIL"
    assert "TRANSACTION_LIMIT_EXCEEDED" in authority["flags"]
    # Sourced from policy.authority.risk_scores, not hardcoded in the engine.
    assert authority["risk_score"] == 85.0
    assert authority["details"]["limit_exceeded_by"] == "1400000.00"


def test_authority_flags_approaching_the_limit(client: TestClient) -> None:
    # 85,000 is 85% of the 100,000 limit.
    authority = evaluate(
        client, propose(client, "Pay ₹85,000 to ABC Technologies for invoice INV-9")
    )["evaluation"]["engine_results"]["authority"]

    assert authority["status"] == "WARN"
    assert "APPROACHING_TRANSACTION_LIMIT" in authority["flags"]


def test_authority_rejects_a_suspended_agent(
    client: TestClient, db: Session
) -> None:
    action_id = propose(client)

    agent = db.get(Agent, 1)
    agent.status = AgentStatus.SUSPENDED
    db.commit()

    authority = evaluate(client, action_id)["evaluation"]["engine_results"]["authority"]
    assert authority["status"] == "FAIL"
    assert "AGENT_SUSPENDED" in authority["flags"]
    assert authority["risk_score"] == 100.0


def test_authority_uses_max_not_sum_of_violations(
    client: TestClient, db: Session
) -> None:
    """Three violations must not out-score one disqualifying breach."""
    action_id = propose(client, OVER_LIMIT_TASK)

    agent = db.get(Agent, 1)
    agent.status = AgentStatus.SUSPENDED
    agent.allowed_currencies = ["USD"]
    db.commit()

    authority = evaluate(client, action_id)["evaluation"]["engine_results"]["authority"]
    assert authority["details"]["violation_count"] >= 3
    # Capped at the single worst violation, never summed past 100.
    assert authority["risk_score"] == 100.0


def test_authority_counts_daily_spend_from_executed_transactions(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    action_id = propose(client)
    proposal = db.execute(select(ActionProposal)).scalars().first()

    # An executed transfer attributed to this agent's proposal.
    db.add(
        Transaction(
            source_account_id=accounts["company"].id,
            destination_account_id=accounts["abc"].id,
            amount=Decimal("450000.00"),
            currency="INR",
            status="COMPLETED",
            proposal_id=proposal.id,
        )
    )
    db.commit()

    authority = evaluate(client, action_id)["evaluation"]["engine_results"]["authority"]

    assert authority["details"]["daily_spend_before"] == "450000.00"
    # 450,000 already spent + 50,000 proposed = 500,000, exactly the daily
    # limit, so it is flagged as approaching but not exceeded.
    assert "DAILY_LIMIT_EXCEEDED" not in authority["flags"]
    assert "APPROACHING_DAILY_LIMIT" in authority["flags"]


# --------------------------------------------------------------------------- #
# Risk fusion (pure function, tested directly)
# --------------------------------------------------------------------------- #

def _result(name: str, score: float | None) -> EngineResult:
    return EngineResult(
        engine=name,
        status=EngineStatus.PASS if score is not None else EngineStatus.NOT_IMPLEMENTED,
        risk_score=score,
    )


def test_fusion_excludes_non_contributing_engines() -> None:
    score, detail = fuse(
        {
            "authority": _result("authority", 100.0),
            "intent": _result("intent", None),
            "anomaly": _result("anomaly", None),
        }
    )

    # Authority is the only contributor, so it fully determines the score
    # rather than being averaged against absent engines.
    assert score == 100.0
    assert detail["contributing_engines"] == ["authority"]
    assert detail["weight_renormalised"] is True


def test_fusion_would_dilute_without_renormalisation() -> None:
    """Guards the exact bug this design avoids.

    Authority's raw group weight is 0.25. Without renormalising, a lone
    finding of 100 would fuse to 25 and look survivable.
    """
    score, _ = fuse({"authority": _result("authority", 100.0)})
    assert score == 100.0
    assert score != 25.0


def test_correlated_engines_combine_by_max_not_sum() -> None:
    """Financial DNA and the anomaly model read overlapping features, so
    stacking them would double-count one behavioural signal."""
    score, detail = fuse(
        {
            "financial_dna": _result("financial_dna", 80.0),
            "anomaly": _result("anomaly", 60.0),
        }
    )

    assert score == 80.0
    behavioural = detail["group_contributions"]["behavioural"]
    assert behavioural["score"] == 80.0
    assert sorted(behavioural["engines"]) == ["anomaly", "financial_dna"]


def test_fusion_weights_groups_when_several_contribute() -> None:
    score, _ = fuse(
        {
            "authority": _result("authority", 100.0),   # group weight 0.25
            "intent": _result("intent", 0.0),            # group weight 0.15
        }
    )
    # (0.25*100 + 0.15*0) / 0.40 = 62.5
    assert score == 62.5


def test_fusion_returns_none_when_nothing_contributed() -> None:
    score, detail = fuse({"intent": _result("intent", None)})
    assert score is None
    assert detail["coverage_ratio"] == 0.0


# --------------------------------------------------------------------------- #
# Trust
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    ("score", "tier"),
    [
        (95.0, "HIGH_AUTONOMY"),
        (85.0, "NORMAL_AUTONOMY"),
        (60.0, "CONSTRAINED"),
        (40.0, "HIGH_MONITORING"),
        (10.0, "SUSPENDED"),
    ],
)
def test_autonomy_tiers(score: float, tier: str) -> None:
    assert autonomy_tier(score) == tier


def test_trust_reports_but_does_not_score(client: TestClient) -> None:
    trust = evaluate(client, propose(client))["evaluation"]["engine_results"]["trust"]

    assert trust["details"]["trust_score"] == 85.0
    assert trust["details"]["autonomy_tier"] == "NORMAL_AUTONOMY"
    # Trust modulates thresholds; it is not summed into risk.
    assert trust["risk_score"] is None


# --------------------------------------------------------------------------- #
# Governance
# --------------------------------------------------------------------------- #

def test_governance_blocks_on_authority_failure(client: TestClient) -> None:
    body = evaluate(client, propose(client, OVER_LIMIT_TASK))

    assert body["evaluation"]["decision"] == "BLOCK"
    assert "AUTHORITY_FAILURE" in body["evaluation"]["engine_results"]["governance"]["flags"]
    # A refusal is fully justified by one engine, so it is not provisional.
    assert body["evaluation"]["provisional"] is False


def test_governance_never_executes_under_partial_coverage(client: TestClient) -> None:
    """Fail-safe: refusing needs one engine, authorising needs all of them."""
    body = evaluate(client, propose(client))
    evaluation = body["evaluation"]

    assert evaluation["engine_results"]["authority"]["status"] == "PASS"
    assert evaluation["decision"] == "ESCALATE"
    assert evaluation["decision"] != "EXECUTE"
    assert evaluation["provisional"] is True
    assert "INSUFFICIENT_ENGINE_COVERAGE" in evaluation["engine_results"]["governance"]["flags"]


def test_governance_can_execute_once_coverage_is_complete(db: Session) -> None:
    """The EXECUTE path is written and works; it is gated, not missing."""
    from app.services.engines.governance import GovernanceService
    from app.services.engines.base import EvaluationContext
    from datetime import datetime, timezone

    results = {
        name: _result(name, 5.0)
        for name in (
            "authority", "anomaly",
            "cascade", "counterparty", "blast_radius", "financial_dna", "intent"
        )
    }
    results["risk_fusion"] = _result("risk_fusion", 5.0)
    results["trust"] = EngineResult(
        engine="trust",
        status=EngineStatus.PASS,
        details={"autonomy_tier": "HIGH_AUTONOMY", "trust_score": 95.0},
    )

    agent = db.get(Agent, 1)
    proposal = ActionProposal(agent_id=agent.id, amount=Decimal("1.00"))
    context = EvaluationContext(
        db=db,
        proposal=proposal,
        agent=agent,
        now=datetime.now(timezone.utc),
        results=results,
    )

    outcome = GovernanceService().evaluate(context)
    assert outcome.details["decision"] == "EXECUTE"
    assert outcome.details["provisional"] is False


# --------------------------------------------------------------------------- #
# Robustness and side effects
# --------------------------------------------------------------------------- #

def test_a_crashing_engine_does_not_break_the_evaluation(
    client: TestClient, db: Session, monkeypatch
) -> None:
    class ExplodingEngine:
        name = "intent"

        def evaluate(self, context):
            raise RuntimeError("model provider exploded")

    from app.services import orchestrator as orchestrator_module

    original = orchestrator_module.SIGNAL_ENGINES
    patched = [e for e in original if e.name != "intent"] + [ExplodingEngine()]
    monkeypatch.setattr(orchestrator_module, "SIGNAL_ENGINES", patched)

    action_id = propose(client)
    # A fresh orchestrator picks up the patched registry.
    body = evaluate(client, action_id)

    intent = body["evaluation"]["engine_results"]["intent"]
    assert intent["status"] == "ERROR"
    assert intent["risk_score"] is None  # errors are not scored as harmless
    assert "model provider exploded" in intent["details"]["error"]
    assert body["evaluation"]["coverage"]["errored"] == ["intent"]


def test_evaluation_moves_the_proposal_to_evaluated(
    client: TestClient, db: Session
) -> None:
    action_id = propose(client)
    assert client.get(f"/actions/{action_id}").json()["status"] == "PROPOSED"

    evaluate(client, action_id)
    assert client.get(f"/actions/{action_id}").json()["status"] == "EVALUATED"


def test_evaluation_moves_no_money(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    before = {a.id: a.balance for a in db.execute(select(BankAccount)).scalars()}

    for task in (NORMAL_TASK, OVER_LIMIT_TASK):
        evaluate(client, propose(client, task))

    db.expire_all()
    assert db.execute(select(func.count()).select_from(Transaction)).scalar_one() == 0
    for account in db.execute(select(BankAccount)).scalars():
        assert account.balance == before[account.id]


def test_re_evaluation_appends_rather_than_overwrites(client: TestClient) -> None:
    action_id = propose(client)

    first = evaluate(client, action_id)["evaluation"]["evaluation_id"]
    second = evaluate(client, action_id)["evaluation"]["evaluation_id"]
    assert first != second

    history = client.get(f"/actions/{action_id}/evaluations").json()
    assert len(history) == 2
    assert [h["evaluation_id"] for h in history] == [second, first]


def test_evaluation_is_audited(client: TestClient, db: Session) -> None:
    evaluate(client, propose(client))

    db.expire_all()
    entry = db.execute(
        select(AuditLog).where(AuditLog.event_type == "PROPOSAL_EVALUATED")
    ).scalar_one()
    assert entry.payload["decision"] == "ESCALATE"
    assert entry.payload["engines_run"] == 10


def test_evaluation_is_persisted(client: TestClient, db: Session) -> None:
    evaluate(client, propose(client))

    db.expire_all()
    stored = db.execute(select(ActionEvaluation)).scalar_one()
    assert stored.decision == "ESCALATE"
    assert stored.engines_run == 10
    assert stored.latency_ms > 0
    assert stored.coverage["complete"] is False


def test_evaluating_an_unknown_action_returns_404(client: TestClient) -> None:
    response = client.post("/actions/act_nope/evaluate")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "action_not_found"
