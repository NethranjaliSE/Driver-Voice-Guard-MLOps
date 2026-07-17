"""
Driver Safety Monitor — training script with MLflow experiment tracking.

Run: python src/train.py --data-path data/raw --test-size 0.25

NOTE ON DATA: RAVDESS is *acted* emotional speech, not real driving audio,
and has no "drowsy" category at all — features.RAVDESS_TO_DRIVER_STATE maps
neutral/calm -> alert, fearful/surprised -> stressed, angry -> angry, and
leaves "drowsy" entirely unmapped. To train a real "drowsy" class, add
labelled audio under --extra-data-path (default: data/raw_extra), one
subfolder per driver state, e.g.:

    data/raw_extra/drowsy/*.wav

The DROZY dataset (https://zenodo.org/record/1487612) is sometimes suggested
for drowsiness research, but it's built around EEG/physiological signals and
video, not voice recordings — it won't directly drop into this folder. Use a
dedicated drowsy-speech corpus, or self-recorded yawning/slow-speech samples,
instead.
"""

import argparse
import glob
import os
import pickle
from collections import Counter
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import yaml
from loguru import logger
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from features import (
    OBSERVED_EMOTIONS,
    augment_audio,
    extract_feature,
    get_emotion_from_filename,
)

import soundfile as sf


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PARAMS = {
    "n_mfcc": 40,
    "test_size": 0.25,
    "random_state": 42,
    "use_augmentation": True,
    "hidden_layer_sizes": (300,),
    "alpha": 0.01,
    "batch_size": 256,
    "max_iter": 500,
    "learning_rate": "adaptive",
}

MLFLOW_EXPERIMENT = "DriverSafety-Experiment"
MIN_SAMPLES_PER_CLASS = 4   # below this, train_test_split can't stratify safely


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_ravdess(data_path: str, augment: bool) -> tuple:
    x, y = [], []
    pattern = os.path.join(data_path, "**/*.wav")
    files = glob.glob(pattern, recursive=True)

    if not files:
        raise FileNotFoundError(
            f"No .wav files found under '{data_path}'. "
            "Download RAVDESS and place Actor_* folders there."
        )

    logger.info(f"Found {len(files)} RAVDESS audio files")

    for i, fpath in enumerate(files, 1):
        state = get_emotion_from_filename(os.path.basename(fpath))
        if state not in OBSERVED_EMOTIONS:
            continue

        try:
            feat = extract_feature(fpath)
            x.append(feat)
            y.append(state)

            if augment:
                with sf.SoundFile(fpath) as sf_file:
                    raw = sf_file.read(dtype="float32")
                    sr = sf_file.samplerate
                if raw.ndim > 1:
                    raw = raw.mean(axis=1)
                for aug in augment_audio(raw, sr)[1:]:
                    aug_feat = extract_feature((aug, sr))
                    x.append(aug_feat)
                    y.append(state)

        except Exception as e:
            logger.warning(f"Skipped {fpath}: {e}")

        if i % 100 == 0:
            logger.info(f"  Processed {i}/{len(files)}")

    return x, y


def _load_extra_data(extra_data_path: str, augment: bool) -> tuple:
    """
    Optional supplementary data: data/raw_extra/<driver_state>/*.wav — for
    classes RAVDESS can't supply (chiefly "drowsy"). Silently skipped if the
    folder doesn't exist; this is meant to be filled in by the user later.
    """
    x, y = [], []
    root = Path(extra_data_path)
    if not root.exists():
        logger.info(
            f"No extra-data folder at '{extra_data_path}' — training only on "
            "RAVDESS-derived classes. See train.py's module docstring for how "
            "to add drowsy-class samples."
        )
        return x, y

    for state_dir in root.iterdir():
        if not state_dir.is_dir() or state_dir.name not in OBSERVED_EMOTIONS:
            continue
        state = state_dir.name
        files = [p for p in state_dir.iterdir() if p.suffix.lower() == ".wav"]
        logger.info(f"Found {len(files)} extra '{state}' samples under {state_dir}")

        for fpath in files:
            try:
                feat = extract_feature(str(fpath))
                x.append(feat)
                y.append(state)

                if augment:
                    with sf.SoundFile(str(fpath)) as sf_file:
                        raw = sf_file.read(dtype="float32")
                        sr = sf_file.samplerate
                    if raw.ndim > 1:
                        raw = raw.mean(axis=1)
                    for aug in augment_audio(raw, sr)[1:]:
                        aug_feat = extract_feature((aug, sr))
                        x.append(aug_feat)
                        y.append(state)
            except Exception as e:
                logger.warning(f"Skipped {fpath}: {e}")

    return x, y


