# AEGIS-X: Project Context & Overview

## What is AEGIS-X?
**AEGIS-X** is a pre-execution security and governance layer designed to protect organizations from autonomous financial AI agents. 

As AI agents become capable of executing real financial transactions (e.g., paying invoices, moving funds), organizations need a firewall between the agent's intent and the actual bank ledger. AEGIS-X sits exactly in this gap. It does not execute actions; it evaluates proposed actions through a multi-engine security pipeline and makes a deterministic decision (`EXECUTE`, `BLOCK`, or `ESCALATE`) before any money moves.

## System Architecture Diagram

```text
                         ┌─────────────────────┐
                         │ USER / ORGANIZATION │
                         │                     │
                         │ Goals               │
                         │ Policies            │
                         │ Limits              │
                         │ Agent authority     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ AUTONOMOUS FINANCIAL│
                         │       AGENT         │
                         │                     │
                         │ Gemini / Agent      │
                         └──────────┬──────────┘
                                    │
                             Action Proposal
                                    │
                                    ▼
             ╔══════════════════════════════════════════╗
             ║              🛡️ AEGIS-X                  ║
             ║       PRE-EXECUTION SECURITY             ║
             ╚════════════════════╤═════════════════════╝
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │ AEGIS-X ORCHESTRATOR    │
                    └────────────┬────────────┘
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       │                         │                         │
       ▼                         ▼                         ▼
┌───────────────┐        ┌────────────────┐       ┌────────────────┐
│ IDENTITY &    │        │ INTENT         │       │ PROMPT         │
│ AUTHORITY     │        │ ALIGNMENT      │       │ MANIPULATION   │
│               │        │                │       │ DETECTION      │
└───────┬───────┘        └───────┬────────┘       └───────┬────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                                 ▼
                       ┌───────────────────┐
                       │  🧬 FINANCIAL DNA │
                       │                   │
                       │ Agent behaviour   │
                       │ history           │
                       │ spending pattern  │
                       └─────────┬─────────┘
                                 │
                                 ▼
                       ┌───────────────────┐
                       │ 📊 ML BEHAVIOUR   │
                       │                   │
                       │ Isolation Forest  │
                       │                   │
                       └─────────┬─────────┘
                                 │
                                 ▼
                       ┌───────────────────┐
                       │ INTENT DRIFT      │
                       └─────────┬─────────┘
                                 │
                                 ▼
                       ┌───────────────────┐
                       │ CASCADE DETECTION │
                       │                   │
                       │ Rapid sequences   │
                       │ Splitting         │
                       └─────────┬─────────┘
                                 │
                                 ▼
             ╔══════════════════════════════════════════╗
             ║ 🌐 COUNTERPARTY INTELLIGENCE             ║
             ║                                          ║
             ║ Graph analysis                           ║
             ║ Mule patterns                            ║
             ║ Fan-in / Fan-out                         ║
             ║ Cross-bank risk signals                  ║
             ╚════════════════════╤═════════════════════╝
                                  │
                                  ▼
                       ┌───────────────────┐
                       │ 💥 BLAST RADIUS   │
                       │                   │
                       │ "How bad could    │
                       │ this become?"     │
                       └─────────┬─────────┘
                                 │
                                 ▼
                       ┌───────────────────┐
                       │ 🧬 RISK FUSION    │
                       │                   │
                       │ Combine signals   │
                       │ into overall risk │
                       └─────────┬─────────┘
                                 │
                                 ▼
                       ┌───────────────────┐
                       │ 📉 DYNAMIC TRUST  │
                       │                   │
                       │ Agent trust      │
                       │ Autonomy level   │
                       └─────────┬─────────┘
                                 │
                                 ▼
                       ┌───────────────────┐
                       │ ⚖️ GOVERNANCE     │
                       └─────────┬─────────┘
                                 │
               ┌─────────────────┼──────────────────┐
               ▼                 ▼                  ▼
           EXECUTE           CONSTRAIN            DELAY
               │
               ├──────────────────────────────────┐
               ▼                                  ▼
             BLOCK                             ESCALATE
                                                  │
                                                  ▼
                                             HUMAN REVIEW
               │
               ▼
       ┌───────────────────┐
       │ 🏦 BANK SIMULATOR │
       │                   │
       │ Update balance    │
       │ Create transaction│
       └─────────┬─────────┘
                 │
                 ▼
       ┌───────────────────┐
       │ 📜 AUDIT LOG      │
       │                   │
       │ What happened?    │
       │ Why?              │
       │ Which engines?    │
       │ What decision?    │
       └───────────────────┘
```

