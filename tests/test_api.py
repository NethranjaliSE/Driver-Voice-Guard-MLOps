"""Tests for FastAPI endpoints (using TestClient, mock predictor)."""

import io
import wave
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient


def make_wav_bytes(duration_s: float = 1.0, sr: int = 22050, amplitude: float = 1.0) -> bytes:
    n = int(duration_s * sr)
    t = np.linspace(0, duration_s, n, endpoint=False)
    audio = (np.sin(2 * np.pi * 440 * t) * amplitude * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


MOCK_RESULT = {
    "emotion": "happy",
    "smoothed": "happy",
    "confidence": 87.5,
    "safety_score": 82,
    "risk_level": "SAFE",
    "driver_state": "energetic",
    "emoji": "😄",
    "headline": "Positive and energetic",
    "description": "Good mood detected.",
    "suggestion": "Great energy! Stay mindful of speed limits.",
    "car_actions": ["Play upbeat music", "Set cruise control reminder"],
    "all_scores": {"happy": 87.5, "calm": 6.5, "neutral": 6.0},
    "is_stable": True,
    "alert_triggered": False,
}


# Swap the predictor singleton for a mock before api.main binds to it.
@pytest.fixture(scope="module")
def client():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

    import predict as pred_module
    pred_module.predictor = MagicMock()
    pred_module.predictor.predict.return_value = MOCK_RESULT
    pred_module.predictor.meta = {}
    pred_module.predictor.is_ready = True

    from api.main import app
    yield TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


class TestModelInfo:
    def test_model_info(self, client):
        res = client.get("/model/info")
        assert res.status_code == 200
        data = res.json()
        assert "trained_states" in data
        assert "features" in data


class TestAnalyzeEndpoint:
    def test_analyze_voice_wav(self, client):
        wav = make_wav_bytes()
        res = client.post(
            "/analyze/voice",
            files={"file": ("test.wav", wav, "audio/wav")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["emotion"] == "happy"
        assert data["driver_state"] == "energetic"
        assert data["headline"] == "Positive and energetic"
        assert data["risk_level"] == "SAFE"
        assert data["car_actions"] == ["Play upbeat music", "Set cruise control reminder"]
        assert "confidence" in data
        assert "all_scores" in data
        assert "is_stable" in data

    def test_analyze_rejects_non_audio(self, client):
        res = client.post(
            "/analyze/voice",
            files={"file": ("test.txt", b"not audio", "text/plain")},
        )
        assert res.status_code == 422

    def test_confidence_in_range(self, client):
        wav = make_wav_bytes()
        res = client.post(
            "/analyze/voice",
            files={"file": ("test.wav", wav, "audio/wav")},
        )
        assert 0 <= res.json()["confidence"] <= 100

    def test_silence_gated_before_model(self, client):
        quiet = make_wav_bytes(amplitude=0.002)
        res = client.post(
            "/analyze/stream",
            files={"file": ("quiet.wav", quiet, "audio/wav")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["emotion"] == "silence"
        assert data["driver_state"] == "calibrating"
        assert data["risk_level"] == "CALIBRATING"
        assert data["confidence"] == 0.0


class TestSessionFlow:
    def test_chunk_and_stats(self, client):
        session_id = client.get("/session/start").json()["session_id"]

        wav = make_wav_bytes()
        res = client.post(
            f"/session/{session_id}/chunk",
            files={"file": ("chunk.wav", wav, "audio/wav")},
        )
        assert res.status_code == 200

        stats = client.get(f"/session/{session_id}/stats").json()
        assert stats["total_chunks"] == 1
        assert stats["state_distribution"] == {"happy": 1}
        assert stats["stable_percentage"] == 100.0
        assert stats["average_confidence"] == pytest.approx(87.5)

    def test_stats_unknown_session_404(self, client):
        assert client.get("/session/nope/stats").status_code == 404


class TestDebugEndpoint:
    def test_predict_debug(self, client):
        res = client.get("/predict/debug")
        assert res.status_code == 200
        data = res.json()
        assert "last_predictions" in data
        assert "feature_shapes" in data
