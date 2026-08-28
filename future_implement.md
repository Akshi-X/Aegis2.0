# AEGIS-X: Future Implementation Roadmap

Based on the core architecture design, the following modules are currently stubbed out as placeholders and are scheduled for future development.

## 1. 📊 ML Behaviour (AnomalyService)
**Status**: Pending ML Model Integration
**Description**: Uses unsupervised machine learning (like an Isolation Forest) to detect complex, multi-dimensional anomalies that rule-based engines (like Financial DNA) might miss. 
**Implementation Steps**:
- Load the trained `.joblib` or `.pkl` model into the backend (e.g., `app/ml_models/`).
- Update `app/services/engines/anomaly.py` to extract features from the `EvaluationContext`.
- Run model inference to generate an anomaly score and surface explainable flags.

## 2. 🌐 Counterparty Intelligence (CounterpartyService)
**Status**: Pending
**Description**: Shifts the security focus from *what* the agent is doing to *who* they are interacting with. Performs graph analysis on the recipient.
**Implementation Steps**:
- Update `app/services/engines/counterparty.py`.
- Detect risky network topologies like money mule patterns.
- Implement "fan-in" (many agents sending to one account) or "fan-out" (one account rapidly distributing funds) detection logic.

## 3. 🌊 Cascade Detection (CascadeService)
**Status**: Pending
**Description**: Evaluates transaction velocity and sequencing to prevent multi-step exploits.
**Implementation Steps**:
- Update `app/services/engines/cascade.py`.
- Detect "smurfing" (an agent splitting a $50,000 transfer into 10 separate $5,000 transfers to evade daily limits).
- Monitor rapid, coordinated financial movements across multiple agents acting in concert.

## 4. 💥 Blast Radius (BlastRadiusService)
**Status**: Pending
**Description**: Assesses the worst-case scenario impact if the current action is allowed to proceed and turns out to be malicious.
**Implementation Steps**:
- Update `app/services/engines/blast_radius.py`.
- Calculate potential maximum financial exposure.
- Evaluate the sensitivity of the systems or accounts the agent is touching.

## 5. 🧑‍💻 Human Review Queue (Frontend & Backend)
**Status**: Pending
**Description**: The governance workflow for handling transactions that the orchestrator routes to `ESCALATE`.
**Implementation Steps**:
- **Backend**: Implement an API endpoint to allow an authorized human to resolve (approve/reject) an `ActionEvaluation` that is in an escalated state.
- **Frontend**: Build out the `/reviews` page in the React dashboard to display the queue of escalated actions, allowing security operators to review the engine flags and make a final manual decision.
