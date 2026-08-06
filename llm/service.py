"""OpenAI-backed LLM service.

All direct OpenAI SDK usage belongs in this module. Callers receive plain
Python values and do not depend on provider-specific APIs.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import OpenAI

from context.memory import ConversationState
from models import ParsedQuery, RetrievalResult

logger = logging.getLogger(__name__)

_MAX_PARSE_RETRIES = 2
_MAX_ANSWER_RETRIES = 1
_RETRY_DELAY_S = 0.75


class LLMServiceError(Exception):
    """Raised when an LLM call fails or returns unusable output."""


_PARSER_SYSTEM_PROMPT = """\
You are a structured query parser for a CPaaS customer-support data assistant.
Return only one JSON object. Do not include markdown, explanation, or commentary.

Normal parse schema:
{
  "entity_type": "number|gateway|source|customer|ticket|operator",
  "entity_value": "identifier string or null for list queries",
  "action": "lookup|list",
  "requested_field": "field name or all",
  "filters": {"column": "value"},
  "confidence": 0.0
}

Clarification schema:
{
  "needs_clarification": true,
  "clarification_question": "one focused question"
}

Entity rules:
- number: phone number, VMN, virtual mobile number, DID, long-code, line. Normalize to 10 digits.
- gateway: GW-prefixed gateway ID. Correct GQ-prefixed typos to GW.
- source: SRC-prefixed source ID.
- customer: CUST-prefixed customer ID or company/customer account.
- ticket: TKT-prefixed ticket ID.
- operator: only when asking which telecom operator is assigned to one number.

Actions:
- lookup fetches one specific record and must include entity_value.
- list fetches records matching filters and must set entity_value to null.

Requested fields by entity:
- number/vmn: status, operator, company_name, gateway_id, provisioned_date, number_type
- gateway: status, company_name, region, created_date
- source: status, line_type, host, port, gateway_id
- customer: status, company_name, account_manager, primary_gateway
- ticket: status, subject, priority, created_date, number
- Use requested_field "all" for details/check/verify/tell me about/look up questions.

Filters (emit these exact stored values — a filter is matched verbatim against
the sheet, so an unrecognised spelling silently returns zero rows):
- status values: active, inactive, suspended, open, resolved, in_progress
- operator values: Airtel, Jio, IDEA, TATA, BSNL
- map Vodafone, Vodafone Idea, Vi, Voda to IDEA; map Tata, Tata Comm, Tata Communications to TATA; map Reliance, Reliance Jio to Jio
- number_type values: transactional, promotional, did, Toll free, Dedicated Incoming SMS, Dedicated Missed call
- map tollfree, toll-free to "Toll free"; map missed call to "Dedicated Missed call"; map incoming sms to "Dedicated Incoming SMS"
- priority values: high, medium, low
- "inactive" must never become "active".

Examples:
Q: What is the status of 9152001212?
{"entity_type":"number","entity_value":"9152001212","action":"lookup","requested_field":"status","filters":{},"confidence":1.0}
Q: Check 915-200-1212
{"entity_type":"number","entity_value":"9152001212","action":"lookup","requested_field":"all","filters":{},"confidence":0.9}
Q: Who owns gateway GW470?
{"entity_type":"gateway","entity_value":"470","action":"lookup","requested_field":"company_name","filters":{},"confidence":1.0}
Q: Show all active VMNs
{"entity_type":"number","entity_value":null,"action":"list","requested_field":"all","filters":{"status":"active"},"confidence":1.0}
Q: List all inactive numbers
{"entity_type":"number","entity_value":null,"action":"list","requested_field":"all","filters":{"status":"inactive"},"confidence":1.0}
Q: Show all Vodafone numbers
{"entity_type":"number","entity_value":null,"action":"list","requested_field":"all","filters":{"operator":"IDEA"},"confidence":0.9}
Q: Show all open high-priority tickets
{"entity_type":"ticket","entity_value":null,"action":"list","requested_field":"all","filters":{"status":"open","priority":"high"},"confidence":1.0}
Q: I need help
{"needs_clarification":true,"clarification_question":"What would you like help with? Please mention a phone number, gateway ID, ticket number, or customer account."}
"""

_ANSWER_SYSTEM_PROMPT = """\
You are a CPaaS customer-support assistant answering internal support-team questions.

