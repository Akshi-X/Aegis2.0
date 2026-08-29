# AEGIS-X

**Pre-execution security and governance layer for autonomous financial agents.**

Autonomous agents are increasingly able to move money. AEGIS-X exists so they
cannot do it unsupervised. Every action an agent proposes is intercepted and
evaluated *before* it reaches banking infrastructure, and is then executed,
constrained, delayed, blocked, or escalated for human approval.

The agent never talks to the bank. It only ever proposes.

```
USER ──▶ AUTONOMOUS AGENT ──▶ [ AEGIS-X ] ──▶ BANK SIMULATOR
                              (evaluate)  └──▶ HUMAN REVIEW
```

---

## Status

Proposals flow through a ten-engine security pipeline that produces a recorded,
explainable decision, and that decision now drives the proposal's outcome: a
`BLOCK` blocks, an `EXECUTE` executes, and anything uncertain is routed to human
review. All seven signal engines and all three aggregation engines are
implemented; the anomaly engine runs a trained Isolation Forest model, and a
governance dashboard exposes the whole pipeline live.

| Component | State |
|---|---|
| Monorepo structure | Done |
| FastAPI backend + health probes | Done |
| React + TypeScript + Vite + Tailwind dashboard | Done |
| Database schema (7 entities) | Done |
| Bank simulator + transactional transfers | Done |
| Autonomous agent + instruction parsing | Done |
| Gemini integration with deterministic fallback | Done |
| Orchestrator + 10 engines (7 signal, 3 aggregation) | Done |
| Authority, risk fusion, trust, governance | Done |
| Intent, financial DNA, cascade, counterparty, blast radius | Done |
| Anomaly detection (trained Isolation Forest) | Done |
| YAML-driven policy + runtime engine toggles | Done |
| Human override + decision-to-status wiring | Done |
| Governance dashboard (7 views) | Done |

> **Note on execution.** When governance returns `EXECUTE` the proposal is
> marked `EXECUTED` directly — a demo stand-in for a settlement worker. In a
> production system a separate worker would perform the settlement against the
> bank; the decision and the money movement stay in different processes on
> purpose.

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/            # HTTP routers
│   │   │   ├── health.py   #   liveness + readiness
│   │   │   ├── accounts.py #   account reads
│   │   │   ├── bank.py     #   POST /bank/transfer
│   │   │   ├── agent.py    #   POST /agent/task
│   │   │   ├── actions.py  #   proposals, evaluation, human override
│   │   │   ├── engines.py  #   runtime engine on/off toggles
│   │   │   └── policy.py   #   read the active security policy
│   │   ├── core/           # Config, policy loader, domain exceptions
│   │   ├── database/       # Engine, session, base, init + seed
│   │   ├── ml/             # Isolation Forest: training script + saved model
│   │   │   ├── train_anomaly_model.py
│   │   │   └── models/     #   isolation_forest_model.joblib, scaler, dataset
│   │   ├── models/         # SQLAlchemy ORM models (7 entities)
│   │   ├── policy/         # policy.yaml — the enforced security policy
│   │   ├── schemas/        # Pydantic request/response contracts
│   │   ├── services/
│   │   │   ├── bank.py     #   the only code that moves money
│   │   │   ├── agent.py    #   instruction → proposal (no bank access)
│   │   │   ├── audit.py    #   append-only event log
│   │   │   ├── orchestrator.py  # the evaluation pipeline
│   │   │   ├── engines/    #   10 security engines
│   │   │   └── llm/        #   Gemini + deterministic parsers
│   │   └── main.py         # FastAPI application entrypoint
│   ├── demo_1_benign.py … demo_5_high_budget.py  # scripted scenarios
│   ├── tests/              # 130 tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/     # Dashboard views, layout, shared UI
│   │   ├── services/       # Typed backend clients (agents, actions, dashboard)
│   │   ├── hooks/          # useAsync and friends
│   │   ├── index.css       # Tailwind v4 entry and design tokens
│   │   └── main.tsx
│   ├── Dockerfile          # dev (Vite) and production (nginx) targets
│   └── package.json
│
├── docs/                   # Architecture and phase notes
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Running the project

### Option A — Docker Compose (recommended)

Starts all three services with one command.

```bash
cp .env.example .env
```

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | `localhost:5432` |

The backend waits for PostgreSQL to pass its healthcheck before starting. Both
backend and frontend hot-reload on file changes.

To stop:

```bash
docker compose down
```

To also discard the database volume:

```bash
docker compose down -v
```

### Option B — Run locally without Docker

You need Python 3.12+, Node 20+, and (optionally) a local PostgreSQL.

