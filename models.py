"""Shared domain models for parsing and retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Action = Literal["lookup", "list"]


@dataclass(frozen=True)
class ParsedQuery:
    """Structured intent from any parser (LLM or rule-based)."""

    entity_type: str
    entity_value: str | None
    action: Action
    requested_field: str
    filters: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParsedQuery:
        """Build from parser JSON; accepts legacy ``filter`` key."""
        entity_value = data.get("entity_value")
        if entity_value is not None:
            entity_value = str(entity_value).strip() or None

        raw_filters = data.get("filters") or data.get("filter") or {}
        filters = (
            {str(k): str(v) for k, v in raw_filters.items()} if raw_filters else {}
        )

        requested_field = str(
            data.get("requested_field", "all")
        ).strip().lower()

        action = _resolve_action(data, requested_field)

        return cls(
            entity_type=str(data.get("entity_type", "")).strip().lower(),
            entity_value=entity_value,
            action=action,
            requested_field=requested_field,
            filters=filters,
        )

    def to_log_dict(self) -> dict[str, Any]:
        """Serializable snapshot for logging."""
        return {
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "action": self.action,
            "requested_field": self.requested_field,
            "filters": self.filters,
        }


def _resolve_action(data: dict[str, Any], requested_field: str) -> Action:
    explicit = str(data.get("action", "")).strip().lower()
    if explicit in ("lookup", "list"):
        return explicit  # type: ignore[return-value]
    if requested_field == "list":
        return "list"
    return "lookup"


@dataclass
class RetrievalResult:
    """Rows returned from a single sheet/data source."""

    source: str
    records: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True
    message: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.records

    @property
    def count(self) -> int:
        return len(self.records)
