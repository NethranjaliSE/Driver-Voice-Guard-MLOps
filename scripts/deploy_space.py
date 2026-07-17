"""
Create/update the Hugging Face Space for this app and wire up its secrets.

Run: python scripts/deploy_space.py [--space-repo-id user/name]
                                     [--model-repo-id user/name] [--private]

Requires HF_TOKEN (write scope) in the environment. Run
scripts/push_model_to_hub.py first (or pass --model-repo-id to point at an
existing model repo) so HF_MODEL_REPO resolves to something real.
"""

import argparse
import os

from huggingface_hub import HfApi

PROJECT_ROOT = "."

IGNORE_PATTERNS = [
    "venv/*", "venv/**/*",
    ".venv/*", ".venv/**/*",
    "frontend/node_modules/*", "frontend/node_modules/**/*",
    "frontend/dist/*", "frontend/dist/**/*",
    "frontend/.env.local",
    "frontend/.env",
    "data/*", "data/**/*",
    "mlruns/*", "mlruns/**/*",
    "logs/*", "logs/**/*",
    "models/*.pkl",
    "models/*.yaml",
    "models/confusion_matrix.png",
    "**/__pycache__/*", "**/__pycache__/**/*",
    "*.pyc",
    ".pytest_cache/*", ".pytest_cache/**/*",
    ".git/*", ".git/**/*",
    ".github/*", ".github/**/*",
    "Dockerfile",        # docker-compose-only backend image; Space uses Dockerfile.space instead
    "Dockerfile.space",  # uploaded separately, renamed to "Dockerfile" below
    ".env",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--space-repo-id", default=None, help="Defaults to <your-username>/driver-safety-monitor")
    parser.add_argument("--model-repo-id", default=None, help="Defaults to <your-username>/driver-safety-monitor-model")
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is not set in the environment.")

    api = HfApi(token=token)
    username = api.whoami()["name"]
    space_repo_id = args.space_repo_id or f"{username}/driver-safety-monitor"
    model_repo_id = args.model_repo_id or f"{username}/driver-safety-monitor-model"

    print(f"Creating/updating Space: {space_repo_id} (private={args.private})")
    api.create_repo(
        repo_id=space_repo_id,
        repo_type="space",
        space_sdk="docker",
        private=args.private,
        exist_ok=True,
    )

    print("Uploading project files (this can take a minute)...")
    api.upload_folder(
        repo_id=space_repo_id,
        repo_type="space",
        folder_path=PROJECT_ROOT,
        ignore_patterns=IGNORE_PATTERNS,
    )

    print("Uploading Dockerfile.space as Dockerfile ...")
    api.upload_file(
        path_or_fileobj="Dockerfile.space",
        path_in_repo="Dockerfile",
        repo_id=space_repo_id,
        repo_type="space",
    )

    print("Setting HF_TOKEN secret and HF_MODEL_REPO variable on the Space...")
    api.add_space_secret(repo_id=space_repo_id, key="HF_TOKEN", value=token)
    api.add_space_variable(repo_id=space_repo_id, key="HF_MODEL_REPO", value=model_repo_id)

    print(f"\nDone: https://huggingface.co/spaces/{space_repo_id}")
    print("The Space will rebuild automatically. Watch progress/logs there, or:")
    print(f"  hf spaces logs {space_repo_id} --build")


if __name__ == "__main__":
    main()
