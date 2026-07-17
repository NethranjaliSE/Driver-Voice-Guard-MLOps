"""
Accuracy gate — reads models/model_meta.yaml and exits 1 if accuracy < threshold.
Used in CI/CD to prevent deploying a degraded model.
"""

import argparse
import sys
from pathlib import Path

import yaml

META_PATH = Path("models/model_meta.yaml")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.65, help="Minimum accuracy")
    args = parser.parse_args()

    if not META_PATH.exists():
        print("❌ models/model_meta.yaml not found. Did training run?")
        sys.exit(1)

    with open(META_PATH) as f:
        meta = yaml.safe_load(f)

    accuracy = meta.get("accuracy", 0)
    print(f"Model accuracy: {accuracy:.4f} (threshold: {args.threshold})")

    if accuracy < args.threshold:
        print(f"❌ Accuracy gate FAILED: {accuracy:.4f} < {args.threshold}")
        sys.exit(1)

    print(f"✅ Accuracy gate PASSED: {accuracy:.4f} >= {args.threshold}")


if __name__ == "__main__":
    main()