# CLAUDE.md — fastapi-hub-spoke

This file is read by Claude Code at the start of every session.
Follow every instruction here without exception.

---

## What this project is

A **Multi-Venture Hub** built on FastAPI + PostgreSQL + LangGraph.
One shared infrastructure layer (`shared_services/`) serves four
commercially distinct ventures (`spokes/`), each with fully isolated
business logic, database rows, and AI orchestration graphs.

---

## Absolute rules — read before touching any file

### 1. Every API response must be scoped to a Venture ID

- Every non-exempt endpoint receives an `X-Venture-ID` HTTP header.
- `VentureIDMiddleware` (`shared_services/middleware/venture_id.py`)
  stores it in `core.context.current_venture_id` (a `ContextVar`).
- `get_db()` (`shared_services/core/database.py`) opens a transaction
  and immediately executes `SET LOCAL app.current_venture_id = '<id>'`.
- PostgreSQL Row-Level Security (`venture_isolation` policy) then
  filters **every** `SELECT`, `INSERT`, `UPDATE`, and `DELETE`
  automatically — no manual `WHERE venture_id = ...` is ever needed or
  acceptable as a substitute for RLS.
- **Never** return rows from one venture to a request carrying a
  different venture's ID. If you add a new table that holds per-venture
  data, it must have a `venture_id` column and an RLS policy before
  any endpoint touches it.

### 2. LangGraph is the orchestration layer

- Multi-step AI workflows (bias detection, gait scoring, demand
  forecasting, shot analysis) are implemented as **LangGraph graphs**,
  not as chains of raw LLM calls or ad-hoc Python functions.
- Each graph lives in `spokes/<venture>/graphs/`.
- Graph nodes are pure async functions; side-effects (DB writes,
  external API calls) happen inside nodes, not between them.
- State schemas are typed `TypedDict`s defined alongside each graph.
- The Claude model used for LLM nodes: `claude-sonnet-4-6` (default)
  or `claude-opus-4-6` for high-reasoning tasks.

### 3. Shared core is read-only from a venture perspective

- `shared_services/` is infrastructure. Never add venture-specific
  logic there.
- Ventures may **read** `hub.organizations`, `hub.users`, and
  `hub.knowledge_base` via `get_db()`.
- Ventures **must not** write to another venture's spoke tables.

### 4. Database conventions

- Hub tables → `hub` PostgreSQL schema.
- Spoke tables → `spokes` schema (or `spokes_<slug>` for ventures
  that need schema-level isolation).
- Every spoke table with user or business data must have:
  - `venture_id UUID NOT NULL` column.
  - RLS enabled (`ENABLE ROW LEVEL SECURITY`).
  - RLS forced (`FORCE ROW LEVEL SECURITY`).
  - `venture_isolation` policy using
    `current_setting('app.current_venture_id', true)`.
- Hub migrations live in `migrations/versions/`.
- Each spoke has its own independent Alembic chain under
  `spokes/<name>/migrations/versions/`, starting from
  `down_revision = None`.

### 5. Environment variables

- Shared: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `APP_ENV`, `DEBUG`
- Per-venture: prefixed with the venture slug in SCREAMING_SNAKE_CASE.
  Examples:
  - `NEUFIN_OPENAI_KEY`, `NEUFIN_ALPACA_API_KEY`
  - `ARISOLE_MQTT_BROKER_URL`, `ARISOLE_DEVICE_TOPIC_PREFIX`
  - `NEUMAS_SHOPIFY_API_KEY`, `NEUMAS_SUPPLIER_WEBHOOK_SECRET`
  - `APEX_GOLF_API_KEY`, `APEX_HANDICAP_SERVICE_URL`

### 6. Code style

- Python 3.12+. Use `X | Y` union syntax, not `Optional[X]`.
- Async everywhere — no synchronous DB calls, no `requests` library.
- Pydantic v2 for all schemas and settings.
- SQLAlchemy 2.x mapped-column style (`Mapped[T]`, `mapped_column()`).
- No `print()` — use structured logging via the standard `logging` module.
- Do not add docstrings, comments, or type annotations to code you did
  not change in the current task.

---

## Venture Guard

These rules are **non-negotiable** and enforced at every layer of the stack
(code structure, middleware, and database).  Treat any violation as a
critical bug regardless of how "convenient" a shortcut seems.

