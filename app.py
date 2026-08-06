
from __future__ import annotations

import sys
import uuid

from config import ANSWER_GENERATION
from context.memory import ConversationMemory, ContextResolver
from core.answer_generator import get_answer_generator
from core.bot_service import BotService
from core.query_router import RoutingError
from datasources.factory import create_data_source
from logging_config import setup_logging
from parsers import create_parser
from parsers.base import ParserError


def run_cli() -> None:
    setup_logging()

    print("CPaaS Support Bot")
    print("Ask about numbers, gateways, tickets, customers, and sources.")
    print("Follow-up questions are supported (e.g. 'What is its status?').")
    print("Type 'quit' or 'exit' to stop.\n")

    try:
        parser = create_parser()
        data_source = create_data_source()
        service = BotService(parser=parser, data_source=data_source)
    except ParserError as exc:
        print(f"Startup error: {exc}", file=sys.stderr)
        sys.exit(1)

    session_id = str(uuid.uuid4())
    memory = ConversationMemory()
    resolver = ContextResolver(memory)
    generator = get_answer_generator() if ANSWER_GENERATION else None

    while True:
        try:
            raw_question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not raw_question:
            continue
        if raw_question.lower() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break

        
        resolved, context_used = resolver.resolve(raw_question, session_id)
        if context_used:
            print(f"  [Context] Resolved to: {resolved}")

        try:
            parsed, result, formatter_answer = service.ask(resolved)
        except ParserError as exc:
            print(f"\nBot: {exc}\n")
            continue
        except RoutingError as exc:
            print(f"\nBot: I'm not sure how to look that up. ({exc})\n")
            continue

        if result.success:
            memory.update(
                conversation_id=session_id,
                entity_type=parsed.entity_type,
                entity_value=parsed.entity_value,
                records=result.records,
                question=raw_question,
            )

        answer = formatter_answer
        if generator is not None and result.success:
            state = memory.get(session_id)
            generated = generator.generate(
                question=raw_question,
                parsed=parsed,
                result=result,
                state=state,
            )
            if generated:
                answer = generated

        print(f"\nBot: {answer}\n")


if __name__ == "__main__":
    run_cli()
