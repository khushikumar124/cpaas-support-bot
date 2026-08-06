"""LLM-backed answer generation with formatter fallback.

This module preserves the existing API used by api.py while delegating all
provider calls to llm.service.
"""

from __future__ import annotations

import logging

from config import OPENAI_API_KEY
from context.memory import ConversationState
from llm.factory import create_llm_service
from models import ParsedQuery, RetrievalResult

logger = logging.getLogger(__name__)


class LLMAnswerGenerator:
    """Converts retrieved records into a grounded natural-language answer."""

    def __init__(self) -> None:
        self._llm = create_llm_service()

    def generate(
        self,
        question: str,
        parsed: ParsedQuery,
        result: RetrievalResult,
        state: ConversationState | None = None,
    ) -> str | None:
        return self._llm.generate_answer(
            question=question,
            parsed=parsed,
            result=result,
            state=state,
        )


_generator: LLMAnswerGenerator | None = None


def get_answer_generator() -> LLMAnswerGenerator | None:
    """Return the lazy answer generator, or None so callers use formatter fallback."""
    global _generator
    if _generator is not None:
        return _generator
    if not OPENAI_API_KEY:
        return None
    try:
        _generator = LLMAnswerGenerator()
        return _generator
    except Exception as exc:
        logger.warning("Could not initialise LLMAnswerGenerator: %s", exc)
        return None
