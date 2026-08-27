"""
Slack Events API adapter.

A common deployment shape puts n8n between Slack and this service:

    Slack → n8n (Slack Trigger → HTTP Request → reply in thread) → POST /query

n8n does no business logic there; it only relays the message and posts the
answer back. This module is the same relay implemented directly, so the project
can talk to Slack without an orchestration tool in the middle.

It is entirely optional. The adapter only mounts when SLACK_BOT_TOKEN and
SLACK_SIGNING_SECRET are set — the demo runs without either.

Setup
-----
1. Create a Slack app at https://api.slack.com/apps
2. OAuth & Permissions → bot token scopes: `app_mentions:read`, `chat:write`,
   `im:history`, `im:read`, `im:write`
3. Event Subscriptions → subscribe to `app_mention` and `message.im`,
   request URL: https://<your-host>/slack/events
4. Install to the workspace, then set in .env:
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_SIGNING_SECRET=...

Threading and memory
--------------------
Replies go back into the originating thread. The `conversation_id` passed to
the bot is the Slack thread timestamp when the message is in a thread, and the
user ID otherwise — so follow-ups ("who owns it?") resolve per-thread rather
than leaking between unrelated conversations.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.request

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

logger = logging.getLogger(__name__)

_SLACK_POST_MESSAGE = "https://slack.com/api/chat.postMessage"

# Slack replays events on timeout; a 3-second handler budget means a slow
# answer can be delivered twice. Remember what we have already handled.
_seen_event_ids: dict[str, float] = {}
_SEEN_TTL_SECONDS = 600


def verify_slack_signature(
    signing_secret: str,
    timestamp: str | None,
    signature: str | None,
    body: bytes,
) -> bool:
    """
    Verify a request genuinely came from Slack.

    Slack signs `v0:<timestamp>:<raw body>` with the app's signing secret.
    Requests older than five minutes are rejected to blunt replay attacks.
    """
    if not (timestamp and signature):
        return False

    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            logger.warning("Rejected Slack request with stale timestamp.")
            return False
    except ValueError:
        return False

    basestring = b"v0:" + timestamp.encode() + b":" + body
    expected = "v0=" + hmac.new(
        signing_secret.encode(), basestring, hashlib.sha256
    ).hexdigest()

    # Constant-time compare — a plain == leaks the signature byte by byte.
    return hmac.compare_digest(expected, signature)


def _post_message(token: str, channel: str, text: str, thread_ts: str | None) -> None:
    payload: dict[str, object] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    request = urllib.request.Request(
        _SLACK_POST_MESSAGE,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read())
        if not body.get("ok"):
            logger.error("Slack chat.postMessage failed: %s", body.get("error"))
    except Exception:
        logger.exception("Could not post message to Slack")


def _strip_mention(text: str) -> str:
    """Remove the leading <@BOTID> token so the parser sees a clean question."""
    import re

    return re.sub(r"<@[A-Z0-9]+>", " ", text or "").strip()


def _forget_stale_events() -> None:
    cutoff = time.time() - _SEEN_TTL_SECONDS
    for event_id in [k for k, seen in _seen_event_ids.items() if seen < cutoff]:
        del _seen_event_ids[event_id]


def build_router(
    *,
    signing_secret: str,
    bot_token: str,
    answer_question,
) -> APIRouter:
    """
    Build the /slack/events router.

    `answer_question(question, conversation_id) -> str` is injected rather than
    imported so this module stays free of the bot internals and is testable
    with a stub.
    """
    router = APIRouter()

    @router.post("/slack/events")
    async def slack_events(request: Request):
        raw_body = await request.body()

        if not verify_slack_signature(
            signing_secret,
            request.headers.get("X-Slack-Request-Timestamp"),
            request.headers.get("X-Slack-Signature"),
            raw_body,
        ):
            logger.warning("Rejected Slack event with an invalid signature.")
            return JSONResponse(status_code=401, content={"error": "bad_signature"})

        payload = json.loads(raw_body or b"{}")

        # One-time endpoint verification when you save the Request URL.
        if payload.get("type") == "url_verification":
            return PlainTextResponse(payload.get("challenge", ""))

        event = payload.get("event") or {}

        # Ignore our own messages and edits/joins, or the bot will answer itself.
        if event.get("bot_id") or event.get("subtype"):
            return {"ok": True}

        event_id = payload.get("event_id")
        if event_id:
            _forget_stale_events()
            if event_id in _seen_event_ids:
                logger.info("Ignoring duplicate Slack delivery %s", event_id)
                return {"ok": True}
            _seen_event_ids[event_id] = time.time()

        question = _strip_mention(event.get("text", ""))
        channel = event.get("channel")
        if not question or not channel:
            return {"ok": True}

        # Thread-scoped memory: follow-ups stay inside their own thread.
        thread_ts = event.get("thread_ts") or event.get("ts")
        conversation_id = thread_ts or event.get("user") or channel

        try:
            answer = answer_question(question, conversation_id)
        except Exception:
            logger.exception("Failed to answer Slack question")
            answer = (
                "Sorry — something went wrong looking that up. Please try again."
            )

        _post_message(bot_token, channel, answer, thread_ts)
        return {"ok": True}

    return router
