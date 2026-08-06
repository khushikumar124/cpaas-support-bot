"""
Shared identifier and phone-number normalizers.

Used by both LLMQueryParser (post-validation) and RuleBasedQueryParser
(pre-regex) so that the two parsers always produce identical canonical forms.

All functions are pure — no side-effects, no imports from the application layer.
"""

from __future__ import annotations

import re

_COUNTRY_CODE_RE = re.compile(r"^(?:\+91|0091)[\s\-.]?")

_SEPARATOR_RE = re.compile(r"[\s\-.()/]")

_TEN_DIGIT_RE = re.compile(r"^\d{10}$")

_TWELVE_DIGIT_91_RE = re.compile(r"^91(\d{10})$")


def normalize_phone(raw: str) -> str | None:
    """
    Normalize a raw phone number string to a canonical 10-digit string.

    Handles:
      +91 9152001212  → 9152001212
      0091-9152001212 → 9152001212
      915-200-1212    → 9152001212
      9152001212      → 9152001212 (passthrough)
      +919152001212   → 9152001212

    Returns None if the result is not exactly 10 digits.
    """
    if not raw:
        return None

    s = raw.strip()

    s = _COUNTRY_CODE_RE.sub("", s)

    s = _SEPARATOR_RE.sub("", s)

    m = _TWELVE_DIGIT_91_RE.match(s)
    if m:
        s = m.group(1)

    if _TEN_DIGIT_RE.match(s):
        return s

    return None

_GATEWAY_ID_RE = re.compile(r"^(?:GW|GQ)(\d+)$", re.IGNORECASE)
_TICKET_ID_RE = re.compile(r"^TKT(\d+)$", re.IGNORECASE)
_CUSTOMER_ID_RE = re.compile(r"^CUST(\d+)$", re.IGNORECASE)
_SOURCE_ID_RE = re.compile(r"^SRC(\d+)$", re.IGNORECASE)


def normalize_gateway_id(raw: str) -> str | None:
    """
    GW123 / gw123 / GQ123 (common typo) → GW123.
    Returns None if the string does not look like a gateway ID.
    """
    m = _GATEWAY_ID_RE.match(raw.strip())
    return f"GW{m.group(1)}" if m else None


def normalize_ticket_id(raw: str) -> str | None:
    """tkt001 / TKT001 → TKT001.  Returns None if not a ticket ID."""
    m = _TICKET_ID_RE.match(raw.strip())
    return f"TKT{m.group(1)}" if m else None


def normalize_customer_id(raw: str) -> str | None:
    """cust001 / CUST001 → CUST001.  Returns None if not a customer ID."""
    m = _CUSTOMER_ID_RE.match(raw.strip())
    return f"CUST{m.group(1)}" if m else None


def normalize_source_id(raw: str) -> str | None:
    """src001 / SRC001 → SRC001.  Returns None if not a source ID."""
    m = _SOURCE_ID_RE.match(raw.strip())
    return f"SRC{m.group(1)}" if m else None


def normalize_entity_value(entity_type: str, raw: str | None) -> str | None:
    """
    Dispatch normalization by entity type.

    Used in LLMQueryParser._validate() so that post-LLM output is always
    in canonical form before a ParsedQuery is constructed.
    """
    if raw is None:
        return None

    stripped = raw.strip()
    if not stripped:
        return None

    if entity_type in ("number", "vmn", "operator", "did", "tollfree"):
        return normalize_phone(stripped) or stripped

    if entity_type in ("gateway", "company"):
        return normalize_gateway_id(stripped) or stripped.upper()

    if entity_type == "ticket":
        return normalize_ticket_id(stripped) or stripped.upper()

    if entity_type == "customer":
        return normalize_customer_id(stripped) or stripped.upper()

    if entity_type == "source":
        return normalize_source_id(stripped) or stripped.upper()

    return stripped
