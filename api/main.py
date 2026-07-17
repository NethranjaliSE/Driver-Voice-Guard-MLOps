"""
Driver Safety Monitor — FastAPI Backend
Endpoints:
  POST /analyze/voice              → single-shot analysis of a longer clip
  POST /analyze/stream              → single-shot analysis of a short chunk
  GET  /session/start               → start a monitoring session
  POST /session/{id}/chunk          → analyze a chunk and append it to the session timeline
  GET  /session/{id}/report         → aggregate report for a session
  POST /report/pdf                  → render a session report as a PDF
  GET  /session/{id}/stats          → prediction-quality stats for a session
  GET  /predict/debug               → last 10 predictions + feature stats
  GET  /health                      → health check
  GET  /model/info                  → model metadata
  POST /model/reload                → hot-reload model from disk
  GET  /metrics                     → Prometheus metrics
"""

import csv
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Add src/ to path so we can import from there
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from predict import predictor, ModelNotTrainedError, CALIBRATING_SAFETY
from features import OBSERVED_EMOTIONS, LAST_FEATURE_STATS, _load_audio, rms_energy
from api import session_store
from api.report import generate_session_pdf
from api.schemas import DriverStateResponse, PdfReportRequest, SessionReport, SessionStartResponse

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Driver Safety Monitor API",
    description="Detects driver vocal state (alert/drowsy/stressed/angry) from voice and tracks session safety.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Analysis pipeline
# ---------------------------------------------------------------------------

# Chunks quieter than this RMS are treated as silence and never reach the
# model — an MLP fed a silent chunk happily returns a confident garbage state.
# Kept low (0.002): RAVDESS studio clips sit around RMS 0.004, and true
# mic-silence chunks measure well under 0.002.
SILENCE_RMS_THRESHOLD = 0.002

# Rolling record of recent predictions for GET /predict/debug.
_DEBUG_LOG = deque(maxlen=10)


def _analyze(audio_bytes: bytes) -> dict:
    # Decode once; everything downstream (RMS gate, feature extraction)
    # accepts the pre-loaded (samples, sample_rate) tuple.
    audio = _load_audio(audio_bytes)
    rms = rms_energy(audio)

    # ── Energy gate: don't classify silence ──────────────────────────────
    if rms <= SILENCE_RMS_THRESHOLD:
        print(f"[predict] silence gate: rms={rms:.5f} <= {SILENCE_RMS_THRESHOLD} — chunk skipped")
        return {
            "emotion": "silence",
            "smoothed": "calibrating",
            "confidence": 0.0,
            "safety_score": CALIBRATING_SAFETY,
            "risk_level": "CALIBRATING",
            "driver_state": "calibrating",
            "emoji": "🤫",
            "headline": "No speech detected",
            "description": "The last chunk was silent — monitoring continues.",
            "suggestion": "Speak naturally; analysis resumes when your voice is heard.",
            "car_actions": [],
            "all_scores": {},
            "is_stable": False,
            "alert_triggered": False,
            "rms_energy": round(rms, 5),
        }

    result = predictor.predict(audio)
    result["rms_energy"] = round(rms, 5)
    print(
        f"[predict] emotion={result['emotion']} smoothed={result['smoothed']} "
        f"state={result['driver_state']} conf={result['confidence']:.1f} "
        f"risk={result['risk_level']} rms={rms:.5f} stable={result['is_stable']}"
    )
    _DEBUG_LOG.append({
        "timestamp": datetime.utcnow().isoformat(),
        "emotion": result["emotion"],
        "smoothed": result["smoothed"],
        "driver_state": result["driver_state"],
        "confidence": result["confidence"],
        "rms_energy": result["rms_energy"],
        "is_stable": result["is_stable"],
    })
    return result


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

REQUEST_COUNT   = Counter("driver_safety_requests_total", "Total analysis requests", ["state"])
REQUEST_LATENCY = Histogram("driver_safety_request_duration_seconds", "Analysis latency")
ERROR_COUNT     = Counter("driver_safety_errors_total", "Total errors")

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_FILE = Path("logs/predictions.csv")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
if not LOG_FILE.exists():
    LOG_FILE.write_text("timestamp,state,confidence,safety_score,latency_ms\n")


def log_prediction(state: str, confidence: float, safety_score: int, latency_ms: float):
    with open(LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.utcnow().isoformat(),
            state,
            round(confidence, 2),
            safety_score,
            round(latency_ms, 1),
        ])


# ---------------------------------------------------------------------------
# Middleware — request timing
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = str(round((time.time() - start) * 1000, 1))
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "model_ready": predictor.is_ready}


@app.get("/model/info")
def model_info():
    return {
        "meta": predictor.meta,
        "configured_states": OBSERVED_EMOTIONS,
        "trained_states": predictor.meta.get("emotions", []),
        "ready": predictor.is_ready,
        "features": "MFCC(40) + ΔMFCC(40) + Δ²MFCC(40) + Chroma(12) + Mel(128) + ZCR(1) + RMS(1) + SpectralCentroid(1)",
    }


