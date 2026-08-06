"""LLM-powered natural-language query parser."""

from __future__ import annotations

from models import ParsedQuery
from parsers.base import ParserError
from parsers.normalizers import normalize_entity_value


class LLMQueryParser:
    """Parses questions into ParsedQuery using the configured LLM service."""

    def __init__(self) -> None:
        from llm.factory import create_llm_service

        self._llm = create_llm_service()

    def parse(self, question: str) -> ParsedQuery:
        question = question.strip()
        if not question:
            raise ParserError("Question cannot be empty.")

        try:
            data = self._llm.parse_query(question)
        except Exception as exc:
            raise ParserError(str(exc)) from exc

        return self._validate(data)

    @staticmethod
    def _validate(data: dict) -> ParsedQuery:
        if data.get("needs_clarification"):
            clarification = data.get(
                "clarification_question",
                "Could you provide more details? (e.g. a phone number, gateway ID, or ticket number)",
            )
            raise ParserError(str(clarification))

        confidence = data.get("confidence")
        if confidence is not None:
            try:
                conf_float = float(confidence)
            except (TypeError, ValueError):
                conf_float = 1.0
            if conf_float < 0.5:
                raise ParserError(
                    "I'm not confident I understood that. Could you rephrase? "
                    "For example: 'Status of 9152001212' or 'Show all active numbers'."
                )

        if not data.get("entity_type"):
            raise ParserError("Parser response missing entity_type.")

        query = ParsedQuery.from_dict(data)
        if not query.requested_field:
            raise ParserError("Parser response missing requested_field.")

        normalized_value = normalize_entity_value(query.entity_type, query.entity_value)
        if normalized_value == query.entity_value:
            return query

        return ParsedQuery(
            entity_type=query.entity_type,
            entity_value=normalized_value,
            action=query.action,
            requested_field=query.requested_field,
            filters=query.filters,
        )
