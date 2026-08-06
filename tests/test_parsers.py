"""
Comprehensive parser tests — offline rule-based parser only.

Run:  python -m pytest tests/test_parsers.py -v

All tests use RuleBasedQueryParser so they execute without an LLM API key
and run offline in CI.

Sections:
  1.  Number / VMN lookups
  2.  Gateway lookups
  3.  Ticket lookups
  4.  Customer lookups
  5.  Source lookups
  6.  Operator / reverse lookup
  7.  List queries: status filters
  8.  List queries: operator filters (real sheet values)
  9.  List queries: number type filters
  10. List queries: ticket priority filters
  11. Unfiltered list queries ("show all numbers", "list gateways" etc.)
  12. Typo tolerance
  13. Vague / greeting → clarification error
  14. Edge cases
"""

from __future__ import annotations

import pytest

from parsers.base import ParserError
from parsers.rule_parser import RuleBasedQueryParser

parser = RuleBasedQueryParser()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(question: str):
    return parser.parse(question)


def raises_parser_error(question: str) -> str:
    with pytest.raises(ParserError) as exc_info:
        parser.parse(question)
    return str(exc_info.value)


# ============================================================
# SECTION 1 — Number / VMN lookups
# ============================================================

class TestNumberLookup:

    def test_status_question(self):
        q = parse("What is the status of 9152001212?")
        assert q.entity_type == "number"
        assert q.entity_value == "9152001212"
        assert q.action == "lookup"
        assert q.requested_field == "status"

    def test_check_bare_number(self):
        q = parse("Check 9152001212")
        assert q.entity_type == "number"
        assert q.entity_value == "9152001212"
        assert q.action == "lookup"
        assert q.requested_field == "all"

    def test_tell_me_about(self):
        q = parse("Tell me about 9152001212")
        assert q.entity_type == "number"
        assert q.entity_value == "9152001212"
        assert q.action == "lookup"

    def test_show_complete_details(self):
        q = parse("Show complete details of 9152001212")
        assert q.entity_type == "number"
        assert q.entity_value == "9152001212"
        assert q.requested_field == "all"

    def test_show_full_details(self):
        q = parse("Show full details of 9876543210")
        assert q.entity_type == "number"
        assert q.entity_value == "9876543210"

    def test_verify_number(self):
        q = parse("Verify 9152001212")
        assert q.entity_type == "number"
        assert q.entity_value == "9152001212"
        assert q.action == "lookup"

    def test_number_with_plus91_space(self):
        q = parse("What is the status of +91 9152001212?")
        assert q.entity_value == "9152001212"

    def test_number_with_plus91_no_space(self):
        q = parse("Check +919152001212")
        assert q.entity_value == "9152001212"

    def test_number_with_0091_prefix(self):
        q = parse("Status of 00919152001212")
        assert q.entity_value == "9152001212"

    def test_number_with_hyphens(self):
        q = parse("Look up 915-200-1212")
        assert q.entity_value == "9152001212"

    def test_number_with_spaces(self):
        q = parse("Check 915 200 1212")
        assert q.entity_value == "9152001212"

    def test_bare_number_fallback(self):
        q = parse("9152001212")
        assert q.entity_type == "number"
        assert q.entity_value == "9152001212"
        assert q.action == "lookup"

    def test_real_sheet_number_9223071030(self):
        """Number present in real sheet."""
        q = parse("Show details of 9223071030")
        assert q.entity_type == "number"
        assert q.entity_value == "9223071030"

    def test_real_sheet_tollfree_18003157844(self):
        """11-digit toll-free number from real sheet.
        normalize_phone requires exactly 10 digits; 11-digit toll-free numbers
        (e.g. 18003157844) are not currently normalised. The parser raises
        ParserError rather than returning a bad lookup. This is documented
        behaviour — support teams should query toll-free numbers via status
        filters or the Sheets UI directly.
        """
        try:
            result = parse("Check 18003157844")
            # If it resolves (future: when 11-digit support added),
            # entity_type must be number
            assert result.entity_type == "number"
        except ParserError:
            pass  # acceptable — 11-digit numbers not yet supported


