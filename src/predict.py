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

# Below this confidence the prediction is treated as unreliable and reported
# as "calibrating" instead of an emotion.
MIN_CONFIDENCE = 60.0
CALIBRATING_SAFETY = 80

# Each of the 8 emotions maps to a complete driver behavior profile
EMOTION_BEHAVIOR = {
    "neutral": {
        "driver_state":   "focused",
        "safety_score":   95,
        "risk_level":     "SAFE",
        "emoji":          "😐",
        "headline":       "Focused and composed",
        "description":    "Your voice is calm and neutral — ideal state for driving.",
        "suggestion":     "Keep it up. Stay hydrated and take breaks every 2 hours.",
        "car_actions":    [],
    },
    "calm": {
        "driver_state":   "relaxed",
        "safety_score":   100,
        "risk_level":     "SAFE",
        "emoji":          "😌",
        "headline":       "Perfectly relaxed",
        "description":    "You sound completely at ease — the best possible driving state.",
        "suggestion":     "Excellent. You are in full control.",
        "car_actions":    ["Play ambient music"],
    },
    "happy": {
        "driver_state":   "energetic",
        "safety_score":   82,
        "risk_level":     "SAFE",
        "emoji":          "😄",
        "headline":       "Positive and energetic",
        "description":    "Good mood detected. Positive drivers are generally safer — "
                          "just watch your speed as excitement can increase it.",
        "suggestion":     "Great energy! Stay mindful of speed limits.",
        "car_actions":    ["Play upbeat music", "Set cruise control reminder"],
    },
    "sad": {
        "driver_state":   "low_mood",
        "safety_score":   55,
        "risk_level":     "CAUTION",
        "emoji":          "😢",
        "headline":       "Low mood detected",
        "description":    "Sadness slows reaction time and reduces concentration. "
                          "Drivers in low mood are 10x more likely to have accidents.",
        "suggestion":     "Consider pulling over for 5 minutes. Call someone you trust.",
        "car_actions":    [
            "Play soft music",
            "Set AC to comfortable (23°C)",
            "Silence notifications",
        ],
    },
    "angry": {
        "driver_state":   "agitated",
        "safety_score":   28,
        "risk_level":     "DANGER",
        "emoji":          "😠",
        "headline":       "High agitation — road rage risk",
        "description":    "Anger is one of the leading causes of fatal accidents. "
                          "Aggressive driving decisions are made in this state.",
        "suggestion":     "Ease off the accelerator. Take 3 deep breaths right now.",
        "car_actions":    [
            "Play calm music",
            "Set AC to cool (20°C)",
            "Start breathing exercise",
            "Silence calls / notifications",
        ],
    },
    "fearful": {
        "driver_state":   "anxious",
        "safety_score":   22,
        "risk_level":     "DANGER",
        "emoji":          "😨",
        "headline":       "Panic or anxiety detected",
        "description":    "Fear or panic severely impairs decision-making and "
                          "causes erratic vehicle control.",
        "suggestion":     "Pull over safely when possible. Do not continue driving in panic.",
        "car_actions":    [
            "Play calming music",
            "Start breathing exercise",
            "Set AC to comfortable (22°C)",
            "Activate hazard lights reminder",
        ],
    },
    "disgust": {
        "driver_state":   "uncomfortable",
        "safety_score":   52,
        "risk_level":     "CAUTION",
        "emoji":          "🤢",
        "headline":       "Discomfort or irritation detected",
        "description":    "Disgust or discomfort creates distraction and "
                          "reduces focus on the road ahead.",
        "suggestion":     "Identify what is bothering you. Pull over if discomfort persists.",
        "car_actions":    [
            "Adjust AC temperature",
            "Open windows for fresh air",
            "Silence notifications",
        ],
    },
    "surprised": {
        "driver_state":   "startled",
        "safety_score":   68,
        "risk_level":     "CAUTION",
        "emoji":          "😲",
        "headline":       "Startled response detected",
        "description":    "Surprise causes a momentary loss of focus. "
                          "Recovery usually takes 2-3 seconds.",
        "suggestion":     "Refocus on the road. Increase following distance briefly.",
        "car_actions":    ["Increase following distance alert"],
    },
}


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
        Predict the driver's emotion from audio bytes, a file path, or a
        pre-loaded (samples, sample_rate) tuple, and attach the full
        behavior profile for the predicted emotion.
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

        # All 8 emotion scores (0-100)
        all_scores = {
            cls: round(float(p) * 100, 2)
            for cls, p in zip(classes, proba)
        }

        confidence = round(float(max(proba)) * 100, 1)

        # Get full behavior profile for the predicted emotion
        behavior = EMOTION_BEHAVIOR.get(raw, {
            "driver_state":  "unknown",
            "safety_score":  50,
            "risk_level":    "CAUTION",
            "emoji":         "❓",
            "headline":      "Uncertain",
            "description":   "Could not determine driver state.",
            "suggestion":    "Please try again.",
            "car_actions":   [],
        })

        # Baseline calibration
        if self._baseline_state is None:
            self._baseline_samples.append(raw)
            if len(self._baseline_samples) == 3:
                self._baseline_state = Counter(
                    self._baseline_samples
                ).most_common(1)[0][0]
                logger.info(f"Calibration baseline set: {self._baseline_state}")
        elif raw == self._baseline_state:
            confidence = min(100.0, confidence * 1.1)

        # Smoothing
        smoothed = self.smoother.update(raw)
        is_stable = self.smoother.is_stable

        # Confidence gate
        if confidence < MIN_CONFIDENCE:
            return {
                "emotion":       "calibrating",
                "smoothed":      smoothed,
                "confidence":    confidence,
                "safety_score":  CALIBRATING_SAFETY,
                "risk_level":    "CALIBRATING",
                "driver_state":  "calibrating",
                "emoji":         "⏳",
                "headline":      "Calibrating...",
                "description":   "Listening to your voice to establish a baseline.",
                "suggestion":    "Please keep speaking naturally.",
                "car_actions":   [],
                "all_scores":    all_scores,
                "is_stable":     is_stable,
                "alert_triggered": False,
            }

        alert_triggered = behavior["risk_level"] in ("DANGER",)

        return {
            "emotion":          raw,
            "smoothed":         smoothed,
            "confidence":       confidence,
            "safety_score":     behavior["safety_score"],
            "risk_level":       behavior["risk_level"],
            "driver_state":     behavior["driver_state"],
            "emoji":            behavior["emoji"],
            "headline":         behavior["headline"],
            "description":      behavior["description"],
            "suggestion":       behavior["suggestion"],
            "car_actions":      behavior["car_actions"],
            "all_scores":       all_scores,
            "is_stable":        is_stable,
            "alert_triggered":  alert_triggered,
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
