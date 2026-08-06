# Project Overview — CPaaS Support Assistant

> See also: [ARCHITECTURE.md](./ARCHITECTURE.md) for system design, [the README](../README.md) for day-to-day usage.

> **Demo build.** This repository is the public demo of the project: it ships fictional CSV data and runs with no API keys. Sections below describing Google Sheets, Slack, or n8n document the original production deployment and are not required to run the demo. See the [README](../README.md).


## 1. Project Objective

Give internal support and operations staff a single conversational interface — Slack — for looking up CPaaS platform data (virtual mobile numbers, gateways, tickets, customers, and source/line configuration) that today lives in Google Sheets, without needing to open the spreadsheet, know which tab to search, or manually cross-reference records.

## 2. Business Problem

CPaaS operations data (VMNs, gateways, tickets, customers, source configuration) is maintained in Google Sheets. Support staff answering "who owns gateway 470?" or "what's the status of this number?" today have to:

- Know which sheet/tab holds the answer
- Manually search or filter rows
- Cross-reference across sheets (e.g. a number → its gateway → that gateway's owning customer)
- Repeat this for every follow-up question in a ticket or chat thread

This is slow, error-prone, and doesn't scale as the number of sheets/rows grows.

## 3. Existing Manual Workflow

1. Support agent receives a question (via ticket, Slack DM, or call) referencing a number, gateway, ticket, customer, or source.
2. Agent opens the relevant Google Sheet.
3. Agent manually searches/filters for the identifier.
4. Agent manually reads off the relevant column(s).
5. For follow-up questions ("who owns it?", "what's its status?"), the agent repeats the search, since there is no memory of what "it" refers to.

## 4. Proposed Solution

A conversational assistant that:

1. Accepts a natural-language question through Slack.
2. Parses the question into a structured query (entity type, identifier, requested field, filters) using an LLM (OpenAI) with an offline rule-based fallback.
3. Routes the query to the correct logical data sheet.
4. Retrieves the matching record(s) from Google Sheets (or CSV in local/dev mode).
5. Formats and, where enabled, generates a natural-language answer grounded strictly in the retrieved data.
6. Remembers the last entity referenced in a conversation, so follow-up questions like "who owns it?" resolve correctly without the user repeating the identifier.
7. Replies in the same Slack thread the question was asked in.

Full request path: **Slack → n8n → FastAPI → OpenAI (parse + optional answer generation) → Google Sheets (retrieval) → JSON response → n8n → Slack**. See [ARCHITECTURE.md](./ARCHITECTURE.md) for the detailed breakdown of each layer.

## 5. Scope

**In scope:**
- Natural-language lookup and list queries across five entity types: VMN/number, gateway, customer, ticket, source.
- Operator lookup for a given number.
- Slack as the production chat interface, via n8n as an integration layer.
- Google Sheets as the production data backend (CSV as a local/offline data backend for development and testing).
- Single-turn and short follow-up conversational memory, keyed by Slack user ID.
- API-key-authenticated backend endpoint (`/query`) as the single integration point for any client.

**Out of scope (see also [Limitations](#7-limitations)):**
- Writing/updating data in Google Sheets (the system is read-only).
- Multi-tenant or role-based access control.
- A hardened production web UI (the included React app is a demo/development interface — see below).
- Persistent, cross-session conversation history (memory is in-process and time-limited).

## 6. Features

- **Natural-language querying** for numbers, gateways, tickets, customers, and source/line records.
- **Lookup and list actions** — "status of 9152001212" (lookup) vs. "show all active numbers" (list, with filters like status/operator).
- **Hybrid parsing** — OpenAI-based parser as primary, with an offline regex/keyword-based rule parser as automatic fallback if the LLM is unavailable, misconfigured, or fails.
- **Conversation memory** — the most recently referenced entity per conversation is remembered for ~30 minutes, so "who owns it?" / "what's its status?" resolve without repeating the identifier.
- **Optional LLM-generated answers** — when enabled, retrieved records are turned into a natural-language answer by OpenAI; a deterministic text formatter is always available as a fallback (`ANSWER_GENERATION=false`, or if the LLM call fails).
- **Google Sheets or CSV backend** — swappable via a single environment variable, with tab-name resolution that tolerates minor naming variation ("Gateway details" vs "Gateways" vs "Gateway", etc.) and a per-sheet column-header alias map.
- **Slack production interface** — via an n8n workflow that relays messages to the backend and replies in-thread.
- **API-key authentication** on the backend endpoint used by n8n.

## 7. Limitations

- **Read-only.** The bot cannot create, update, or delete records in Google Sheets or CSV data.
- **In-memory conversation state.** Conversation memory lives in a single process's memory (a plain Python dict), not a database. It is lost on backend restart, and if the backend is ever run with multiple worker processes, a user's follow-up question can land on a different worker and lose context. Single-worker deployment is required until this is addressed (see [Production notes in the README](../README.md#production-notes)).
- **Single LLM provider.** Only OpenAI is currently wired in (`LLM_PROVIDER=openai`); other providers are not implemented.
- **No authentication/authorization on *who* is asking within Slack** — any Slack user who can message the bot can query any record; access is not scoped per user or channel.
- **The React frontend is a demo/development interface.** It was used to build and test the backend before Slack became the production interface, and was not part of the production deployment. In this demo build it is the primary way to try the bot (see [ARCHITECTURE.md](./ARCHITECTURE.md)).
- **English-language, support-domain question patterns.** The parser (both LLM and rule-based) is tuned for CPaaS support phrasing; open-ended or unrelated questions will be rejected or met with a clarification request.

## 8. Future Enhancements

These are natural extensions **not currently implemented** — listed here as candidates for future work, not commitments:

- Shared/external conversation memory (e.g. Redis) to support multi-worker deployment and horizontal scaling.
- Additional LLM providers behind the existing `llm/factory.py` seam.
- Write-capable actions (e.g. updating a ticket's status) with appropriate guardrails.
- Per-user/per-channel access control in Slack.
- Structured audit logging of who asked what and when.
- Rate limiting on the `/query` endpoint.

See [Production notes in the README](../README.md#production-notes) for a fuller list of known risks and suggested next steps.

---

## Diagrams

The request-flow and layering diagrams live in [ARCHITECTURE.md](./ARCHITECTURE.md#1-overall-system-architecture).