### Rule 1 — No cross-spoke imports

Spoke code must never import from another spoke's package.

```
# ILLEGAL — Neufin importing Arisole logic
from spokes.arisole.graphs.gait_analysis import GaitState   # ← forbidden

# LEGAL — using shared hub infrastructure
from shared_services.core.database import get_db
from shared_services.graph.pii import scrub
```

If two spokes need the same helper, extract it into `shared_services/`
only if it is genuinely domain-agnostic.  Domain concepts belong to
their venture's spoke exclusively.

### Rule 2 — Venture-specific prompts stay in their spoke

All system prompts, few-shot examples, and prompt templates that are
specific to a venture must live inside `spokes/<venture>/`.

```
spokes/neufin/prompts/bias_detection.py    ✓
shared_services/graph/nodes/agent_node.py  ✓  (generic, configurable)
shared_services/graph/neufin_prompts.py    ✗  (venture logic in shared)
```

The hub's `agent_node` receives its persona from the Router node at
runtime — it must not hard-code venture-specific instructions.

### Rule 3 — Shared services changes must be backward-compatible

Before modifying any file under `shared_services/`, verify that the
change does not break the contract relied on by all four ventures.

Checklist before any `shared_services/` edit:
- [ ] `get_db()` still sets `SET LOCAL app.current_venture_id` in a
      transaction before yielding.
- [ ] `VentureIDMiddleware` still enforces all three Zero Trust gates.
- [ ] `ChatState` keys are additive only — never rename or remove fields.
- [ ] `pii.scrub()` still returns `(str, list[str])`.
- [ ] No new mandatory env vars added without defaults.

---

## Zero Trust — how the middleware enforces venture isolation

`shared_services/middleware/venture_id.py` runs three sequential gates:

| Gate | Check | Failure |
|---|---|---|
| 1 — Presence | Both `X-Venture-ID` and `X-API-Key` headers exist | 400 |
| 2 — Signature | HMAC-SHA256 of `"{slug}:{venture_id}"` matches the key's embedded sig | 401 |
| 3 — Path scope | If the URL is under `/api/v1/spokes/{slug}/…`, the key's slug must match | 403 |

**Key format:** `{venture_slug}.{base64url(hmac_sha256(secret, "{slug}:{uuid}"))}`

**Scenario: Neufin key → Arisole endpoint**
```
X-Venture-ID: <neufin-uuid>
X-API-Key:    neufin.<valid-neufin-sig>
Path:         /api/v1/spokes/arisole/telemetry

Gate 2 → PASS  (HMAC of "neufin:<neufin-uuid>" is valid)
Gate 3 → FAIL  (path slug "arisole" ≠ key slug "neufin") → 403 Forbidden
```

**Generating a key (management script / one-time CLI):**
```python
from shared_services.core.api_keys import make_api_key
key = make_api_key("neufin", "<neufin-org-uuid>")
# neufin.abc123…
```

Spoke endpoint convention — register all venture-specific routes under:
```
/api/v1/spokes/{venture_slug}/…
```

Hub-level endpoints (e.g. `/api/v1/chat`) have no slug in the path;
Gate 3 is skipped and any venture with a valid key may call them.

---

## Ventures

### Neufin — `spokes/neufin/` — Quant / Finance

| | |
|---|---|
| Domain | **Fintech / Behavioral Bias Detection** |
| Core problem | Identify cognitive biases (loss aversion, overconfidence, recency bias) in real-time trading behaviour; surface actionable nudges before a trade executes |
| Spoke tables | `spokes.neufin_trades`, `spokes.neufin_bias_scores`, `spokes.neufin_nudges` |
| LangGraph graphs | `bias_detection_graph` — trade event → multi-bias scorer → nudge generator → audit log |
| Spoke endpoint prefix | `/api/v1/spokes/neufin/` |

**Tech stack — Quant / Finance**