## Architecture Explanation

### 1. The Proposal Phase
An autonomous agent (like a Procurement Agent guided by the Organization's goals and policies) decides to perform a financial action. It submits an `ActionProposal` to AEGIS-X containing the amount, recipient, purpose, and the raw prompt/reasoning (`provenance`) that led to this decision.

### 2. The AEGIS-X Orchestrator Pipeline
The Orchestrator (`app/services/orchestrator.py`) is the central nervous system. It takes the proposal and runs it through two tiers of security engines.

**Tier 1: Independent Signal Engines**
These engines evaluate the transaction from different perspectives. They run in parallel (or sequentially but independently) and do not see each other's results.
- **Identity & Authority**: Checks hard limits (daily spend limits, allowed currencies, transaction caps). *(Implemented)*
- **Intent Security**: Analyzes the prompt for jailbreaks, checks if the transaction aligns with the agent's core objective, and detects behavioral drift. *(Implemented in `IntentService`)*
- **Financial DNA**: A behavioral baseline checking if the transaction matches historical patterns (amount, time, trusted counterparties). *(Implemented)*
- **Anomaly Detection (ML Behaviour)**: Unsupervised learning (Isolation Forest) to detect complex anomalies. *(Pending ML Integration)*
- **Cascade Detection**: Detects rapid sequential transactions (e.g., smurfing large transfers to bypass limits). *(Placeholder)*
- **Counterparty Intelligence**: Analyzes the recipient for money mule graph patterns, fan-in, and fan-out topologies. *(Placeholder)*
- **Blast Radius**: Assesses worst-case exposure and financial sensitivity. *(Placeholder)*

**Tier 2: Aggregation Engines**
These engines run in a strict order to synthesize the independent signals from Tier 1.
- **Risk Fusion**: Aggregates the risk scores from all Tier 1 engines into a single `overall_risk_score`. *(Implemented)*
- **Dynamic Trust**: Uses the overall risk score and historical performance to assign the agent a trust tier (e.g., `HIGH_AUTONOMY`, `CONSTRAINED`). *(Implemented)*
- **Governance**: Makes the final routing decision (`EXECUTE`, `BLOCK`, `ESCALATE`) based on the fused risk and the agent's current trust tier. *(Implemented)*

### 3. Execution & Audit
If the Governance engine decides to `EXECUTE`, the AEGIS-X Bank Simulator (`app/services/bank.py`) processes the transaction, updating ledger balances atomicity. If Governance decides to `ESCALATE`, it waits for a `HUMAN REVIEW`. 

Regardless of the decision (`EXECUTE`, `BLOCK`, `ESCALATE`), the entire evaluation, reasonings, and engine sub-scores are immutably written to the `AuditLog` so you always know *what* happened and *why*.

## What Has Been Built (Phases 1-6)
1. **Database & ORM**: Full SQLite implementation with models for `Agent`, `ActionProposal`, `ActionEvaluation`, `BankAccount`, and `AuditLog`.
2. **Bank Simulator**: A robust simulation of a bank ledger with strict double-entry accounting principles to test the agent actions.
3. **Orchestrator**: The core pipeline runner that catches engine errors and safely fuses risk scores.
4. **Security Engines**: 
   - `AuthorityService`
   - `FinancialDNAService`
   - `IntentService` (Jailbreak detection, semantic alignment, and drift)
   - `RiskFusionService`
   - `TrustService`
   - `GovernanceService`
5. **Frontend Dashboard**: A Palantir-style React/Tailwind application to visualize active agents, monitor action proposals, and deeply inspect the timeline of the security pipeline evaluations.

## Running the Stack
- **Backend**: `cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000`
- **Frontend**: `cd frontend && npm run dev`
- **Tests**: `cd backend && .venv/bin/python -m pytest`
