"""
Offline rule-based parser — no API calls.

Used as:
  - Primary parser when PARSER_MODE=rule or no API key is set.
  - Fallback in HybridQueryParser when the LLM parser fails.

"""

from __future__ import annotations

import re

from models import ParsedQuery
from parsers.base import ParserError
from parsers.normalizers import (
    normalize_customer_id,
    normalize_gateway_id,
    normalize_phone,
    normalize_source_id,
    normalize_ticket_id,
)

_GATEWAY_PREFIX_RE = re.compile(r"\b(GW\d+|GQ\d+)\b", re.IGNORECASE)
_GATEWAY_NUMERIC_RE = re.compile(r"\bgateway(?:\s+id)?\s+(\d+)\b", re.IGNORECASE)

_NUMBER_RAW_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+91[\s\-.]?|0{2}91[\s\-.]?)?"
    r"(?:\d[\s\-.]?){9}\d"
    r"(?!\d)",
)
_TICKET_RE = re.compile(r"\b(TKT\d+)\b", re.IGNORECASE)
_CUSTOMER_RE = re.compile(r"\b(CUST\d+)\b", re.IGNORECASE)
_SOURCE_RE = re.compile(r"\b(SRC\d+)\b", re.IGNORECASE)


_OPERATOR_ALIASES: dict[str, str] = {
    
    "idea":                 "IDEA",
    "vi":                   "IDEA",
    "voda":                 "IDEA",
    "vodafone idea":        "IDEA",
    # Vodafone and Idea merged into a single operator; the sheet records both
    # under "IDEA", so every phrasing has to resolve to the same value or the
    # filter silently returns zero rows.
    "vodafone":             "IDEA",

    "tata":                 "TATA",
    "tata comm":            "TATA",
    "tata communications":  "TATA",

    "jio":                  "Jio",
    "reliance jio":         "Jio",
    "reliance":             "Jio",

    "airtel":               "Airtel",
    "bharti airtel":        "Airtel",

    "bsnl":                 "BSNL",

    "knowlarity":           "Knowlarity",
    "syniverse":            "Syniverse",
    "tanla":                "Tanla",
}

_SORTED_OPERATORS = sorted(_OPERATOR_ALIASES.keys(), key=len, reverse=True)

_NUMBER_TYPE_MAP: dict[str, str] = {

    "dedicated incoming sms":   "Dedicated Incoming SMS",
    "incoming sms":             "Dedicated Incoming SMS",
    "toll free":                "Toll free",
    "tollfree":                 "Toll free",
    "toll-free":                "Toll free",
    "missed call":              "Dedicated Missed call",
    "dedicated missed call":    "Dedicated Missed call",
    "transactional":            "transactional",
    "promotional":              "promotional",
    "promo":                    "promotional",
    "did":                      "did",
    "direct inward":            "did",
}

_MULTI_WORD_STATUS: list[tuple[str, str]] = [
    ("temporarily deactivated",         "Temporarily Deactivated"),
    ("temp deactivated",                "Temporarily Deactivated"),
    ("temp. deactivated",               "Temporarily Deactivated"),
    ("free pool",                       "Free Pool"),
    ("fresh number",                    "Fresh Number (To Be Activated)"),
    ("to be activated",                 "Fresh Number (To Be Activated)"),
    ("in_progress",                     "in_progress"),
    ("in progress",                     "in_progress"),
]

_TYPO_MAP: dict[str, str] = {
    "sttaus":   "status",
    "staus":    "status",
    "statu ":   "status ",
    "stauts":   "status",
    "memeber":  "member",
    "membrs":   "members",
    "suspened": "suspended",
    "suspnded": "suspended",
    "inactve":  "inactive",
    "inacitve": "inactive",
    "actve":    "active",
    "acitve":   "active",
    "gatewy":   "gateway",
    "gatway":   "gateway",
    "tickt":    "ticket",
    "custmer":  "customer",
    "custoemr": "customer",
    "numbr":    "number",
    "numer":    "number",
}

_LIST_VERBS = frozenset({
    "show", "list", "find", "get", "return", "display",
    "give", "fetch", "pull", "retrieve",
})

