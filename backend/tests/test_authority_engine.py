"""Authority engine and policy configuration tests.

The five scenarios the phase requires, plus the property that makes the policy
system worth having: changing a threshold in the policy file must change the
decision, with no code edit.
"""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.policy import (
    DEFAULT_POLICY_PATH,
    Policy,
    PolicyError,
    get_policy,
    load_policy,
    reload_policy,
)
from app.models import (
    ActionProposal,
    Agent,
    AgentStatus,
    BankAccount,
    Transaction,
)
from app.services.engines.authority import AuthorityService, authorized_account_ids
from app.services.engines.base import EvaluationContext

NORMAL_TASK = "Pay ₹50,000 to ABC Technologies for invoice INV-204"


def propose(client: TestClient, task: str = NORMAL_TASK) -> str:
    response = client.post("/agent/task", json={"agent_id": 1, "task": task})
    assert response.status_code == 201, response.text
    return response.json()["proposal"]["action_id"]


def authority_of(client: TestClient, action_id: str) -> dict:
    response = client.post(f"/actions/{action_id}/evaluate")
    assert response.status_code == 201, response.text
    return response.json()["evaluation"]["engine_results"]["authority"]


def decision_of(client: TestClient, action_id: str) -> str:
    response = client.post(f"/actions/{action_id}/evaluate")
    assert response.status_code == 201, response.text
    return response.json()["evaluation"]["decision"]


# --------------------------------------------------------------------------- #
# 1. Valid payment
# --------------------------------------------------------------------------- #

def test_valid_payment_passes(client: TestClient) -> None:
    authority = authority_of(client, propose(client))

    assert authority["status"] == "PASS"
    assert authority["risk_score"] == 0
    assert authority["flags"] == []

    details = authority["details"]
    assert details["agent_exists"] is True
    assert details["agent_status"] == "ACTIVE"
    assert details["requested_amount"] == "50000.00"
    assert details["max_limit"] == "100000.00"
    assert details["requested_currency"] == "INR"
    assert details["allowed_currencies"] == ["INR"]
    assert details["daily_spend_before"] == "0.00"
    assert details["violation_count"] == 0


# --------------------------------------------------------------------------- #
# 2. Amount above transaction limit
# --------------------------------------------------------------------------- #

def test_amount_above_transaction_limit(client: TestClient) -> None:
    authority = authority_of(
        client, propose(client, "Pay ₹5,00,000 to ABC Technologies for invoice INV-9")
    )

    assert authority["status"] == "FAIL"
    assert "TRANSACTION_LIMIT_EXCEEDED" in authority["flags"]
    # Sourced from policy.authority.risk_scores.transaction_limit_exceeded.
    assert authority["risk_score"] == 85

    details = authority["details"]
    assert details["requested_amount"] == "500000.00"
    assert details["max_limit"] == "100000.00"
    assert details["limit_exceeded_by"] == "400000.00"
    assert details["limit_multiple"] == 5.0


def test_over_limit_payment_is_blocked(client: TestClient) -> None:
    assert decision_of(
        client, propose(client, "Pay ₹5,00,000 to ABC Technologies for invoice INV-9")
    ) == "BLOCK"


# --------------------------------------------------------------------------- #
# 3. Daily limit exceeded
# --------------------------------------------------------------------------- #

def test_daily_limit_exceeded(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    action_id = propose(client)
    proposal = db.execute(select(ActionProposal)).scalars().first()

    # 480,000 already executed today against a 500,000 daily limit, so the
    # 50,000 proposal projects to 530,000 while staying under the 100,000
    # per-transaction limit. Only the daily rule should fire.
    db.add(
        Transaction(
            source_account_id=accounts["company"].id,
            destination_account_id=accounts["abc"].id,
            amount=Decimal("480000.00"),
            currency="INR",
            status="COMPLETED",
            proposal_id=proposal.id,
        )
    )
    db.commit()

    authority = authority_of(client, action_id)

    assert authority["status"] == "FAIL"
    assert "DAILY_LIMIT_EXCEEDED" in authority["flags"]
    assert "TRANSACTION_LIMIT_EXCEEDED" not in authority["flags"]
    assert authority["risk_score"] == 80

    details = authority["details"]
    assert details["daily_spend_before"] == "480000.00"
    assert details["projected_daily_total"] == "530000.00"
    assert details["daily_limit_exceeded_by"] == "30000.00"


def test_daily_spend_ignores_transfers_with_no_proposal(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    """A direct bank transfer is not attributable to any agent."""
    action_id = propose(client)

    client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["company"].id,
            "destination_account_id": accounts["abc"].id,
            "amount": "490000.00",
        },
    )

    authority = authority_of(client, action_id)
    assert authority["details"]["daily_spend_before"] == "0.00"
    assert "DAILY_LIMIT_EXCEEDED" not in authority["flags"]


