"""Intent alignment, drift, and prompt manipulation engine.

Since an actual LLM integration is not configured, this engine uses a semantic heuristic
(keyword overlap and blocklists) to evaluate whether the agent's intent aligns with its
objective, whether it is drifting from historical behavior, and whether prompt manipulation
is detected in its provenance payload.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Set

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import settings
from app.models import ActionProposal, ProposalStatus
from app.services.engines.base import EngineResult, EngineStatus, EvaluationContext, SecurityEngine

class LLMEvaluation(BaseModel):
    risk_score: float = Field(description="Risk score from 0.0 to 100.0")
    reasoning: str = Field(description="Detailed explanation for the score")



class IntentService(SecurityEngine):
    name = "intent"
    
    # Common jailbreak or prompt injection signatures
    MANIPULATION_SIGNATURES = {
        "ignore previous",
        "ignore all",
        "system prompt",
        "bypass",
        "override",
        "developer mode",
        "disregard",
        "jailbreak",
        "new instructions",
        "forget everything",
    }

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        if not context.agent:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.ERROR,
                risk_score=None,
                flags=["AGENT_NOT_FOUND"],
                details={"error": "Cannot evaluate intent without an agent."}
            )

        proposal = context.proposal
        agent = context.agent
        
        flags = []
        violations = []
        details = {}

        # 1. Prompt Manipulation Detection
        manipulation_score = self._detect_prompt_manipulation(proposal)
        details["prompt_manipulation_score"] = manipulation_score
        
        if manipulation_score > 80:
            flags.append("PROMPT_INJECTION_DETECTED")
            violations.append(manipulation_score)
        elif manipulation_score > 0:
            flags.append("SUSPICIOUS_PROVENANCE")
            violations.append(manipulation_score)

        # 2. Intent Alignment
        self._latest_reasoning = None
        alignment_score = self._evaluate_alignment(proposal.purpose, agent.objective)
        details["intent_alignment_score"] = alignment_score
        if self._latest_reasoning:
            details["gemini_reasoning"] = self._latest_reasoning
        
        if alignment_score > 70:
            flags.append("INTENT_MISALIGNED")
            violations.append(alignment_score)

        # 3. Intent Drift
        drift_score = self._evaluate_drift(context)
        details["intent_drift_score"] = drift_score
        
        if drift_score > 60:
            flags.append("INTENT_DRIFT_DETECTED")
            violations.append(drift_score)

        # Synthesize final score
        if not violations:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.PASS,
                risk_score=0.0,
                flags=[],
                details=details
            )
            
        final_score = float(max(violations))
        
        status = EngineStatus.WARN
        if final_score >= 80.0:
            status = EngineStatus.FAIL

        return EngineResult(
            engine=self.name,
            status=status,
            risk_score=final_score,
            flags=flags,
            details=details
        )

    def _detect_prompt_manipulation(self, proposal: ActionProposal) -> float:
        """Scan the provenance for jailbreak or injection patterns."""
        if not proposal.provenance:
            return 0.0
            
        try:
            provenance_text = json.dumps(proposal.provenance).lower()
        except Exception:
            return 0.0

        matches = [sig for sig in self.MANIPULATION_SIGNATURES if sig in provenance_text]
        
        if not matches:
            return 0.0
            
        # If we find explicit override attempts, it's highly critical (95.0)
        return 95.0

    def _evaluate_alignment(self, purpose: str, objective: str) -> float:
        """Evaluate semantic alignment using Gemini if available, falling back to heuristic."""
        if not purpose or not objective:
            return 50.0 # Ambiguous
            
        if settings.gemini_api_key:
            try:
                client = genai.Client(api_key=settings.gemini_api_key)
                prompt = f"""
                You are a strict cybersecurity orchestrator evaluating an autonomous AI agent's requested action.
                
                Agent's Core Corporate Objective:
                "{objective}"
                
                Action Purpose (Stated intent of the transaction):
                "{purpose}"
                
                Evaluate whether the Action Purpose strictly aligns with the Agent's Core Objective. 
                If it aligns perfectly, risk_score is 0. 
                If it deviates slightly, risk_score is 20-50.
                If it directly contradicts or performs an unauthorized action outside the objective, risk_score is 80-100.
                """
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LLMEvaluation,
                        temperature=0.1
                    )
                )
                
                result = response.parsed
                self._latest_reasoning = getattr(result, 'reasoning', 'No reasoning provided.')
                return float(getattr(result, 'risk_score', 0.0))
            except Exception as e:
                print(f"Gemini evaluation failed: {e}")
                pass # Fall through to heuristic
                
        # Very simple mock logic fallback
        purpose_words = self._extract_keywords(purpose)
        objective_words = self._extract_keywords(objective)
        
        if not objective_words:
            return 0.0
            
        overlap = len(purpose_words.intersection(objective_words))
        
        if overlap == 0:
            return 75.0
            
        return 0.0

    def _evaluate_drift(self, context: EvaluationContext) -> float:
        """Check if the current purpose drastically diverges from recent history."""
        # Fetch the last 5 executed or evaluated proposals
        statement = select(ActionProposal).where(
            ActionProposal.agent_id == context.agent.id,
            ActionProposal.status != ProposalStatus.PROPOSED,
            ActionProposal.id != context.proposal.id
        ).order_by(ActionProposal.id.desc()).limit(5)
        
        historical = list(context.db.execute(statement).scalars())
        
        if not historical:
             # Not enough history to detect drift
             return 0.0
             
        current_words = self._extract_keywords(context.proposal.purpose)
        
        # Build an aggregate profile of historical keywords
        historical_words: Set[str] = set()
        for h in historical:
             historical_words.update(self._extract_keywords(h.purpose))
             
        if not historical_words or not current_words:
             return 0.0
             
        overlap = len(current_words.intersection(historical_words))
        
        # If the new purpose has zero overlap with the aggregate history,
        # it might be a sudden shift (drift)
        if overlap == 0:
             return 65.0 # Warning level risk
             
        return 0.0
        
    def _extract_keywords(self, text: str) -> Set[str]:
        """Simple tokenizer to extract meaningful keywords."""
        stopwords = {"to", "for", "the", "a", "an", "and", "or", "in", "of", "with", "is"}
        words = "".join(c if c.isalnum() else " " for c in text.lower()).split()
        return {w for w in words if w not in stopwords and len(w) > 2}
