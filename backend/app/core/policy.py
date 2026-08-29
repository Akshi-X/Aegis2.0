"""Centralised security policy.

Every threshold, weight, and risk score used by the engines is loaded from
``app/policy/policy.yaml`` and validated here. Engines read policy; they never
define constants of their own.

Two properties are deliberate:

* **Unknown keys are rejected.** ``extra="forbid"`` means a misspelled setting
  fails loudly at load rather than being ignored while the code silently falls
  back to a default -- which, for a security control, is the difference between
  a visible error and an invisible hole.
* **Cross-field invariants are validated.** Weights must sum to 1.0, every
  engine must map to a declared group, trust tiers must descend, and governance
  bands must ascend. A policy that cannot express a coherent decision is
  rejected at load, not discovered at evaluation time.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import BACKEND_ROOT

logger = logging.getLogger(__name__)

DEFAULT_POLICY_PATH = BACKEND_ROOT / "app" / "policy" / "policy.yaml"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorityRiskScores(_Strict):
    """Risk each violation justifies on its own, 0-100."""

    agent_not_found: float = Field(100, ge=0, le=100)
    agent_not_active: float = Field(100, ge=0, le=100)
    action_type_not_permitted: float = Field(100, ge=0, le=100)
    unauthorized_source_account: float = Field(95, ge=0, le=100)
    source_account_missing: float = Field(95, ge=0, le=100)
    transaction_limit_exceeded: float = Field(85, ge=0, le=100)
    currency_not_permitted: float = Field(80, ge=0, le=100)
    daily_limit_exceeded: float = Field(80, ge=0, le=100)
    insufficient_funds: float = Field(70, ge=0, le=100)
    approaching_transaction_limit: float = Field(25, ge=0, le=100)
    approaching_daily_limit: float = Field(25, ge=0, le=100)


class AuthorityPolicy(_Strict):
    risk_scores: AuthorityRiskScores = Field(default_factory=AuthorityRiskScores)
    approaching_limit_ratio: float = Field(0.80, gt=0, le=1)
    fail_at_or_above: float = Field(70, ge=0, le=100)


class FusionPolicy(_Strict):
    group_weights: dict[str, float]
    engine_groups: dict[str, str]
    warn_at_or_above: float = Field(30, ge=0, le=100)
    fail_at_or_above: float = Field(70, ge=0, le=100)

    @model_validator(mode="after")
    def _check_consistency(self) -> FusionPolicy:
        total = sum(self.group_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"fusion.group_weights must sum to 1.0, got {total:.4f}. "
                "Weights are renormalised per evaluation, but the declared "
                "policy must still describe full coverage."
            )

        unknown = set(self.engine_groups.values()) - set(self.group_weights)
        if unknown:
            raise ValueError(
                f"fusion.engine_groups references undeclared groups: "
                f"{sorted(unknown)}"
            )

        unused = set(self.group_weights) - set(self.engine_groups.values())
        if unused:
            raise ValueError(
                f"fusion.group_weights declares groups no engine belongs to: "
                f"{sorted(unused)}. Their weight would silently vanish."
            )

        if self.warn_at_or_above > self.fail_at_or_above:
            raise ValueError("fusion.warn_at_or_above must not exceed fail_at_or_above")

        return self


class TrustTier(_Strict):
    min_score: float = Field(ge=0, le=100)
    tier: str


class TrustPolicy(_Strict):
    tiers: list[TrustTier]

    @model_validator(mode="after")
    def _check_tiers(self) -> TrustPolicy:
        if not self.tiers:
            raise ValueError("trust.tiers must not be empty")

        scores = [tier.min_score for tier in self.tiers]
        if scores != sorted(scores, reverse=True):
            raise ValueError(
                "trust.tiers must be ordered from highest min_score to lowest; "
                "they are matched first-wins."
            )

        if self.tiers[-1].min_score != 0:
            raise ValueError(
                "trust.tiers must end with a min_score of 0 so every score "
                "resolves to a tier."
            )

        return self

    def tier_for(self, score: float) -> str:
        for tier in self.tiers:
            if score >= tier.min_score:
                return tier.tier
        return self.tiers[-1].tier


class GovernancePolicy(_Strict):
    hard_override_risk: float = Field(90, ge=0, le=100)
    execute_below: float = Field(30, ge=0, le=100)
    constrain_below: float = Field(50, ge=0, le=100)
    delay_below: float = Field(70, ge=0, le=100)
    autonomous_tiers: list[str]
    required_engines_for_autonomy: list[str]

    @model_validator(mode="after")
    def _check_bands(self) -> GovernancePolicy:
        bands = [self.execute_below, self.constrain_below, self.delay_below]
        if bands != sorted(bands):
            raise ValueError(
                "governance bands must ascend: execute_below <= "
                "constrain_below <= delay_below"
            )
        if not self.required_engines_for_autonomy:
            raise ValueError(
                "governance.required_engines_for_autonomy must not be empty; "
                "an empty list would let AEGIS-X authorise actions on no evidence."
            )
        return self


class CounterpartyPolicy(_Strict):
    """Counterparty-intelligence risk scores and graph thresholds."""

    # Risk each finding justifies on its own, 0-100. The engine reports the max.
    risk_unresolved_recipient: float = Field(80, ge=0, le=100)
    risk_unverified_recipient: float = Field(55, ge=0, le=100)
    risk_untrusted_counterparty: float = Field(75, ge=0, le=100)
    risk_pass_through: float = Field(70, ge=0, le=100)
    risk_rapid_forwarding: float = Field(65, ge=0, le=100)
    risk_proximity_to_flagged: float = Field(60, ge=0, le=100)

    # Money-flow graph thresholds.
    fan_out_mule_min: int = Field(3, ge=1)
    forwarding_ratio_min: float = Field(0.80, gt=0, le=1)
    proximity_risk_score: float = Field(70, ge=0, le=100)

    warn_at_or_above: float = Field(40, ge=0, le=100)
    fail_at_or_above: float = Field(70, ge=0, le=100)

    @model_validator(mode="after")
    def _check_bands(self) -> CounterpartyPolicy:
        if self.warn_at_or_above > self.fail_at_or_above:
            raise ValueError(
                "counterparty.warn_at_or_above must not exceed fail_at_or_above"
            )
        return self


class CascadePolicy(_Strict):
    """Sequence-analysis windows, thresholds, and risk scores."""

    burst_window_minutes: int = Field(10, gt=0)
    velocity_window_minutes: int = Field(60, gt=0)
    coordination_window_minutes: int = Field(15, gt=0)

    rapid_repeat_count: int = Field(4, ge=2)
    structuring_lower_ratio: float = Field(0.70, gt=0, le=1)
    structuring_min_slices: int = Field(3, ge=2)
    velocity_spike_factor: float = Field(4.0, gt=1)
    velocity_min_events: int = Field(3, ge=1)
    coordination_min_sources: int = Field(3, ge=2)

    risk_rapid_repeats: float = Field(65, ge=0, le=100)
    risk_structuring: float = Field(85, ge=0, le=100)
    risk_velocity_spike: float = Field(60, ge=0, le=100)
    risk_coordinated_cascade: float = Field(80, ge=0, le=100)

    warn_at_or_above: float = Field(40, ge=0, le=100)
    fail_at_or_above: float = Field(70, ge=0, le=100)

    @model_validator(mode="after")
    def _check_bands(self) -> CascadePolicy:
        if self.warn_at_or_above > self.fail_at_or_above:
            raise ValueError(
                "cascade.warn_at_or_above must not exceed fail_at_or_above"
            )
        return self


class Policy(_Strict):
    """The complete, validated security policy."""

    version: int
    description: str = ""
    authority: AuthorityPolicy = Field(default_factory=AuthorityPolicy)
    fusion: FusionPolicy
    trust: TrustPolicy
    governance: GovernancePolicy
    counterparty: CounterpartyPolicy = Field(default_factory=CounterpartyPolicy)
    cascade: CascadePolicy = Field(default_factory=CascadePolicy)

    @model_validator(mode="after")
    def _check_cross_section(self) -> Policy:
        declared = set(self.fusion.engine_groups)
        required = set(self.governance.required_engines_for_autonomy)
        unknown = required - declared
        if unknown:
            raise ValueError(
                "governance.required_engines_for_autonomy names engines absent "
                f"from fusion.engine_groups: {sorted(unknown)}. They could never "
                "report, so EXECUTE would be permanently unreachable."
            )
        return self


class PolicyError(RuntimeError):
    """Raised when the policy file is missing or invalid."""


def load_policy(path: Path | str | None = None) -> Policy:
    """Read and validate a policy file. Not cached; use ``get_policy`` normally."""
    policy_path = Path(path) if path is not None else DEFAULT_POLICY_PATH

    try:
        raw: Any = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyError(f"Policy file not found: {policy_path}") from exc
    except yaml.YAMLError as exc:
        raise PolicyError(f"Policy file is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise PolicyError(f"Policy file must contain a mapping: {policy_path}")

    try:
        policy = Policy.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError
        raise PolicyError(f"Policy file failed validation: {exc}") from exc

    logger.info("Loaded security policy v%s from %s", policy.version, policy_path)
    return policy


@lru_cache
def get_policy() -> Policy:
    """The active policy. Cached, so engines can call this freely."""
    return load_policy()


def reload_policy() -> Policy:
    """Drop the cache and re-read from disk."""
    get_policy.cache_clear()
    return get_policy()