@app.post("/model/reload")
def reload_model():
    try:
        predictor.reload()
        return {"status": "reloaded", "ready": predictor.is_ready, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/voice", response_model=DriverStateResponse)
async def analyze_voice(file: UploadFile = File(...)):
    """Single-shot analysis of a longer (e.g. ~30s) voice clip."""
    t0 = time.time()
    try:
        audio_bytes = await file.read()
        analysis = _analyze(audio_bytes)
    except ModelNotTrainedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Voice analysis error: {e}")
        raise HTTPException(status_code=422, detail=f"Could not process audio: {e}")

    latency_ms = (time.time() - t0) * 1000
    REQUEST_COUNT.labels(state=analysis["driver_state"]).inc()
    REQUEST_LATENCY.observe(latency_ms / 1000)
    log_prediction(analysis["driver_state"], analysis["confidence"], analysis["safety_score"], latency_ms)

    return DriverStateResponse(**analysis, latency_ms=round(latency_ms, 1))


@app.post("/analyze/stream", response_model=DriverStateResponse)
async def analyze_stream(file: UploadFile = File(...)):
    """Single-shot analysis of a short (~3s) chunk, with no session attached."""
    t0 = time.time()
    try:
        audio_bytes = await file.read()
        analysis = _analyze(audio_bytes)
    except ModelNotTrainedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Stream analysis error: {e}")
        raise HTTPException(status_code=422, detail=f"Could not process audio: {e}")

    latency_ms = (time.time() - t0) * 1000
    REQUEST_COUNT.labels(state=analysis["driver_state"]).inc()
    REQUEST_LATENCY.observe(latency_ms / 1000)

    return DriverStateResponse(**analysis, latency_ms=round(latency_ms, 1))


@app.get("/predict/debug")
def predict_debug():
    """Last 10 predictions + feature-extraction stats, for troubleshooting."""
    return {
        "last_predictions": list(_DEBUG_LOG),
        "feature_shapes": [s["shape"] for s in LAST_FEATURE_STATS],
        "feature_stats": list(LAST_FEATURE_STATS),
    }


@app.get("/session/start", response_model=SessionStartResponse)
def session_start():
    # Fresh session → fresh smoothing window and calibration baseline, so
    # one driver's leftovers never bleed into the next session.
    predictor.reset_session_state()
    return session_store.create_session()


@app.post("/session/{session_id}/chunk", response_model=DriverStateResponse)
async def session_chunk(session_id: str, file: UploadFile = File(...)):
    """Analyze a ~3s chunk and append the result to the session's timeline."""
    t0 = time.time()
    try:
        audio_bytes = await file.read()
        analysis = _analyze(audio_bytes)
    except ModelNotTrainedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Session chunk analysis error: {e}")
        raise HTTPException(status_code=422, detail=f"Could not process audio: {e}")

    latency_ms = (time.time() - t0) * 1000
    timestamp = datetime.utcnow().isoformat()

    try:
        session_store.add_chunk(session_id, {
            "timestamp": timestamp,
            "state": analysis["driver_state"],
            "confidence": analysis["confidence"],
            "safety_score": analysis["safety_score"],
            "alert_triggered": analysis["alert_triggered"],
        })
        session_store.add_prediction(session_id, {
            "timestamp": timestamp,
            "raw_emotion": analysis["emotion"],
            "smoothed_state": analysis["smoothed"],
            "confidence": analysis["confidence"],
            "safety_score": analysis["safety_score"],
            "rms_energy": analysis["rms_energy"],
            "is_stable": analysis["is_stable"],
        })
    except session_store.SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown session_id '{session_id}'. Call GET /session/start first.",
        )

    REQUEST_COUNT.labels(state=analysis["driver_state"]).inc()
    REQUEST_LATENCY.observe(latency_ms / 1000)

    return DriverStateResponse(**analysis, latency_ms=round(latency_ms, 1))


@app.get("/session/{session_id}/stats")
def session_stats(session_id: str):
    """Prediction-quality stats: how certain and stable this session's chunks were."""
    try:
        return session_store.get_accuracy_stats(session_id)
    except session_store.SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown session_id '{session_id}'.")


@app.get("/session/{session_id}/report", response_model=SessionReport)
def session_report(session_id: str):
    try:
        return session_store.build_report(session_id)
    except session_store.SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown session_id '{session_id}'.")


@app.post("/report/pdf")
def report_pdf(body: PdfReportRequest):
    try:
        report = session_store.build_report(body.session_id)
    except session_store.SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown session_id '{body.session_id}'.")

    pdf_bytes = generate_session_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="driver_safety_report_{body.session_id[:8]}.pdf"',
        },
    )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Serve the built frontend (combined Docker/Space deployment) — registered
# last so it never shadows the API routes above. No-op for local dev, where
# frontend/dist doesn't exist (Vite's own dev server serves the frontend).
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