| Layer | Library / Service | Purpose |
|---|---|---|
| Market data | `ccxt` (async) or `alpaca-trade-api` | Real-time + historical OHLCV tick data |
| Signal processing | `pandas`, `numpy`, `ta-lib` | Rolling statistics, technical indicators, bias feature extraction |
| Time series | `statsmodels` | Volatility modelling (GARCH), regime detection |
| LLM | `anthropic` — `claude-sonnet-4-6` | Nudge text generation, bias explanation |
| Orchestration | `langgraph` | Stateful bias detection pipeline |
| Audit | PostgreSQL + `venture_id` + RLS | Every scored trade and generated nudge is logged and tenant-isolated |

**Key constraints:** P99 bias scoring latency < 200 ms (stream LLM tokens). Financial data
classified as PII-adjacent — PII scrubber must run on all LLM outputs. All nudges stored
with `venture_id + user_id` before being returned to the client.

---

### Arisole — `spokes/arisole/` — Sensor / Telemetry

| | |
|---|---|
| Domain | **IoT / Gait Analysis** |
| Core problem | Collect 200 Hz accelerometer + gyroscope streams from smart insoles; detect gait abnormalities and injury-risk patterns in real time |
| Spoke tables | `spokes.arisole_devices`, `spokes.arisole_sessions`, `spokes.arisole_gait_events` |
| LangGraph graphs | `gait_analysis_graph` — telemetry batch → gait segmentation → biomechanical risk score → event store |
| Spoke endpoint prefix | `/api/v1/spokes/arisole/` |

**Tech stack — Sensor / Telemetry**

| Layer | Library / Service | Purpose |
|---|---|---|
| Ingestion | `aiomqtt` | Async MQTT subscriber for device telemetry streams |
| Serialisation | `msgspec` or `protobuf` | Binary payload decoding (MessagePack / protobuf) at 200 Hz |
| Signal processing | `scipy`, `numpy` | FFT, peak detection, gait cycle segmentation |
| Similarity search | `pgvector` (cosine) | Match current gait embedding against known pathological patterns |
| LLM | `anthropic` — `claude-sonnet-4-6` | Clinical-language risk summary for physiotherapist reports |
| Orchestration | `langgraph` | Multi-stage telemetry → insight pipeline |

**Key constraints:** Telemetry endpoint accepts raw binary (`Content-Type: application/msgpack`
or `application/x-protobuf`). Device IDs are venture-scoped — no cross-venture device
lookup is permitted at any layer, including the database.

---

### Neumas — `spokes/neumas/` — Supply Chain

| | |
|---|---|
| Domain | **Retail / Inventory Intelligence** |
| Core problem | Predict stock-outs and overstock using sales velocity, supplier lead times, and demand signals; auto-draft replenishment purchase orders |
| Spoke tables | `spokes.neumas_products`, `spokes.neumas_inventory`, `spokes.neumas_replenishment_orders` |
| LangGraph graphs | `replenishment_graph` — stock analysis → demand forecast → reorder decision → PO draft (pending human approval) |
| Spoke endpoint prefix | `/api/v1/spokes/neumas/` |

**Tech stack — Supply Chain**

| Layer | Library / Service | Purpose |
|---|---|---|
| Forecasting | `statsforecast` (ARIMA, ETS, CrostonOptimized) | SKU-level demand forecasting with intermittent demand support |
| Webhooks | `httpx` (async) | Shopify order events, supplier SLA callbacks |
| Scheduler | `APScheduler` (async) | Nightly reorder evaluation job per venture |
| LLM | `anthropic` — `claude-sonnet-4-6` | PO narrative, supplier communication drafts |
| Orchestration | `langgraph` | Stateful supply-chain decision pipeline |
| Approval gate | PostgreSQL `status` enum (`pending`, `approved`, `rejected`) | Replenishment orders never auto-dispatch; humans approve |

**Key constraints:** Inventory levels and supplier pricing are commercially sensitive —
RLS is mandatory on all spoke tables. The `replenishment_graph` must terminate at
`status=pending`; no node may call a dispatch API directly.

---

### Apex — `spokes/apex/` — Events / Scheduling

| | |
|---|---|
| Domain | **Events / Golf Performance** |
| Core problem | Track round-by-round golf performance, club statistics, and course-specific handicap trends; deliver scheduling, tee-time and coaching insights |
| Spoke tables | `spokes.apex_players`, `spokes.apex_rounds`, `spokes.apex_shots` |
| LangGraph graphs | `performance_analysis_graph` — scorecard ingest → strokes-gained computation → similarity search → coaching insight |
| Spoke endpoint prefix | `/api/v1/spokes/apex/` |

