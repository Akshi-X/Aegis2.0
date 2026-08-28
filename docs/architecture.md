# AEGIS-X — Architecture

## The core idea

An autonomous financial agent must not be able to execute a financial action
directly. It may only *propose* one. An independent layer — AEGIS-X — evaluates
each proposal and decides its fate.

```
USER / COMPANY
      │  financial goal
      ▼
AUTONOMOUS FINANCIAL AGENT
      │  action proposal (never an execution)
      ▼
┌─────────────────────────────────────────┐
│  AEGIS-X                                │
│    Identity & Authority                 │
│    Intent Alignment                     │
│    Financial DNA                        │
│    Behavioural Anomaly (Isolation Forest)│
│    Prompt Manipulation                  │
│    Intent Drift                         │
│    Cascade / Sequence                   │
│    Counterparty Intelligence            │
│    Blast Radius                         │
│    Risk Fusion → Dynamic Trust          │
│    Governance                           │
└─────────────────────────────────────────┘
      │
      ├── EXECUTE ─────▶ BANK SIMULATOR
      ├── CONSTRAIN
      ├── DELAY
      ├── BLOCK          (never reaches the bank)
      └── ESCALATE ────▶ HUMAN REVIEW
```

## Design principles

**1. No decision is cosmetic.** Every verdict the UI displays must originate
from backend logic — rules, calculations, model inference, or LLM analysis.
The frontend renders decisions; it never makes them.

**2. The agent is untrusted by construction.** AEGIS-X does not assume the
agent is compromised, but it never relies on the agent being honest either.
Authority limits are enforced server-side against stored policy.

**3. Evaluation inputs include provenance, not just the action.** A structured
proposal like `{"action": "TRANSFER", "amount": 500000}` looks identical
whether it came from a legitimate instruction or a successful prompt injection.
To detect manipulation at all, the evaluator must also receive the original
natural-language instruction and any retrieved context the agent consumed.
This shapes the proposal schema from Phase 1 onward.

**4. Degrade, never fail.** LLM-backed engines sit behind an interface with a
deterministic fallback implementation. If the model provider is slow,
rate-limited, or unreachable, AEGIS-X still returns a decision.

**5. Every decision is auditable.** One immutable record per evaluation,
holding each engine's raw output, the fusion arithmetic, any policy overrides
that fired, and the final explanation.

## Phase plan

| Phase | Scope |
|---|---|
| 0 | Monorepo, FastAPI skeleton, health probes, Postgres config, Docker. |
| 1 | Database schema (6 entities), bank simulator, transactional transfers, seed data. |
| 2 | Autonomous agent: instruction → structured proposal. Gemini + deterministic fallback. |
| **3** | Orchestrator, 10 engine interfaces, Authority engine, fusion, trust, governance. **← current** |
| 4 | Financial DNA and Isolation Forest anomaly engine with calibrated scoring. |
| 5 | Prompt manipulation, intent alignment, intent drift. |
| 6 | Cascade detection, counterparty graph (NetworkX), blast radius. |
| 7 | Trust adjustment, full governance state machine, decisions wired to execution. |
| 8 | Governance dashboard and demo scenario runner. |

## Phase 0 decisions on record

**Health is split into liveness and readiness.** `/health` has no external
dependencies, so a database blip cannot cause an orchestrator to kill an
otherwise healthy process. `/health/ready` checks PostgreSQL and returns 503
when it is down.

**The database engine is created lazily.** Importing the database module opens
no connection, so the service boots and serves traffic before PostgreSQL is
available.

**Empty packages are committed deliberately.** `app/models/`, `app/services/`,
and `app/ml/` exist with docstrings but no implementation. They fix the shape
of the codebase so later phases add files rather than reorganise the tree.

## Phase 1 decisions on record

**Money is `NUMERIC(18,2)`, never `FLOAT`.** Binary floating point cannot
represent decimal currency amounts exactly, and the error compounds across a
ledger. Amounts also serialise as JSON *strings*, because JavaScript numbers
are float64 and would reintroduce the same loss at the API boundary.

**Transfers are one database transaction, with ordered row locks.** The debit,
the credit, and the ledger insert commit together or not at all. Both account
rows are locked `FOR UPDATE` before being read — a balance check is a
read-modify-write, so without locking two concurrent transfers could each
observe a sufficient balance and jointly overdraw the account. Locks are always
acquired in ascending id order so opposing transfers cannot deadlock. A
`CHECK (balance >= 0)` constraint backstops the whole thing at the database
level.

**Rejected transfers are audit events, not ledger rows.** A `Transaction` row
means money moved. A refusal is recorded in `AuditLog` instead, written in its
own transaction after the failed unit of work is rolled back.