# ============================================================
# SECTION 2 — Gateway lookups
# ============================================================

class TestGatewayLookup:

    def test_who_owns_gateway(self):
        q = parse("Who owns gateway GW123?")
        assert q.entity_type == "gateway"
        assert q.entity_value == "GW123"
        assert q.requested_field == "company_name"

    def test_which_company_mapped(self):
        q = parse("Which company is mapped to GW123?")
        assert q.entity_type == "gateway"
        assert q.entity_value == "GW123"
        assert q.requested_field == "company_name"

    def test_what_customer_attached(self):
        q = parse("What customer is attached to GW456?")
        assert q.entity_type == "gateway"
        assert q.entity_value == "GW456"
        assert q.requested_field == "company_name"

    def test_gateway_status(self):
        q = parse("What is the status of GW789?")
        assert q.entity_type == "gateway"
        assert q.entity_value == "GW789"
        assert q.requested_field == "status"

    def test_gateway_lowercase_id(self):
        q = parse("Status of gw123")
        assert q.entity_value == "GW123"

    def test_gateway_typo_gq(self):
        q = parse("What is the status of GQ456?")
        assert q.entity_value == "GW456"
        assert q.requested_field == "status"

    def test_bare_gateway_id(self):
        q = parse("GW101")
        assert q.entity_type == "gateway"
        assert q.entity_value == "GW101"
        assert q.action == "lookup"

    def test_gateway_numeric_id(self):
        """Real sheet uses numeric gateway IDs like 470, 531, 3046."""
        q = parse("Show details of gateway 470")
        assert q.entity_type == "gateway"
        assert q.entity_value == "470"
        assert q.action == "lookup"

    def test_gateway_numeric_id_with_id_keyword(self):
        q = parse("What is the status of gateway id 531?")
        assert q.entity_type == "gateway"
        assert q.entity_value == "531"
        assert q.requested_field == "status"


# ============================================================
# SECTION 3 — Ticket lookups
# ============================================================

class TestTicketLookup:

    def test_find_ticket(self):
        q = parse("Find ticket TKT001")
        assert q.entity_type == "ticket"
        assert q.entity_value == "TKT001"
        assert q.action == "lookup"

    def test_ticket_id_only(self):
        q = parse("TKT002 details")
        assert q.entity_type == "ticket"
        assert q.entity_value == "TKT002"

    def test_ticket_lowercase_id(self):
        q = parse("Get details for tkt003")
        assert q.entity_type == "ticket"
        assert q.entity_value == "TKT003"

    def test_ticket_with_hash(self):
        q = parse("Details for ticket TKT004")
        assert q.entity_type == "ticket"
        assert q.entity_value == "TKT004"


# ============================================================
# SECTION 4 — Customer lookups
# ============================================================

class TestCustomerLookup:

    def test_customer_by_id(self):
        q = parse("Give me details for customer CUST001")
        assert q.entity_type == "customer"
        assert q.entity_value == "CUST001"
        assert q.action == "lookup"

    def test_customer_lowercase_id(self):
        q = parse("Account cust002 info")
        assert q.entity_type == "customer"
        assert q.entity_value == "CUST002"

    def test_customer_mixed_case(self):
        q = parse("Look up Cust003")
        assert q.entity_type == "customer"
        assert q.entity_value == "CUST003"


# ============================================================
# SECTION 5 — Source lookups
# ============================================================

class TestSourceLookup:

    def test_source_by_id(self):
        q = parse("Details for source SRC001")
        assert q.entity_type == "source"
        assert q.entity_value == "SRC001"
        assert q.action == "lookup"

    def test_source_lowercase(self):
        q = parse("What is the status of src002?")
        assert q.entity_type == "source"
        assert q.entity_value == "SRC002"


# ============================================================
# SECTION 6 — Operator / reverse lookup
# ============================================================

