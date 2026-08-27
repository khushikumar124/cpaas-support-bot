from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import (
    ANSWER_GENERATION,
    BOT_API_KEY,
    CORS_ALLOWED_ORIGINS,
    DEMO_MODE,
    SLACK_BOT_TOKEN,
    SLACK_SIGNING_SECRET,
)
from context.memory import ConversationMemory, ContextResolver
from core.answer_generator import get_answer_generator
from core.bot_service import BotService
from datasources.factory import create_data_source
from logging_config import setup_logging
from parsers.factory import create_parser

logger = logging.getLogger(__name__)

_service: BotService | None = None
_memory: ConversationMemory = ConversationMemory()
_resolver: ContextResolver = ContextResolver(_memory)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service
    setup_logging()
    _service = BotService(parser=create_parser(), data_source=create_data_source())
    logger.info(
        "BotService ready. Answer generation: %s",
        "enabled" if ANSWER_GENERATION else "disabled (formatter fallback)",
    )
    yield
    _service = None

app = FastAPI(
    title="CPaaS Support Bot API",
    description="Internal support assistant for CPaaS customer data",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question")
    conversation_id: str | None = Field(
        default=None,
        description=(
            "Stable ID for the current chat session. "
            "Used to resolve follow-up questions ('What is its status?'). "
            "Omit for stateless single-turn queries."
        ),
    )


class QueryResponse(BaseModel):
    answer: str
    context_used: bool = Field(
        default=False,
        description="True if the answer was informed by conversation context.",
    )
    # Structured view of the same result. The plain `answer` string stays the
    # contract for text-only clients (n8n/Slack); richer clients use these to
    # render cards without re-parsing the prose.
    entity_type: str = Field(default="", description="Resolved entity type.")
    action: str = Field(default="", description="'lookup' or 'list'.")
    source: str = Field(default="", description="Sheet the rows came from.")
    records: list[dict] = Field(
        default_factory=list, description="Rows the answer was built from."
    )

def get_service() -> BotService:
    if _service is None:
        raise RuntimeError("BotService is not initialised")
    return _service


def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key")
) -> None:
    """Require a valid X-API-Key header. Only n8n should hold this key."""
    if DEMO_MODE and not BOT_API_KEY:
        # Public demo build: the data is fictional and there is nothing to
        # protect, so an unconfigured key means "open" rather than "reject".
        # A real deployment sets DEMO_MODE=false and falls through below.
        return
    if not BOT_API_KEY:
        # Fail closed: an unconfigured key must never be treated as "no auth".
        logger.error("BOT_API_KEY is not set — rejecting request.")
        raise HTTPException(status_code=401, detail="API authentication is not configured.")
    if not x_api_key or x_api_key != BOT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Structured JSON for malformed request bodies (e.g. missing 'question')."""
    return JSONResponse(status_code=400, content={"error": "bad_request", "detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort catch-all so every response is structured JSON, never a bare 500 page."""
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse, dependencies=[Depends(verify_api_key)])
def query(body: QueryRequest) -> QueryResponse:
    
    from parsers.base import ParserError
    from core.query_router import RoutingError

    raw_question = body.question.strip()
    cid = body.conversation_id

    
    resolved_question, context_used = _resolver.resolve(raw_question, cid)

    
    service = get_service()

    try:
        parsed, result, formatter_answer = service.ask(resolved_question)
    except ParserError as exc:
        logger.warning("Parse failed: %s", exc)
        return QueryResponse(
            answer=str(exc),
            context_used=context_used,
        )
    except RoutingError as exc:
        logger.warning("Routing failed: %s", exc)
        return QueryResponse(
            answer=f"I'm not sure how to look that up. ({exc})",
            context_used=context_used,
        )
    except Exception as exc:
        logger.exception("Unexpected error in BotService.ask()")
        return QueryResponse(
            answer="Something went wrong while processing your request. Please try again.",
            context_used=context_used,
        )

    
    if cid and result.success:
        _memory.update(
            conversation_id=cid,
            entity_type=parsed.entity_type,
            entity_value=parsed.entity_value,
            records=result.records,
            question=raw_question, 
        )

    
    answer = formatter_answer   

    if ANSWER_GENERATION and result.success:
        generator = get_answer_generator()
        if generator is not None:
            
            state = _memory.get(cid) if cid else None
            generated = generator.generate(
                question=raw_question,
                parsed=parsed,
                result=result,
                state=state,
            )
            if generated:
                answer = generated
                logger.info("Answer generation succeeded (%d chars)", len(answer))
            else:
                logger.info("Answer generation unavailable — using formatter output")

    return QueryResponse(
        answer=answer,
        context_used=context_used,
        entity_type=parsed.entity_type,
        action=parsed.action,
        source=result.source,
        records=result.records if result.success else [],
    )


# --- Optional Slack surface -------------------------------------------------
# Mounted only when both Slack settings are present, so the demo and the CLI
# are unaffected when they are not.
def _answer_for_slack(question: str, conversation_id: str) -> str:
    """Adapter seam: turn a Slack message into the bot's plain-text answer."""
    return query(
        QueryRequest(question=question, conversation_id=conversation_id)
    ).answer


if SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET:
    from slack_adapter import build_router

    app.include_router(
        build_router(
            signing_secret=SLACK_SIGNING_SECRET,
            bot_token=SLACK_BOT_TOKEN,
            answer_question=_answer_for_slack,
        )
    )
    logger.info("Slack adapter mounted at POST /slack/events")
else:
    logger.info(
        "Slack adapter not mounted "
        "(set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET to enable)."
    )
