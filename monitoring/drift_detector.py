"""
Prediction drift detector.
Reads logs/predictions.csv and flags if emotion distribution has shifted
significantly compared to a saved baseline.

Run weekly via cron or GitHub Actions:
  python monitoring/drift_detector.py --baseline monitoring/baseline.json
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from loguru import logger

LOG_FILE = Path("logs/predictions.csv")
BASELINE_FILE = Path("monitoring/baseline.json")


def load_recent_predictions(days: int = 7) -> pd.DataFrame:
    if not LOG_FILE.exists():
        logger.warning("No prediction log found.")
        return pd.DataFrame()
    df = pd.read_csv(LOG_FILE, parse_dates=["timestamp"])
    cutoff = datetime.utcnow() - timedelta(days=days)
    return df[df["timestamp"] >= cutoff]


def compute_distribution(df: pd.DataFrame) -> dict:
    dist = df["emotion"].value_counts(normalize=True).to_dict()
    return {k: round(v, 4) for k, v in dist.items()}


def save_baseline(dist: dict):
    BASELINE_FILE.parent.mkdir(exist_ok=True)
    with open(BASELINE_FILE, "w") as f:
        json.dump({"distribution": dist, "created_at": datetime.utcnow().isoformat()}, f, indent=2)
    logger.info(f"Baseline saved → {BASELINE_FILE}")


def check_drift(current: dict, baseline: dict, threshold: float = 0.15) -> bool:
    """Return True if any emotion proportion shifted by more than threshold."""
    drift_detected = False
    for emotion, base_prob in baseline.items():
        curr_prob = current.get(emotion, 0.0)
        delta = abs(curr_prob - base_prob)
        status = "⚠️  DRIFT" if delta > threshold else "✅ ok"
        logger.info(f"  {emotion:10s}: baseline={base_prob:.2f} current={curr_prob:.2f} Δ={delta:.2f} {status}")
        if delta > threshold:
            drift_detected = True
    return drift_detected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--threshold", type=float, default=0.15)
    parser.add_argument("--save-baseline", action="store_true")
    args = parser.parse_args()

    df = load_recent_predictions(args.days)
    if df.empty:
        logger.info("No recent predictions to analyze.")
        return

    current_dist = compute_distribution(df)
    logger.info(f"\nRecent distribution (last {args.days} days, n={len(df)}):")
    for k, v in current_dist.items():
        logger.info(f"  {k}: {v:.2%}")

    if args.save_baseline:
        save_baseline(current_dist)
        return

    if not BASELINE_FILE.exists():
        logger.warning("No baseline found. Run with --save-baseline first.")
        save_baseline(current_dist)
        return

    with open(BASELINE_FILE) as f:
        baseline_data = json.load(f)

    logger.info(f"\nBaseline from: {baseline_data['created_at']}")
    drift = check_drift(current_dist, baseline_data["distribution"], args.threshold)

    if drift:
        logger.warning("\n🚨 Drift detected! Consider re-training the model.")
        exit(1)   # non-zero exit triggers GitHub Actions failure
    else:
        logger.info("\n✅ No significant drift detected.")


if __name__ == "__main__":
    main()