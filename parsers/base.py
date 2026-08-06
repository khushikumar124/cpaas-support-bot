"""Parser protocol and shared exceptions."""

from __future__ import annotations

from typing import Protocol

from models import ParsedQuery


class ParserError(Exception):
    """Raised when parsing fails or returns invalid structure."""


class QueryParserProtocol(Protocol):
    def parse(self, question: str) -> ParsedQuery: ...
