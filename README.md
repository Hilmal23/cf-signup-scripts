# Cloudflare Workers AI Proxy

OpenAI-compatible gateway for Cloudflare Workers AI with account-pool rotation,
**neuron budget tracking**, and a **React dashboard**.

Rotates across all your `cloudflare-ai` accounts (imported from the 9router DB),
auto-skips accounts on 429 **and** proactively skips accounts that have used up
their 10,000 free neurons for the UTC day.

## Stack

- **Backend**: Node 22 + Express + built-in `node:sqlite` + native `fetch`. No native builds.
- **Frontend**: Vite + React + [Mantine](https://mantine.dev) + `react-markdown` (lazy-loaded).
  Served by the backend in production. Code-split: mantine + the markdown renderer ship as
  separate cacheable chunks; the Logs tab (with markdown) is fetched only when opened.

## Quick start

```bash
# 1. install + build the dashboard
npm install
npm run build            # installs & builds web/ into web/dist

# 2. configure (optional — sensible defaults)
cp .env.example .env

# 3. run
npm start                # node --env-file=.env --no-warnings server.js
```

Then open <http://127.0.0.1:8750> for the dashboard, and click **Import from 9router**
to populate the account pool (import is manual — nothing is imported at boot).

Dev mode with hot reload (frontend on :5173, proxied to the backend on :8750):

```bash
npm run dev              # backend with --watch
cd web && npm run dev    # vite dev server
```

## Neuron tracking — how it works, and its limits

The `cfut_` account tokens are scoped to inference only, so Cloudflare's official
neuron analytics (GraphQL `totalNeurons`) returns *"not authorized"*. Instead, the
proxy **estimates** neuron usage from the token `usage` that CF returns on every
response (both streaming and non-streaming):

```
neurons ≈ prompt_tokens × rate_in + completion_tokens × rate_out
```

Rates come from [CF's pricing page](https://developers.cloudflare.com/workers-ai/platform/pricing/)
(`lib/neurons.js`). Models CF hasn't published yet (kimi, glm, qwq) fall back to a
70b-class rate — deliberately high, so the proxy skips early rather than overrunning.

> This is an **estimate (±a few %)**, not CF billing. It's for "how much is left
> today" and proactive rotation — not accounting.

Counters reset per account at **00:00 UTC** (lazily, on first use after the rollover).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/health` | Pool stats (available / cooldown / neurons used+remaining today) |
| GET  | `/v1/models` | Live model list from CF (Cloudflare-hosted only, newest-first) |
| POST | `/v1/chat/completions` | OpenAI-compatible chat (stream + non-stream) |
| POST | `/v1/embeddings` | OpenAI-compatible embeddings |
| POST | `/ai/run/:model` | Generic CF passthrough for ANY task (image, speech, translation, …) |
| GET  | `/api/stats` | Aggregate pool + neuron stats (dashboard) |
| GET  | `/api/accounts` | Per-account rows: status, neurons today, remaining, requests |
| GET  | `/api/models` | Rich model list (name, task, capabilities, added date). `?fresh=1` bypasses the cache |
| GET  | `/api/logs` | Recent request log (in-memory ring buffer, newest-first) |
| DELETE | `/api/logs` | Clear the request log |
| POST | `/api/import` | Manual import from the 9router DB → `{imported, skipped, total}` |

The proxy supports **all Cloudflare Workers AI capabilities**, not just chat:
text generation, embeddings, text-to-image, text-to-speech, speech recognition,
translation, classification, and image-to-text. Each call rotates across the
account pool with the same 429-cooldown and neuron-budget logic as chat.

> Note on neuron accounting: chat and `/ai/run` responses include token usage,
> so they're counted. CF's embeddings endpoint returns no `usage`, so embeddings
> calls are not counted toward the per-account neuron budget (they're cheap).

When `CF_PROXY_API_KEY` is set, `/v1/*`, `/api/*`, `/ai/*`, and `/health` require
`Authorization: Bearer <key>` (matched case-insensitively). The dashboard prompts
for the key and stores it locally.

## Model IDs — short, mid, or full

The `/v1/models` list is fetched live from Cloudflare (Cloudflare-hosted models
only — third-party/partner models are excluded), sorted newest-first. Any model
CF adds appears automatically within the 10-minute cache TTL; there is no
hardcoded list and no "add model" step.

You can call a model by its **full**, **vendor/model**, or **short** id — the proxy
resolves it to the full CF id before the upstream call:

| Input | Resolves to |
|-------|-------------|
| `@cf/meta/llama-3.2-1b-instruct` | (used as-is) |
| `meta/llama-3.2-1b-instruct` | `@cf/meta/llama-3.2-1b-instruct` |
| `llama-3.2-1b-instruct` | `@cf/meta/llama-3.2-1b-instruct` |

If a short id is ambiguous (two vendors share a model name), the proxy returns
`409` with the candidate full ids so you can disambiguate with `vendor/model`.
Unknown model → `404`.

## Dashboard

Served at `/` (built SPA). Tabs:

- **Accounts** — per-account status (available / cooldown / exhausted), neuron
  usage bar, requests today. Paginated, sortable, auto-refreshes every 10s.
- **Models** — live model list with task, capabilities, and a **NEW** badge for
  models Cloudflare added in the last 30 days. Search + task filter + sort.
- **Logs** — recent requests (last 500, in-memory). Each row expands to a
  **humanized** view of three payloads: **Client Request** (as received),
  **Provider Request** (after model-resolve + content-flatten, i.e. what was sent
  to CF), and **Provider Response** (final). Chat payloads render as role bubbles
  (system / user / assistant / tool) with:
  - `tools` definitions shown as a collapsible panel
  - `tool_calls` shown inline as `→ calls name(args)`
  - reasoning (`<think>…</think>`) split into a collapsible **Reasoning** panel
  - the assistant answer rendered as markdown

  The request log is in-memory (not persisted) and clears on restart.

## 9router integration

Point 9router at this proxy as an OpenAI-compatible provider:

- Base URL: `http://127.0.0.1:8750/v1`
- API Key: whatever you set in `CF_PROXY_API_KEY` (or empty)
- Models: `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b`, etc.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CF_PROXY_HOST` | `0.0.0.0` | Listen host |
| `CF_PROXY_PORT` | `8750` | Listen port |
| `CF_PROXY_API_KEY` | (empty) | Bearer token auth (empty = no auth) |
| `CF_PROXY_9ROUTER_DB` | `~/.9router/db/data.sqlite` | Source DB for the import button |
| `CF_PROXY_DB` | `./data/accounts.db` | Own accounts + neuron-counter DB |
| `CF_PROXY_COOLDOWN_429` | `90` | Seconds to skip an account after a **rate-limit** 429. A daily-neuron-limit 429 (CF error code 4006) always cools until 00:00 UTC regardless. |
| `CF_PROXY_MAX_RETRIES` | `5` | Max accounts to try per request |
| `CF_PROXY_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARN` / `ERROR` |

## Project layout

```
server.js            entry: config, auth, wires routes, serves web/dist
lib/
  db.js              node:sqlite init + neuron-column migration
  pool.js            AccountPool: rotation, 429 cooldown, neuron budget + reservations
  neurons.js         per-model neuron rate table + estimate()
  models.js          live CF model list (cached) + short→full id resolver
  importer.js        9router → accounts import
  cf.js              upstream calls (chat/embeddings/run), usage + error extraction
  log.js             in-memory request-log ring buffer
routes/
  chat.js            /v1/chat/completions, /v1/embeddings, /ai/run/:model
  admin.js           /health, /v1/models, /api/*
web/                 Vite + React + Mantine dashboard
```

## Tests

```bash
npm run selftest         # neuron estimation self-check
```
