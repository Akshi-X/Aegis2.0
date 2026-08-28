"""Autonomous agent tests.

The load-bearing test here is ``test_agent_never_moves_money``: the entire
premise of AEGIS-X is that an agent cannot execute, so that guarantee needs a
test that would fail loudly if someone ever wired the agent to the bank.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ActionProposal, AuditLog, BankAccount, Transaction
from app.services.llm import HeuristicParser, ParsedAction, ParserError
from app.services.llm.factory import parse_instruction

NORMAL_TASK = "Pay ₹50,000 to ABC Technologies for invoice INV-204"
HIGH_VALUE_TASK = "Transfer ₹15,00,000 to XYZ Cloud for annual infrastructure renewal"
UNKNOWN_RECIPIENT_TASK = "Pay ₹75,000 to Quantum Holdings for consulting services"


def post_task(client: TestClient, task: str, agent_id: object = 1):
    return client.post("/agent/task", json={"agent_id": agent_id, "task": task})


# --------------------------------------------------------------------------- #
# The core guarantee
# --------------------------------------------------------------------------- #

def test_agent_never_moves_money(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    balances_before = {
        account.id: account.balance
        for account in db.execute(select(BankAccount)).scalars()
    }

    for task in (NORMAL_TASK, HIGH_VALUE_TASK, UNKNOWN_RECIPIENT_TASK):
        assert post_task(client, task).status_code == 201

    db.expire_all()

    # No ledger entries...
    assert db.execute(select(func.count()).select_from(Transaction)).scalar_one() == 0

    # ...and not a rupee moved anywhere.
    for account in db.execute(select(BankAccount)).scalars():
        assert account.balance == balances_before[account.id]

    # Every proposal is inert.
    statuses = {p.status for p in db.execute(select(ActionProposal)).scalars()}
    assert statuses == {"PROPOSED"}


def _imported_names(module) -> set[str]:
    """Every module path imported by a module, via AST.

    Parsing imports rather than grepping the source means prose about the bank
    in a docstring does not trip the check, while a real import always does.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names)

    return names


def test_agent_module_cannot_reach_the_bank() -> None:
    """Structural check: the agent has no import path to the bank simulator.

    Catches the mistake at the import, rather than relying on a reviewer
    noticing a new dependency in a diff.
    """
    import app.api.agent as agent_api
    import app.services.agent as agent_service

    for module in (agent_service, agent_api):
        imported = _imported_names(module)
        offending = {name for name in imported if "services.bank" in name}
        assert not offending, f"{module.__name__} imports {offending}"


# --------------------------------------------------------------------------- #
# 1. Normal vendor payment
# --------------------------------------------------------------------------- #

def test_normal_vendor_payment(client: TestClient) -> None:
    response = post_task(client, NORMAL_TASK)
    assert response.status_code == 201, response.text

    body = response.json()
    proposal = body["proposal"]

    assert proposal["action_type"] == "TRANSFER"
    assert Decimal(proposal["amount"]) == Decimal("50000.00")
    assert proposal["currency"] == "INR"
    assert proposal["recipient"] == "ABC Technologies"
    assert proposal["purpose"] == "invoice INV-204"
    assert proposal["status"] == "PROPOSED"
    assert proposal["action_id"].startswith("act_")

    # Recipient resolved to a seeded counterparty.
    assert proposal["recipient_known"] is True
    assert proposal["recipient_account_number"] == "ACC2000000001"

    # Source account comes from the agent's authority envelope, not the text.
    assert proposal["source_account"]["account_number"] == "ACC1000000001"


def test_invoice_number_is_not_mistaken_for_the_amount(client: TestClient) -> None:
    """'INV-204' must never be parsed as an amount of 204."""
    proposal = post_task(client, NORMAL_TASK).json()["proposal"]
    assert Decimal(proposal["amount"]) == Decimal("50000.00")


# --------------------------------------------------------------------------- #
# 2. High-value payment
# --------------------------------------------------------------------------- #

def test_high_value_payment(client: TestClient) -> None:
    response = post_task(client, HIGH_VALUE_TASK)
    assert response.status_code == 201, response.text

    proposal = response.json()["proposal"]
    # Indian digit grouping: 15,00,000 is fifteen lakh.
    assert Decimal(proposal["amount"]) == Decimal("1500000.00")
    assert proposal["recipient"] == "XYZ Cloud"

    # Far beyond the agent's 100,000 limit, yet still only PROPOSED. Enforcing
    # that limit is the Authority Engine's job in a later phase; the agent's job
    # is simply never to act on its own.
    assert proposal["status"] == "PROPOSED"


def test_magnitude_words_are_expanded(client: TestClient) -> None:
    proposal = post_task(
        client, "Pay 5 lakh to ABC Technologies for infrastructure"
    ).json()["proposal"]
    assert Decimal(proposal["amount"]) == Decimal("500000.00")

    proposal = post_task(
        client, "Transfer 1.2 crore to XYZ Cloud for capacity expansion"
    ).json()["proposal"]
    assert Decimal(proposal["amount"]) == Decimal("12000000.00")


# --------------------------------------------------------------------------- #
# 3. Unknown recipient
# --------------------------------------------------------------------------- #

def test_unknown_recipient_still_produces_a_proposal(client: TestClient) -> None:
    response = post_task(client, UNKNOWN_RECIPIENT_TASK)
    assert response.status_code == 201, response.text

    proposal = response.json()["proposal"]
    assert proposal["recipient"] == "Quantum Holdings"
    # Unresolved: a signal for AEGIS-X, not an error for the agent.
    assert proposal["recipient_known"] is False
    assert proposal["recipient_account_number"] is None
    assert proposal["status"] == "PROPOSED"


