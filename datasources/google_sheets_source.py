"""Google Sheets data source for the CPaaS support bot."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from datasources.base import DataSource

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

# Logical sheet ID -> candidate Google Sheet tab names.
SHEET_TAB_MAP: dict[str, tuple[str, ...]] = {
    "vmn": (
        "Sheet1",
        "VMN",
        "VMNs",
        "Numbers",
        "Number details",
        "VMN details",
    ),
    "gateway": (
        "Gateway details",
        "Gateway Details",
        "Gateways",
        "Gateway",
    ),
    "gateways": (
        "Gateway details",
        "Gateway Details",
        "Gateways",
        "Gateway",
    ),
    "customers": (
        "Customers",
        "Customer details",
        "Customer Details",
    ),
    "tickets": (
        "Tickets",
        "Ticket details",
        "Ticket Details",
    ),
    "source_information": (
        "Source Information",
        "Source information",
        "Source Info",
        "Sources",
    ),
}

# Exact sheet header (stripped) -> canonical column name.
# Unknown headers are slugified so new columns still show up in answers.
COLUMN_MAPS: dict[str, dict[str, str]] = {
    "vmn": {
        "VMN/Number": "number",
        "VMN/Number ": "number",
        "VMN": "number",
        "Number": "number",
        "Number: Code Number": "number",
        "Number/Code Number": "number",
        "Code Number": "number",
        "Phone Number": "number",
        "MSISDN": "number",
        "Type": "number_type",
        "Number Type": "number_type",
        "Code Type": "number_type",
        "Operator": "operator",
        "Operator Name": "operator",
        "Provider": "operator",
        "Vendor": "operator",
        "Status": "status",
        "State": "status",
    },
    "gateway": {
        "Gateway ID": "gateway_id",
        "Gateway Id": "gateway_id",
        "GW ID": "gateway_id",
        "GWID": "gateway_id",
        "Gateway": "gateway_id",
        "Domestic/International": "region",
        "Region": "region",
        "Vendor": "operator",
        "Operator": "operator",
        "Type": "gateway_type",
        "Gateway Type": "gateway_type",
        "State": "status",
        "Status": "status",
        "Account Name": "company_name",
        "Company": "company_name",
        "Company Name": "company_name",
        "Customer": "company_name",
        "GW Details": "gw_details",
        "Gateway Details": "gw_details",
        "TPS": "tps",
        "Host": "host",
        "Port": "port",
        "Sessions": "sessions",
        "Bindtype": "bind_type",
        "Bind Type": "bind_type",
        "Encoding": "encoding",
        "Tomcat Servers": "tomcat_servers",
        "Tomcat Port": "tomcat_port",
        "Node": "node",
    },
    "customers": {
        "Customer ID": "customer_id",
        "Customer Id": "customer_id",
        "Customer": "customer_id",
        "Account Name": "company_name",
        "Company": "company_name",
        "Company Name": "company_name",
        "Status": "status",
        "State": "status",
        "Account Manager": "account_manager",
    },
    "tickets": {
        "Ticket ID": "ticket_id",
        "Ticket Id": "ticket_id",
        "Ticket": "ticket_id",
        "Subject": "subject",
        "Issue": "subject",
        "Status": "status",
        "State": "status",
        "Priority": "priority",
    },
    "source_information": {
        "Source ID": "source_id",
        "Source Id": "source_id",
        "Source": "source_id",
        "Status": "status",
        "State": "status",
        "Line Type": "line_type",
        "Type": "line_type",
    },
}
COLUMN_MAPS["gateways"] = COLUMN_MAPS["gateway"]


class GoogleSheetsDataSource(DataSource):
    """Google Sheets-backed datasource implementing the DataSource interface."""

    def __init__(
        self,
        *,
        credentials_path: str | None = None,
        spreadsheet_id: str | None = None,
        cache_ttl_seconds: int = 60,
    ) -> None:
        self._spreadsheet_id = spreadsheet_id
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._cache_time: dict[str, float] = {}

        credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES,
        )
        client = gspread.authorize(credentials)
        self._spreadsheet = client.open_by_key(spreadsheet_id)
        logger.info(
            "GoogleSheetsDataSource ready - spreadsheet_id=%s ttl=%ds",
            spreadsheet_id,
            cache_ttl_seconds,
        )

    def get_records(self, sheet_id: str) -> list[dict[str, Any]]:
        now = time.time()
        cache_time = self._cache_time.get(sheet_id)

        if cache_time is not None and (now - cache_time) < self._cache_ttl_seconds:
            return list(self._cache[sheet_id])

        records = self._load_sheet(sheet_id)
        self._cache[sheet_id] = records
        self._cache_time[sheet_id] = now
        return list(records)

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

        available_columns = _available_columns(records)
        if column not in available_columns:
            logger.warning(
                "Column '%s' not found in sheet '%s'. Available: %s",
                column,
                sheet_id,
                available_columns,
            )
            raise ValueError(
                f"Column '{column}' not found in sheet '{sheet_id}'. "
                f"Available columns: {available_columns}"
            )

        normalized = str(value).strip().lower()
        return [
            row for row in records
            if (
                str(row.get(column, "")).strip().lower() == normalized
                if exact
                else normalized in str(row.get(column, "")).strip().lower()
            )
        ]

    def filter_records(
        self,
        sheet_id: str,
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        records = self.get_records(sheet_id)
        if not filters:
            return list(records)

        available_columns = _available_columns(records)
        missing = [column for column in filters if column not in available_columns]
        if missing:
            raise ValueError(
                f"Filter column(s) {missing} not found in sheet '{sheet_id}'. "
                f"Available columns: {available_columns}"
            )

        result: list[dict[str, Any]] = []
        for row in records:
            if all(
                str(row.get(col, "")).strip().lower()
                == str(expected).strip().lower()
                for col, expected in filters.items()
            ):
                result.append(row)
        return result

    def clear_cache(self) -> None:
        self._cache.clear()
        self._cache_time.clear()
        logger.info("GoogleSheetsDataSource cache cleared")

    def _load_sheet(self, sheet_id: str) -> list[dict[str, Any]]:
        tab_names = SHEET_TAB_MAP.get(sheet_id)
        if not tab_names:
            raise KeyError(
                f"Unknown sheet_id '{sheet_id}'. "
                f"Add it to SHEET_TAB_MAP in google_sheets_source.py."
            )

        worksheet = self._resolve_worksheet(sheet_id, tab_names)
        logger.info("Fetching tab '%s' (sheet_id=%s)", worksheet.title, sheet_id)
        start = time.perf_counter()

        raw_rows = _rows_from_values(worksheet.get_all_values())
        column_map = COLUMN_MAPS.get(sheet_id, {})
        normalized = [_normalize_row(row, column_map) for row in raw_rows]
        normalized = [row for row in normalized if any(row.values())]

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Loaded %d rows for sheet_id='%s' in %.0f ms",
            len(normalized),
            sheet_id,
            elapsed_ms,
        )
        return normalized

    def _resolve_worksheet(
        self,
        sheet_id: str,
        tab_names: tuple[str, ...],
    ) -> gspread.Worksheet:
        for tab_name in tab_names:
            try:
                return self._spreadsheet.worksheet(tab_name)
            except gspread.exceptions.WorksheetNotFound:
                continue

        wanted = {_normalize_label(tab_name) for tab_name in tab_names}
        worksheets = self._spreadsheet.worksheets()
        for worksheet in worksheets:
            if _normalize_label(worksheet.title) in wanted:
                return worksheet

        available = [worksheet.title for worksheet in worksheets]
        raise KeyError(
            f"No tab found for sheet_id '{sheet_id}'. Tried: {list(tab_names)}. "
            f"Available tabs: {available}"
        )


def _normalize_row(
    raw_row: dict[str, Any],
    column_map: dict[str, str],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_key, raw_value in raw_row.items():
        if raw_key is None:
            continue
        key_stripped = str(raw_key).strip()
        if not key_stripped:
            continue

        canonical = column_map.get(key_stripped) or _slugify(key_stripped)
        value = str(raw_value).strip() if raw_value is not None else ""
        result[canonical] = value

    return result


def _rows_from_values(values: list[list[Any]]) -> list[dict[str, str]]:
    """
    Convert raw sheet values into dict rows without gspread header restrictions.

    Google Sheets edits often leave duplicate or blank headers behind.
    get_all_records() rejects those; this keeps the first occurrence of each
    non-empty header and ignores trailing columns with no header.
    """
    if not values:
        return []

    headers = [str(header).strip() for header in values[0]]
    rows: list[dict[str, str]] = []

    for raw_row in values[1:]:
        row: dict[str, str] = {}
        for index, header in enumerate(headers):
            if not header or header in row:
                continue
            value = raw_row[index] if index < len(raw_row) else ""
            row[header] = str(value).strip() if value is not None else ""
        rows.append(row)

    return rows


def _available_columns(records: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for row in records:
        for column in row:
            if column not in columns:
                columns.append(column)
    return columns


def _slugify(header: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", header.strip().lower())
    return slug.strip("_")


def _normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())
