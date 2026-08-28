"""Domain exceptions.

The service layer raises these; the API layer maps them to HTTP status codes.
Keeping them HTTP-agnostic means the same services can later be driven by the
AEGIS-X orchestrator rather than only by a request handler.
"""

from __future__ import annotations

from decimal import Decimal


class AegisError(Exception):
    """Base class for all AEGIS-X domain errors."""

    code = "aegis_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AccountNotFoundError(AegisError):
    code = "account_not_found"

    def __init__(self, account_id: int, role: str = "account") -> None:
        super().__init__(f"No bank account with id {account_id} ({role}).")
        self.account_id = account_id
        self.role = role


class InsufficientFundsError(AegisError):
    code = "insufficient_funds"

    def __init__(self, account_id: int, balance: Decimal, requested: Decimal) -> None:
        super().__init__(
            f"Account {account_id} has a balance of {balance}, "
            f"which is insufficient for a transfer of {requested}."
        )
        self.account_id = account_id
        self.balance = balance
        self.requested = requested


class CurrencyMismatchError(AegisError):
    code = "currency_mismatch"

    def __init__(self, expected: str, actual: str, account_id: int) -> None:
        super().__init__(
            f"Account {account_id} is denominated in {actual}, "
            f"but the transfer specified {expected}. "
            "Cross-currency transfers are not supported."
        )
        self.expected = expected
        self.actual = actual
        self.account_id = account_id


class AgentNotFoundError(AegisError):
    code = "agent_not_found"

    def __init__(self, reference: str) -> None:
        super().__init__(f"No agent matching {reference!r} (by id or name).")
        self.reference = reference


class NoSourceAccountError(AegisError):
    code = "no_source_account"

    def __init__(self, agent_name: str) -> None:
        super().__init__(
            f"Agent {agent_name!r} has no source account and therefore cannot "
            "propose a transfer."
        )
        self.agent_name = agent_name


class InstructionParseError(AegisError):
    code = "instruction_not_understood"

    def __init__(self, message: str, *, provider: str = "unknown") -> None:
        super().__init__(message)
        self.provider = provider


class ProposalNotFoundError(AegisError):
    code = "action_not_found"

    def __init__(self, reference: str, detail: str | None = None) -> None:
        super().__init__(
            detail or f"No action proposal matching {reference!r}."
        )
        self.reference = reference


class SameAccountTransferError(AegisError):
    code = "same_account_transfer"

    def __init__(self, account_id: int) -> None:
        super().__init__(
            f"Source and destination are both account {account_id}; "
            "a transfer must move money between two different accounts."
        )
        self.account_id = account_id
