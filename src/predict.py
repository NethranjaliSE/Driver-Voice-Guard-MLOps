"""
Inference helper — loads the saved driver-state model and runs predictions.
Used by api/main.py at startup.
"""

import os
import pickle
from collections import Counter, deque
from pathlib import Path
from typing import Union

import yaml
from huggingface_hub import hf_hub_download
from loguru import logger

from features import extract_feature


_MODEL_PATH = Path(__file__).parent.parent / "models" / "driver_model.pkl"
_META_PATH  = Path(__file__).parent.parent / "models" / "model_meta.yaml"

# Raw RAVDESS emotion → (driver state, baseline safety score). Used when the
# loaded model predicts raw emotions (the old ser_model.pkl). The current
# driver_model.pkl predicts driver states directly, which map to themselves
# via STATE_SAFETY below — so both model generations work.
EMOTION_TO_DRIVER = {
    "calm":    ("alert",    100),
    "happy":   ("alert",     90),
    "fearful": ("stressed",  65),
    "disgust": ("stressed",  60),
    "neutral": ("alert",    100),
    "surprised": ("stressed", 65),
}

# Driver-state classes map to themselves. Scores mirror api/main.py's
# SAFETY_WEIGHTS so both layers tell the same story.
STATE_SAFETY = {"alert": 100, "stressed": 65, "angry": 40, "drowsy": 20}

# Below this confidence the prediction is treated as unreliable and reported
# as "calibrating" instead of a driver state.
MIN_CONFIDENCE = 60.0
CALIBRATING_SAFETY = 80


def map_emotion(raw: str) -> tuple:
    """Map a raw model class to (driver_state, baseline_safety_score)."""
    if raw in EMOTION_TO_DRIVER:
        return EMOTION_TO_DRIVER[raw]
    return raw, STATE_SAFETY.get(raw, 50)


class StateSmoother:
    """
    Rolling-majority smoother over the last `maxlen` chunk predictions.
    The reported state only changes when at least 2 of the last 3 chunks
    agree; with no majority, the previous smoothed state stands. Kills the
    flicker of single misclassified chunks.
    """

    def __init__(self, maxlen: int = 3):
        self.window = deque(maxlen=maxlen)
        self.current = None

    def update(self, state: str) -> str:
        self.window.append(state)
        top, count = Counter(self.window).most_common(1)[0]
        if count >= 2 or self.current is None:
            self.current = top
        return self.current

    @property
    def is_stable(self) -> bool:
        return len(self.window) == self.window.maxlen and len(set(self.window)) == 1

    def reset(self):
        self.window.clear()
        self.current = None


class ModelNotTrainedError(RuntimeError):
    """Raised when a prediction is requested but no model has been loaded."""


