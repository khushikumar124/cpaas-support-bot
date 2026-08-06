"""Abstract data source — business layer depends only on sheet IDs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DataSource(ABC):
    """
    Tabular data access by logical sheet ID (e.g. ``vmn``, ``gateways``).

    Implementations map sheet IDs to CSV files or Google Sheet tabs.
    """

    @abstractmethod
    def get_records(self, sheet_id: str) -> list[dict[str, Any]]:
        """Return all rows for a sheet."""

    @abstractmethod
    def find_records(
        self,
        sheet_id: str,
        column: str,
        value: str,
        *,
        exact: bool = True,
    ) -> list[dict[str, Any]]:
        """Return rows where ``column`` matches ``value``."""

    def filter_records(
        self,
        sheet_id: str,
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Return rows matching all filters (case-insensitive string match)."""
        records = self.get_records(sheet_id)
        if not filters:
            return records

        result: list[dict[str, Any]] = []
        for row in records:
            if all(
                str(row.get(col, "")).lower() == str(val).lower()
                for col, val in filters.items()
                if col in row
            ):
                result.append(row)
        return result