**`ActionProposal.provenance` exists before anything reads it.** Adding it
later would mean retrofitting every call site once the manipulation engine
needs it, and the field is the only thing that makes injection detectable.

**Schema is created with `create_all`, not Alembic migrations.** The schema
changes every phase; hand-maintaining migrations against a moving target costs
more than it returns. Alembic is already a dependency for when it settles.

## Phase 2 decisions on record

**The agent cannot execute, structurally.** `app/services/agent.py` and
`app/api/agent.py` have no import path to `app/services/bank.py`, and the agent
service can only emit `PROPOSED`. A test parses both modules' ASTs and fails if
a bank import ever appears, so the guarantee is enforced at the import rather
than by a reviewer noticing a diff.

**LLM calls degrade, they do not fail.** Gemini sits behind the same
`InstructionParser` interface as the deterministic parser. Any failure --
timeout, HTTP error, malformed JSON, schema violation -- raises `ParserError`,
which the factory catches and falls back on. The response reports which parser
ran and whether a fallback occurred, so degradation is visible instead of
silent.

**Model output is re-validated.** Gemini is asked for constrained JSON via
`responseSchema` at `temperature: 0`, and the result is still validated with
Pydantic afterwards. A model claiming to follow a schema is not evidence that
it did.

**Recipient resolution is deterministic, and deliberately not fuzzy.** Matching
a payee name to a counterparty is backend logic, never the model's job. It
matches exactly, or exactly after case/punctuation normalisation, and then
stops. "ABC Technologies Ltd" silently resolving to the trusted "ABC
Technologies" is precisely the typosquatting behaviour a payments system must
not have; an unresolved recipient is a useful signal for AEGIS-X, not a problem
to paper over.

**The source account comes from the agent's authority envelope.** It is never
read from the instruction, so no wording can redirect which account is drained.

**Amounts survive as exact decimals.** A model returns JSON floats, and
`Decimal(0.1)` is not 0.1, so parsed amounts are coerced via `str` and
quantised to two places before they reach the database.

## Phase 3 decisions on record

**Absent is not zero.** A not-yet-implemented engine returns
`risk_score = None`, never `0`. Zero is a finding — "I looked and saw no risk";
null is "I did not look". Fusion aggregates only contributing engines and
renormalises their weights, and every evaluation carries a `coverage` block so
a low score is never mistaken for a clean bill of health. Without this, six
stubs would dilute an Authority failure of 100 to roughly 10.

**Correlated engines are grouped and combined by max.** This resolves the open
question carried since Phase 0. Financial DNA and the Isolation Forest share the
`behavioural` group; a group contributes the maximum of its members, not their
sum, so one behavioural signal cannot be counted twice. The structure is in
place before either engine exists, so Phase 4 changes no fusion code.

**Hard overrides run before fusion, not inside it.** A disqualifying finding
decides the outcome by itself. Authority carries a group weight of 0.25, so a
breach scoring 100 would contribute just 25 points through the weighted path and
survive — the override layer is what prevents that, and it is why the ordering
is structural rather than a tuning choice.

**Authority scores by max, not sum.** Three simultaneous violations are not
"worse than certain". Summing would also let three minor flags outrank one hard
limit breach.

**Governance fails safe under partial coverage.** It can justify a refusal from
one engine but will not authorise an action on partial evidence, so `EXECUTE` is
unreachable until every signal engine reports. Anything that would otherwise
pass is escalated and marked `provisional`.

**Trust reports; it does not score.** `TrustService` returns `risk_score = None`
and exposes the autonomy tier in `details`. This resolves the Phase 0 concern
about trust death-spirals: trust modulates governance *thresholds* rather than
feeding the risk sum, so a block cannot mechanically raise the risk that caused
it.

**One engine's crash cannot fail an evaluation.** The orchestrator catches per
engine and records an `ERROR` result with a null score — excluded from fusion
rather than scored as harmless.

**Deciding is not acting.** The orchestrator records a decision and moves the
proposal to `EVALUATED`. Nothing executes, and no proposal is blocked or
approved as a side effect.

## Open questions for later phases

*(Correlated risk signals and trust feedback loops were resolved in Phase 3 —
see above.)*

- **Anomaly score direction.** scikit-learn's `score_samples` returns *lower*
  values for more anomalous points. Mapping to a 0–100 risk scale needs an
  explicit, tested transform — ideally a percentile rank against the training
  distribution, persisted alongside the model.
- **Escalation resumption.** Whether human approval re-runs evaluation or
  bypasses it is a policy decision that needs to be made explicitly.

- **Concurrent daily-limit checks.** Daily spend is computed from executed
  transactions at evaluation time. Two proposals evaluated before either
  executes could both pass the daily check and jointly breach it. A reservation
  or hold mechanism resolves this when execution is wired up.
