"""Maps entity types to logical sheets (VMN, Gateway, Ticket, Customer, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from models import ParsedQuery


@dataclass(frozen=True)
class SheetRoute:
    """Target sheet and column metadata for a parsed query."""

    sheet_id: str
    id_column: str
    lookup_column: str | None = None


class SheetRegistry:
    """
    Registry of entity_type → sheet routing rules.

    sheet_id values here must match keys in SHEET_TAB_MAP in
    google_sheets_source.py (and SHEET_FILE_MAP in csv_source.py).

    id_column values must match the canonical column names produced by
    _normalize_row() in google_sheets_source.py.
    """

    ENTITY_SHEET_MAP: dict[str, tuple[str, str]] = {
        # VMN / phone number queries → "vmn" sheet, lookup by "number" column
        "number":   ("vmn", "number"),
        "vmn":      ("vmn", "number"),
        "operator": ("vmn", "number"),   # operator lookup by phone number

        # Gateway queries → "gateways" sheet, lookup by "gateway_id" column
        "gateway":  ("gateways", "gateway_id"),
        "company":  ("gateways", "gateway_id"),

        # Other entities
        "customer": ("customers", "customer_id"),
        "ticket":   ("tickets", "ticket_id"),
        "source":   ("source_information", "source_id"),
    }

    def resolve(self, query: ParsedQuery) -> SheetRoute | None:
        """Return sheet route for entity_type, or None if unsupported."""
        mapping = self.ENTITY_SHEET_MAP.get(query.entity_type)
        if not mapping:
            return None

        sheet_id, id_column = mapping
        lookup_column = self._lookup_column(query, id_column)
        return SheetRoute(
            sheet_id=sheet_id,
            id_column=id_column,
            lookup_column=lookup_column,
        )

    @staticmethod
    def _lookup_column(query: ParsedQuery, default_id_column: str) -> str | None:
        """Operator queries look up VMN by phone number, not operator name."""
        if query.entity_type == "operator":
            return "number"
        return default_id_column


_default_registry = SheetRegistry()


def get_registry() -> SheetRegistry:
    return _default_registry