_LIST_ENTITY_NOUNS: dict[str, str] = {
    "vmn":          "number",
    "vmns":         "number",
    "number":       "number",
    "numbers":      "number",
    "member":       "number",
    "members":      "number",
    "line":         "number",
    "lines":        "number",
    "did":          "number",
    "dids":         "number",
    "tollfree":     "number",
    "records":      "number",
    "entries":      "number",
    "entry":        "number",
    "gateway":      "gateway",
    "gateways":     "gateway",
    "gw":           "gateway",
    "ticket":       "ticket",
    "tickets":      "ticket",
    "issue":        "ticket",
    "issues":       "ticket",
    "customer":     "customer",
    "customers":    "customer",
    "account":      "customer",
    "accounts":     "customer",
    "source":       "source",
    "sources":      "source",
    "connection":   "source",
    "connections":  "source",
}

_DETAIL_PHRASES = frozenset({
    "complete details", "full details", "show details", "all details",
    "full info", "complete info", "all info", "everything about",
    "tell me about", "check", "verify", "look up", "lookup",
    "pull up", "get info", "what about", "info on",
    "details for", "details of", "show me", "find",
})

_GREETING_RE = re.compile(
    r"^(hi|hello|hey|greetings|good\s+(?:morning|afternoon|evening)"
    r"|how\s+are\s+you)\b",
    re.IGNORECASE,
)

_VAGUE_RE = re.compile(
    r"^(i\s+need\s+help|help(\s+me)?|what\s+happened|check\s+this|"
    r"any\s+update|status\s+update|please\s+help|can\s+you\s+help)\b",
    re.IGNORECASE,
)

class RuleBasedQueryParser:
    """Parses common support questions using regex — no API calls."""

    def parse(self, question: str) -> ParsedQuery:
        raw = question.strip()
        if not raw:
            raise ParserError("Question cannot be empty.")

        lowered, preserved = _normalize_text(raw)

        if _GREETING_RE.search(lowered):
            raise ParserError(
                "I'm the CPaaS support assistant. Ask me about phone numbers, "
                "gateways, operators, tickets, customers, or sources — for example: "
                "'What is the status of 9152001212?' or 'Find ticket TKT001'."
            )

        if _VAGUE_RE.search(lowered.strip().rstrip("?.")):
            raise ParserError(
                "Could you be more specific? Please share a phone number, "
                "gateway ID, ticket ID, or customer ID. For example: "
                "'Status of 9152001212' or 'Find TKT001'."
            )

        if list_query := _try_parse_list_query(lowered, preserved):
            return list_query

        if src := _first_source(preserved):
            return ParsedQuery(
                entity_type="source",
                entity_value=src,
                action="lookup",
                requested_field="all",
            )

        if tid := _first_ticket(preserved):
            return ParsedQuery(
                entity_type="ticket",
                entity_value=tid,
                action="lookup",
                requested_field="all",
            )

        if cid := _first_customer(preserved):
            return ParsedQuery(
                entity_type="customer",
                entity_value=cid,
                action="lookup",
                requested_field="all",
            )

        if re.search(r"\boperator\b", lowered) and (num := _first_number(preserved)):
            return ParsedQuery(
                entity_type="operator",
                entity_value=num,
                action="lookup",
                requested_field="operator",
            )

        if (
            re.search(r"\b(company|owns|owner|mapped|attached|customer)\b", lowered)
            and (gw := _first_gateway(preserved))
        ):
            return ParsedQuery(
                entity_type="gateway",
                entity_value=gw,
                action="lookup",
                requested_field="company_name",
            )

        if (
            re.search(r"\b(company|owns|owner|belongs)\b", lowered)
            and (num := _first_number(preserved))
        ):
            return ParsedQuery(
                entity_type="number",
                entity_value=num,
                action="lookup",
                requested_field="company_name",
            )

        if re.search(r"\bregion\b", lowered) and (gw := _first_gateway(preserved)):
            return ParsedQuery(
                entity_type="gateway",
                entity_value=gw,
                action="lookup",
                requested_field="region",
            )

        if re.search(r"\bstatus\b", lowered) and (gw := _first_gateway(preserved)):
            return ParsedQuery(
                entity_type="gateway",
                entity_value=gw,
                action="lookup",
                requested_field="status",
            )

        if re.search(r"\bstatus\b", lowered) and (num := _first_number(preserved)):
            return ParsedQuery(
                entity_type="number",
                entity_value=num,
                action="lookup",
                requested_field="status",
            )
        
        if gw := _first_gateway(preserved):
            return ParsedQuery(
                entity_type="gateway",
                entity_value=gw,
                action="lookup",
                requested_field="all",
            )

        if num := _first_number(preserved):
            return ParsedQuery(
                entity_type="number",
                entity_value=num,
                action="lookup",
                requested_field="all",
            )

        raise ParserError(
            "I could not understand that. Examples: "
            "'Show all inactive members', "
            "'What is the status of 9152001212?', "
            "'Which company owns gateway GW123?', "
            "'Find ticket TKT001'."
        )


