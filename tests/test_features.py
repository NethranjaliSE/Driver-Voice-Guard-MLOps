"""Tests for feature extraction."""

import io
import wave

import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from features import extract_feature, get_emotion_from_filename, OBSERVED_EMOTIONS, RAVDESS_EMOTIONS


def make_wav_bytes(duration_s: float = 1.0, sr: int = 22050) -> bytes:
    """Generate a minimal valid WAV file in memory (sine wave)."""
    n = int(duration_s * sr)
    t = np.linspace(0, duration_s, n, endpoint=False)
    audio = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


WAV_BYTES = make_wav_bytes()

# ZCR, RMS and spectral centroid are always appended (1 value each).
N_ALWAYS_ON = 3


class TestExtractFeature:
    def test_returns_ndarray(self):
        feat = extract_feature(WAV_BYTES)
        assert isinstance(feat, np.ndarray)

    def test_mfcc_only_shape(self):
        feat = extract_feature(WAV_BYTES, mfcc=True, chroma=False, mel=False)
        # 40 MFCC + 40 delta + 40 delta-delta + ZCR/RMS/centroid
        assert feat.shape == (120 + N_ALWAYS_ON,)

    def test_chroma_only_shape(self):
        feat = extract_feature(WAV_BYTES, mfcc=False, chroma=True, mel=False)
        assert feat.shape == (12 + N_ALWAYS_ON,)

    def test_all_features_shape(self):
        feat = extract_feature(WAV_BYTES, mfcc=True, chroma=True, mel=True)
        # 40 mfcc + 40 Δ + 40 Δ² + 12 chroma + 128 mel + 3 = 263,
        # matching n_features in models/model_meta.yaml.
        assert feat.shape == (263,)

    def test_no_nan(self):
        feat = extract_feature(WAV_BYTES)
        assert not np.any(np.isnan(feat))

    def test_no_inf(self):
        feat = extract_feature(WAV_BYTES)
        assert not np.any(np.isinf(feat))


class TestGetEmotionFromFilename:
    """Filenames map RAVDESS emotion codes to raw emotion names."""

    def test_mapped_emotions(self):
        assert get_emotion_from_filename("03-01-01-01-01-01-01.wav") == "neutral"
        assert get_emotion_from_filename("03-01-02-01-01-01-01.wav") == "calm"
        assert get_emotion_from_filename("03-01-03-01-01-01-01.wav") == "happy"
        assert get_emotion_from_filename("03-01-05-01-01-01-01.wav") == "angry"
        assert get_emotion_from_filename("03-01-06-01-01-01-01.wav") == "fearful"

    def test_all_eight_codes_map_to_an_emotion(self):
        # Every RAVDESS code is used — no training files are skipped.
        for code in ("01", "02", "03", "04", "05", "06", "07", "08"):
            fname = f"03-01-{code}-01-01-01-01.wav"
            emotion = get_emotion_from_filename(fname)
            assert emotion == RAVDESS_EMOTIONS[code]
            assert emotion in OBSERVED_EMOTIONS

    def test_unknown_returns_none(self):
        assert get_emotion_from_filename("invalid.wav") is None
        assert get_emotion_from_filename("03-01-99-01-01-01-01.wav") is None


class TestObservedEmotions:
    def test_all_eight_emotions(self):
        assert set(OBSERVED_EMOTIONS) == {
            "neutral", "calm", "happy", "sad",
            "angry", "fearful", "disgust", "surprised",
        }

    def test_length(self):
        assert len(OBSERVED_EMOTIONS) == 8
