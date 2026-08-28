"""Provider selection and the fallback chain.

``parse_instruction`` is the only entry point callers should use. It tries the
configured provider and silently degrades to the deterministic parser, so the
system keeps producing proposals whether or not Gemini is reachable.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.services.llm.base import ParsedAction, InstructionParser, ParserError
from app.services.llm.gemini import GeminiParser
from app.services.llm.heuristic import HeuristicParser

logger = logging.getLogger(__name__)


def get_primary_parser() -> InstructionParser:
    """Resolve the configured provider.

    ``auto`` (the default) uses Gemini when a key is present and the
    deterministic parser otherwise.
    """
    provider = (settings.llm_provider or "auto").lower()

    if provider == "heuristic":
        return HeuristicParser()

    if provider == "gemini":
        return GeminiParser()

    gemini = GeminiParser()
    return gemini if gemini.available() else HeuristicParser()


def parse_instruction(task: str) -> tuple[ParsedAction, dict]:
    """Parse an instruction, falling back to the deterministic parser.

    Returns the action plus a provenance record describing which provider
    produced it and whether a fallback occurred.
    """
    primary = get_primary_parser()

    if primary.name != "heuristic" and primary.available():
        try:
            action, detail = primary.parse(task)
            detail["fallback_used"] = False
            return action, detail
        except ParserError as exc:
            # Degrade, do not fail. The deterministic parser handles the
            # instruction shapes that matter for a demo, and a model outage
            # must not take the agent offline.
            logger.warning(
                "Provider %r failed (%s); falling back to the deterministic parser.",
                primary.name,
                exc.message,
            )
            fallback_reason = exc.message
    else:
        fallback_reason = None

    action, detail = HeuristicParser().parse(task)
    detail["fallback_used"] = fallback_reason is not None
    if fallback_reason:
        detail["fallback_reason"] = fallback_reason
        detail["attempted_provider"] = primary.name
    return action, detail