def _normalize_text(raw: str) -> tuple[str, str]:
    """
    Return (lowered_normalized, preserved_normalized).

    lowered  — lowercased + typos corrected; used for intent detection.
    preserved — typos corrected, original case kept; used for ID extraction.
    """
    lowered = raw.lower()
    for wrong, right in _TYPO_MAP.items():
        lowered = lowered.replace(wrong, right)

    preserved = re.sub(r"\bGQ(\d+)\b", r"GW\1", raw, flags=re.IGNORECASE)
    for wrong, right in _TYPO_MAP.items():
        preserved = re.sub(re.escape(wrong), right, preserved, flags=re.IGNORECASE)

    return lowered, preserved

def _first_number(text: str) -> str | None:
    match = _NUMBER_RAW_RE.search(text)
    if not match:
        return None
    return normalize_phone(match.group(0))


def _first_gateway(text: str) -> str | None:
    """
    Recognises:
      GW123 / gw123 / GQ123  → normalised to "GW123"
      gateway 470            → "470"  (numeric IDs as stored in real sheet)
      gateway id 470         → "470"
    """
    m = _GATEWAY_PREFIX_RE.search(text)
    if m:
        raw = m.group(1)
        normalised = normalize_gateway_id(raw)
        return normalised if normalised else raw.upper()

    m2 = _GATEWAY_NUMERIC_RE.search(text)
    if m2:
        return m2.group(1) 

    return None


def _first_ticket(text: str) -> str | None:
    m = _TICKET_RE.search(text)
    return normalize_ticket_id(m.group(1)) if m else None


def _first_customer(text: str) -> str | None:
    m = _CUSTOMER_RE.search(text)
    return normalize_customer_id(m.group(1)) if m else None


def _first_source(text: str) -> str | None:
    m = _SOURCE_RE.search(text)
    return normalize_source_id(m.group(1)) if m else None

def _try_parse_list_query(lowered: str, preserved: str) -> ParsedQuery | None:
    """
    Return a list ParsedQuery if the question has list intent, or None.

    Guard: if a specific entity ID is present (TKT001, CUST001, gateway 470,
    GW123 etc.), this is a single-record lookup, not a list — return None and
    let the single-lookup branches handle it.

    Two tiers:
    1. EXPLICIT ALL: "show all numbers", "list all gateways", "get all VMNs"
       → list with empty filters (return every record of that type).
       The word "all" makes the intent unambiguous.

    2. QUALIFIED LIST: "show active numbers", "list Jio lines",
       "show all inactive gateways"
       → list with filters extracted from the question.
       At least one filter must be present for this tier.

    3. BARE VERB + NOUN with no qualifier and no "all":
       "show numbers", "list records" etc.
       → ambiguous intent; treated the same as tier 1 (return all records)
       when the noun is specific enough (gateway, ticket, customer, source).
       For "number"/"vmn"/"member" without "all", we also allow it since the
       support team asking "show numbers" clearly wants to see numbers.
    """
    if not _has_list_intent(lowered):
        return None

    if _has_specific_id(preserved):
        return None

    entity_type = _infer_list_entity_type(lowered)
    has_all = _has_all_keyword(lowered)

    filters: dict[str, str] = {}

    if status := _extract_status_filter(lowered):
        filters["status"] = status

    if op := _extract_operator_filter(lowered):
        filters["operator"] = op

    if nt := _extract_number_type_filter(lowered):
        filters["number_type"] = nt

    if pr := _extract_priority_filter(lowered):
        filters["priority"] = pr

    if not filters:
        if has_all or entity_type != "number":
            
            return ParsedQuery(
                entity_type=entity_type,
                entity_value=None,
                action="list",
                requested_field="all",
                filters={},
            )
        if _has_specific_entity_noun(lowered):
            return ParsedQuery(
                entity_type=entity_type,
                entity_value=None,
                action="list",
                requested_field="all",
                filters={},
            )
        
        return None

    return ParsedQuery(
        entity_type=entity_type,
        entity_value=None,
        action="list",
        requested_field="all",
        filters=filters,
    )


