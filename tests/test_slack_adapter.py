"""Tests for the Slack Events adapter — signature verification and relay logic."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from slack_adapter import _strip_mention, verify_slack_signature

SECRET = "test-signing-secret"


def _sign(body: bytes, timestamp: str, secret: str = SECRET) -> str:
    basestring = b"v0:" + timestamp.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()


class TestSignatureVerification:
    def test_accepts_a_correctly_signed_request(self):
        body = json.dumps({"type": "event_callback"}).encode()
        ts = str(int(time.time()))
        assert verify_slack_signature(SECRET, ts, _sign(body, ts), body)

    def test_rejects_a_wrong_signature(self):
        body = b'{"type":"event_callback"}'
        ts = str(int(time.time()))
        assert not verify_slack_signature(SECRET, ts, "v0=deadbeef", body)

    def test_rejects_a_signature_made_with_another_secret(self):
        body = b'{"type":"event_callback"}'
        ts = str(int(time.time()))
        forged = _sign(body, ts, secret="attacker-secret")
        assert not verify_slack_signature(SECRET, ts, forged, body)

    def test_rejects_a_replayed_old_request(self):
        """A valid signature from six minutes ago must still be refused."""
        body = b'{"type":"event_callback"}'
        ts = str(int(time.time()) - 360)
        assert not verify_slack_signature(SECRET, ts, _sign(body, ts), body)

    def test_rejects_a_tampered_body(self):
        ts = str(int(time.time()))
        signature = _sign(b'{"question":"safe"}', ts)
        assert not verify_slack_signature(SECRET, ts, signature, b'{"question":"evil"}')

    @pytest.mark.parametrize(
        "timestamp,signature",
        [(None, "v0=abc"), ("123", None), (None, None), ("not-a-number", "v0=abc")],
    )
    def test_rejects_missing_or_malformed_headers(self, timestamp, signature):
        assert not verify_slack_signature(SECRET, timestamp, signature, b"{}")


class TestMentionStripping:
    def test_strips_the_leading_bot_mention(self):
        assert _strip_mention("<@U012BOT> what is the status of 9152001212?") == (
            "what is the status of 9152001212?"
        )

    def test_leaves_a_plain_message_alone(self):
        assert _strip_mention("who owns gateway 470?") == "who owns gateway 470?"

    def test_handles_empty_text(self):
        assert _strip_mention("") == ""
        assert _strip_mention(None) == ""