def test_recipient_matching_is_not_fuzzy(client: TestClient) -> None:
    """A near-miss name must not silently resolve to a trusted vendor.

    "ABC Technologies Ltd" quietly becoming "ABC Technologies" is the
    typosquatting failure mode this system exists to prevent.
    """
    proposal = post_task(
        client, "Pay ₹10,000 to ABC Technologies Ltd for invoice INV-9"
    ).json()["proposal"]
    assert proposal["recipient_known"] is False


def test_case_and_punctuation_differences_do_resolve(client: TestClient) -> None:
    proposal = post_task(
        client, "Pay ₹10,000 to abc technologies for invoice INV-9"
    ).json()["proposal"]
    assert proposal["recipient_known"] is True


# --------------------------------------------------------------------------- #
# Provenance and audit
# --------------------------------------------------------------------------- #

def test_provenance_preserves_the_original_instruction(
    client: TestClient, db: Session
) -> None:
    context = [{"source": "email:msg-88", "content": "Invoice INV-204 attached."}]
    response = client.post(
        "/agent/task",
        json={"agent_id": 1, "task": NORMAL_TASK, "context": context},
    )
    assert response.status_code == 201

    db.expire_all()
    proposal = db.execute(select(ActionProposal)).scalar_one()

    assert proposal.provenance["user_instruction"] == NORMAL_TASK
    assert proposal.provenance["retrieved_context"] == context
    assert proposal.provenance["parser"]["provider"] == "heuristic"
    assert proposal.provenance["recipient_resolution"]["known"] is True


def test_proposal_creation_is_audited(client: TestClient, db: Session) -> None:
    post_task(client, NORMAL_TASK)

    db.expire_all()
    entry = db.execute(
        select(AuditLog).where(AuditLog.event_type == "PROPOSAL_CREATED")
    ).scalar_one()
    assert entry.payload["recipient"] == "ABC Technologies"
    assert entry.payload["status"] == "PROPOSED"
    assert entry.agent_id == 1


# --------------------------------------------------------------------------- #
# Error handling
# --------------------------------------------------------------------------- #

def test_unknown_agent_returns_404(client: TestClient) -> None:
    response = post_task(client, NORMAL_TASK, agent_id=9999)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "agent_not_found"


def test_agent_can_be_addressed_by_name(client: TestClient) -> None:
    response = post_task(client, NORMAL_TASK, agent_id="Treasury Agent")
    assert response.status_code == 201


@pytest.mark.parametrize(
    "task",
    [
        "Hello there, how are you?",           # no financial action
        "Pay ABC Technologies for invoice",     # no amount
        "Transfer ₹50,000 urgently",            # no recipient
    ],
)
def test_uninterpretable_instructions_return_422(
    client: TestClient, task: str
) -> None:
    response = post_task(client, task)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "instruction_not_understood"


def test_failed_parse_is_audited_and_creates_no_proposal(
    client: TestClient, db: Session
) -> None:
    post_task(client, "Hello there, how are you?")

    db.expire_all()
    assert db.execute(select(func.count()).select_from(ActionProposal)).scalar_one() == 0
    entry = db.execute(
        select(AuditLog).where(AuditLog.event_type == "PROPOSAL_REJECTED")
    ).scalar_one()
    assert "financial action" in entry.message


def test_empty_task_is_rejected_by_validation(client: TestClient) -> None:
    response = client.post("/agent/task", json={"agent_id": 1, "task": ""})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Read endpoints
# --------------------------------------------------------------------------- #

def test_list_and_fetch_actions(client: TestClient) -> None:
    first = post_task(client, NORMAL_TASK).json()["proposal"]
    post_task(client, UNKNOWN_RECIPIENT_TASK)

    listed = client.get("/actions")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 2
    # Newest first.
    assert body[0]["recipient"] == "Quantum Holdings"

    by_action_id = client.get(f"/actions/{first['action_id']}")
    assert by_action_id.status_code == 200
    assert by_action_id.json()["action_id"] == first["action_id"]


def test_actions_can_be_filtered_by_status(client: TestClient) -> None:
    post_task(client, NORMAL_TASK)

    assert len(client.get("/actions", params={"status": "PROPOSED"}).json()) == 1
    assert len(client.get("/actions", params={"status": "EXECUTED"}).json()) == 0


def test_unknown_action_returns_404(client: TestClient) -> None:
    response = client.get("/actions/act_doesnotexist")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "action_not_found"


# --------------------------------------------------------------------------- #
# Provider fallback
# --------------------------------------------------------------------------- #

def test_parse_falls_back_when_the_primary_provider_fails(monkeypatch) -> None:
    """A Gemini outage must degrade the system, not break it."""

    class BrokenParser:
        name = "gemini"

        def available(self) -> bool:
            return True

        def parse(self, task: str):
            raise ParserError("connection reset", provider="gemini")

    monkeypatch.setattr(
        "app.services.llm.factory.get_primary_parser", lambda: BrokenParser()
    )

    action, detail = parse_instruction(NORMAL_TASK)

    assert isinstance(action, ParsedAction)
    assert action.amount == Decimal("50000.00")
    assert detail["fallback_used"] is True
    assert detail["fallback_reason"] == "connection reset"
    assert detail["attempted_provider"] == "gemini"


def test_heuristic_parser_is_deterministic() -> None:
    parser = HeuristicParser()
    first, _ = parser.parse(NORMAL_TASK)
    second, _ = parser.parse(NORMAL_TASK)
    assert first == second
