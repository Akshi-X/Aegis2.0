"""Financial DNA engine.

Interface only. Implemented in Phase 4.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models import BankAccount, Transaction
from app.models.enums import TransactionStatus
from app.services.engines.base import EngineResult, EngineStatus, EvaluationContext

class FinancialDNAService:
    name = "financial_dna"
    planned_phase = 4
    summary = (
        "Compares the action against the agent's learned behavioural profile: typical amount, hour, recipients, frequency, and daily totals."
    )

    def _get_historical_transactions(self, context: EvaluationContext) -> list[Transaction]:
        if not context.agent or not context.agent.source_account_id:
            return []
        
        # In a real system we'd limit this or pre-aggregate. For Phase 5, we fetch all.
        stmt = select(Transaction).where(
            Transaction.source_account_id == context.agent.source_account_id,
            Transaction.status == TransactionStatus.COMPLETED
        ).order_by(Transaction.timestamp)
        return list(context.db.scalars(stmt).all())
        
    def get_profile(self, context: EvaluationContext) -> dict:
        """Calculate the agent's behavioral profile."""
        transactions = self._get_historical_transactions(context)
        
        if not transactions:
            return {
                "normal_amount_range": (0.0, 0.0),
                "normal_hours": (9, 17), # default
                "known_recipients": [],
                "typical_daily_transactions": 0,
                "typical_daily_exposure": 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        amounts = [float(t.amount) for t in transactions]
        hours = [t.timestamp.hour for t in transactions]
        
        dest_account_ids = {t.destination_account_id for t in transactions}
        
        # Get names for these accounts
        known_recipients = []
        if dest_account_ids:
            stmt = select(BankAccount.account_name).where(BankAccount.id.in_(dest_account_ids))
            known_recipients = list(context.db.scalars(stmt).all())
            
        # Daily aggregations
        daily_counts = defaultdict(int)
        daily_amounts = defaultdict(float)
        
        for t in transactions:
            day_key = t.timestamp.date()
            daily_counts[day_key] += 1
            daily_amounts[day_key] += float(t.amount)
            
        avg_amount = statistics.mean(amounts) if amounts else 0.0
        std_amount = statistics.stdev(amounts) if len(amounts) > 1 else 0.0
        
        avg_daily_count = statistics.mean(daily_counts.values()) if daily_counts else 0.0
        avg_daily_amount = statistics.mean(daily_amounts.values()) if daily_amounts else 0.0
        
        min_hour = min(hours) if hours else 9
        max_hour = max(hours) if hours else 17
        
        # Set normal amount range to roughly mean +/- 2 stddev
        min_normal = max(0.0, avg_amount - (2 * std_amount))
        max_normal = avg_amount + (2 * std_amount)
        
        return {
            "normal_amount_range": (min_normal, max_normal),
            "normal_hours": (min_hour, max_hour),
            "known_recipients": known_recipients,
            "typical_daily_transactions": int(avg_daily_count),
            "typical_daily_exposure": avg_daily_amount,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        if not context.agent:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.PASS,
                risk_score=0,
                flags=[],
                details={"reason": "No agent provided"}
            )
            
        profile = self.get_profile(context)
        proposal = context.proposal
        
        flags = []
        violations = []
        details = {
            "normal_amount_range": profile["normal_amount_range"],
            "requested_amount": float(proposal.amount),
            "normal_hours": profile["normal_hours"],
            "requested_hour": context.now.hour,
            "known_recipients": profile["known_recipients"],
            "requested_recipient": proposal.recipient_name
        }
        
        # 1. Amount deviation
        min_amt, max_amt = profile["normal_amount_range"]
        req_amt = float(proposal.amount)
        
        if req_amt > max_amt:
            flags.append("AMOUNT_OUTSIDE_NORMAL_RANGE")
            # Risk scales with how far outside the range it is, up to 95
            excess_ratio = (req_amt - max_amt) / max_amt if max_amt > 0 else 1.0
            amount_risk = min(95.0, 50.0 + (excess_ratio * 20.0))
            violations.append(amount_risk)
        
        # 2. Time deviation
        min_hour, max_hour = profile["normal_hours"]
        req_hour = context.now.hour
        
        if req_hour < min_hour or req_hour > max_hour:
            flags.append("UNUSUAL_TRANSACTION_TIME")
            violations.append(60.0) # Moderate risk for unusual time
            
        # 3. Recipient deviation
        if proposal.recipient_name not in profile["known_recipients"]:
            # Check if it resolved to an account at least
            if not proposal.recipient_account_number:
                flags.append("UNKNOWN_RECIPIENT")
                violations.append(85.0) # High risk for completely unknown recipient
            else:
                flags.append("FIRST_TIME_RECIPIENT")
                violations.append(65.0) # Moderate-high risk for first time but resolved recipient
                
        # --- Verdict ---
        risk_score = max(violations) if violations else 0.0
        
        if risk_score >= 80.0:
            status = EngineStatus.FAIL
        elif risk_score >= 50.0:
            status = EngineStatus.WARN
        else:
            status = EngineStatus.PASS
            
        return EngineResult(
            engine=self.name,
            status=status,
            risk_score=risk_score,
            flags=flags,
            details=details,
        )
