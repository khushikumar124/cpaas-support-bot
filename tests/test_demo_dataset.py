"""
End-to-end tests over the bundled demo CSV data.

These run fully offline (rule parser + CSVDataSource) and exist to catch the
two failure modes that are invisible to the parser-only tests:

  1. A sheet_id in SheetRegistry that no data source knows about — the bug that
     made every gateway query fail with KeyError: 'Unknown sheet ID: gateway'.
  2. A parser emitting a filter value that does not appear in the data, which
     silently returns zero rows instead of raising.
"""

from __future__ import annotations

import pytest

from core.bot_service import BotService
from datasources.csv_source import SHEET_FILE_MAP, CSVDataSource
from datasources.google_sheets_source import SHEET_TAB_MAP
from parsers.rule_parser import RuleBasedQueryParser
from registry.sheet_registry import SheetRegistry


@pytest.fixture(scope="module")
def service() -> BotService:
    return BotService(parser=RuleBasedQueryParser(), data_source=CSVDataSource())


def _registry_sheet_ids() -> set[str]:
    return {sheet_id for sheet_id, _ in SheetRegistry.ENTITY_SHEET_MAP.values()}


# --- 1. Routing integrity -------------------------------------------------

@pytest.mark.parametrize("sheet_id", sorted(_registry_sheet_ids()))
def test_every_registry_sheet_id_is_backed_by_a_csv(sheet_id: str) -> None:
    assert sheet_id in SHEET_FILE_MAP, (
        f"SheetRegistry routes to '{sheet_id}' but csv_source.SHEET_FILE_MAP "
        f"has no entry for it — every query for that entity would fail."
    )


@pytest.mark.parametrize("sheet_id", sorted(_registry_sheet_ids()))
def test_every_registry_sheet_id_is_backed_by_a_sheets_tab(sheet_id: str) -> None:
    assert sheet_id in SHEET_TAB_MAP, (
        f"SheetRegistry routes to '{sheet_id}' but google_sheets_source."
        f"SHEET_TAB_MAP has no entry for it."
    )


def test_registry_id_columns_exist_in_the_data() -> None:
    source = CSVDataSource()
    for entity, (sheet_id, id_column) in SheetRegistry.ENTITY_SHEET_MAP.items():
        rows = source.get_records(sheet_id)
        assert rows, f"sheet '{sheet_id}' is empty"
        assert id_column in rows[0], (
            f"entity '{entity}' looks up column '{id_column}' in sheet "
            f"'{sheet_id}', which has columns {sorted(rows[0])}"
        )


# --- 2. Referential integrity of the demo data ---------------------------

def test_every_vmn_points_at_a_real_gateway() -> None:
    source = CSVDataSource()
    gateway_ids = {row["gateway_id"] for row in source.get_records("gateways")}
    for row in source.get_records("vmn"):
        assert row["gateway_id"] in gateway_ids, (
            f"number {row['number']} references unknown gateway "
            f"{row['gateway_id']}"
        )


def test_every_ticket_points_at_a_real_number() -> None:
    source = CSVDataSource()
    numbers = {row["number"] for row in source.get_records("vmn")}
    for row in source.get_records("tickets"):
        assert row["number"] in numbers, (
            f"ticket {row['ticket_id']} references unknown number {row['number']}"
        )


def test_every_customer_points_at_a_real_gateway() -> None:
    source = CSVDataSource()
    gateway_ids = {row["gateway_id"] for row in source.get_records("gateways")}
    for row in source.get_records("customers"):
        assert row["primary_gateway"] in gateway_ids, (
            f"customer {row['customer_id']} references unknown gateway "
            f"{row['primary_gateway']}"
        )


def test_every_source_points_at_a_real_gateway() -> None:
    source = CSVDataSource()
    gateway_ids = {row["gateway_id"] for row in source.get_records("gateways")}
    for row in source.get_records("source_information"):
        assert row["gateway_id"] in gateway_ids, (
            f"source {row['source_id']} references unknown gateway "
            f"{row['gateway_id']}"
        )


# --- 3. Every quick-command question returns real rows -------------------

# Mirrors frontend/src/config/quickCommands.js. If a question here stops
# returning rows, the demo UI has a dead button.
QUICK_COMMANDS = [
    "Show all numbers",
    "Show all active numbers",
    "Show all suspended numbers",
    "Show all Vodafone numbers",
    "List all Airtel numbers",
    "Show details of 9152001212",
    "Which operator is assigned to 9223071030?",
    "Show all gateways",
    "Show all active gateways",
    "Show gateway 470",
    "Who owns gateway 470?",
    "What is the status of gateway 926?",
    "Show all open tickets",
    "Show all high priority tickets",
    "Show details of TKT007",
    "What is the status of TKT011?",
    "Show customer CUST003",
    "Who is the account manager for CUST008?",
    "Show source SRC008",
    "waht is the staus of 9152001212",
    "show all gatways",
    "list suspnded numbers",
]


@pytest.mark.parametrize("question", QUICK_COMMANDS)
def test_quick_command_returns_records(service: BotService, question: str) -> None:
    _, result, answer = service.ask(question)

    assert result.success, f"{question!r} failed: {result.message}"
    assert result.records, f"{question!r} matched no rows: {result.message}"
    assert answer.strip()


# --- 4. Conversation memory follow-ups -----------------------------------

def test_followup_resolves_against_previous_entity(service: BotService) -> None:
    from context.memory import ContextResolver, ConversationMemory

    memory = ConversationMemory()
    resolver = ContextResolver(memory)
    cid = "test-session"

    parsed, result, _ = service.ask("Show gateway 470")
    memory.update(cid, parsed.entity_type, parsed.entity_value,
                  result.records, "Show gateway 470")

    resolved, used = resolver.resolve("Who owns it?", cid)
    assert used, "follow-up was not resolved against the remembered entity"
    assert "470" in resolved

    _, followup_result, answer = service.ask(resolved)
    assert followup_result.success and followup_result.records
    assert "Acme Retail" in answer
