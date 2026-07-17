---
title: Driver Safety Monitor
emoji: 🚗
colorFrom: red
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Voice-based drowsiness/stress/anger monitoring dashboard for drivers (research prototype).
---

# Driver Safety Monitor

A live dashboard that listens to a driver's voice while they drive and
estimates their vocal state — **alert**, **drowsy**, **stressed**, or
**angry** — every few seconds, turning that into a 0-100 safety score, a
risk level, and pull-over alerts.

**This is a research prototype, not a certified safety device.** It should
not be relied on as the sole signal for any real driving-safety decision.
See [Accuracy & data notes](#accuracy--data-notes) below — it matters.

## Who it's for

Anyone exploring voice-based driver-monitoring as an alternative or
complement to camera-based Driver Monitoring Systems (DMS) — researchers,
hobbyists, or fleet-safety prototyping. It is **not** ready for production
use in a vehicle.

## How it works

1. Click **Start Monitoring** → the browser opens a session and starts the
   mic.
2. Every 3 seconds, a short audio chunk is sent to the backend, which
   extracts acoustic features and classifies the driver's vocal state.
3. The dashboard updates a safety-score gauge, a 60-second timeline, and an
   alert feed in real time. Three consecutive high-risk readings trigger a
   full-screen "pull over" warning.
4. Click **Stop + Report** for a session summary, or **Export PDF** for a
   downloadable report.

## Run locally

```bash
pip install -r requirements.txt
python src/train.py --data-path data/raw          # produces models/driver_model.pkl
PYTHONPATH=src uvicorn api.main:app --reload --port 8000   # backend
cd frontend && npm install && npm run dev                  # frontend, separate terminal
```

Open the Vite dev server URL (usually http://localhost:5173). Copy
`.env.example` to `.env` if you want the model served from the Hugging Face
Hub instead of a local file (see below) — not required for local dev.

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/analyze/voice` | POST | Single-shot analysis of a longer (~30s) clip |
| `/analyze/stream` | POST | Single-shot analysis of a short (~3s) chunk, no session |
| `/session/start` | GET | Start a monitoring session, returns `session_id` |
| `/session/{id}/chunk` | POST | Analyze a chunk and append it to that session's timeline |
| `/session/{id}/report` | GET | Aggregate report for a session |
| `/report/pdf` | POST | Render a session report as a downloadable PDF |
| `/model/info`, `/model/reload` | GET / POST | Model metadata, hot-reload after retraining |
| `/health`, `/metrics` | GET | Health check, Prometheus metrics |

Sessions are stored **in-memory** (see `api/session_store.py`) — they don't
survive a backend restart, and won't work correctly with multiple uvicorn
workers. Fine for a prototype; swap for Redis/a database for anything more.

## Accuracy & data notes

The classifier is an MLPClassifier on MFCC + Δ/Δ² MFCC + Chroma + Mel +
Zero-Crossing-Rate + RMS + Spectral Centroid features (263-dim), trained on
[RAVDESS](https://zenodo.org/record/1188976) and **relabelled** to
driver-relevant states:

| RAVDESS emotion | Driver state |
|---|---|
| neutral, calm | alert |
| fearful, surprised | stressed |
| angry | angry |
| happy, sad, disgust | *(unused — no driver-safety analogue)* |
| *(none)* | **drowsy — no RAVDESS data exists for this class** |

RAVDESS is **acted** emotional speech, not real driving audio, so this
mapping is a best-effort proxy, not a validated correspondence between
"sounding calm" and "being an alert driver." On the actor data currently in
`data/raw/`, the trained model reaches **~88% held-out accuracy** on the
three classes it actually has data for (alert/angry/stressed) — `drowsy` is
correctly and automatically excluded from training (and from predictions)
until it has real data, rather than being faked.

To add a real `drowsy` class, drop labelled audio under
`data/raw_extra/drowsy/*.wav` (one subfolder per state — see the docstring
in `src/train.py`). The DROZY dataset is sometimes suggested for
drowsiness research, but it's built on EEG/physiological signals and video,
not voice recordings, so it won't directly drop into this folder — you'd
need a dedicated drowsy-speech corpus or self-recorded samples instead.

The safety-score weights (`alert=100, stressed=65, angry=40, drowsy=20`)
and risk thresholds in `api/main.py` are starting points for a prototype,
not empirically calibrated against real driving outcomes.

## Why voice? vs. camera-based DMS

Camera-based Driver Monitoring Systems (eye closure, head pose, gaze) are
the current industry standard and generally more validated. A voice-based
approach is being explored here because it:

- Works with sunglasses, low light, or a camera blocked/turned off.
- Needs only a microphone — cheaper hardware, easier to retrofit.
- Can pick up *emotional* state (anger, stress) that a camera focused on
  eyelids may miss entirely.

The trade-off: voice is more affected by background noise, passengers, and
phone calls, and — as the data notes above make clear — there's far less
mature, labelled audio data for drowsiness specifically than there is video
data. Treat this project as evidence for "worth researching further," not
"ready to replace a camera DMS."

## Deploy to a Hugging Face Space

```bash
python scripts/push_model_to_hub.py   # uploads models/driver_model.pkl to the Hub
python scripts/deploy_space.py        # creates/updates the Space, uploads code, wires HF_MODEL_REPO
```

Both need `HF_TOKEN` (write scope) in your environment. See each script's
`--help` for repo-naming overrides.

## Architecture

- `src/` — feature extraction, training (`train.py`), inference
  (`predict.py` — downloads the model from the Hub if `HF_MODEL_REPO` is
  set, otherwise uses the local `models/driver_model.pkl`)
- `api/` — FastAPI backend (`main.py`, `session_store.py`, `report.py`,
  `schemas.py`)
- `frontend/` — React + Vite dashboard (Tailwind, framer-motion, Chart.js)
- `docker-compose.yml` — local API + MLflow, built from `Dockerfile.space`
- `Dockerfile` — API-only image (no frontend), for deploying the backend
  separately
- `Dockerfile.space` — combined frontend+backend image used by both
  `docker-compose.yml` and Hugging Face Spaces
