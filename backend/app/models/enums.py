"""Status vocabularies shared by models and API schemas.

These are ``StrEnum``s stored in plain ``String`` columns rather than native
PostgreSQL ENUM types. Native enums require a migration to add a single value,
which is the wrong trade-off for a schema that will keep growing.
"""

from __future__ import annotations

from enum import StrEnum


class AgentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"  # trust-driven, recoverable
    FROZEN = "FROZEN"        # operator kill switch, manual release only


class OwnerType(StrEnum):
    COMPANY = "COMPANY"    # the organisation's own accounts
    VENDOR = "VENDOR"      # approved suppliers
    EXTERNAL = "EXTERNAL"  # everything else


class TransactionStatus(StrEnum):
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class ActionType(StrEnum):
    TRANSFER = "TRANSFER"
    PAYMENT = "PAYMENT"


class ProposalStatus(StrEnum):
    """Lifecycle of an agent's proposed action.

    Phase 1 only ever writes PROPOSED. The remaining states are the governance
    state machine that AEGIS-X drives in later phases -- declared now so the
    vocabulary is fixed before anything depends on it.
    """

    PROPOSED = "PROPOSED"
    EVALUATED = "EVALUATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class GovernanceDecision(StrEnum):
    """The five outcomes AEGIS-X may reach."""

    EXECUTE = "EXECUTE"
    CONSTRAIN = "CONSTRAIN"
    DELAY = "DELAY"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class AuditEventType(StrEnum):
    TRANSFER_EXECUTED = "TRANSFER_EXECUTED"
    TRANSFER_REJECTED = "TRANSFER_REJECTED"
    PROPOSAL_CREATED = "PROPOSAL_CREATED"
    PROPOSAL_REJECTED = "PROPOSAL_REJECTED"
    PROPOSAL_EVALUATED = "PROPOSAL_EVALUATED"
    SEED_APPLIED = "SEED_APPLIED"