**Backend**

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
```

**Frontend** (in a second terminal)

```bash
cd frontend && npm install && npm run dev
```

The backend starts and serves `/health` even with no database running — the
liveness probe deliberately has no external dependencies.

---

## The dashboard

The frontend at http://localhost:5173 is a live governance console over the
backend. Seven views:

| View | What it shows |
|---|---|
| **Overview** | Fleet-wide security metrics and a live decision feed. |
| **Agents** | The agent registry and each agent's authority envelope. |
| **Actions** | Every proposal, its evaluation, and per-engine findings. |
| **Financial DNA** | Learned behavioural profile and deviation ranges. |
| **Security** | Engine coverage and the runtime on/off toggles. |
| **Human Review** | Escalated proposals awaiting an approve/reject decision. |
| **Audit Logs** | The append-only event timeline, refusals included. |

---

## Testing the health endpoint

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "aegis-x"
}
```

There is a second, deeper probe that also verifies PostgreSQL connectivity:

```bash
curl -i http://localhost:8000/health/ready
```

Returns `200` with `"database": "connected"` when PostgreSQL is reachable, and
`503` with `"status": "degraded"` when it is not. This separation matters:
liveness failing should restart the container, readiness failing should only
stop traffic being routed to it.

---

## Environment variables

Copy `.env.example` to `.env`. Nothing is required — every variable has a
working default — but these are what you can configure.

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | Environment name; affects SQL echo logging. |
| `DEBUG` | `true` | Verbose logging. |
| `POSTGRES_USER` | `aegis` | Database user. |
| `POSTGRES_PASSWORD` | `aegis` | Database password. **Change outside local dev.** |
| `POSTGRES_DB` | `aegis` | Database name. |
| `POSTGRES_HOST` | `localhost` | Only used when running the backend on the host. |
| `POSTGRES_PORT` | `5432` | Published database port. |
| `DATABASE_URL` | *(unset)* | Overrides the assembled URL entirely. Compose sets this to reach the `db` service. |
| `GEMINI_API_KEY` | *(unset)* | Enables Gemini instruction parsing. Falls back to the deterministic parser when absent. |
| `LLM_PROVIDER` | `auto` | `auto`, `gemini`, or `heuristic`. |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed origins. |
| `VITE_API_BASE` | `http://localhost:8000` | Backend URL as seen from the browser. |

Two notes worth knowing:

- **`VITE_API_BASE` is read by the browser, not the container**, so it must be
  a host-reachable URL (`http://localhost:8000`) rather than the compose
  service name.
- **Only `VITE_`-prefixed variables reach client code.** Never put a secret
  behind that prefix; it ends up in the JavaScript bundle.

---

## API surface

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service metadata |
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe including PostgreSQL |
| `GET` | `/accounts` | List all bank accounts |
| `GET` | `/accounts/{id}` | Fetch one account |
| `GET` | `/accounts/{id}/transactions` | Ledger history (both directions) |
| `POST` | `/bank/transfer` | Execute a simulated transfer |
| `POST` | `/agent/task` | Give the agent a natural-language instruction |
| `GET` | `/actions` | List action proposals |
| `GET` | `/actions/{action_id}` | Fetch one proposal |
| `POST` | `/actions/{action_id}/evaluate` | Run the AEGIS-X pipeline |
| `GET` | `/actions/{action_id}/evaluations` | Evaluation history |
| `PATCH` | `/actions/{action_id}/status` | Human override of a proposal's status |
| `GET` | `/engines/config` | Current on/off state of every engine |
| `PATCH` | `/engines/config/{engine_key}` | Toggle an engine on or off at runtime |
| `GET` | `/policy` | The active, enforced security policy |
| `GET` | `/docs` | Swagger UI |

A human override (`PATCH /actions/{id}/status`) cannot resurrect a settled
proposal: once a proposal is `EXECUTED` or `FAILED`, the endpoint returns `400
invalid_status`.

---

## Database schema

Seven entities, all in [`backend/app/models/`](backend/app/models/).

| Entity | Purpose |
|---|---|
| `BankAccount` | Ledger balances. `CHECK (balance >= 0)`. |
| `Agent` | Autonomous agent registry and its authority envelope. |
| `Counterparty` | Known payees; `trusted` flag and `risk_score`. |
| `Transaction` | Actual money movement. A row here means money moved. |
| `ActionProposal` | What an agent *wants* to do. Never auto-executed. |
| `ActionEvaluation` | An immutable record of one pipeline run over a proposal. |
| `AuditLog` | Append-only event record, including refusals. |

Two schema decisions worth knowing:

- **Money is `NUMERIC(18,2)`, never `FLOAT`.** Binary floating point cannot
  represent decimal currency exactly and the error compounds across a ledger.
- **`ActionProposal.provenance` exists from day one.** It carries the original
  instruction and any retrieved context the agent consumed. Once an instruction
  has been flattened into structured fields, a successful prompt injection is
  indistinguishable from a legitimate request — manipulation can only be
  detected by inspecting what the agent *read*.

