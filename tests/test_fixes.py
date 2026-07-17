"""
Regression tests for the prediction-quality fixes:
feature extraction shape/NaN safety, the silence gate, the
emotion→driver-state mapping, and rolling-majority smoothing.
"""
import io

import numpy as np
import pytest
import soundfile as sf

from features import extract_feature, is_speech, rms_energy
from predict import EMOTION_TO_DRIVER, StateSmoother, map_emotion

SR = 22050


def _wav_bytes(samples: np.ndarray, sr: int = SR) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV")
    return buf.getvalue()


def _sine(duration_s: float = 3.0, freq: float = 220.0, amplitude: float = 0.5) -> np.ndarray:
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# ---------------------------------------------------------------------------
# 1. Feature shape
# ---------------------------------------------------------------------------

def test_feature_shape_and_sanity():
    # The deployed driver_model.pkl was trained on 263 features
    # (40 MFCC + 40 Δ + 40 Δ² + 12 chroma + 128 mel + ZCR + RMS + centroid),
    # NOT 260 — see models/model_meta.yaml. This pins the contract the
    # model actually requires.
    result = extract_feature(_wav_bytes(_sine()))
    assert result.shape == (263,)
    assert not np.isnan(result).any()
    assert not np.isinf(result).any()


def test_features_never_nan_on_short_audio():
    # A tiny fragment must still produce a clean vector, not NaN garbage.
    result = extract_feature(_wav_bytes(_sine(duration_s=0.2)))
    assert result.shape == (263,)
    assert not np.isnan(result).any()
    assert not np.isinf(result).any()


# ---------------------------------------------------------------------------
# 2. Silence gate
# ---------------------------------------------------------------------------

def test_silence_is_not_speech():
    quiet = _wav_bytes(_sine(amplitude=0.001))
    assert is_speech(quiet, threshold=0.01) is False


def test_normal_speech_level_is_speech():
    loud = _wav_bytes(_sine(amplitude=0.5))
    assert is_speech(loud, threshold=0.01) is True


def test_rms_energy_of_silence_near_zero():
    assert rms_energy(_wav_bytes(np.zeros(SR, dtype=np.float32))) == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 3. Emotion → driver-state mapping
# ---------------------------------------------------------------------------

def test_happy_maps_to_alert_not_stressed():
    state, safety = map_emotion("happy")
    assert state == "alert"
    assert safety == 90


def test_disgust_maps_to_stressed():
    state, safety = map_emotion("disgust")
    assert state == "stressed"
    assert safety == 60


def test_full_mapping_table():
    assert EMOTION_TO_DRIVER["calm"] == ("alert", 100)
    assert EMOTION_TO_DRIVER["happy"] == ("alert", 90)
    assert EMOTION_TO_DRIVER["fearful"] == ("stressed", 65)
    assert EMOTION_TO_DRIVER["disgust"] == ("stressed", 60)


def test_driver_state_classes_map_to_themselves():
    # driver_model.pkl predicts driver states directly — they must pass
    # through the mapping unchanged.
    assert map_emotion("alert")[0] == "alert"
    assert map_emotion("angry")[0] == "angry"
    assert map_emotion("stressed")[0] == "stressed"


# ---------------------------------------------------------------------------
# 4. Rolling-majority smoothing
# ---------------------------------------------------------------------------

def test_smoothing_majority_wins():
    s = StateSmoother(maxlen=3)
    for state in ["alert", "angry", "alert"]:
        result = s.update(state)
    assert result == "alert"


def test_smoothing_two_of_three_angry():
    s = StateSmoother(maxlen=3)
    for state in ["angry", "angry", "alert"]:
        result = s.update(state)
    assert result == "angry"


def test_smoothing_holds_previous_without_majority():
    s = StateSmoother(maxlen=3)
    s.update("alert")
    s.update("alert")
    s.update("alert")
    # Window becomes [alert, angry, stressed] — no majority → hold "alert".
    s.update("angry")
    assert s.update("stressed") == "alert"


def test_smoothing_stability_flag():
    s = StateSmoother(maxlen=3)
    s.update("alert")
    assert s.is_stable is False
    s.update("alert")
    s.update("alert")
    assert s.is_stable is True
    s.update("angry")
    assert s.is_stable is False
