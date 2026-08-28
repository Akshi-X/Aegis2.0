"""Instruction-parsing contract shared by every provider.

Providers convert a natural-language instruction into a validated
``ParsedAction``. They do no resolution and no policy work: turning a recipient
*name* into an account, and deciding whether the action is permissible, are
deterministic backend concerns that must never depend on a language model.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ActionType

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP"}


class ParserError(Exception):
    """Raised when an instruction cannot be turned into a valid action.

    A provider raising this is a signal to fall back, not to fail the request.
    """

    def __init__(self, message: str, *, provider: str = "unknown") -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider


class ParsedAction(BaseModel):
    """The structured action extracted from an instruction."""

    action_type: ActionType = ActionType.TRANSFER
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    recipient: str = Field(min_length=1, max_length=160)
    purpose: str = Field(default="", max_length=256)

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount(cls, value: object) -> Decimal:
        """Normalise whatever the provider produced into an exact Decimal.

        A model returning JSON gives us a float, and ``Decimal(0.1)`` is not
        0.1. Going via ``str`` keeps the decimal value the model actually
        intended.
        """
        if isinstance(value, Decimal):
            return value.quantize(Decimal("0.01"))
        if isinstance(value, (int, float)):
            return Decimal(str(value)).quantize(Decimal("0.01"))
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("₹", "").strip()
            try:
                return Decimal(cleaned).quantize(Decimal("0.01"))
            except InvalidOperation as exc:
                raise ValueError(f"Cannot interpret {value!r} as an amount") from exc
        raise ValueError(f"Unsupported amount type: {type(value).__name__}")

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str) -> str:
        currency = value.upper()
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency {currency!r}")
        return currency

    @field_validator("recipient", "purpose")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


@runtime_checkable
class InstructionParser(Protocol):
    """Every provider implements exactly this."""

    name: str

    def available(self) -> bool:
        """Whether this provider can currently be used at all."""
        ...

    def parse(self, task: str) -> tuple[ParsedAction, dict]:
        """Return the parsed action plus raw provider detail for provenance.

        Raises ``ParserError`` if the instruction cannot be parsed.
        """
        ...