def load_dataset(data_path: str, extra_data_path: str, augment: bool = False) -> tuple:
    """Load RAVDESS (remapped to driver states) plus any extra-data samples."""
    x_ravdess, y_ravdess = _load_ravdess(data_path, augment)
    x_extra, y_extra = _load_extra_data(extra_data_path, augment)

    x = x_ravdess + x_extra
    y = y_ravdess + y_extra

    counts = Counter(y)
    logger.info(f"Loaded {len(x)} samples across driver states: {dict(counts)}")

    missing = [e for e in OBSERVED_EMOTIONS if counts.get(e, 0) == 0]
    if missing:
        logger.warning(
            f"No training data at all for: {missing}. The model will be "
            f"trained without {'these classes' if len(missing) > 1 else 'this class'} "
            "— add samples under data/raw_extra/<state>/ to include them."
        )

    too_few = [e for e, c in counts.items() if 0 < c < MIN_SAMPLES_PER_CLASS]
    if too_few:
        logger.warning(
            f"Dropping classes with fewer than {MIN_SAMPLES_PER_CLASS} samples "
            f"(can't reliably stratify-split): {too_few}"
        )
        keep_idx = [i for i, label in enumerate(y) if label not in too_few]
        x = [x[i] for i in keep_idx]
        y = [y[i] for i in keep_idx]

    return np.array(x), y


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(data_path: str, extra_data_path: str, params: dict, grid_search: bool = False):
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    with mlflow.start_run() as run:
        logger.info(f"MLflow run ID: {run.info.run_id}")

        # Load data
        X, y = load_dataset(data_path, extra_data_path, augment=params["use_augmentation"])
        trained_classes = sorted(set(y))
        if len(trained_classes) < 2:
            raise RuntimeError(
                f"Only {len(trained_classes)} usable class(es) ({trained_classes}) — "
                "need at least 2 to train a classifier."
            )

        x_train, x_test, y_train, y_test = train_test_split(
            X, y,
            test_size=params["test_size"],
            random_state=params["random_state"],
            stratify=y,
        )

        mlflow.log_params({
            "train_size": len(x_train),
            "test_size_n": len(x_test),
            "n_features": x_train.shape[1],
            "augmentation": params["use_augmentation"],
            "configured_emotions": str(OBSERVED_EMOTIONS),
            "trained_emotions": str(trained_classes),
            **{k: v for k, v in params.items() if k not in ("use_augmentation",)},
        })

        # Model
        # MFCC/Chroma/Mel features live on wildly different scales (MFCC ~
        # -760..76, Mel ~1e-9..0.02), which starves the gradient-based MLP
        # of signal from the smaller-magnitude features. StandardScaler is
        # fit only on x_train and bundled into the pipeline so the exact
        # same transform is replayed at inference time in predict.py.
        if grid_search:
            logger.info("Running GridSearchCV (this may take a while)…")
            param_grid = {
                "mlp__hidden_layer_sizes": [(300,), (300, 150), (512, 256, 128)],
                "mlp__alpha": [0.001, 0.01, 0.1],
                "mlp__learning_rate": ["adaptive", "constant"],
            }
            base = Pipeline([
                ("scaler", StandardScaler()),
                ("mlp", MLPClassifier(
                    batch_size=params["batch_size"],
                    max_iter=params["max_iter"],
                    random_state=params["random_state"],
                )),
            ])
            search = GridSearchCV(base, param_grid, cv=5, n_jobs=-1, verbose=1)
            search.fit(x_train, y_train)
            best = search.best_params_
            mlflow.log_params({"best_" + k: v for k, v in best.items()})
            model = search.best_estimator_
        else:
            model = Pipeline([
                ("scaler", StandardScaler()),
                ("mlp", MLPClassifier(
                    hidden_layer_sizes=params["hidden_layer_sizes"],
                    alpha=params["alpha"],
                    batch_size=params["batch_size"],
                    max_iter=params["max_iter"],
                    learning_rate=params["learning_rate"],
                    random_state=params["random_state"],
                    epsilon=1e-8,
                    # NOTE: MLPClassifier does NOT support class_weight —
                    # passing it raises TypeError. RAVDESS is near-balanced
                    # (only neutral has half the samples), so no reweighting
                    # is applied.
                )),
            ])
            model.fit(x_train, y_train)

        # Evaluation
        y_pred = model.predict(x_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)

        mlflow.log_metric("accuracy", acc)
        for state in trained_classes:
            if state in report:
                mlflow.log_metric(f"f1_{state}", report[state]["f1-score"])
                mlflow.log_metric(f"precision_{state}", report[state]["precision"])
                mlflow.log_metric(f"recall_{state}", report[state]["recall"])

        logger.info(f"\n{'='*50}")
        logger.info(f"Accuracy: {acc:.4f} ({acc*100:.2f}%)")
        logger.info(f"\n{classification_report(y_test, y_pred)}")

        # Save model
        Path("models").mkdir(exist_ok=True)
        model_path = "models/driver_model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        # Save metadata — cast to plain Python types so yaml.safe_load can
        # read it back. accuracy_score() returns numpy.float64 which
        # yaml.dump serialises as a !!python object tag that safe_load
        # refuses to parse, so we use yaml.safe_dump instead.
        meta = {
            "accuracy":           float(acc),
            "emotions":           list(trained_classes),
            "configured_emotions": list(OBSERVED_EMOTIONS),
            "n_features":         int(x_train.shape[1]),
            "run_id":             str(run.info.run_id),
        }
        with open("models/model_meta.yaml", "w") as f:
            yaml.safe_dump(meta, f)

        # Log artifacts to MLflow
        mlflow.sklearn.log_model(
            model,
            artifact_path="driver_model",
            registered_model_name="DriverSafety-MLPClassifier",
        )
        mlflow.log_artifact(model_path)
        mlflow.log_artifact("models/model_meta.yaml")

        logger.info(f"Model saved → {model_path}")
        logger.info(f"MLflow run complete. View: mlflow ui")

        return model, acc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Driver Safety voice-state model")
    parser.add_argument("--data-path", default="data/raw", help="Path to RAVDESS data")
    parser.add_argument(
        "--extra-data-path", default="data/raw_extra",
        help="Optional path with one subfolder per driver state (e.g. drowsy/) "
             "for classes RAVDESS can't supply",
    )
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--grid-search", action="store_true")
    parser.add_argument("--no-augment", action="store_true")
    args = parser.parse_args()

    PARAMS["test_size"] = args.test_size
    PARAMS["use_augmentation"] = not args.no_augment

    train(args.data_path, args.extra_data_path, PARAMS, grid_search=args.grid_search)