# --------------------------------------------------------------------------- #
# 4. Inactive agent
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("agent_status", [AgentStatus.SUSPENDED, AgentStatus.FROZEN])
def test_inactive_agent_fails(
    client: TestClient, db: Session, agent_status: str
) -> None:
    action_id = propose(client)

    agent = db.get(Agent, 1)
    agent.status = agent_status
    db.commit()

    authority = authority_of(client, action_id)

    assert authority["status"] == "FAIL"
    assert f"AGENT_{agent_status}" in authority["flags"]
    assert authority["risk_score"] == 100
    assert authority["details"]["agent_status"] == agent_status


def test_inactive_agent_is_blocked(client: TestClient, db: Session) -> None:
    action_id = propose(client)
    db.get(Agent, 1).status = AgentStatus.FROZEN
    db.commit()

    assert decision_of(client, action_id) == "BLOCK"


def test_foreign_key_prevents_a_dangling_agent_reference(
    client: TestClient, db: Session
) -> None:
    """The database is the first line of defence for check #1.

    A proposal cannot reference a non-existent agent at all -- the foreign key
    refuses the write.
    """
    from sqlalchemy.exc import IntegrityError

    propose(client)
    proposal = db.execute(select(ActionProposal)).scalars().first()
    proposal.agent_id = 9999

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_missing_agent_is_blocked_not_errored(db: Session) -> None:
    """Defence in depth for check #1.

    The foreign key makes this unreachable through the API, so the engine is
    exercised directly. If an agent is ever absent, the action is refused --
    an unattributable payment must not escape evaluation.
    """
    propose_row = ActionProposal(
        agent_id=1, amount=Decimal("1000.00"), currency="INR", action_type="TRANSFER"
    )
    context = EvaluationContext(
        db=db,
        proposal=propose_row,
        agent=None,  # the case under test
        now=datetime.now(timezone.utc),
    )

    result = AuthorityService().evaluate(context)

    assert result.status == "FAIL"
    assert result.flags == ["AGENT_NOT_FOUND"]
    assert result.risk_score == 100
    assert result.details["agent_exists"] is False


# --------------------------------------------------------------------------- #
# 5. Unauthorized account
# --------------------------------------------------------------------------- #