### Seed data

Applied automatically on startup (idempotent). Manual control:

```bash
cd backend && .venv/bin/python -m app.database.seed --reset
```

| id | Account | Number | Balance | Type |
|---|---|---|---|---|
| 1 | Main Company Account | `ACC1000000001` | 5,000,000.00 INR | COMPANY |
| 2 | ABC Technologies | `ACC2000000001` | 0.00 INR | VENDOR (trusted) |
| 3 | XYZ Cloud | `ACC2000000002` | 0.00 INR | VENDOR (trusted) |
| 4 | Unknown Account | `ACC9000000001` | 0.00 INR | EXTERNAL (untrusted) |

Plus **Treasury Agent** — objective *"Pay legitimate company vendor invoices."*,
max transaction 100,000 INR, daily limit 500,000 INR.

---

## Bank simulator

`POST /bank/transfer` checks the balance, debits the source, credits the
destination, and writes a ledger row — all inside **one database transaction**,
so a partial transfer cannot occur. Both account rows are locked with
`SELECT ... FOR UPDATE` in ascending id order, which prevents two concurrent
transfers from jointly overdrawing an account without risking deadlock.

```bash
curl -X POST http://localhost:8000/bank/transfer \
  -H "Content-Type: application/json" \
  -d '{"source_account_id":1,"destination_account_id":2,"amount":"50000.00","reference":"INV-204"}'
```

| Outcome | Status | `detail.code` |
|---|---|---|
| Success | `201` | — |
| Insufficient balance | `422` | `insufficient_funds` |
| Unknown source/destination | `404` | `account_not_found` |
| Currency mismatch | `422` | `currency_mismatch` |
| Amount ≤ 0, or same account | `422` | *(validation error)* |

Money amounts are serialised as **JSON strings** (`"50000.00"`), not numbers.
JavaScript numbers are IEEE-754 doubles, so parsing currency as a number
reintroduces exactly the precision loss `NUMERIC` avoids.

---

## Autonomous agent

```
natural language ──▶ parse ──▶ resolve ──▶ ActionProposal (PROPOSED)
                                                    │
                                                    ▼
                                        [ AEGIS-X evaluation ]
```

The agent's only job is to propose. It cannot execute: `app/services/agent.py`
and `app/api/agent.py` have no import path to the bank simulator, and the
service can only emit `PROPOSED`. Both properties are covered by tests
(`test_agent_never_moves_money`, `test_agent_module_cannot_reach_the_bank`).

```bash
curl -X POST http://localhost:8000/agent/task \
  -H "Content-Type: application/json" \
  -d '{"agent_id": 1, "task": "Pay ₹50,000 to ABC Technologies for invoice INV-204"}'
```

`agent_id` accepts the numeric id or the agent's name (`"Treasury Agent"`).

### Instruction parsing, with or without Gemini

Parsing sits behind one interface with two implementations:

| Provider | When used | Notes |
|---|---|---|
| `gemini` | `GEMINI_API_KEY` is set | Constrained decoding via `responseSchema`, `temperature: 0`, output re-validated with Pydantic. |
| `heuristic` | No key, or Gemini failed | Deterministic rules. Handles `₹`, Indian grouping (`15,00,000`), and magnitude words (`5 lakh`, `1.2 crore`). |

**No key is required.** With `LLM_PROVIDER=auto` (the default) the system uses
Gemini when configured and the deterministic parser otherwise. If a Gemini call
times out or fails, the request *still succeeds* via fallback — the response
reports `parser` and `fallback_used` so degradation is visible rather than
silent.

Two decisions worth knowing:

- **Recipient resolution is not the model's job.** Matching a payee name to a
  counterparty is deterministic backend logic. Matching is exact or
  case/punctuation-insensitive-exact, and deliberately *not* fuzzy — "ABC
  Technologies Ltd" silently resolving to "ABC Technologies" is the
  typosquatting failure mode this system exists to prevent.
- **The source account comes from the agent, never the instruction.** No
  wording can redirect which account is drained.

### Error handling

| Condition | Status | `detail.code` |
|---|---|---|
| Unknown agent | `404` | `agent_not_found` |
| Instruction not understood | `422` | `instruction_not_understood` |
| Agent has no source account | `409` | `no_source_account` |

Both successful proposals and rejected instructions are written to `AuditLog`.

---

## AEGIS-X orchestrator

```bash
curl -X POST http://localhost:8000/actions/{action_id}/evaluate
```

Ten engines run in two tiers. **Signal engines** produce independent findings
and never read each other's results; **aggregation engines** run afterwards in a
fixed order, because fusion needs the signals and governance needs both the
fused score and the trust tier.

