"""Formats retrieval results into human-readable responses."""

from __future__ import annotations

from config import FIELD_LABELS
from models import ParsedQuery, RetrievalResult


class ResponseFormatter:
    """Builds console/Slack-friendly text from queries and retrieval results."""

    def format(self, query: ParsedQuery, result: RetrievalResult) -> str:
        if not result.success:
            return f"Error: {result.message or 'Retrieval failed.'}"

        if result.is_empty:
            return result.message or "No matching records found."

        if query.action == "list":
            return self._format_list(result, query)

        if len(result.records) == 1 and query.requested_field not in ("all", "list"):
            return self._format_single_field(query, result.records[0])

        return self._format_full_records(result.records)

    def _format_single_field(self, query: ParsedQuery, row: dict[str, str]) -> str:
        field = self._resolve_field_key(query.requested_field, row)
        if field is None:
            return self._format_full_records([row])

        label = FIELD_LABELS.get(field, field.replace("_", " ").title())
        value = row.get(field, "N/A")
        entity_label = query.entity_value or "record"
        return f"{label} for {entity_label}: {value}"

    def _resolve_field_key(self, requested: str, row: dict[str, str]) -> str | None:
        aliases = {"company": "company_name", "company_name": "company_name"}
        key = aliases.get(requested, requested)
        if key in row:
            return key
        for col in row:
            if requested in col.lower():
                return col
        return None

    def _format_list(self, result: RetrievalResult, query: ParsedQuery) -> str:
        count = result.count
        filter_desc = ", ".join(f"{k}={v}" for k, v in query.filters.items())
        header = f"Found {count} record(s) from {result.source}"
        if filter_desc:
            header += f" ({filter_desc})"
        header += ":\n"

        lines: list[str] = [header]
        for idx, row in enumerate(result.records, start=1):
            lines.append(f"  {idx}. {self._row_summary(row)}")
        return "\n".join(lines)

    def _format_full_records(self, rows: list[dict[str, str]]) -> str:
        blocks: list[str] = []
        for i, row in enumerate(rows):
            if len(rows) > 1:
                blocks.append(f"--- Record {i + 1} ---")
            for key, value in row.items():
                label = FIELD_LABELS.get(key, key.replace("_", " ").title())
                blocks.append(f"  {label}: {value}")
        return "\n".join(blocks)

    @staticmethod
    def _row_summary(row: dict[str, str]) -> str:
        number = row.get("number", "")
        status = row.get("status", "")
        operator = row.get("operator", "")
        gateway = row.get("gateway_id", "")
        company = row.get("company_name", "")
        ticket_id = row.get("ticket_id", "")
        source_id = row.get("source_id", "")
        customer_id = row.get("customer_id", "")

        # Most specific identifier first. Tickets and sources also carry a
        # "number"/"gateway_id" column, so checking those first would label
        # every ticket row as a phone number.
        if ticket_id:
            parts = [f"Ticket {ticket_id}"]
            if row.get("subject"):
                parts.append(row["subject"])
            if status:
                parts.append(f"status={status}")
            if row.get("priority"):
                parts.append(f"priority={row['priority']}")
            return " | ".join(parts)

        if customer_id:
            parts = [f"Customer {customer_id}"]
            if company:
                parts.append(company)
            if status:
                parts.append(f"status={status}")
            return " | ".join(parts)

        if source_id:
            parts = [f"Source {source_id}"]
            if row.get("line_type"):
                parts.append(row["line_type"])
            if gateway:
                parts.append(f"gateway={gateway}")
            if status:
                parts.append(f"status={status}")
            return " | ".join(parts)

        if number:
            parts = [f"Number {number}"]
            if status:
                parts.append(f"status={status}")
            if operator:
                parts.append(f"operator={operator}")
            return " | ".join(parts)

        if gateway:
            return f"Gateway {gateway} → {company} ({row.get('status', '')})"

        return ", ".join(f"{k}={v}" for k, v in row.items() if v)
