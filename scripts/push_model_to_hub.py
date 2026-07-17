"""
Upload the trained driver-state model to a Hugging Face model repo.

Run: python scripts/push_model_to_hub.py [--repo-id user/name] [--private]

Requires HF_TOKEN (write scope) in the environment.
"""

import argparse
from pathlib import Path

import yaml
from huggingface_hub import HfApi

MODEL_PATH = Path("models/driver_model.pkl")
META_PATH = Path("models/model_meta.yaml")


def build_model_card(meta: dict, repo_id: str) -> str:
    accuracy = meta.get("accuracy")
    states = meta.get("emotions", ["alert", "drowsy", "stressed", "angry"])
    n_features = meta.get("n_features", 263)
    accuracy_line = f"{accuracy * 100:.2f}%" if accuracy is not None else "N/A"

    return f"""---
library_name: scikit-learn
tags:
  - driver-safety
  - audio-classification
  - mlp
  - ravdess
license: mit
---

# Driver Safety Monitor — Voice-State MLPClassifier

`StandardScaler` + `MLPClassifier` (scikit-learn `Pipeline`) trained on
[RAVDESS](https://zenodo.org/record/1188976) (relabelled to driver-relevant
states — see the project README for the mapping and its limitations) to
classify a short voice recording into one of {len(states)} states:
{", ".join(states)}.

Input features (per clip, {n_features}-dim): MFCC(40) + ΔMFCC(40) +
Δ²MFCC(40) + Chroma(12) + Mel(128) + Zero-Crossing-Rate(1) + RMS Energy(1)
+ Spectral Centroid(1), extracted with `librosa` (see `extract_feature()` in
the project's `src/features.py`).

- Held-out test accuracy: **{accuracy_line}**

**This is a research prototype, not a validated driver-safety device.**
RAVDESS is acted emotional speech, not real driving audio, and has no
"drowsy" category at all — see the project README for details.

## Usage

```python
import pickle
from huggingface_hub import hf_hub_download

model_path = hf_hub_download(repo_id="{repo_id}", filename="driver_model.pkl")
with open(model_path, "rb") as f:
    model = pickle.load(f)

# features: 1-D array, see extract_feature() in the project's src/features.py
state = model.predict(features.reshape(1, -1))[0]
proba = model.predict_proba(features.reshape(1, -1))[0]
```

This repo also hosts `model_meta.yaml` with training metadata (accuracy,
feature count, trained state labels).
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", default=None, help="Defaults to <your-username>/driver-safety-monitor-model")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    api = HfApi()
    username = api.whoami()["name"]
    repo_id = args.repo_id or f"{username}/driver-safety-monitor-model"

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"{MODEL_PATH} not found. Run `python src/train.py` first.")

    meta = {}
    if META_PATH.exists():
        with open(META_PATH) as f:
            meta = yaml.safe_load(f) or {}

    print(f"Creating/updating model repo: {repo_id} (private={args.private})")
    api.create_repo(repo_id=repo_id, repo_type="model", private=args.private, exist_ok=True)

    print("Uploading driver_model.pkl ...")
    api.upload_file(
        path_or_fileobj=str(MODEL_PATH),
        path_in_repo="driver_model.pkl",
        repo_id=repo_id,
        repo_type="model",
    )

    if META_PATH.exists():
        print("Uploading model_meta.yaml ...")
        api.upload_file(
            path_or_fileobj=str(META_PATH),
            path_in_repo="model_meta.yaml",
            repo_id=repo_id,
            repo_type="model",
        )

    print("Uploading model card (README.md) ...")
    api.upload_file(
        path_or_fileobj=build_model_card(meta, repo_id).encode(),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="model",
    )

    print(f"\nDone: https://huggingface.co/{repo_id}")
    print(f"Set HF_MODEL_REPO={repo_id} in .env (or as a Space variable) so predict.py downloads from here.")


if __name__ == "__main__":
    main()
