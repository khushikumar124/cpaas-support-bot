"""Factory for the configured LLM service."""

from __future__ import annotations

import logging

from config import LLM_PROVIDER, OPENAI_API_KEY, OPENAI_MODEL
from llm.service import LLMServiceError, OpenAILLMService

logger = logging.getLogger(__name__)


def create_llm_service() -> OpenAILLMService:
    """Return the configured LLM service.

    The application currently supports OpenAI only. Keeping this factory small
    avoids leaking provider configuration outside the llm package.
    """
    if LLM_PROVIDER != "openai":
        raise LLMServiceError(
            f"Unsupported LLM_PROVIDER: '{LLM_PROVIDER}'. Supported value: openai"
        )

    logger.info("LLM provider: OpenAI (model=%s)", OPENAI_MODEL)
    return OpenAILLMService(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
