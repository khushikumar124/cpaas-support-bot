"""
Lightweight conversation memory for the CPaaS support bot.

Design constraints
------------------
* No external dependencies — plain Python dicts + dataclasses.
* BotService, Retriever, DataSource are NOT modified.
* Memory is resolved BEFORE a question reaches BotService.ask().
  The context resolver rewrites the question string so the parser always
  receives a fully-specified, self-contained input.
* In-process dict keyed by conversation_id (str).
  Caveat: memory is per-worker. Multi-worker uvicorn deployments will lose
  context on cross-worker requests. A shared store (Redis / DB) replaces
  this dict for production.
* Bounded: evicts oldest entry when MAX_CONVERSATIONS is reached; each
  entry expires after TTL_SECONDS of inactivity.

Phase 1 scope
-------------
Stores only the MOST RECENT successfully resolved entity per conversation.
Sufficient for:
    "Show details of 9152001212"   → sets entity = (number, 9152001212)
    "What is its status?"          → resolved: status of 9152001212
    "Who owns it?"                 → resolved: owner of 9152001212
    "Which operator is assigned?"  → resolved: operator of 9152001212
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MAX_CONVERSATIONS: int = 500
TTL_SECONDS: int = 60 * 30   # 30-minute inactivity window


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ConversationState:
    last_entity_type: str | None = None
    last_entity_value: str | None = None
    last_records: list[dict[str, Any]] = field(default_factory=list)
    last_question: str = ""
    last_active: float = field(default_factory=time.time)

    def update(
        self,
        entity_type: str,
        entity_value: str | None,
        records: list[dict[str, Any]],
        question: str,
    ) -> None:
        self.last_entity_type = entity_type
        self.last_entity_value = entity_value
        self.last_records = records
        self.last_question = question
        self.last_active = time.time()

    def has_entity(self) -> bool:
        return bool(self.last_entity_type and self.last_entity_value)


# ---------------------------------------------------------------------------
# Memory store
# ---------------------------------------------------------------------------

class ConversationMemory:
    def __init__(
        self,
        max_conversations: int = MAX_CONVERSATIONS,
        ttl_seconds: int = TTL_SECONDS,
    ) -> None:
        self._store: dict[str, ConversationState] = {}
        self._max = max_conversations
        self._ttl = ttl_seconds

    def get(self, conversation_id: str) -> ConversationState | None:
        if conversation_id not in self._store:
            return None
        state = self._store[conversation_id]
        if time.time() - state.last_active > self._ttl:
            del self._store[conversation_id]
            logger.debug("Session %s expired", conversation_id)
            return None
        return state

    def get_or_create(self, conversation_id: str) -> ConversationState:
        state = self.get(conversation_id)
        if state is None:
            state = ConversationState()
            self._store[conversation_id] = state
            self._evict_if_full()
        return state

    def update(
        self,
        conversation_id: str,
        entity_type: str,
        entity_value: str | None,
        records: list[dict[str, Any]],
        question: str,
    ) -> None:
        state = self.get_or_create(conversation_id)
        state.update(entity_type, entity_value, records, question)
        logger.debug(
            "Memory updated cid=%s type=%s value=%s",
            conversation_id, entity_type, entity_value,
        )

    def _evict_if_full(self) -> None:
        if len(self._store) <= self._max:
            return
        oldest = min(self._store, key=lambda k: self._store[k].last_active)
        del self._store[oldest]
        logger.debug("Evicted session %s (store full)", oldest)

    @property
    def size(self) -> int:
        return len(self._store)


# ---------------------------------------------------------------------------
# Context resolver
# ---------------------------------------------------------------------------

# Back-reference pronouns/phrases that signal a follow-up
_BACK_REFERENCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bits\b", re.IGNORECASE),
    re.compile(r"\bit\b", re.IGNORECASE),
    re.compile(r"\bthis\s+(number|vmn|gateway|gw|ticket|customer|source)\b", re.IGNORECASE),
    re.compile(r"\bthat\s+(number|vmn|gateway|gw|ticket|customer|source)\b", re.IGNORECASE),
    re.compile(r"\bthe\s+(number|vmn|gateway|gw|ticket|customer|source)\b", re.IGNORECASE),
    re.compile(r"\bsame\s+(number|vmn|gateway|gw|ticket|customer|source)\b", re.IGNORECASE),
    re.compile(r"\bthis one\b", re.IGNORECASE),
    re.compile(r"\bthat one\b", re.IGNORECASE),
]

# Concrete identifiers — if present, the question is self-contained
_IDENTIFIER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\d{10}\b"),
    re.compile(r"\+91\d{10}\b"),
    re.compile(r"\bGW\d+\b", re.IGNORECASE),
    re.compile(r"\bGQ\d+\b", re.IGNORECASE),
    re.compile(r"\bTKT\d+\b", re.IGNORECASE),
    re.compile(r"\bCUST\d+\b", re.IGNORECASE),
    re.compile(r"\bSRC\d+\b", re.IGNORECASE),
]

# Vocabulary for bare follow-up detection
_SUPPORT_FIELD_WORDS = frozenset([
    "status",
    "operator",
    "company",
    "owner",
    "customer",
    "region",
    "priority",
    "subject",
    "assigned",
    "details",
    "info",
    "provisioned",
    "created",
    "type",
    "host",
    "port",
    "account",
    "manager",
])

_LIST_SIGNAL_WORDS: frozenset[str] = frozenset([
    "all", "list", "every", "each", "multiple", "records",
])

_ENTITY_NOUN: dict[str, str] = {
    "number": "number",
    "vmn": "number",
    "operator": "number",
    "gateway": "gateway",
    "company": "gateway",
    "ticket": "ticket",
    "customer": "customer",
    "source": "source",
}


class ContextResolver:
    """
    Rewrites pronoun / bare field follow-up questions to include the last
    known entity so the parser always receives a self-contained input.
    """

    def __init__(self, memory: ConversationMemory) -> None:
        self._memory = memory

    def resolve(
        self, question: str, conversation_id: str | None
    ) -> tuple[str, bool]:
        """Return (resolved_question, context_was_injected)."""
        if not conversation_id:
            return question, False

        state = self._memory.get(conversation_id)
        if state is None or not state.has_entity():
            return question, False

        # Self-contained question — leave unchanged
        if _has_concrete_identifier(question):
            return question, False

        # Explicit back-reference pronoun
        if _has_back_reference(question):
            rewritten = _inject_entity(question, state)
            logger.info("Context injected cid=%s: %r → %r", conversation_id, question, rewritten)
            return rewritten, True

        # Bare follow-up field question (short, no list intent, field vocabulary)
        if _is_bare_followup(question):
            rewritten = _prefix_entity(question, state)
            logger.info("Bare follow-up resolved cid=%s: %r → %r", conversation_id, question, rewritten)
            return rewritten, True

        return question, False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _has_concrete_identifier(question: str) -> bool:
    return any(p.search(question) for p in _IDENTIFIER_PATTERNS)


def _has_back_reference(question: str) -> bool:
    return any(p.search(question) for p in _BACK_REFERENCE_PATTERNS)


def _is_bare_followup(question: str) -> bool:
    """
    Only treat vague questions as follow-ups.

    Examples:
        Status?
        Which operator?
        Who owns it?

    NOT:
        gateway 531
        gateway id 470
        9152001212
        ticket TKT001
    """

    q = question.lower().strip().rstrip("?. ")

    # If the question contains any explicit entity reference,
    # NEVER treat it as a follow-up.
    if (
        re.search(r"\b\d{10}\b", q)
        or re.search(r"\bgateway\b", q)
        or re.search(r"\bgateway\s+id\b", q)
        or re.search(r"\bgw\d+\b", q)
        or re.search(r"\bgq\d+\b", q)
        or re.search(r"\btkt\d+\b", q)
        or re.search(r"\bcust\d+\b", q)
    ):
        return False

    words = q.split()

    if len(words) > 6:
        return False

    if any(w in _LIST_SIGNAL_WORDS for w in words):
        return False

    return any(w in _SUPPORT_FIELD_WORDS for w in words)


def _inject_entity(question: str, state: ConversationState) -> str:
    """
    Inline pronoun substitution; falls back to prefix if no match.

    "What is its status?"   → "What is gateway 470's status?"
    "Who owns it?"          → "Who owns gateway 470?"
    "Who owns this gateway?"→ "Who owns gateway 470?"

    The substituted text is *qualified* with the entity noun rather than being
    the bare identifier. A bare "470" is not self-describing — the rule parser
    cannot tell it from a ticket or customer number and rejects the question —
    whereas "gateway 470" round-trips through both parsers.
    """
    entity_type = state.last_entity_type or "number"
    noun = _ENTITY_NOUN.get(entity_type, entity_type)
    entity_value = _qualified_reference(state)
    q = question.strip()

    # "its" → "<value>'s"
    result = re.sub(r"\bits\b", f"{entity_value}'s", q, flags=re.IGNORECASE)
    # bare "it" → entity value
    result = re.sub(r"\bit\b", entity_value, result, flags=re.IGNORECASE)
    # "this/that/the/same/above <noun>" → entity value
    result = re.sub(
        r"\b(this|that|the|same|above)\s+" + re.escape(noun) + r"\b",
        entity_value, result, flags=re.IGNORECASE,
    )
    # "this one" / "that one" → entity value
    result = re.sub(r"\b(this|that)\s+one\b", entity_value, result, flags=re.IGNORECASE)
    # "this/that <any entity noun>" → entity value
    result = re.sub(
        r"\b(this|that)\s+(number|vmn|gateway|gw|ticket|customer|source)\b",
        entity_value, result, flags=re.IGNORECASE,
    )

    if result != q:
        return result.strip()

    return _prefix_entity(q, state)


def _qualified_reference(state: ConversationState) -> str:
    """
    Return the remembered entity as a self-describing phrase.

    Identifiers that already carry their own type — a 10-digit number, or a
    TKT/CUST/SRC/GW prefix — are returned as-is. Bare numeric IDs get the
    entity noun prepended so the parser can classify them.
    """
    value = str(state.last_entity_value or "").strip()
    entity_type = state.last_entity_type or "number"
    noun = _ENTITY_NOUN.get(entity_type, entity_type)

    if not value:
        return value
    if re.fullmatch(r"\d{10}", value):
        return value
    if re.match(r"(?i)^(GW|GQ|TKT|CUST|SRC)\d+$", value):
        return value
    return f"{noun} {value}"


def _prefix_entity(question: str, state: ConversationState) -> str:
    """
    Safe fallback: prepend 'Regarding <noun> <value>: ' to the question.
    The parser will extract the identifier from the prefix.

    "Which operator is assigned?" → "Regarding number 9152001212: Which operator is assigned?"
    """
    entity_value = state.last_entity_value
    entity_type = state.last_entity_type or "number"
    noun = _ENTITY_NOUN.get(entity_type, entity_type)
    return f"Regarding {noun} {entity_value}: {question.strip()}"
