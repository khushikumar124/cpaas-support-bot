"""Executes lookups against a DataSource using routed sheet metadata."""

from __future__ import annotations

import logging
import re

from datasources.base import DataSource
from models import ParsedQuery, RetrievalResult
from registry.sheet_registry import SheetRoute

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieves records from a sheet via the injected DataSource."""

    def __init__(self, data_source: DataSource) -> None:
        self._source = data_source

    def retrieve(self, query: ParsedQuery, route: SheetRoute) -> RetrievalResult:
        """Fetch records for a parsed query on the routed sheet."""
        sheet_id = route.sheet_id

        try:
            if query.action == "list":
                records = self._source.filter_records(sheet_id, query.filters)
                if not records:
                    filter_desc = (
                        ", ".join(f"{k}={v}" for k, v in query.filters.items())
                        or "criteria"
                    )
                    return RetrievalResult(
                        source=sheet_id,
                        records=[],
                        success=True,
                        message=f"No records found matching {filter_desc}.",
                    )
                return RetrievalResult(source=sheet_id, records=records)

            return self._lookup(query, route)
        except (KeyError, FileNotFoundError, ValueError) as exc:
            logger.exception("Retrieval failed for sheet_id=%s", sheet_id)
            return RetrievalResult(
                source=sheet_id,
                records=[],
                success=False,
                message=str(exc),
            )

    def _lookup(self, query: ParsedQuery, route: SheetRoute) -> RetrievalResult:
        if not query.entity_value:
            return RetrievalResult(
                source=route.sheet_id,
                records=[],
                success=False,
                message="Lookup requires entity_value.",
            )

        column = route.lookup_column or route.id_column
        lookup_value = _normalize_lookup_value(query, column)
        records = self._source.find_records(
            route.sheet_id,
            column,
            lookup_value,
        )

        if not records:
            return RetrievalResult(
                source=route.sheet_id,
                records=[],
                success=True,
                message=(
                    f"No record found in '{route.sheet_id}' "
                    f"where {column}='{lookup_value}'."
                ),
            )

        return RetrievalResult(source=route.sheet_id, records=records)


def _normalize_lookup_value(query: ParsedQuery, column: str) -> str:
    """Normalize gateway IDs for lookup without affecting other entity types."""
    value = str(query.entity_value or "").strip()
    if query.entity_type != "gateway" or column != "gateway_id":
        return value

    match = re.fullmatch(r"(?i)(?:gateway|gw)?\s*[-_#:]?\s*(\d+)", value)
    if match:
        return match.group(1)
    return value
