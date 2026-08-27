# Deployment Guide — CPaaS Support Assistant

> See also: [ARCHITECTURE.md](./ARCHITECTURE.md) for how the pieces fit together, [the API section of the README](../README.md#api) for the endpoint contract n8n depends on, [Production notes in the README](../README.md#production-notes) for the production readiness checklist.

> **Demo build.** This repository is the public demo of the project: it ships fictional CSV data and runs with no API keys. Sections below describing Google Sheets, Slack, or n8n describe an optional production deployment and are not required to run the demo. See the [README](../README.md).


## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python | 3.11+ recommended (the codebase uses modern type-hint syntax such as `str \| None`, which requires 3.10+). |
| pip | For installing `requirements.txt`. |
| A Google Cloud project | For the Sheets service account (live data backend option). |
| A Google Sheet | Pre-populated with the five expected tabs (see [§7](#7-google-sheet-configuration)). |
| An OpenAI API key | For LLM-based parsing and (optionally) answer generation. |
| An n8n instance | Self-hosted or cloud, reachable by Slack and able to reach the FastAPI backend. |
| A Slack App | With Events API + a bot token — see [§10](#10-slack-integration). |
| A GCP VM (or equivalent) | To host the FastAPI backend — see [§9](#9-deploying-to-a-gcp-vm). |

## 2. Python Version

3.11 or newer.

## 3. Required Packages

From `requirements.txt`:

```
pandas>=2.2.0
openai>=1.0.0
python-dotenv>=1.0.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.0.0
gspread>=6.0.0
google-auth>=2.0.0
```

Install with:

```bash
pip install -r requirements.txt
```

## 4. Environment Variables

Copy `.env.example` to `.env` in the project root and fill in the values below. `config.py` loads this file automatically via `python-dotenv`.

| Variable | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | LLM backend selector. Only `openai` is currently implemented. | `openai` |
| `OPENAI_API_KEY` | Your OpenAI API key. Required for LLM parsing/answer generation; if unset, the system automatically falls back to the offline rule parser and deterministic formatter. | *(none)* |
| `OPENAI_MODEL` | OpenAI model name. | `gpt-4.1-mini` |
| `PARSER_MODE` | `auto` \| `openai` \| `rule` — see [ARCHITECTURE.md §6](./ARCHITECTURE.md#6-parser-fallback). | `auto` |
| `DATA_SOURCE` | `csv` \| `google_sheets`. | `csv` |
| `GOOGLE_SPREADSHEET_ID` | The target spreadsheet's ID (from its URL). Required when `DATA_SOURCE=google_sheets`. | *(empty)* |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | **File path** to the service account JSON key. Required when `DATA_SOURCE=google_sheets`. | *(empty)* |
| `SHEETS_CACHE_TTL_SECONDS` | How long sheet reads are cached in-process before re-fetching. | `60` |
| `LOG_LEVEL` | Standard Python logging level. | `INFO` |
| `ANSWER_GENERATION` | `true`/`false` — enable OpenAI-generated natural-language answers on top of the deterministic formatter. | `true` |
| `BOT_API_KEY` | Shared secret required in the `X-API-Key` header on every `/query` request. **Required in production** — the endpoint fails closed (rejects all requests) if this is unset. | *(none)* |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origins allowed via CORS. Only relevant if the React frontend is used; leave empty when no browser client talks to the API. | *(empty)* |

## 5. OpenAI Setup

1. Create an API key at https://platform.openai.com/api-keys.
2. Set `OPENAI_API_KEY` in `.env`.
3. Set `OPENAI_MODEL` if you want a model other than the default.
4. If you want to run without OpenAI (offline/rule-only mode), leave `OPENAI_API_KEY` unset and/or set `PARSER_MODE=rule` — see [ARCHITECTURE.md §6](./ARCHITECTURE.md#6-parser-fallback).

## 6. Google Service Account Setup

1. In a Google Cloud project, enable the **Google Sheets API**.
2. Create a service account and generate a JSON key for it.
3. Share the target Google Sheet with the service account's email address (**Viewer** access is sufficient — the app only requests `spreadsheets.readonly` scope).
4. Place the downloaded JSON key file somewhere on the server **outside the project's source directory**, with restrictive permissions:
   ```bash
   chmod 600 /path/to/service-account.json
   ```
5. Set `GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json` in `.env`.

> **Security note:** this repository contains only the template `service-account-example.json` — no real credentials. Treat any credential file that ends up inside the project directory as compromised: regenerate the key in Google Cloud Console rather than reusing it. `.gitignore` excludes `service-account.json` and `*.pem`/`*.key`, but keep the real key outside the repo entirely (or in a secrets manager) rather than relying on `.gitignore` alone.

## 7. Google Sheet Configuration

The backend expects **five logical sheets**, each resolved to a worksheet tab by trying a list of candidate names (so exact tab naming has some flexibility). If none of the candidates for a sheet exist, retrieval for that entity type will fail with a clear error naming the tabs it tried and the tabs that do exist.

| Logical sheet | Candidate tab names tried | Entity types routed here |
|---|---|---|
| `vmn` | `Sheet1`, `VMN`, `VMNs`, `Numbers`, `Number details`, `VMN details` | number, vmn, operator |
| `gateways` | `Gateway details`, `Gateway Details`, `Gateways`, `Gateway` | gateway, company |
| `customers` | `Customers`, `Customer details`, `Customer Details` | customer |
| `tickets` | `Tickets`, `Ticket details`, `Ticket Details` | ticket |
| `source_information` | `Source Information`, `Source information`, `Source Info`, `Sources` | source |

Column headers are also flexible — see the alias tables in `datasources/google_sheets_source.py` (`COLUMN_MAPS`) for exactly which header text maps to which canonical field per sheet (e.g. `gateway` tab: "Account Name", "Company", or "Company Name" all map to `company_name`). Any header not in the alias table is kept as-is (slugified), so new columns still surface in answers without code changes.

For reference, the bundled CSV sample data (`data/*.csv`, used when `DATA_SOURCE=csv`) shows the expected canonical shape of each sheet — e.g. `vmn.csv` has columns `number, status, operator, company_name, gateway_id, provisioned_date, number_type`.

## 8. Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# edit .env — for a quick local test, DATA_SOURCE=csv works with no Google setup at all

# 3a. Run the CLI (no Slack/n8n needed)
python app.py

# 3b. Or run the API server
uvicorn api:app --reload --port 8000
# then: curl -X POST http://localhost:8000/query \
#         -H "Content-Type: application/json" \
#         -H "X-API-Key: <your BOT_API_KEY>" \
#         -d '{"question": "status of 9152001212", "conversation_id": "test-user"}'
```

The React frontend (`frontend/`) exercises the same `/query` API as any other client, and is the primary interface in this demo build. A Slack deployment would not use it. To run it locally: `cd frontend && npm install && npm run dev` — the Vite dev server proxies `/query` and `/health` to `http://127.0.0.1:8000`, so no `frontend/.env` is needed unless the API runs elsewhere.

## 9. Deploying to a GCP VM

1. Provision a VM (a small general-purpose instance is sufficient for this workload).
2. Install Python 3.11+, `git`, and `pip`.
3. Clone/copy the project to the VM (excluding `service-account.json` — copy that separately with restricted permissions, as described in [§6](#6-google-service-account-setup)).
4. Create and activate a virtual environment, then `pip install -r requirements.txt`.
5. Create `.env` on the VM (never commit it) with production values, including a freshly generated `BOT_API_KEY`:
   ```bash
   openssl rand -hex 32   # use the output as BOT_API_KEY
   ```
6. Firewall the VM so the FastAPI port (see [§10 below](#running-with-uvicorn)) is reachable **only from n8n's IP**, not the public internet.
7. Run the app as a managed service (systemd unit, or your preferred process manager) so it restarts on failure/reboot, rather than a bare foreground process.

## Running with uvicorn

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1
```

**`--workers 1` is a hard requirement, not a tuning choice.** Conversation memory (`ConversationMemory` in `context/memory.py`) is an in-process Python dictionary. Running multiple uvicorn workers means each worker has its own independent memory store — a user's follow-up question can be routed to a different worker than the one that saw their original question, silently breaking context resolution. Do not scale this service horizontally with multiple workers/replicas without first moving conversation memory to a shared store (see [Production notes in the README](../README.md#production-notes)).

## Reverse Proxy Recommendations

Run FastAPI behind nginx or Caddy to terminate TLS — do not expose plain HTTP with an API key traveling in a header. A minimal nginx example:

```nginx
server {
    listen 443 ssl;
    server_name your-backend-domain.example.com;

    ssl_certificate     /etc/letsencrypt/live/your-backend-domain.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-backend-domain.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 10. Slack Integration

See [ARCHITECTURE.md §2](./ARCHITECTURE.md#slack) for the conceptual role of Slack, and the n8n workflow file for the concrete implementation. Summary of required Slack App configuration:

**OAuth Scopes (Bot Token):**
- `app_mentions:read`
- `chat:write`
- `channels:history`, `groups:history`, `im:history`, `mpim:history`
- `im:read`

**Event Subscriptions:**
- Request URL: the n8n Slack Trigger's webhook URL (generated when the workflow is activated).
- Subscribed bot events: `app_mention`, `message.im` (add `message.channels` / `message.groups` if the bot should also respond to plain messages in channels it's a member of, not just @-mentions).

## 11. n8n Integration

Import the provided n8n workflow (`cpaas-slack-n8n-workflow.json`). After import:

1. Attach a Slack credential (bot token) to the Slack Trigger node and both Slack reply nodes.
2. Set environment variables on the n8n instance:
   - `BACKEND_URL` — the FastAPI backend's base URL (e.g. `https://your-backend-domain.example.com`), no trailing slash.
   - `BOT_API_KEY` — must exactly match the value set in the backend's `.env`.
3. Activate the workflow and copy its generated webhook URL into the Slack App's Event Subscriptions Request URL.

The workflow's HTTP Request node sends `{"question": ..., "conversation_id": ...}` with an `X-API-Key` header, matching the backend contract exactly — see [the API section of the README](../README.md#api). If the backend call fails or returns a non-2xx status, the workflow's error branch posts a generic fallback message to the Slack thread rather than leaving the user without a reply.

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every `/query` call returns `401 Invalid or missing API key` | `BOT_API_KEY` not set on the backend, or n8n's `X-API-Key` header doesn't match | Confirm both values are set and identical (no trailing whitespace) |
| `/query` returns `401 API authentication is not configured` | `BOT_API_KEY` is unset/empty on the backend | Set `BOT_API_KEY` in the server's `.env` and restart |
| Backend answers "No sheet configured for entity_type=..." | The parsed entity type isn't in `SheetRegistry.ENTITY_SHEET_MAP` | See [`registry/sheet_registry.py`](../registry/sheet_registry.py) for adding a new entity type |
| Backend answers with a `KeyError`/tab-not-found style message | `DATA_SOURCE=google_sheets` but the expected tab name isn't present, or the service account doesn't have access | Check the candidate tab names in [§7](#7-google-sheet-configuration), confirm the sheet is shared with the service account email |
| Follow-up questions ("who owns it?") don't resolve correctly, intermittently | Backend is running with more than one uvicorn worker | Re-deploy with `--workers 1`, see [§9](#running-with-uvicorn) |
| Slack shows the generic "couldn't reach the support backend" fallback message | HTTP call from n8n to FastAPI failed or errored (network, auth, or backend exception) | Check n8n execution log for the specific error, check backend logs for a corresponding entry |
| Answers ignore the connected data entirely / look hallucinated | `ANSWER_GENERATION=true` but the LLM is not grounded correctly — should not happen given the current prompt design, but if seen, set `ANSWER_GENERATION=false` to fall back to the deterministic formatter while investigating | See `llm/service.py` `_ANSWER_SYSTEM_PROMPT` |
| Bot replies to its own messages / loops | Slack event filtering misconfigured in n8n | Confirm the "Ignore Bot Messages" IF node in the n8n workflow is upstream of the HTTP Request node |