| Engine | Tier | Role |
|---|---|---|
| `authority` | Signal | Agent status, action/currency allow-lists, per-transaction and daily limits, source account, balance. |
| `intent` | Signal | Objective alignment, behavioural drift, and prompt-manipulation cues (semantic heuristic). |
| `financial_dna` | Signal | Deviation from the agent's learned behavioural profile. |
| `anomaly` | Signal | Unsupervised Isolation Forest inference over transaction features. |
| `cascade` | Signal | Splitting, velocity, and burst-sequence patterns across recent activity. |
| `counterparty` | Signal | Who is being paid, judged from the money-flow network. |
| `blast_radius` | Signal | Potential damage if the action *is* bad — impact, not probability. |
| `risk_fusion` | Aggregation | Weighted aggregation over contributing engines. |
| `trust` | Aggregation | Reports stored trust and autonomy tier (read-only). |
| `governance` | Aggregation | Hard overrides, then thresholds. |

Every engine returns the same structure, so replacing or extending one is a
single-file change the orchestrator and API never see:

```json
{"engine": "authority", "status": "PASS", "risk_score": 0, "flags": [], "details": {}}
```

### Runtime engine toggles

Any engine can be switched off at runtime via `PATCH /engines/config/{key}` (the
Security view exposes this). A bypassed engine is skipped and does not
contribute to fusion — useful for demonstrating how much a single signal changes
the outcome. Toggling governance off makes the pipeline default to `ESCALATE`
rather than silently authorising anything.

### Three decisions that shape the whole pipeline

**A non-contributing engine returns `risk_score: null`, never `0`.** Zero is a
finding — "I looked and saw no risk". Null means "I did not look, or I have
nothing to say here". Conflating them would let quiet engines dilute a genuine
Authority failure of 100 down toward 10, producing a system that looks like it
works while assuring nothing. Fusion excludes non-contributing engines and
renormalises the remaining weights.

**Correlated engines share a group and combine by `max`, not sum.** Financial
DNA and the Isolation Forest read overlapping features, so adding both counts
one signal twice. Grouping keeps correlated evidence from double-counting.

**Governance authorises conservatively.** Refusing an action can be justified by
the Authority engine alone; *authorising* one requires broad coverage. When
coverage is incomplete, anything that would otherwise pass is escalated for
human review and marked `provisional`.

### Decisions

| Situation | Decision | Proposal status |
|---|---|---|
| Authority `FAIL` (limit breach, suspended agent, disallowed currency) | `BLOCK` | `BLOCKED` |
| Any engine at risk ≥ 90 | `BLOCK` | `BLOCKED` |
| No disqualifying finding, coverage incomplete | `ESCALATE` | `PENDING_APPROVAL` |
| Full coverage, fused risk < 30, trusted agent | `EXECUTE` | `EXECUTED` |

Each evaluation is persisted immutably in `action_evaluations`. Re-evaluating
appends a new record rather than overwriting one, and the resulting decision
updates the proposal's status so the dashboard reflects the outcome immediately.

---

## Anomaly model

The anomaly engine loads a trained Isolation Forest from
`app/ml/models/isolation_forest_model.joblib` with its feature scaler. To
retrain against the sample dataset:

```bash
cd backend && .venv/bin/python -m app.ml.train_anomaly_model
```

---

## Demo scenarios

Five scripted end-to-end scenarios drive the full agent → evaluate → decide flow
against a running backend:

```bash
cd backend && .venv/bin/python demo_1_benign.py
```

| Script | Scenario |
|---|---|
| `demo_1_benign.py` | A routine, in-policy vendor payment. |
| `demo_2_escalate.py` | A borderline action routed to human review. |
| `demo_3_malicious.py` | A payment that trips the security engines and is blocked. |
| `demo_4_cascade.py` | A split/burst sequence caught by the cascade engine. |
| `demo_5_high_budget.py` | A high-value action against limits and blast radius. |

---

## Running tests

```bash
cd backend && .venv/bin/python -m pytest
```

130 tests, covering transfers, atomicity and money conservation; instruction
parsing, recipient resolution, and provider fallback; the guarantee that the
agent never moves money; every security engine; risk-fusion arithmetic;
engine-failure isolation; and the fail-safe governance gate.

Tests default to a throwaway SQLite file so the suite needs no running
services. To exercise the real PostgreSQL target:

```bash
cd backend && TEST_DATABASE_URL=postgresql+psycopg://aegis:aegis@localhost:5432/aegis_test .venv/bin/python -m pytest
```

---

## Running without Docker or PostgreSQL

The backend defaults to PostgreSQL. To run with no infrastructure at all,
override the URL with SQLite:

```bash
cd backend && DATABASE_URL=sqlite:///./aegis.db .venv/bin/uvicorn app.main:app --reload --port 8000
```

This is a development convenience only. PostgreSQL is the real target: SQLite
has no row-level locking and stores `NUMERIC` via float.

---

See [`docs/architecture.md`](docs/architecture.md) for the architecture and
design notes.