def test_unauthorized_source_account(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    action_id = propose(client)

    # Redirect the proposal to an account the agent has no claim over.
    proposal = db.execute(select(ActionProposal)).scalars().first()
    proposal.source_account_id = accounts["xyz"].id
    db.commit()

    authority = authority_of(client, action_id)

    assert authority["status"] == "FAIL"
    assert "UNAUTHORIZED_SOURCE_ACCOUNT" in authority["flags"]
    assert authority["risk_score"] == 95
    assert authority["details"]["requested_source_account_id"] == accounts["xyz"].id
    assert authority["details"]["authorized_account_ids"] == [accounts["company"].id]


def test_explicitly_delegated_account_is_authorized(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    """'Belongs to OR is authorized for' -- delegation is honoured."""
    action_id = propose(client)

    agent = db.get(Agent, 1)
    agent.authorized_account_ids = [accounts["xyz"].id]
    proposal = db.execute(select(ActionProposal)).scalars().first()
    proposal.source_account_id = accounts["xyz"].id
    db.commit()

    authority = authority_of(client, action_id)
    assert "UNAUTHORIZED_SOURCE_ACCOUNT" not in authority["flags"]


def test_malformed_delegation_entries_do_not_widen_authority(db: Session) -> None:
    agent = db.get(Agent, 1)
    agent.authorized_account_ids = [7, "8", None, "not-an-id", {}]
    assert authorized_account_ids(agent) == {agent.source_account_id, 7, 8}


# --------------------------------------------------------------------------- #
# Other authority checks
# --------------------------------------------------------------------------- #

def test_disallowed_action_type(client: TestClient, db: Session) -> None:
    action_id = propose(client)
    db.get(Agent, 1).allowed_actions = ["PAYMENT"]  # proposal is a TRANSFER
    db.commit()

    authority = authority_of(client, action_id)
    assert "ACTION_TYPE_NOT_PERMITTED" in authority["flags"]
    assert authority["risk_score"] == 100


def test_disallowed_currency(client: TestClient, db: Session) -> None:
    action_id = propose(client)
    db.get(Agent, 1).allowed_currencies = ["USD"]
    db.commit()

    authority = authority_of(client, action_id)
    assert "CURRENCY_NOT_PERMITTED" in authority["flags"]
    assert authority["risk_score"] == 80


def test_insufficient_funds_is_flagged(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    action_id = propose(client)
    accounts["company"].balance = Decimal("100.00")
    db.commit()

    authority = authority_of(client, action_id)
    assert "INSUFFICIENT_FUNDS" in authority["flags"]
    assert authority["details"]["source_account_balance"] == "100.00"


def test_risk_is_max_not_sum_of_violations(client: TestClient, db: Session) -> None:
    action_id = propose(client, "Pay ₹5,00,000 to ABC Technologies for invoice INV-9")

    agent = db.get(Agent, 1)
    agent.status = AgentStatus.SUSPENDED   # 100
    agent.allowed_currencies = ["USD"]     # 80
    db.commit()

    authority = authority_of(client, action_id)
    assert authority["details"]["violation_count"] >= 3
    # The worst single violation, never a sum that would exceed 100.
    assert authority["risk_score"] == 100


# --------------------------------------------------------------------------- #
# Policy configuration system
# --------------------------------------------------------------------------- #

def test_shipped_policy_file_is_valid() -> None:
    policy = load_policy(DEFAULT_POLICY_PATH)
    assert policy.version >= 1
    assert policy.authority.risk_scores.transaction_limit_exceeded == 85
    assert pytest.approx(sum(policy.fusion.group_weights.values())) == 1.0


def test_policy_endpoint_exposes_active_policy(client: TestClient) -> None:
    response = client.get("/policy")
    assert response.status_code == 200

    body = response.json()
    assert body["authority"]["risk_scores"]["transaction_limit_exceeded"] == 85
    assert body["governance"]["hard_override_risk"] == 90


def _write_policy(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(textwrap.dedent(body))
    return path


BASE_POLICY = """
    version: 99
    fusion:
      group_weights: {authority: 1.0}
      engine_groups: {authority: authority}
    trust:
      tiers:
        - {min_score: 0, tier: SUSPENDED}
    governance:
      autonomous_tiers: [HIGH_AUTONOMY]
      required_engines_for_autonomy: [authority]
"""


def test_policy_thresholds_actually_drive_the_engine(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    """The point of the whole config system.

    Raising the per-transaction limit risk below the FAIL threshold must turn a
    FAIL into a WARN with no code change.
    """
    relaxed = _write_policy(
        tmp_path,
        BASE_POLICY
        + """
    authority:
      fail_at_or_above: 90
      risk_scores:
        transaction_limit_exceeded: 85
    """,
    )

    monkeypatch.setattr("app.core.policy.DEFAULT_POLICY_PATH", relaxed)
    reload_policy()
    try:
        authority = authority_of(
            client,
            propose(client, "Pay ₹5,00,000 to ABC Technologies for invoice INV-9"),
        )
        # Same 85 risk, but the policy no longer treats 85 as failing.
        assert authority["risk_score"] == 85
        assert authority["status"] == "WARN"
    finally:
        # Undo the patch *before* clearing, so the next load reads the real
        # file. monkeypatch would otherwise stay active until teardown, and
        # reloading here would simply re-cache the temporary policy.
        monkeypatch.undo()
        get_policy.cache_clear()

    # Default policy restored: 85 fails again.
    authority = authority_of(
        client, propose(client, "Pay ₹5,00,000 to ABC Technologies for invoice INV-9")
    )
    assert authority["status"] == "FAIL"


def test_unknown_policy_key_is_rejected(tmp_path: Path) -> None:
    """A misspelled setting must fail loudly, not silently disable a control."""
    path = _write_policy(
        tmp_path,
        BASE_POLICY
        + """
    authority:
      fail_at_or_abov: 70
    """,
    )
    with pytest.raises(PolicyError, match="failed validation"):
        load_policy(path)


def test_fusion_weights_must_sum_to_one(tmp_path: Path) -> None:
    path = _write_policy(
        tmp_path,
        """
    version: 1
    fusion:
      group_weights: {authority: 0.5, intent: 0.2}
      engine_groups: {authority: authority, intent: intent}
    trust:
      tiers:
        - {min_score: 0, tier: SUSPENDED}
    governance:
      autonomous_tiers: [HIGH_AUTONOMY]
      required_engines_for_autonomy: [authority]
    """,
    )
    with pytest.raises(PolicyError, match="must sum to 1.0"):
        load_policy(path)


def test_engine_mapped_to_undeclared_group_is_rejected(tmp_path: Path) -> None:
    path = _write_policy(
        tmp_path,
        """
    version: 1
    fusion:
      group_weights: {authority: 1.0}
      engine_groups: {authority: authority, anomaly: behavioural}
    trust:
      tiers:
        - {min_score: 0, tier: SUSPENDED}
    governance:
      autonomous_tiers: [HIGH_AUTONOMY]
      required_engines_for_autonomy: [authority]
    """,
    )
    with pytest.raises(PolicyError, match="undeclared groups"):
        load_policy(path)


def test_governance_bands_must_ascend(tmp_path: Path) -> None:
    path = _write_policy(
        tmp_path,
        BASE_POLICY
        + """
    governance_unused: {}
    """,
    )
    # Rebuild with deliberately inverted bands.
    path.write_text(
        textwrap.dedent(
            """
    version: 1
    fusion:
      group_weights: {authority: 1.0}
      engine_groups: {authority: authority}
    trust:
      tiers:
        - {min_score: 0, tier: SUSPENDED}
    governance:
      execute_below: 70
      constrain_below: 50
      delay_below: 30
      autonomous_tiers: [HIGH_AUTONOMY]
      required_engines_for_autonomy: [authority]
    """
        )
    )
    with pytest.raises(PolicyError, match="must ascend"):
        load_policy(path)


def test_trust_tiers_must_descend_and_reach_zero(tmp_path: Path) -> None:
    path = _write_policy(
        tmp_path,
        """
    version: 1
    fusion:
      group_weights: {authority: 1.0}
      engine_groups: {authority: authority}
    trust:
      tiers:
        - {min_score: 30, tier: LOW}
        - {min_score: 90, tier: HIGH}
    governance:
      autonomous_tiers: [HIGH]
      required_engines_for_autonomy: [authority]
    """,
    )
    with pytest.raises(PolicyError, match="highest min_score to lowest"):
        load_policy(path)


def test_required_engine_absent_from_fusion_is_rejected(tmp_path: Path) -> None:
    """Would make EXECUTE permanently unreachable."""
    path = _write_policy(
        tmp_path,
        """
    version: 1
    fusion:
      group_weights: {authority: 1.0}
      engine_groups: {authority: authority}
    trust:
      tiers:
        - {min_score: 0, tier: SUSPENDED}
    governance:
      autonomous_tiers: [HIGH_AUTONOMY]
      required_engines_for_autonomy: [authority, telepathy]
    """,
    )
    with pytest.raises(PolicyError, match="permanently unreachable"):
        load_policy(path)


def test_missing_policy_file_raises_clearly(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="not found"):
        load_policy(tmp_path / "nope.yaml")


def test_no_engine_hardcodes_thresholds() -> None:
    """Every engine must source its numbers from policy.

    Guards the actual goal of this phase: thresholds are configured in one
    place, not scattered through the codebase.
    """
    import ast

    engines = Path("app/services/engines")
    offenders: list[str] = []

    for module in sorted(engines.glob("*.py")):
        if module.name in {"__init__.py", "base.py"}:
            continue
        tree = ast.parse(module.read_text())
        for node in ast.walk(tree):
            # A module-level CONSTANT = <number> is the pattern policy replaces.
            if isinstance(node, ast.Assign) and isinstance(
                node.value, ast.Constant
            ):
                if not isinstance(node.value.value, (int, float)):
                    continue
                if isinstance(node.value.value, bool):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        offenders.append(f"{module.name}:{target.id}")

    assert not offenders, f"hardcoded thresholds still present: {offenders}"
