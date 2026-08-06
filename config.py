"""Application configuration (environment, paths, display labels)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() not in ("false", "0", "no")


# --- Demo mode ---
# This repository is the public demo build: it ships fictional CSV data and is
# meant to run straight from a clone with no API keys and no .env file.
#
# DEMO_MODE relaxes exactly two things that would otherwise block that:
#   1. /query no longer requires an X-API-Key header (see api.py).
#   2. localhost origins are allowed through CORS so the Vite dev server works.
#
# It changes nothing else. Set DEMO_MODE=false for a real deployment and the
# original fail-closed behaviour returns.
DEMO_MODE: bool = _flag("DEMO_MODE", "true")

# --- API / parser ---
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").strip().lower()
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
PARSER_MODE: str = os.getenv("PARSER_MODE", "auto").strip().lower()

# --- Data source: csv | google_sheets (placeholder) ---
DATA_SOURCE: str = os.getenv("DATA_SOURCE", "csv").strip().lower()

GOOGLE_SPREADSHEET_ID: str = os.getenv(
    "GOOGLE_SPREADSHEET_ID",
    ""
)

GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    ""
)

SHEETS_CACHE_TTL_SECONDS: int = int(
    os.getenv("SHEETS_CACHE_TTL_SECONDS", "60")
)

# --- API security ---
# Shared secret that n8n must send as the "X-API-Key" header on every
# /query request. No default — an empty value means auth is unconfigured
# and the endpoint will reject all requests (fail closed, see api.py).
BOT_API_KEY: str = os.getenv("BOT_API_KEY", "")

# Comma-separated list of browser origins allowed to call the API via CORS.
# Slack/n8n call the API server-to-server and are unaffected by this
# setting; it only matters for the React frontend.
# Empty by default = no browser origins allowed.
_DEMO_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

CORS_ALLOWED_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
] or (_DEMO_ORIGINS if DEMO_MODE else [])

# --- Logging ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# --- Formatter field labels (not tied to CSV/Sheets) ---
FIELD_LABELS: dict[str, str] = {
    "source_id": "Source ID",
    "gateway_id": "Gateway ID",
    "line_type": "Line Type",
    "company_name": "Company",
    "region": "Region",
    "status": "Status",
    "created_date": "Created Date",
    "number": "Number",
    "operator": "Operator",
    "provisioned_date": "Provisioned Date",
    "number_type": "Number Type",
    "customer_id": "Customer ID",
    "account_manager": "Account Manager",
    "ticket_id": "Ticket ID",
    "subject": "Subject",
    "priority": "Priority",
}

ANSWER_GENERATION: bool = os.getenv("ANSWER_GENERATION", "true").strip().lower() != "false"