class DriverStatePredictor:
    """Singleton wrapper around the trained driver-state MLPClassifier."""

    def __init__(self, model_path: Union[str, Path] = _MODEL_PATH):
        self.model_path = Path(model_path)
        self._model = None
        self._meta = {}
        self.smoother = StateSmoother(maxlen=3)
        # First 3 confident predictions form a "baseline" of the driver's
        # normal vocal state; later matches get a small confidence boost.
        self._baseline_samples = []
        self._baseline_state = None
        self._load()

    def _resolve_model_path(self) -> Path:
        if self.model_path.exists():
            return self.model_path

        hub_repo = os.getenv("HF_MODEL_REPO")
        if not hub_repo:
            return None

        logger.info(f"Model not found locally — downloading from HF Hub repo {hub_repo}")
        try:
            downloaded = hf_hub_download(
                repo_id=hub_repo,
                filename="driver_model.pkl",
                token=os.getenv("HF_TOKEN"),
            )
            return Path(downloaded)
        except Exception as e:
            logger.warning(f"Could not download driver_model.pkl from {hub_repo}: {e}")
            return None

    def _load(self):
        model_path = self._resolve_model_path()
        if model_path is None:
            logger.warning(
                f"No trained model found at {self.model_path} and no usable "
                "HF_MODEL_REPO. Run `python src/train.py` first. The API will "
                "start, but predictions will fail until a model is loaded."
            )
            self._model = None
            self._meta = {}
            return

        with open(model_path, "rb") as f:
            self._model = pickle.load(f)

        # Load metadata — gracefully handle missing file, corrupted YAML, or
        # (in deployment) a meta file that only exists on the Hub alongside
        # the model.
        meta_path = _META_PATH
        if not meta_path.exists():
            hub_repo = os.getenv("HF_MODEL_REPO")
            if hub_repo:
                try:
                    meta_path = Path(hf_hub_download(
                        repo_id=hub_repo,
                        filename="model_meta.yaml",
                        token=os.getenv("HF_TOKEN"),
                    ))
                except Exception as e:
                    logger.warning(f"Could not download model_meta.yaml from {hub_repo}: {e}")
                    meta_path = None

        if meta_path and meta_path.exists():
            try:
                with open(meta_path) as f:
                    self._meta = yaml.safe_load(f) or {}
            except yaml.constructor.ConstructorError:
                logger.warning(
                    "model_meta.yaml contains numpy types and could not be loaded with safe_load. "
                    "Deleting it — re-train to regenerate a clean version."
                )
                if meta_path == _META_PATH:
                    _META_PATH.unlink(missing_ok=True)
                self._meta = {}
            except Exception as e:
                logger.warning(f"Could not read model_meta.yaml: {e}")
                self._meta = {}

        logger.info(f"Model loaded from {model_path}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def predict(self, audio_source) -> dict:
        """
        Predict driver state from audio bytes, a file path, or a pre-loaded
        (samples, sample_rate) tuple.

        Returns:
            {
                "emotion":        str,    # raw model class
                "state":          str,    # mapped driver state, or "calibrating"
                "confidence":     float,  # 0-100, 1 decimal
                "safety_score":   int,
                "all_scores":     {class: probability*100, ...},
                "smoothed_state": str,    # rolling 2-of-3 majority
                "is_stable":      bool,   # last 3 chunks all agree
            }
        """
        if self._model is None:
            raise ModelNotTrainedError(
                "No trained model is loaded. Run `python src/train.py`, or "
                "set HF_MODEL_REPO to download one from the Hugging Face Hub, "
                "then call POST /model/reload."
            )

        features = extract_feature(audio_source).reshape(1, -1)
        raw      = self._model.predict(features)[0]
        proba    = self._model.predict_proba(features)[0]
        classes  = self._model.classes_.tolist()

        scores = {
            cls: round(float(p) * 100, 2)
            for cls, p in zip(classes, proba)
        }

        state, safety_score = map_emotion(raw)
        confidence = float(max(proba)) * 100

        # Calibration baseline: remember the driver's first 3 states; when a
        # later prediction matches that baseline, boost confidence by 10%
        # (the model agreeing with the session's established normal is a
        # weak extra signal).
        if self._baseline_state is None:
            self._baseline_samples.append(state)
            if len(self._baseline_samples) == 3:
                self._baseline_state = Counter(self._baseline_samples).most_common(1)[0][0]
                logger.info(f"Calibration baseline set: {self._baseline_state}")
        elif state == self._baseline_state:
            confidence = min(100.0, confidence * 1.1)

        smoothed_state = self.smoother.update(state)
        is_stable = self.smoother.is_stable

        if confidence < MIN_CONFIDENCE:
            state = "calibrating"
            safety_score = CALIBRATING_SAFETY

        return {
            "emotion": raw,
            "state": state,
            "confidence": round(confidence, 1),
            "safety_score": int(safety_score),
            "all_scores": scores,
            "smoothed_state": smoothed_state,
            "is_stable": is_stable,
        }

    def reset_session_state(self):
        """Clear the smoother + calibration baseline (new monitoring session)."""
        self.smoother.reset()
        self._baseline_samples = []
        self._baseline_state = None

    @property
    def meta(self) -> dict:
        return self._meta

    def reload(self):
        """Hot-reload model from disk (useful after re-training)."""
        self._load()
        logger.info("Model reloaded.")


# Module-level singleton — imported by api/main.py
predictor = DriverStatePredictor()