def _has_specific_id(preserved: str) -> bool:
    """
    True if preserved text contains a concrete structured entity ID.
    Used to prevent list-intent matching from stealing single-record lookups.
    """
    if _TICKET_RE.search(preserved):
        return True
    if _CUSTOMER_RE.search(preserved):
        return True
    if _SOURCE_RE.search(preserved):
        return True
    if _GATEWAY_PREFIX_RE.search(preserved):
        return True
    if _GATEWAY_NUMERIC_RE.search(preserved):
        return True
    return False


def _has_list_intent(lowered: str) -> bool:
    """True if the question clearly asks for multiple records."""
    tokens = lowered.split()

    
    for i, tok in enumerate(tokens[:-1]):
        if tok in _LIST_VERBS and tokens[i + 1] == "all":
            return True

    
    has_verb = any(t in _LIST_VERBS for t in tokens)
    has_entity_noun = any(t in _LIST_ENTITY_NOUNS for t in tokens)
    if has_verb and has_entity_noun:
        return True

    
    if re.search(r"\ball\s+(active|inactive|suspended)\b", lowered):
        return True

    if "associated with" in lowered or "associated to" in lowered:
        return True

    return False


def _has_all_keyword(lowered: str) -> bool:
    """True if the question contains an explicit 'all' quantifier."""
    return bool(re.search(r"\ball\b", lowered))


def _has_specific_entity_noun(lowered: str) -> bool:
    """
    True if the question contains a specific, unambiguous entity noun.
    'records' and 'entries' are excluded as they are too generic.
    """
    ambiguous = {"records", "entries", "entry"}
    tokens = lowered.split()
    return any(
        t in _LIST_ENTITY_NOUNS and t not in ambiguous
        for t in tokens
    )


def _infer_list_entity_type(lowered: str) -> str:
    """Return entity type from context nouns; defaults to 'number'."""
    tokens = lowered.split()
    for tok in tokens:
        if tok in _LIST_ENTITY_NOUNS:
            return _LIST_ENTITY_NOUNS[tok]
    return "number"


def _extract_status_filter(lowered: str) -> str | None:
    """
    Extract status filter.

    Checks multi-word phrases first, then single-word status words.
    'inactive' is checked before 'active' to avoid false matches.
    """
    
    for phrase, canonical in _MULTI_WORD_STATUS:
        if phrase in lowered:
            return canonical

    
    if re.search(r"\binactive\b", lowered):
        return "inactive"
    if re.search(r"\bsuspended\b", lowered):
        return "suspended"
    if re.search(r"\bopen\b", lowered):
        return "open"
    if re.search(r"\bresolved\b", lowered):
        return "resolved"
    if re.search(r"\bactive\b", lowered):
        return "active"
    return None


def _extract_operator_filter(lowered: str) -> str | None:
    """
    Extract telecom operator from text.

    Checks longest aliases first so 'vodafone idea' matches before 'vodafone',
    and 'tata communications' matches before 'tata'.
    """
    for alias in _SORTED_OPERATORS:
        if re.search(r"\b" + re.escape(alias) + r"\b", lowered):
            return _OPERATOR_ALIASES[alias]
    return None


def _extract_number_type_filter(lowered: str) -> str | None:
    for keyword, canonical in _NUMBER_TYPE_MAP.items():
        if keyword in lowered:
            return canonical
    return None


def _extract_priority_filter(lowered: str) -> str | None:
    if re.search(r"\bhigh[\s\-]?priority\b", lowered):
        return "high"
    if re.search(r"\bmedium[\s\-]?priority\b", lowered):
        return "medium"
    if re.search(r"\blow[\s\-]?priority\b", lowered):
        return "low"
    return None


def _has_detail_intent(lowered: str) -> bool:
    return any(phrase in lowered for phrase in _DETAIL_PHRASES)
