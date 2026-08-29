"""Train the behavioural-anomaly Isolation Forest.

The model this script produces is only meaningful if it is trained on the same
distribution the engine sees at inference time. Two things therefore have to
stay in lockstep and are the whole point of this file:

* the per-agent transaction *profiles* below are the same ones
  ``app/database/seed_historical.py`` uses to populate the database, so the
  training amounts, hours and frequencies match production data; and
* every feature is computed here exactly the way ``AnomalyService`` computes it
  at inference -- in particular ``deviation_from_role_avg`` is a per-agent
  z-score, ``(amount - agent_mean) / agent_std``, which is scale-invariant and
  therefore comparable across a Marketing agent (~4k) and an HR agent (~250k).

A previous model was trained on a toy dataset two orders of magnitude smaller
than the real transactions, so every legitimate transfer was hundreds of
standard deviations out of distribution and scored ~100. Regenerate the
artifacts with ``python -m app.ml.train_anomaly_model`` whenever the seed
profiles change.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Must match app/database/seed_historical.py. If you change one, change both.
PROFILES = {
    "Treasury Agent": {"min_amt": 20000, "max_amt": 80000, "min_hour": 9, "max_hour": 17},
    "Procurement Agent": {"min_amt": 5000, "max_amt": 150000, "min_hour": 10, "max_hour": 16},
    "Marketing Agent": {"min_amt": 1000, "max_amt": 8000, "min_hour": 7, "max_hour": 22},
    "HR Agent": {"min_amt": 100000, "max_amt": 400000, "min_hour": 8, "max_hour": 11},
}

FEATURES = [
    "amount", "hour_of_day", "is_new_recipient", "agent_rolling_avg_amount",
    "deviation_from_role_avg", "txns_last_5min", "counterparty_risk_tier",
]

NORMAL_PER_AGENT = 1000
ANOMALY_FRACTION = 0.05  # share of rows that are injected anomalies
RANDOM_SEED = 42


def _build_dataset() -> pd.DataFrame:
    rng = random.Random(RANDOM_SEED)
    rows: list[dict] = []

    for name, prof in PROFILES.items():
        # The agent's "normal" is defined by its own history, so derive the
        # baseline the same way inference does: mean/std of the agent's own
        # completed amounts.
        normal_amounts = [
            rng.uniform(prof["min_amt"], prof["max_amt"]) for _ in range(NORMAL_PER_AGENT)
        ]
        agent_mean = float(np.mean(normal_amounts))
        agent_std = float(np.std(normal_amounts)) or 1.0

        def make_row(amount, hour, is_new, txns_5min, tier):
            return {
                "amount": round(amount, 2),
                "hour_of_day": hour,
                "is_new_recipient": is_new,
                "agent_rolling_avg_amount": round(agent_mean, 2),
                "deviation_from_role_avg": round((amount - agent_mean) / agent_std, 4),
                "txns_last_5min": txns_5min,
                "counterparty_risk_tier": tier,
                "agent": name,
                "is_anomaly": 0,
            }

        for amount in normal_amounts:
            # Legitimate variation lives here on purpose: a new recipient, an
            # occasional out-of-band hour, a small burst, a riskier tier -- any
            # one of these alone is normal business. The model must not isolate
            # a normal-amount transfer just because it is to someone new, or the
            # engine flags every real payment. Amount deviation is the signal
            # that has to carry weight, so the *normal* set is deliberately
            # noisy on every other feature.
            off_hour = rng.random() < 0.08
            row = make_row(
                amount=amount,
                hour=rng.choice([0, 1, 6, 22, 23]) if off_hour
                else rng.randint(prof["min_hour"], prof["max_hour"]),
                is_new=1 if rng.random() < 0.10 else 0,
                txns_5min=rng.choices([0, 1, 2, 3], weights=[70, 18, 8, 4])[0],
                tier=rng.choices([1, 2, 3], weights=[80, 15, 5])[0],
            )
            rows.append(row)

        # Injected anomalies are amount-driven: a spike well outside the agent's
        # own range is the defining trait, matching the engine's amount-spike
        # flag. The other features are varied independently rather than all
        # pinned to their extremes, so the model learns "large deviation" as the
        # anomaly rather than memorising a single all-features-extreme fingerprint.
        n_anom = int(NORMAL_PER_AGENT * ANOMALY_FRACTION / (1 - ANOMALY_FRACTION))
        for _ in range(n_anom):
            spike = rng.uniform(4, 30) * prof["max_amt"]
            row = make_row(
                amount=spike,
                hour=rng.choice([0, 1, 2, 3, 4, 23]) if rng.random() < 0.6
                else rng.randint(prof["min_hour"], prof["max_hour"]),
                is_new=1 if rng.random() < 0.7 else 0,
                txns_5min=rng.randint(0, 8),
                tier=rng.choices([1, 2, 3], weights=[20, 30, 50])[0],
            )
            row["is_anomaly"] = 1
            rows.append(row)

    return pd.DataFrame(rows)


def train() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    ml_dir = Path(__file__).resolve().parent / "models"
    ml_dir.mkdir(parents=True, exist_ok=True)

    df = _build_dataset()
    X = df[FEATURES]

    scaler = StandardScaler().fit(X)
    X_scaled = scaler.transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=ANOMALY_FRACTION,
        random_state=RANDOM_SEED,
    ).fit(X_scaled)

    # Sanity check: normal rows should score cleanly below the anomalies.
    raw = model.decision_function(X_scaled)
    lo, hi = raw.min(), raw.max()
    calibrated = (1.0 - (raw - lo) / (hi - lo)) * 100
    df = df.assign(calibrated_score=calibrated)
    normal_p95 = df.loc[df.is_anomaly == 0, "calibrated_score"].quantile(0.95)
    anom_med = df.loc[df.is_anomaly == 1, "calibrated_score"].median()
    logger.info("normal 95th pct score=%.1f | anomaly median score=%.1f", normal_p95, anom_med)

    joblib.dump(model, ml_dir / "isolation_forest_model.joblib")
    joblib.dump(scaler, ml_dir / "feature_scaler.joblib")
    df.to_csv(ml_dir / "agent_transactions.csv", index=False)
    logger.info("Saved model, scaler and %d-row calibration dataset to %s", len(df), ml_dir)


if __name__ == "__main__":
    train()
