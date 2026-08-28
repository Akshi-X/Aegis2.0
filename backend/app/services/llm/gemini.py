"""Gemini-backed instruction parser.

Constrained decoding (``responseSchema`` + ``responseMimeType``) makes Gemini
return schema-conforming JSON rather than prose, and the result is still
re-validated with Pydantic afterwards -- a model claiming to follow a schema is
not evidence that it did.

Every failure path raises ``ParserError`` so the caller can fall back. A slow
or unreachable model must degrade the system, never break it.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings
from app.services.llm.base import ParsedAction, ParserError

logger = logging.getLogger(__name__)

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_SYSTEM_PROMPT = """\
You convert a treasury instruction into a structured payment action.

Rules:
- Extract only what the instruction states. Never invent a recipient or amount.
- `amount` is the monetary value as a plain number, with no symbols, commas, or
  grouping. Expand Indian magnitude words: "5 lakh" is 500000, "1.2 crore" is
  12000000.
- `currency` is a 3-letter ISO code. The symbol ₹ and the words "Rs"/"rupees"
  mean INR. Default to INR when no currency is indicated.
- `recipient` is the payee name exactly as written, with no honorifics, account
  numbers, or trailing punctuation.
- `purpose` is the stated reason, such as an invoice reference. Use an empty
  string if none is given.
- An invoice or reference number, for example "INV-204", is never the amount.

Instruction:
{task}
"""

# Gemini uses an OpenAPI-subset schema vocabulary with uppercase type names.
_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "action_type": {"type": "STRING", "enum": ["TRANSFER", "PAYMENT"]},
        "amount": {"type": "NUMBER"},
        "currency": {"type": "STRING"},
        "recipient": {"type": "STRING"},
        "purpose": {"type": "STRING"},
    },
    "required": ["action_type", "amount", "currency", "recipient", "purpose"],
}


class GeminiParser:
    """Calls the Gemini REST API. Unavailable without an API key."""

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.timeout = timeout or settings.llm_timeout_seconds

    def available(self) -> bool:
        return bool(self.api_key)

    def parse(self, task: str) -> tuple[ParsedAction, dict]:
        if not self.available():
            raise ParserError("GEMINI_API_KEY is not configured.", provider=self.name)

        payload = {
            "contents": [{"parts": [{"text": _SYSTEM_PROMPT.format(task=task)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
                # Deterministic output: the same instruction must yield the same
                # proposal every time, or a demo cannot be re-run.
                "temperature": 0.0,
                "candidateCount": 1,
            },
        }

        try:
            response = httpx.post(
                _ENDPOINT.format(model=self.model),
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as exc:
            raise ParserError(
                f"Gemini did not respond within {self.timeout}s.", provider=self.name
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ParserError(
                f"Gemini returned HTTP {exc.response.status_code}.", provider=self.name
            ) from exc
        except httpx.HTTPError as exc:
            raise ParserError(f"Gemini request failed: {exc}", provider=self.name) from exc

        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            # Also the shape seen when a response is blocked by safety filters.
            raise ParserError(
                "Gemini response did not contain a usable candidate.",
                provider=self.name,
            ) from exc

        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParserError(
                "Gemini returned malformed JSON despite a response schema.",
                provider=self.name,
            ) from exc

        try:
            action = ParsedAction.model_validate(raw)
        except Exception as exc:  # pydantic ValidationError
            raise ParserError(
                f"Gemini output failed validation: {exc}", provider=self.name
            ) from exc

        detail = {
            "provider": self.name,
            "model": self.model,
            "raw_response": raw,
            "finish_reason": body.get("candidates", [{}])[0].get("finishReason"),
            "usage": body.get("usageMetadata", {}),
        }
        return action, detail
