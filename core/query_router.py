"""Routes parsed queries to the correct logical sheet."""

from __future__ import annotations

import logging

from models import ParsedQuery
from registry.sheet_registry import SheetRegistry, SheetRoute, get_registry

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    """Raised when no sheet can be resolved for a query."""


class QueryRouter:
    """Determines which sheet/data source should handle a parsed query."""

    def __init__(self, registry: SheetRegistry | None = None) -> None:
        self._registry = registry or get_registry()

    def route(self, query: ParsedQuery) -> SheetRoute:
        """
        Resolve entity_type to a target sheet.

        Raises RoutingError if the entity type is not registered.
        """
        route = self._registry.resolve(query)
        if route is None:
            raise RoutingError(
                f"No sheet configured for entity_type='{query.entity_type}'."
            )

        logger.info(
            "Routed query entity_type=%s -> sheet_id=%s id_column=%s",
            query.entity_type,
            route.sheet_id,
            route.lookup_column or route.id_column,
        )
        return route
