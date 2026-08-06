"""Orchestrates parse → route → retrieve → format (CLI and future Slack)."""

from __future__ import annotations

import logging
import time
from typing import Protocol

from core.query_router import QueryRouter, RoutingError
from core.retriever import Retriever
from datasources.base import DataSource
from formatter import ResponseFormatter
from models import ParsedQuery, RetrievalResult

logger = logging.getLogger(__name__)


class QueryParserProtocol(Protocol):
    def parse(self, question: str) -> ParsedQuery: ...


class BotService:
    """Application service — swap parser/datasource without changing callers."""

    def __init__(
        self,
        parser: QueryParserProtocol,
        data_source: DataSource,
        *,
        router: QueryRouter | None = None,
        retriever: Retriever | None = None,
        formatter: ResponseFormatter | None = None,
    ) -> None:
        self._parser = parser
        self._router = router or QueryRouter()
        self._retriever = retriever or Retriever(data_source)
        self._formatter = formatter or ResponseFormatter()
        self._data_source_name = type(data_source).__name__

    def ask(self, question: str) -> tuple[ParsedQuery, RetrievalResult, str]:
        """
        Process one question end-to-end.

        Returns (parsed_query, retrieval_result, formatted_response).
        """
        start = time.perf_counter()

        parsed = self._parser.parse(question)
        logger.info("Parsed query: %s", parsed.to_log_dict())

        route = self._router.route(parsed)
        logger.info(
            "Selected datasource=%s sheet_id=%s",
            self._data_source_name,
            route.sheet_id,
        )

        result = self._retriever.retrieve(parsed, route)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "Retrieval complete source=%s record_count=%d success=%s elapsed_ms=%.1f",
            result.source,
            result.count,
            result.success,
            elapsed_ms,
        )

        response = self._formatter.format(parsed, result)
        return parsed, result, response

    def ask_safe(self, question: str) -> str:
        """Like ask() but returns user-facing errors as strings."""
        from parsers.base import ParserError

        try:
            _, _, response = self.ask(question)
            return response
        except ParserError as exc:
            logger.warning("Parse failed: %s", exc)
            return f"Sorry, I could not understand that question. ({exc})"
        except RoutingError as exc:
            logger.warning("Routing failed: %s", exc)
            return f"Sorry, I cannot route that question. ({exc})"
        except Exception as exc:
            logger.exception("Unexpected error")
            return f"Something went wrong. ({exc})"