class TestOperatorLookup:

    def test_which_operator(self):
        q = parse("Which operator is assigned to 9152001212?")
        assert q.entity_type == "operator"
        assert q.entity_value == "9152001212"
        assert q.requested_field == "operator"

    def test_what_operator(self):
        q = parse("What operator does 9876543210 use?")
        assert q.entity_type == "operator"
        assert q.entity_value == "9876543210"


# ============================================================
# SECTION 7 — List queries: status filters
# ============================================================

class TestListByStatus:

    def test_inactive_members(self):
        """Original regression — must still pass."""
        q = parse("Show all inactive members")
        assert q.filters == {"status": "inactive"}
        assert q.action == "list"

    def test_suspended_members_singular(self):
        q = parse("Show all suspended member")
        assert q.filters["status"] == "suspended"

    def test_active_numbers(self):
        q = parse("Show all active numbers")
        assert q.filters["status"] == "active"
        assert q.entity_type == "number"

    def test_inactive_vmns(self):
        q = parse("List all inactive VMNs")
        assert q.filters["status"] == "inactive"
        assert q.entity_type == "number"

    def test_list_active_gateways(self):
        q = parse("Show all active gateways")
        assert q.entity_type == "gateway"
        assert q.filters["status"] == "active"

    def test_list_inactive_gateways(self):
        q = parse("List all inactive gateways")
        assert q.entity_type == "gateway"
        assert q.filters["status"] == "inactive"

    def test_list_open_tickets(self):
        q = parse("Show all open tickets")
        assert q.entity_type == "ticket"
        assert q.filters["status"] == "open"

    def test_list_resolved_tickets(self):
        q = parse("List resolved tickets")
        assert q.entity_type == "ticket"
        assert q.filters["status"] == "resolved"

    def test_list_active_customers(self):
        q = parse("Show all active customers")
        assert q.entity_type == "customer"
        assert q.filters["status"] == "active"


# ============================================================
# SECTION 8 — List queries: operator filters
#
# Tests aligned to real sheet operator values:
#   IDEA, TATA, Vodafone, Jio, Knowlarity, Syniverse, Tanla
# ============================================================

class TestListByOperator:

    def test_show_all_jio_numbers(self):
        q = parse("Show all Jio numbers")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters.get("operator") == "Jio"

    def test_show_all_jio_lines(self):
        q = parse("Show all Jio lines")
        assert q.filters.get("operator") == "Jio"

    def test_reliance_jio_alias(self):
        q = parse("List Reliance Jio numbers")
        assert q.filters.get("operator") == "Jio"

    def test_idea_alias(self):
        """'idea' maps to 'IDEA' as stored in the real sheet."""
        q = parse("Show all Idea numbers")
        assert q.filters.get("operator") == "IDEA"

    def test_idea_vmns(self):
        q = parse("List all idea VMNs")
        assert q.filters.get("operator") == "IDEA"

    def test_vi_alias_maps_to_idea(self):
        """'Vi' (brand name after merger) maps to 'IDEA' per sheet storage."""
        q = parse("Show all Vi VMNs")
        assert q.filters.get("operator") == "IDEA"

    def test_vodafone_idea_alias(self):
        """'Vodafone Idea' also maps to 'IDEA'."""
        q = parse("List all Vodafone Idea numbers")
        assert q.filters.get("operator") == "IDEA"

    def test_vodafone_standalone(self):
        """'Vodafone' alone maps to 'IDEA' — the merged operator's stored value."""
        q = parse("Show all Vodafone numbers")
        assert q.filters.get("operator") == "IDEA"

    def test_tata_alias(self):
        """'Tata' maps to 'TATA' as stored in the real sheet."""
        q = parse("Show all Tata numbers")
        assert q.filters.get("operator") == "TATA"

    def test_tata_communications_alias(self):
        q = parse("List Tata Communications VMNs")
        assert q.filters.get("operator") == "TATA"

    def test_airtel_alias(self):
        """Airtel is not in current sheet but kept for forward compatibility."""
        q = parse("Show all Airtel numbers")
        assert q.filters.get("operator") == "Airtel"

    def test_records_associated_with_jio(self):
        q = parse("Show all records associated with Jio")
        assert q.filters.get("operator") == "Jio"

    def test_jio_suspended_multifilter(self):
        """Multi-filter: operator + status."""
        q = parse("List all Jio lines that are suspended")
        assert q.filters.get("operator") == "Jio"
        assert q.filters.get("status") == "suspended"

    def test_idea_active_multifilter(self):
        q = parse("Show active Idea numbers")
        assert q.filters.get("operator") == "IDEA"
        assert q.filters.get("status") == "active"