Strict rules:
1. Use only facts from the DATA BLOCK.
2. Do not guess or invent values. If a fact is missing, say it is not in the retrieved data.
3. If no records were found, tell the user clearly.
4. Keep answers concise and professional. Use one or two sentences for simple lookups.
5. Plain text only. For multi-record results, a short bullet list is acceptable.
6. Render status values naturally, for example in_progress as in progress.
"""


class OpenAILLMService:
    """Thin wrapper around the official OpenAI Python SDK."""

    def __init__(self, api_key: str | None, model: str) -> None:
        if not api_key:
            raise LLMServiceError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        if not model:
            raise LLMServiceError("OPENAI_MODEL is not set.")

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def parse_query(self, question: str) -> dict[str, Any]:
        """Parse a natural-language query into the structured JSON contract."""
        raw = self._chat_completion(
            system_prompt=_PARSER_SYSTEM_PROMPT,
            user_prompt=f"Parse this support question:\n{question}",
            temperature=0.0,
            max_tokens=600,
            json_response=True,
            retries=_MAX_PARSE_RETRIES,
        )
        return _extract_json(raw)

    def generate_answer(
        self,
        question: str,
        parsed: ParsedQuery,
        result: RetrievalResult,
        state: ConversationState | None = None,
    ) -> str | None:
        """Generate a grounded answer, returning None on failure."""
        try:
            answer = self._chat_completion(
                system_prompt=_ANSWER_SYSTEM_PROMPT,
                user_prompt=_build_answer_prompt(question, parsed, result, state),
                temperature=0.1,
                max_tokens=512,
                json_response=False,
                retries=_MAX_ANSWER_RETRIES,
            )
            return answer.strip() or None
        except LLMServiceError as exc:
            logger.warning("OpenAI answer generation failed: %s", exc)
            return None

    def _chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_response: bool,
        retries: int,
    ) -> str:
        last_exc: Exception | None = None
        kwargs: dict[str, Any] = {}
        if json_response:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(1, retries + 2):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                content = response.choices[0].message.content
                if not content:
                    raise LLMServiceError("OpenAI returned an empty response.")
                return content.strip()
            except Exception as exc:
                last_exc = exc
                message = str(exc)
                if attempt <= retries and _is_retryable_error(message):
                    logger.warning(
                        "OpenAI transient error (attempt %d/%d): %s",
                        attempt,
                        retries + 1,
                        message,
                    )
                    time.sleep(_RETRY_DELAY_S)
                    continue
                break

        raise LLMServiceError(f"OpenAI API call failed: {last_exc}") from last_exc


def _records_to_prompt_block(
    records: list[dict[str, Any]], empty_message: str | None = None
) -> str:
    if not records:
        return f"No records found. {empty_message or ''}".strip()

    return "\n".join(json.dumps(row, ensure_ascii=False) for row in records)


def _build_answer_prompt(
    question: str,
    parsed: ParsedQuery,
    result: RetrievalResult,
    state: ConversationState | None,
) -> str:
    context_block = ""
    if state and state.has_entity() and state.last_question:
        context_block = (
            "\nCONVERSATION CONTEXT (previous turn):\n"
            f"  Previous question: {state.last_question}\n"
            f"  Previous entity: {state.last_entity_type} = {state.last_entity_value}\n"
        )

    return (
        f"USER QUESTION: {question}\n"
        f"\nQUERY INTENT: entity_type={parsed.entity_type}, "
        f"action={parsed.action}, requested_field={parsed.requested_field}\n"
        f"{context_block}"
        "\nDATA BLOCK (retrieved records; use only these facts):\n"
        f"{_records_to_prompt_block(result.records, result.message or '')}\n"
        "\nAnswer the user's question using only the data block above."
    )


def _extract_json(text: str) -> dict[str, Any]:
    if not text:
        raise LLMServiceError("OpenAI returned an empty response.")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _extract_first_json_object(text)

    if not isinstance(data, dict):
        raise LLMServiceError("OpenAI returned JSON that is not an object.")
    return data


def _extract_first_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    if start == -1:
        raise LLMServiceError(f"No JSON object in OpenAI output: {text[:200]}")

    depth = 0
    in_string = False
    escape_next = False

    for index, char in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : index + 1]
                try:
                    data = json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise LLMServiceError(
                        f"Could not parse JSON from OpenAI output: {candidate[:200]}"
                    ) from exc
                if not isinstance(data, dict):
                    raise LLMServiceError("OpenAI returned JSON that is not an object.")
                return data

    raise LLMServiceError(f"Unbalanced JSON in OpenAI output: {text[:200]}")


def _is_retryable_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        signal in lowered
        for signal in (
            "connection",
            "timeout",
            "temporarily",
            "rate limit",
            "429",
            "500",
            "502",
            "503",
            "504",
            "unavailable",
        )
    )
