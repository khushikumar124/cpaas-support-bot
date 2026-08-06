"""Build parser from environment configuration."""

from __future__ import annotations

import logging

from config import OPENAI_API_KEY, PARSER_MODE
from models import ParsedQuery
from parsers.base import ParserError, QueryParserProtocol
from parsers.llm_parser import LLMQueryParser
from parsers.rule_parser import RuleBasedQueryParser

logger = logging.getLogger(__name__)


class HybridQueryParser:
    """OpenAI parser with rule-based fallback."""

    def __init__(self) -> None:
        self._llm = LLMQueryParser()
        self._rule = RuleBasedQueryParser()

    def parse(self, question: str) -> ParsedQuery:
        try:
            return self._llm.parse(question)
        except ParserError as exc:
            logger.warning("OpenAI parser failed; falling back to rule parser: %s", exc)
            try:
                return self._rule.parse(question)
            except ParserError:
                raise exc


def create_parser() -> QueryParserProtocol:
    mode = PARSER_MODE

    if mode == "rule":
        logger.info("Using RuleBasedQueryParser")
        print("[Parser] Offline rule-based mode.\n")
        return RuleBasedQueryParser()

    if mode not in {"auto", "openai"}:
        logger.warning("Unknown PARSER_MODE '%s'; using auto mode", mode)

    if not OPENAI_API_KEY:
        logger.info("No OpenAI API key; using RuleBasedQueryParser")
        print("[Parser] No OpenAI API key; using offline rule parser.\n")
        return RuleBasedQueryParser()

    logger.info("Using HybridQueryParser (OpenAI + rule fallback)")
    return HybridQueryParser()
