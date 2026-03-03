# Project Map — fastapi-hub-spoke

## Architecture

```
fastapi-hub-spoke/
├── shared_services/        # Hub — shared core, never edited per-venture
│   ├── core/               #   config, database (RLS), redis, context
│   ├── middleware/         #   VentureIDMiddleware (X-Venture-ID header)
│   ├── models/             #   hub.organizations, hub.users, hub.knowledge_base
│   └── api/                #   health, shared routers
│
├── spokes/                 # One sub-directory per venture (isolated)
│   ├── neufin/             #   Fintech / Behavioral Bias Detection
│   ├── arisole/            #   IoT / Gait Analysis
│   ├── neumas/             #   Retail / Inventory Intelligence
│   └── apex/               #   Events / Golf Performance
│
├── migrations/             # Alembic — hub-level schema migrations
│   └── versions/
│       └── 001_knowledge_base_pgvector.py
├── scripts/
│   └── init-db.sql         # Bootstrap: extensions, schemas, optional role
├── alembic.ini
├── docker-compose.yml
└── requirements.txt
```

---

## Shared Core (`shared_services/`)

All ventures share a single deployment of `shared_services`. It is the only
service with direct access to the hub PostgreSQL database.

| Concern | Location | Notes |
|---|---|---|
| Database session | `core/database.py` | Sets `app.current_venture_id` via `SET LOCAL` on every transaction |
| Request context | `core/context.py` | `ContextVar` — async-safe, no thread locals |
| Tenant isolation | `middleware/venture_id.py` | Rejects requests without `X-Venture-ID`; populates ContextVar |
| Shared tables | `models/hub.py` | `organizations`, `users`, `knowledge_base` (pgvector + RLS) |
| Row-Level Security | PostgreSQL policies | `venture_isolation` policy on every RLS-enabled table |

**Rule:** `shared_services/` must never contain venture-specific business logic.
Any domain concept that applies to only one venture belongs in that venture's spoke.

---

## Ventures

### 1. Neufin — `spokes/neufin/`

| Property | Value |
|---|---|
| Domain | Fintech / Behavioral Bias Detection |
| Core problem | Identify cognitive biases (loss aversion, overconfidence, recency bias) in real-time trading behaviour and surface actionable nudges |
| Key data | Trade events, portfolio snapshots, user session signals |
| Planned spoke tables | `spokes.neufin_trades`, `spokes.neufin_bias_scores`, `spokes.neufin_nudges` |
| Venture ID header | `X-Venture-ID: <neufin-uuid>` |

### 2. Arisole — `spokes/arisole/`

| Property | Value |
|---|---|
| Domain | IoT / Gait Analysis |
| Core problem | Collect high-frequency accelerometer/gyroscope data from smart insoles; detect gait abnormalities and injury risk in real time |
| Key data | Device telemetry streams, gait cycle segments, biomechanical risk scores |
| Planned spoke tables | `spokes.arisole_devices`, `spokes.arisole_sessions`, `spokes.arisole_gait_events` |
| Venture ID header | `X-Venture-ID: <arisole-uuid>` |

### 3. Neumas — `spokes/neumas/`

| Property | Value |
|---|---|
| Domain | Retail / Inventory Intelligence |
| Core problem | Predict stock-outs and overstock situations using sales velocity, supplier lead times, and demand signals; auto-generate replenishment orders |
| Key data | Product catalogue, stock levels, sales history, supplier SLAs |
| Planned spoke tables | `spokes.neumas_products`, `spokes.neumas_inventory`, `spokes.neumas_replenishment_orders` |
| Venture ID header | `X-Venture-ID: <neumas-uuid>` |

### 4. Apex — `spokes/apex/`

| Property | Value |
|---|---|
| Domain | Events / Golf Performance |
| Core problem | Track round-by-round golf performance, club-level statistics, and course-specific handicap trends; serve insights to players and coaches |
| Key data | Rounds, hole-by-hole scores, shot tracking, club bag configurations |
| Planned spoke tables | `spokes.apex_players`, `spokes.apex_rounds`, `spokes.apex_shots` |
| Venture ID header | `X-Venture-ID: <apex-uuid>` |

---

## Isolation Contract

Each spoke **must** follow these rules to preserve tenant isolation:

1. **All spoke tables live in the `spokes` PostgreSQL schema** (or a venture-specific
   sub-schema such as `spokes_neufin`) — never in `hub`.

2. **Spoke tables that store user data must include a `venture_id` column**
   and have PostgreSQL RLS enabled with the `venture_isolation` policy pattern
   (see `migrations/versions/001_knowledge_base_pgvector.py` for the template).

3. **A spoke may read from hub tables** (`hub.organizations`, `hub.users`,
   `hub.knowledge_base`) via the shared `get_db()` dependency — the RLS
   context is already set for the request's venture.

4. **A spoke must not write to another spoke's tables** — cross-venture
   reads/writes must go through an explicit hub API contract.

5. **Spoke-specific configuration** (API keys, model endpoints, device
   topics) lives in environment variables prefixed with the venture slug,
   e.g. `NEUFIN_OPENAI_KEY`, `ARISOLE_MQTT_BROKER_URL`.

6. **Each spoke has its own Alembic revision chain** starting from `down_revision = None`
   and is applied separately — hub migrations and spoke migrations do not mix.

---

## Running a Spoke Locally

```bash
# From the project root
X_VENTURE_ID=<uuid>          # set in shell or .env
SPOKE=neufin                 # which spoke to run

uvicorn spokes.$SPOKE.main:app --reload --port 8010
```

All spoke services inherit the base `requirements.txt`; add spoke-specific
packages in `spokes/<name>/requirements.txt`.
