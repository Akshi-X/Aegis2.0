"""Behavioural anomaly engine.

Implemented with an unsupervised Isolation Forest model trained on historical transaction features.
"""

from __future__ import annotations

import logging
import joblib
import pandas as pd
from pathlib import Path
from datetime import timedelta
from sqlalchemy import select, func

from google import genai
from app.core.config import settings

from app.models import Transaction
from app.models.enums import TransactionStatus
from app.services.engines.base import EngineResult, EngineStatus, EvaluationContext

logger = logging.getLogger(__name__)

# Constants matching model training baseline
FEATURES = [
    "amount", "hour_of_day", "is_new_recipient", "agent_rolling_avg_amount",
    "deviation_from_role_avg", "txns_last_5min", "counterparty_risk_tier",
]

class AnomalyService:
    name = "anomaly"

    def __init__(self) -> None:
        self._model = None
        self._scaler = None
        self._raw_min = None
        self._raw_max = None
        self._initialized = False
        self.agent_role_avg_amount = 250.0
        self.agent_role_std_amount = 60.0

    def _initialize_model(self) -> None:
        if self._initialized:
            return

        try:
            ml_dir = Path(__file__).resolve().parents[2] / "ml" / "models"
            model_path = ml_dir / "isolation_forest_model.joblib"
            scaler_path = ml_dir / "feature_scaler.joblib"
            csv_path = ml_dir / "agent_transactions.csv"

            logger.info("Loading Anomaly Isolation Forest model from %s", model_path)
            self._model = joblib.load(model_path)
            self._scaler = joblib.load(scaler_path)

            # Compute bounds for calibration
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                X = df[FEATURES]
                X_scaled = self._scaler.transform(X)
                raw_scores = self._model.decision_function(X_scaled)
                self._raw_min = raw_scores.min()
                self._raw_max = raw_scores.max()
            else:
                # Fallback to precomputed bounds if CSV is missing
                self._raw_min = -0.21947793395611936
                self._raw_max = 0.18810272712074555

            self._initialized = True
        except Exception as exc:
            logger.error("Failed to initialize Anomaly Isolation Forest model", exc_info=True)
            raise RuntimeError("Anomaly model initialization failed") from exc

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        if not context.agent:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.PASS,
                risk_score=0.0,
                flags=[],
                details={"reason": "No agent provided"}
            )

        try:
            self._initialize_model()
        except Exception as exc:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.ERROR,
                risk_score=None,
                flags=["MODEL_LOAD_ERROR"],
                details={"error": str(exc)}
            )

        # 1. Fetch completed historical transactions for context agent
        stmt = select(Transaction).where(
            Transaction.source_account_id == context.agent.source_account_id,
            Transaction.status == TransactionStatus.COMPLETED
        ).order_by(Transaction.timestamp)
        historical_txns = list(context.db.scalars(stmt).all())

        if len(historical_txns) < 3:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.PASS,
                risk_score=15.0,
                flags=[],
                details={
                    "reason": "Insufficient transaction history for behavioral profiling",
                    "calibrated_score": 15.0
                }
            )

        # 2. Extract features
        amount = float(context.proposal.amount)
        hour_of_day = context.now.hour

        # is_new_recipient: check if we've sent to this recipient name or account number before
        known_names = set()
        known_numbers = set()
        for tx in historical_txns:
            if tx.destination_account:
                known_names.add(tx.destination_account.account_name)
                known_numbers.add(tx.destination_account.account_number)

        is_new_recipient = 0
        if context.proposal.recipient_name not in known_names:
            is_new_recipient = 1
            if context.proposal.recipient_account_number and context.proposal.recipient_account_number in known_numbers:
                is_new_recipient = 0

        # agent_rolling_avg_amount / agent baseline. The baseline is the agent's
        # *own* history, not a global constant: agents operate at wildly
        # different scales (Marketing ~4k, HR ~250k), so a single hardcoded
        # role average makes every agent look anomalous. This must match how
        # train_anomaly_model.py builds the training features.
        amounts = [float(tx.amount) for tx in historical_txns]
        if amounts:
            agent_rolling_avg_amount = sum(amounts) / len(amounts)
            variance = sum((a - agent_rolling_avg_amount) ** 2 for a in amounts) / len(amounts)
            agent_std_amount = variance ** 0.5 or self.agent_role_std_amount
        else:
            agent_rolling_avg_amount = amount
            agent_std_amount = self.agent_role_std_amount

        # deviation_from_role_avg: z-score against this agent's own baseline,
        # so the feature is comparable across agents of different scale.
        deviation_from_role_avg = (amount - agent_rolling_avg_amount) / agent_std_amount

        # txns_last_5min
        window_start = context.now - timedelta(minutes=5)
        stmt_count = select(func.count()).select_from(Transaction).where(
            Transaction.source_account_id == context.agent.source_account_id,
            Transaction.timestamp >= window_start,
            Transaction.timestamp <= context.now
        )
        txns_last_5min = context.db.scalar(stmt_count) or 0

        # counterparty_risk_tier
        if context.counterparty:
            if context.counterparty.trusted:
                counterparty_risk_tier = 1
            else:
                score = float(context.counterparty.risk_score)
                if score < 33.0:
                    counterparty_risk_tier = 1
                elif score < 66.0:
                    counterparty_risk_tier = 2
                else:
                    counterparty_risk_tier = 3
        else:
            counterparty_risk_tier = 3

        # Prepare input data for the model
        row = pd.DataFrame([{
            "amount": amount,
            "hour_of_day": hour_of_day,
            "is_new_recipient": is_new_recipient,
            "agent_rolling_avg_amount": agent_rolling_avg_amount,
            "deviation_from_role_avg": deviation_from_role_avg,
            "txns_last_5min": txns_last_5min,
            "counterparty_risk_tier": counterparty_risk_tier,
        }])[FEATURES]

        # 3. Model Inference & Calibration
        try:
            X_scaled = self._scaler.transform(row)
            raw_score = self._model.decision_function(X_scaled)[0]
            # Normalize to 0-100 range, but cap at 89.0 to prevent hard blocking (allow human escalation instead)
            denom = self._raw_max - self._raw_min
            if denom > 0:
                risk_score = round(float((1.0 - (raw_score - self._raw_min) / denom) * 100), 2)
            else:
                risk_score = 50.0  # fallback default

            risk_score = max(0.0, min(89.0, risk_score))
        except Exception as exc:
            logger.error("Inference failed in AnomalyService", exc_info=True)
            return EngineResult(
                engine=self.name,
                status=EngineStatus.ERROR,
                risk_score=None,
                flags=["INFERENCE_ERROR"],
                details={"error": str(exc)}
            )

        # 4. Status determination & flags
        flags = []
        if risk_score >= 70.0:
            status = EngineStatus.FAIL
            flags.append("HIGH_BEHAVIOURAL_ANOMALY")
        elif risk_score >= 40.0:
            status = EngineStatus.WARN
            flags.append("MEDIUM_BEHAVIOURAL_ANOMALY")
        else:
            status = EngineStatus.PASS

        # Additional explainability flags for specific feature triggers
        if amount > agent_rolling_avg_amount + 3 * agent_std_amount:
            flags.append("ANOMALOUS_AMOUNT_SPIKE")
        if hour_of_day < 6 or hour_of_day > 22:
            flags.append("ANOMALOUS_OFF_HOURS_ACTIVITY")
        if txns_last_5min >= 3:
            flags.append("ANOMALOUS_HIGH_FREQUENCY")
        if is_new_recipient == 1:
            flags.append("ANOMALOUS_NEW_RECIPIENT")

        details = {
            "amount": amount,
            "hour_of_day": hour_of_day,
            "is_new_recipient": bool(is_new_recipient),
            "agent_rolling_avg_amount": round(agent_rolling_avg_amount, 2),
            "agent_std_amount": round(agent_std_amount, 2),
            "deviation_from_role_avg": round(deviation_from_role_avg, 2),
            "txns_last_5min": txns_last_5min,
            "counterparty_risk_tier": counterparty_risk_tier,
            "raw_decision_score": round(float(raw_score), 4),
            "calibrated_score": risk_score
        }

        # 5. Gemini AI Explanation
        if flags and settings.gemini_api_key:
            try:
                client = genai.Client(api_key=settings.gemini_api_key)
                prompt = f"""
                You are a cybersecurity expert analyzing an anomaly detected by an Isolation Forest ML model.
                
                The transaction amount was {amount}, while the agent's historical rolling average is {round(agent_rolling_avg_amount, 2)}.
                The transaction occurred at hour {hour_of_day}.
                Is the recipient new to this agent? {"Yes" if is_new_recipient else "No"}.
                Transactions in the last 5 minutes: {txns_last_5min}.
                
                The model flagged the following anomalies: {", ".join(flags)}.
                
                Provide a short, 2-3 sentence technical explanation of why this transaction is anomalous based on the ML features provided. Be concise and professional.
                """
                response = client.models.generate_content(
                    model='gemini-2.5-pro',
                    contents=prompt,
                )
                if response.text:
                    details["gemini_reasoning"] = response.text.strip()
            except Exception as e:
                logger.warning(f"Failed to generate Gemini reasoning for anomaly: {e}")

        return EngineResult(
            engine=self.name,
            status=status,
            risk_score=risk_score,
            flags=flags,
            details=details,
        )
