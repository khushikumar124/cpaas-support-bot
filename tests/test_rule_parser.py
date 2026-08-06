"""Quick tests for rule-based parser (run: python -m pytest tests/ -q)."""

from parsers.rule_parser import RuleBasedQueryParser

parser = RuleBasedQueryParser()


def test_inactive_members():
    q = parser.parse("Show all inactive members")
    assert q.filters == {"status": "inactive"}
    assert q.action == "list"


def test_suspended_members_singular():
    q = parser.parse("Show all suspended member")
    assert q.filters == {"status": "suspended"}


def test_active_numbers():
    q = parser.parse("Show all active numbers")
    assert q.filters == {"status": "active"}


def test_gateway_status_typo():
    q = parser.parse("What is the sttaus of GQ456")
    assert q.entity_value == "GW456"
    assert q.requested_field == "status"


def test_company_gateway():
    q = parser.parse("Which company owns gateway GW123")
    assert q.entity_value == "GW123"
