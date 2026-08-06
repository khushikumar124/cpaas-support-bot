from __future__ import annotations

from typing import Any

from core.retriever import Retriever
from datasources.base import DataSource
from models import ParsedQuery
from registry.sheet_registry import SheetRoute


class FakeDataSource(DataSource):
    def __init__(self) -> None:
        self.last_lookup: tuple[str, str, str] | None = None
        self.rows = [{"gateway_id": "470", "status": "active"}]

    def get_records(self, sheet_id: str) -> list[dict[str, Any]]:
        return list(self.rows)

    def find_records(
        self,
        sheet_id: str,
        column: str,
        value: str,
        *,
        exact: bool = True,
    ) -> list[dict[str, Any]]:
        self.last_lookup = (sheet_id, column, value)
        return [
            row
            for row in self.rows
            if str(row.get(column, "")).strip().lower() == value.strip().lower()
        ]


def _gateway_query(value: str) -> ParsedQuery:
    return ParsedQuery(
        entity_type="gateway",
        entity_value=value,
        action="lookup",
        requested_field="all",
    )


def test_gateway_lookup_strips_optional_prefixes():
    route = SheetRoute(sheet_id="gateway", id_column="gateway_id")

    for value in ("470", "GW470", "gw470", "Gateway 470"):
        source = FakeDataSource()
        result = Retriever(source).retrieve(_gateway_query(value), route)

        assert result.records == [{"gateway_id": "470", "status": "active"}]
        assert source.last_lookup == ("gateway", "gateway_id", "470")


def test_gateway_normalization_does_not_affect_other_entities():
    source = FakeDataSource()
    route = SheetRoute(sheet_id="vmn", id_column="number")
    query = ParsedQuery(
        entity_type="number",
        entity_value="GW470",
        action="lookup",
        requested_field="all",
    )

    Retriever(source).retrieve(query, route)

    assert source.last_lookup == ("vmn", "number", "GW470")