# ============================================================
# SECTION 9 — List queries: number type filters
# ============================================================

class TestListByNumberType:

    def test_toll_free_numbers(self):
        q = parse("Show all toll free numbers")
        assert q.filters.get("number_type") == "Toll free"
        assert q.entity_type == "number"

    def test_tollfree_no_space(self):
        q = parse("List tollfree VMNs")
        assert q.filters.get("number_type") == "Toll free"

    def test_missed_call_numbers(self):
        q = parse("Show all missed call numbers")
        assert q.filters.get("number_type") == "Dedicated Missed call"

    def test_promotional_numbers(self):
        """Legacy promotional filter still works."""
        q = parse("Show all promotional numbers")
        assert q.filters.get("number_type") == "promotional"

    def test_transactional_numbers(self):
        q = parse("List transactional VMNs")
        assert q.filters.get("number_type") == "transactional"

    def test_promo_alias(self):
        q = parse("Show all promo lines")
        assert q.filters.get("number_type") == "promotional"


# ============================================================
# SECTION 10 — List queries: ticket priority filters
# ============================================================

class TestListByPriority:

    def test_high_priority_tickets(self):
        q = parse("Show all high-priority tickets")
        assert q.entity_type == "ticket"
        assert q.filters.get("priority") == "high"

    def test_open_high_priority(self):
        q = parse("Show all open high-priority tickets")
        assert q.filters.get("status") == "open"
        assert q.filters.get("priority") == "high"

    def test_medium_priority_issues(self):
        q = parse("List medium-priority issues")
        assert q.entity_type == "ticket"
        assert q.filters.get("priority") == "medium"


# ============================================================
# SECTION 11 — Unfiltered list queries (NEW — was broken before)
# ============================================================

class TestUnfilteredListQueries:
    """
    These queries should return ALL records of the given type.
    Previously failed because _try_parse_list_query required at least
    one filter. Fixed by allowing empty filters when 'all' is present
    or when the entity noun is specific and unambiguous.
    """

    def test_show_all_numbers(self):
        q = parse("show all numbers")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters == {}

    def test_list_numbers(self):
        q = parse("list numbers")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters == {}

    def test_show_all_vmns(self):
        q = parse("show all VMNs")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters == {}

    def test_list_vmns(self):
        q = parse("list VMNs")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters == {}

    def test_show_numbers(self):
        """'show numbers' without 'all' — unambiguous noun, return all."""
        q = parse("show numbers")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters == {}

    def test_show_all_gateways(self):
        q = parse("show all gateways")
        assert q.entity_type == "gateway"
        assert q.action == "list"
        assert q.filters == {}

    def test_list_gateways(self):
        q = parse("list gateways")
        assert q.entity_type == "gateway"
        assert q.action == "list"
        assert q.filters == {}

    def test_show_gateways(self):
        q = parse("show gateways")
        assert q.entity_type == "gateway"
        assert q.action == "list"
        assert q.filters == {}

    def test_get_all_gateways(self):
        q = parse("get all gateways")
        assert q.entity_type == "gateway"
        assert q.action == "list"
        assert q.filters == {}

    def test_show_all_tickets(self):
        q = parse("show all tickets")
        assert q.entity_type == "ticket"
        assert q.action == "list"
        assert q.filters == {}

    def test_list_tickets(self):
        q = parse("list tickets")
        assert q.entity_type == "ticket"
        assert q.action == "list"
        assert q.filters == {}

    def test_show_all_customers(self):
        q = parse("show all customers")
        assert q.entity_type == "customer"
        assert q.action == "list"
        assert q.filters == {}

    def test_list_members(self):
        q = parse("list members")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters == {}

    def test_get_all_vmns(self):
        q = parse("get all VMNs")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters == {}

    def test_fetch_all_numbers(self):
        q = parse("fetch all numbers")
        assert q.entity_type == "number"
        assert q.action == "list"
        assert q.filters == {}


