"""CSV-backed data source — file mapping lives only in this module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from config import DATA_DIR
from datasources.base import DataSource

# Logical sheet ID → CSV filename (Google Sheets tab name later)
SHEET_FILE_MAP: dict[str, str] = {
    "source_information": "source_info.csv",
    "gateways": "gateways.csv",
    "vmn": "vmn.csv",
    "customers": "customers.csv",
    "tickets": "tickets.csv",
}


class CSVDataSource(DataSource):
    """Loads sheet data from CSV files under ``data/``."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or DATA_DIR
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def get_records(self, sheet_id: str) -> list[dict[str, Any]]:
        if sheet_id not in self._cache:
            path = self._resolve_path(sheet_id)
            frame = pd.read_csv(path, dtype=str).fillna("")
            self._cache[sheet_id] = frame.to_dict(orient="records")
        return [dict(row) for row in self._cache[sheet_id]]

    def find_records(
        self,
        sheet_id: str,
        column: str,
        value: str,
        *,
        exact: bool = True,
    ) -> list[dict[str, Any]]:
        records = self.get_records(sheet_id)
        if not records:
            return []

        if column not in records[0]:
            raise ValueError(f"Column '{column}' not found in sheet '{sheet_id}'")

        normalized = str(value).strip().lower()
        matched: list[dict[str, Any]] = []

        for row in records:
            cell = str(row.get(column, "")).strip()
            if exact:
                if cell.lower() == normalized:
                    matched.append(row)
            elif normalized in cell.lower():
                matched.append(row)

        return matched

    def clear_cache(self) -> None:
        """Invalidate cached sheets after file updates."""
        self._cache.clear()

    def _resolve_path(self, sheet_id: str) -> Path:
        filename = SHEET_FILE_MAP.get(sheet_id)
        if not filename:
            raise KeyError(f"Unknown sheet ID: {sheet_id}")
        path = self._data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        return path
