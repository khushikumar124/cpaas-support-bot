# CPaaS Support Bot

A conversational assistant that answers natural-language questions about CPaaS
operations data — virtual mobile numbers, gateways, customers, support tickets,
and SMPP/HTTP line configuration.

```
You: Who owns gateway 470?
Bot: Company for 470: Acme Retail Pvt Ltd

You: What is its status?
Bot: Status for 470: active
```

Support staff used to answer these questions by opening a Google Sheet, finding
the right tab, searching for an identifier, and cross-referencing other tabs for
every follow-up. This turns that into one question in a chat box.

> **About this repository.** I originally built this during my internship at
> Netcore Cloud, where it was deployed as a Slack bot backed by the team's live
> Google Sheets. **This is a standalone demo build.** All data in `data/` is
> fictional, and no proprietary data or credentials are included. It runs
> entirely offline against bundled CSVs.

---

## Quickstart

Nothing to configure — no API key, no `.env`, no database.

```bash
pip install -r requirements.txt
```

**Terminal:**

```bash
python app.py
```

**Web UI** — run the API and the frontend in two terminals:

```bash
uvicorn api:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Then open <http://localhost:5173>. The Vite dev server proxies `/query` and
`/health` to the API on port 8000.

**Tests:**

```bash
python -m pytest tests/ -q
```

---

## What it can answer

| Kind | Examples |
|---|---|
| **Lookups** | `What is the status of 9152001212?` · `Who owns gateway 470?` · `Show details of TKT007` |
| **Filtered lists** | `Show all active numbers` · `Show all Vodafone numbers` · `Show all high priority tickets` |
| **Reverse lookups** | `Which operator is assigned to 9223071030?` |
| **Follow-ups** | `Show gateway 470` → `Who owns it?` → `What is its status?` |
| **Typos** | `waht is the staus of 9152001212` · `show all gatways` |

Five entity types are supported: numbers/VMNs, gateways, customers, tickets, and
sources. Try the **Quick Commands** panel in the UI for the full list.

---

## How it works

A question flows through five stages. Each is a separate module behind an
interface, so any one can be swapped without touching the others.

```
Question
   │
   ├─▶ ContextResolver      resolves "it"/"its" against the last entity,
   │                        rewriting the question to be self-contained
   │
   ├─▶ Parser               natural language → ParsedQuery
   │                        (entity_type, entity_value, action, field, filters)
   │
   ├─▶ QueryRouter          entity_type → which sheet + which column
   │
   ├─▶ Retriever            fetches rows via the DataSource interface
   │
   └─▶ Formatter            rows → text
       or AnswerGenerator   rows → LLM-written answer, grounded in those rows
   │
   ▼
{ "answer": "...", "context_used": true }
```

**Everything degrades instead of failing.** Each stage has a fallback, which is
why the demo runs with no API key at all:

| Stage | Primary | Fallback |
|---|---|---|
| Parsing | OpenAI structured parse | Regex/keyword rule parser (offline) |
| Answers | LLM, grounded in retrieved rows | Deterministic formatter |
| Data | Google Sheets | Bundled CSVs |

Set `OPENAI_API_KEY` and the LLM paths activate automatically. Leave it empty and
the rule-based parser and formatter handle everything — no network calls.

### Design decisions worth calling out

**The parser returns structured data, not prose.** The LLM's only job is
`"who owns gateway 470?"` → `{"entity_type": "gateway", "entity_value": "470",
"requested_field": "company_name"}`. Retrieval is ordinary data access against
that structure. The model never sees the full dataset and never invents a record.

**Answers are grounded by construction.** When answer generation is on, the LLM
receives only the rows already retrieved and is instructed to use nothing else.
It phrases facts; it doesn't supply them.

**Follow-ups are resolved before parsing, not inside it.** `ContextResolver`
rewrites `"who owns it?"` into `"who owns gateway 470?"` up front, so the parser
only ever sees complete questions and stays stateless. The rewritten identifier
is qualified (`gateway 470`, not a bare `470`) — a bare numeric ID isn't
self-describing, and the offline parser can't classify it.

**One vocabulary, enforced by tests.** Filters are matched verbatim against the
data, so a parser emitting `"Vodafone Idea"` where the sheet stores `"IDEA"`
returns zero rows and *no error*. Both parsers are pinned to one canonical set of
values, and `tests/test_demo_dataset.py` runs every UI quick-command against the
real data to assert it returns rows.

### Layout

```
api.py                  FastAPI /query + /health
app.py                  CLI entry point
core/                   bot_service · query_router · retriever · answer_generator
parsers/                rule_parser (offline) · llm_parser · factory (hybrid)
datasources/            base ABC · csv_source · google_sheets_source · factory
context/memory.py       conversation memory + follow-up resolution
registry/               entity_type → sheet/column routing table
formatter.py            deterministic text output
data/                   fictional CSV dataset
frontend/               React + Vite + Tailwind chat UI
tests/                  151 tests, fully offline
```

`documentation/` has the deeper write-ups: [architecture](documentation/ARCHITECTURE.md),
[project overview](documentation/PROJECT_OVERVIEW.md), and
[deployment](documentation/DEPLOYMENT_GUIDE.md).

---

## The demo dataset

Fictional, but shaped like the real thing — 10 gateways, 30 numbers, 10
customers, 14 tickets, 12 source lines, with foreign keys that actually resolve
(every ticket points at a real number, every number at a real gateway). Tests
enforce that referential integrity.

Some deliberate quirks are preserved from the production schema, because
handling them is the interesting part:

- Gateway IDs are bare numbers (`470`), so `GW470`, `gw 470`, and `Gateway 470`
  all have to normalize to the same lookup.
- The merged Vodafone/Idea operator is stored as `IDEA`, so `Vi`, `Voda`,
  `Vodafone`, and `Vodafone Idea` must all resolve to it.
- Number types are stored as human labels (`Toll free`, `Dedicated Missed call`)
  rather than slugs.

---

## Configuration

Every setting has a working default; `.env` is optional. See
[`.env.example`](.env.example).

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `true` | Skips API-key auth and allows localhost CORS. **Set `false` in production.** |
| `DATA_SOURCE` | `csv` | `csv` or `google_sheets` |
| `PARSER_MODE` | `auto` | `auto` (LLM + fallback) or `rule` (offline only) |
| `OPENAI_API_KEY` | empty | Enables LLM parsing and answer generation |
| `ANSWER_GENERATION` | `true` | `false` forces the deterministic formatter |
| `BOT_API_KEY` | empty | Required as `X-API-Key` when `DEMO_MODE=false` |

With `DEMO_MODE=false` and no `BOT_API_KEY`, `/query` rejects every request
rather than running unauthenticated — the demo relaxes that only because the
bundled data is fictional.

### API

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "Who owns gateway 470?", "conversation_id": "abc"}'
```

```json
{ "answer": "Company for 470: Acme Retail Pvt Ltd", "context_used": false }
```

Reuse a `conversation_id` across requests to enable follow-up questions. Omit it
for stateless one-off queries. Interactive docs at `/docs`.

---

## Production notes

The original deployment used **Slack → n8n → this API → Google Sheets**, with
n8n relaying messages and replying in-thread, and the Slack user ID as the
`conversation_id`. That integration isn't part of this repo — `/query` is the
single integration point, so any client can sit in front of it.

Known limitations, carried over honestly:

- **Read-only.** No writes back to Sheets.
- **In-process memory.** Conversation state is a bounded dict with a 30-minute
  TTL, lost on restart. Multi-worker deployments need a shared store (Redis).
- **No per-user authorization.** Anyone who can reach the bot can query any record.
- **English, support-domain phrasing.** Open-ended questions get a clarification
  prompt rather than a guess.

---

## Tech stack

Python 3.11+ · FastAPI · Pydantic · pandas · OpenAI · gspread · pytest ·
React 18 · Vite · Tailwind CSS