**Tech stack — Events / Scheduling**

| Layer | Library / Service | Purpose |
|---|---|---|
| Scheduling | `APScheduler` (async) + `icalendar` | Tee-time booking, event calendar management, iCal export |
| Handicap | `httpx` → external WHS API | World Handicap System index retrieval and differential calculation |
| Similarity search | `pgvector` (cosine) | Shot-pattern matching against course and player archives |
| LLM | `anthropic` — `claude-sonnet-4-6` | Personalised coaching language, post-round summary |
| Orchestration | `langgraph` | Round ingest → insight pipeline |

**Key constraints:** Player handicap index is PII — RLS mandatory on all spoke tables.
Shot embeddings written to `hub.knowledge_base` must include the correct `venture_id`
so the RLS policy scopes them correctly. Scheduling endpoints must be idempotent
(tee-time double-booking must be prevented at the DB constraint level).

---

## File layout reference

```
fastapi-hub-spoke/
├── shared_services/
│   ├── core/
│   │   ├── config.py          # Pydantic Settings (incl. ANTHROPIC_API_KEY)
│   │   ├── context.py         # ContextVar current_venture_id
│   │   ├── database.py        # get_db() with SET LOCAL RLS
│   │   ├── api_keys.py        # HMAC signing/verification — Zero Trust
│   │   └── redis.py
│   ├── middleware/
│   │   └── venture_id.py      # VentureIDMiddleware — 3-gate Zero Trust
│   ├── models/
│   │   └── hub.py             # Organization, User, KnowledgeBase
│   ├── graph/
│   │   ├── state.py           # ChatState TypedDict
│   │   ├── pii.py             # PII scrubber (7 pattern types)
│   │   ├── chat_graph.py      # compiled StateGraph (Router→Agent→Security)
│   │   └── nodes/
│   │       ├── router_node.py # loads venture persona from DB
│   │       ├── agent_node.py  # calls claude-sonnet-4-6
│   │       └── security_node.py # PII scrub + audit log
│   ├── api/
│   │   ├── health.py
│   │   ├── chat.py            # POST /api/v1/chat
│   │   └── router.py
│   └── main.py
│
├── spokes/
│   ├── neufin/
│   │   ├── graphs/            # LangGraph graphs
│   │   ├── models/            # SQLAlchemy spoke models
│   │   ├── api/               # FastAPI routers
│   │   ├── migrations/        # Independent Alembic chain
│   │   └── main.py
│   ├── arisole/               # same structure
│   ├── neumas/                # same structure
│   └── apex/                  # same structure
│
├── migrations/                # Hub-level Alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_knowledge_base_pgvector.py
│
├── scripts/
│   └── init-db.sql
├── alembic.ini
├── docker-compose.yml
├── requirements.txt
└── project-map.md
```

---

## Quick-reference commands

```bash
# Apply hub migrations
alembic upgrade head

# Apply a spoke's migrations (once spoke alembic.ini exists)
alembic -c spokes/neufin/alembic.ini upgrade head

# Run the hub locally
cd shared_services && uvicorn main:app --reload --port 8000

# Run a spoke locally
cd spokes/neufin && uvicorn main:app --reload --port 8010

# Generate a signed API key for a venture (Python REPL from project root)
python - <<'EOF'
import sys; sys.path.insert(0, "shared_services")
from core.api_keys import make_api_key
print(make_api_key("neufin", "<neufin-org-uuid>"))
EOF

# Test the Zero Trust middleware (health is exempt — no key needed)
curl http://localhost:8000/api/v1/health

# Test a protected endpoint with both required headers
curl -X POST http://localhost:8000/api/v1/chat \
  -H "X-Venture-ID: <uuid>" \
  -H "X-API-Key: neufin.<sig>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'

# Verify cross-venture 403 (Neufin key → Arisole endpoint)
curl -X GET http://localhost:8000/api/v1/spokes/arisole/telemetry \
  -H "X-Venture-ID: <neufin-uuid>" \
  -H "X-API-Key: neufin.<sig>"
# → 403 Forbidden: Access denied: 'neufin' API key cannot access 'arisole' endpoints
```