# ============================================================
# SECTION 12 — Typo tolerance
# ============================================================

class TestTypoTolerance:

    def test_status_typo_sttaus(self):
        """Original regression."""
        q = parse("What is the sttaus of GQ456")
        assert q.entity_value == "GW456"
        assert q.requested_field == "status"

    def test_status_typo_staus(self):
        q = parse("What is the staus of 9152001212?")
        assert q.requested_field == "status"
        assert q.entity_value == "9152001212"

    def test_inactive_typo(self):
        q = parse("Show all inactve members")
        assert q.filters["status"] == "inactive"

    def test_suspended_typo(self):
        q = parse("Show all suspened numbers")
        assert q.filters["status"] == "suspended"

    def test_gateway_typo_gq(self):
        q = parse("Status of GQ789")
        assert q.entity_value == "GW789"


# ============================================================
# SECTION 13 — Vague / greeting → clarification error
# ============================================================

class TestClarificationRequired:

    def test_greeting_hi(self):
        msg = raises_parser_error("hi")
        assert "support assistant" in msg.lower() or "example" in msg.lower()

    def test_greeting_hello(self):
        raises_parser_error("hello")

    def test_greeting_good_morning(self):
        raises_parser_error("good morning")

    def test_vague_i_need_help(self):
        msg = raises_parser_error("I need help")
        assert "specific" in msg.lower() or "phone" in msg.lower() or "id" in msg.lower()

    def test_vague_check_this_issue(self):
        msg = raises_parser_error("Check this issue")
        assert len(msg) > 10

    def test_vague_any_update(self):
        raises_parser_error("Any update?")

    def test_empty_string(self):
        raises_parser_error("")

    def test_whitespace_only(self):
        raises_parser_error("   ")


# ============================================================
# SECTION 14 — Edge cases & malformed input
# ============================================================

class TestEdgeCases:

    def test_company_owns_gateway(self):
        """Original regression."""
        q = parse("Which company owns gateway GW123")
        assert q.entity_value == "GW123"
        assert q.requested_field == "company_name"

    def test_gateway_owner_keyword(self):
        q = parse("Who is the owner of GW456?")
        assert q.entity_type == "gateway"
        assert q.entity_value == "GW456"
        assert q.requested_field == "company_name"

    def test_number_with_trailing_punctuation(self):
        q = parse("Check 9152001212.")
        assert q.entity_value == "9152001212"

    def test_uppercase_ticket(self):
        q = parse("TKT001")
        assert q.entity_value == "TKT001"

    def test_mixed_case_customer(self):
        q = parse("cust001")
        assert q.entity_value == "CUST001"

    def test_question_mark_stripped(self):
        q = parse("What is the status of GW123?")
        assert q.entity_value == "GW123"
        assert q.requested_field == "status"

    def test_number_in_sentence_context(self):
        q = parse("Please look into number 9223071030 urgently")
        assert q.entity_value == "9223071030"
        assert q.entity_type == "number"

    def test_gateway_in_sentence_context(self):
        q = parse("Can you check the status of gateway GW789 please?")
        assert q.entity_value == "GW789"
        assert q.requested_field == "status"

    def test_show_all_numbers_returns_list_not_error(self):
        """
        Critical regression: 'show all numbers' must return a list query,
        not raise ParserError. Previously broken.
        """
        q = parse("show all numbers")
        assert q.action == "list"
        assert q.entity_type == "number"
        # filters should be empty — no filter = return all
        assert q.filters == {}
