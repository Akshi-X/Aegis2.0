"""Deterministic instruction parser.

This is the fallback when Gemini is unconfigured, slow, or unreachable, and it
is also what the test suite runs against. It is intentionally rule-based: the
same instruction always yields the same action, which is what makes a live
demo reproducible.

It handles the shapes a treasury instruction actually takes, including Indian
number formatting ("15,00,000") and magnitude words ("5 lakh", "1.2 crore").
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.models.enums import ActionType
from app.services.llm.base import ParsedAction, ParserError

_SYMBOL_TO_CURRENCY = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
}

_MULTIPLIERS = {
    "k": Decimal(1_000),
    "thousand": Decimal(1_000),
    "lakh": Decimal(100_000),
    "lakhs": Decimal(100_000),
    "lac": Decimal(100_000),
    "lacs": Decimal(100_000),
    "million": Decimal(1_000_000),
    "m": Decimal(1_000_000),
    "crore": Decimal(10_000_000),
    "crores": Decimal(10_000_000),
}

# The negative lookbehind/lookahead keep digits that are part of a token --
# "INV-204", "AC-99" -- from ever being read as an amount.
_AMOUNT_RE = re.compile(
    r"""
    (?P<symbol>₹|\$|€|£|Rs\.?|INR|USD|EUR|GBP)?
    \s*
    (?<![\w-])
    (?P<number>\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)
    (?![\w-])
    \s*
    (?P<multiplier>lakhs?|lacs?|crores?|thousand|million|k|m)?\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# "to <recipient>", stopping at a purpose clause or punctuation.
_RECIPIENT_RE = re.compile(
    r"\bto\s+(?P<recipient>.+?)"
    r"(?=\s+(?:for|towards|regarding|against|re:|as|on|with)\b|[.,;:]|$)",
    re.IGNORECASE,
)

_PURPOSE_RE = re.compile(
    r"\b(?:for|towards|regarding|against|re:)\s+(?P<purpose>.+?)\s*[.]?$",
    re.IGNORECASE,
)

_TRANSFER_VERBS = re.compile(
    r"\b(pay|transfer|send|remit|wire|settle|clear|disburse|release)\b", re.IGNORECASE
)

# Leading noise left over once the verb and amount are stripped.
_RECIPIENT_NOISE = re.compile(
    r"^(?:the\s+|a\s+|an\s+|account\s+of\s+|vendor\s+|supplier\s+)", re.IGNORECASE
)


def _extract_amount(task: str) -> tuple[Decimal, str | None]:
    """Return (amount, currency_hint). Raises ParserError if none found."""
    candidates = []
    for match in _AMOUNT_RE.finditer(task):
        number = match.group("number")
        if not number:
            continue

        value = Decimal(number.replace(",", ""))
        multiplier = (match.group("multiplier") or "").lower()
        if multiplier in _MULTIPLIERS:
            value *= _MULTIPLIERS[multiplier]

        symbol = (match.group("symbol") or "").lower()
        currency = _SYMBOL_TO_CURRENCY.get(symbol)

        candidates.append(
            {
                "value": value,
                "currency": currency,
                # An explicit currency marker or magnitude word is strong
                # evidence this number is the amount rather than an incidental
                # figure elsewhere in the sentence.
                "confident": bool(symbol or multiplier),
            }
        )

    if not candidates:
        raise ParserError(
            "No monetary amount found in the instruction.", provider="heuristic"
        )

    confident = [c for c in candidates if c["confident"]]
    chosen = confident[0] if confident else candidates[0]
    return chosen["value"].quantize(Decimal("0.01")), chosen["currency"]


def _extract_recipient(task: str) -> str:
    match = _RECIPIENT_RE.search(task)
    if not match:
        raise ParserError(
            "No recipient found; expected a phrase of the form 'to <recipient>'.",
            provider="heuristic",
        )

    recipient = _RECIPIENT_NOISE.sub("", match.group("recipient").strip())
    # Guard against "pay to 50000" style inputs where the amount was captured
    # as the recipient.
    if not recipient or not re.search(r"[A-Za-z]", recipient):
        raise ParserError(
            "Recipient could not be identified from the instruction.",
            provider="heuristic",
        )
    return recipient.strip(" .,;:")


def _extract_purpose(task: str) -> str:
    match = _PURPOSE_RE.search(task)
    return match.group("purpose").strip(" .,;:") if match else ""


class HeuristicParser:
    """Rule-based parser. Always available, never makes a network call."""

    name = "heuristic"

    def available(self) -> bool:
        return True

    def parse(self, task: str) -> tuple[ParsedAction, dict]:
        instruction = (task or "").strip()
        if not instruction:
            raise ParserError("Instruction is empty.", provider="heuristic")

        if not _TRANSFER_VERBS.search(instruction):
            raise ParserError(
                "No recognised financial action. Expected an instruction such as "
                "'Pay ₹50,000 to ABC Technologies for invoice INV-204'.",
                provider="heuristic",
            )

        amount, currency_hint = _extract_amount(instruction)
        recipient = _extract_recipient(instruction)
        purpose = _extract_purpose(instruction)

        action = ParsedAction(
            action_type=ActionType.TRANSFER,
            amount=amount,
            currency=currency_hint or "INR",
            recipient=recipient,
            purpose=purpose,
        )

        detail = {
            "provider": self.name,
            "currency_inferred": currency_hint is None,
            "matched_verb": bool(_TRANSFER_VERBS.search(instruction)),
        }
        return action, detail
