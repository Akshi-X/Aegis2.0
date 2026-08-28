"""Instruction parsing: natural language in, structured action out.

Providers sit behind one interface (``InstructionParser``) with a deterministic
implementation always available, so the agent works with or without an LLM.
Adding another provider means adding one file and a branch in the factory.
"""

from app.services.llm.base import InstructionParser, ParsedAction, ParserError
from app.services.llm.factory import get_primary_parser, parse_instruction
from app.services.llm.gemini import GeminiParser
from app.services.llm.heuristic import HeuristicParser

__all__ = [
    "GeminiParser",
    "HeuristicParser",
    "InstructionParser",
    "ParsedAction",
    "ParserError",
    "get_primary_parser",
    "parse_instruction",
]
