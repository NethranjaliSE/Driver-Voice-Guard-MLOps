---
title: Driver Safety Monitor
emoji: 🚗
colorFrom: red
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Voice-based emotion-aware driver monitoring dashboard (research prototype).
---

# Driver Safety Monitor

A speech-emotion-recognition system turned into a live driver-safety
dashboard. It listens to the driver's voice, classifies the emotion in
each 3-second chunk across **all 8 RAVDESS emotions**, maps that emotion
to a **driver behavior profile** (state, safety score, risk level,
suggestion, smart-car actions), and streams the result to a real-time
React dashboard.

**This is a research prototype, not a certified safety device.** It must
not be the sole signal for any real driving-safety decision. See
[Evaluation & limitations](#evaluation--limitations).

## Problem statement

Driver emotional state is a major road-safety factor — anger, panic, and
low mood measurably degrade reaction time and decision quality — yet most
Driver Monitoring Systems (DMS) rely on cameras (eye closure, head pose)
that fail with sunglasses, low light, or a covered lens, and that cannot
see *emotion* at all. Voice is a cheap, retrofit-friendly signal that
carries emotional information. This project explores whether real-time
voice emotion recognition can power useful, actionable driver feedback:
detect the driver's emotional state every few seconds, quantify the risk,
and suggest concrete in-car interventions (music, AC, breathing exercise,
break reminders) matched to that state.

## Who it's for (users)

- **Researchers / students** exploring speech emotion recognition (SER)
  applied to driver monitoring.
- **Fleet-safety and automotive prototypers** evaluating voice as a
  complement to camera-based DMS.
- **Hobbyists** who want a complete, end-to-end ML project: dataset →
  features → model → API → live frontend → deployment.

It is **not** production-ready for use in a real vehicle.

## How it works (method)

1. **Audio capture** — the browser records the driver's voice; the live
   monitor sends a self-contained 3-second WebM chunk to the API every 3
   seconds (a one-shot *Voice check* mode accepts uploads or single
   recordings).
2. **Silence gate** — each chunk's RMS energy is measured first; chunks
   below the threshold never reach the model and return a "calibrating"
   response instead of a hallucinated emotion.
3. **Feature extraction (263-dim)** — MFCC (40) + ΔMFCC (40) + Δ²MFCC
   (40) + Chroma (12) + Mel spectrogram (128) + Zero-Crossing Rate + RMS
   + Spectral Centroid, extracted with librosa. NaN/Inf values are
   zeroed defensively.
4. **Classification** — a scikit-learn `Pipeline(StandardScaler →
   MLPClassifier)` predicts one of the 8 raw RAVDESS emotions with
   per-class probabilities.
5. **Stabilisation** — a confidence gate (<60% → "calibrating"), a
   rolling 2-of-3 majority smoother across chunks, and a session baseline
   (first 3 predictions) that slightly boosts confidence when a
   prediction matches the driver's established normal.
6. **Behavior mapping** — the predicted emotion is mapped *after*
   prediction to a full driver behavior profile (`EMOTION_BEHAVIOR` in
   `src/predict.py`): driver state, safety score, risk level, headline,
   description, suggestion, and smart-car actions.
7. **Dashboard** — safety-score gauge, behavior card with all 8 emotion
   probability bars, risk badge, 60-second timeline, alert feed,
   playback of the exact audio chunks that were analysed, and clickable
   (simulated) car-action suggestions. Three consecutive DANGER readings
   trigger a full-screen "pull over" warning.

### Emotion → driver behavior mapping

| Emotion | Driver state | Safety score | Risk | Example actions |
|---|---|---|---|---|
| calm | relaxed | 100 | SAFE | ambient music |
| neutral | focused | 95 | SAFE | — |
| happy | energetic | 82 | SAFE | upbeat music, cruise-control reminder |
| surprised | startled | 68 | CAUTION | following-distance alert |
| sad | low_mood | 55 | CAUTION | soft music, AC 23°C, silence notifications |
| disgust | uncomfortable | 52 | CAUTION | adjust AC, fresh air, silence notifications |
| angry | agitated | 28 | DANGER | calm music, AC 20°C, breathing exercise |
| fearful | anxious | 22 | DANGER | calming music, breathing exercise, hazard-lights reminder |

## Dataset

[RAVDESS](https://zenodo.org/record/1188976) — the Ryerson Audio-Visual
Database of Emotional Speech and Song (speech subset): **1,440 WAV
clips, 24 professional actors** (12 female, 12 male), 8 emotions.
Every file is used — nothing is discarded:

| Emotion | Files |
|---|---|
| neutral | 96 *(recorded at one intensity only)* |
| calm, happy, sad, angry, fearful, disgust, surprised | 192 each |

Training applies **audio augmentation** (Gaussian noise, pitch shift,
time stretch) for 4× the data — 5,760 training samples. RAVDESS is
*acted* emotional speech recorded in a studio, not real driving audio —
the single biggest limitation of this project.

## Models

| Model | Classes | Features | Accuracy | Status |
|---|---|---|---|---|
| `ser_model.pkl` (original SER) | calm / happy / fearful / disgust | 180 | — | legacy, unused |
| 3-class grouped driver model | alert / stressed / angry | 263 | ~79–90% | superseded |
| **`driver_model.pkl` (current)** | **all 8 RAVDESS emotions** | **263** | **65%** | **deployed** |

The earlier approach grouped acoustically dissimilar emotions into shared
driver states *before* training (e.g. happy + calm + neutral → "alert"),
which caused systematic misclassification. The current model trains on
the 8 raw emotions directly — no information loss — and does the
driver-state mapping *after* prediction, where it is transparent and
adjustable without retraining.

Architecture: `Pipeline(StandardScaler, MLPClassifier(hidden=(300,),
alpha=0.01, batch_size=256, max_iter=500, adaptive LR))`, tracked with
MLflow (params, per-class metrics, model registry).

## Evaluation

Held-out test split (25% of the augmented dataset, n=1,440):

```
              precision    recall  f1-score   support

       angry       0.77      0.78      0.77       192
        calm       0.70      0.75      0.72       192
     disgust       0.65      0.62      0.63       192
     fearful       0.61      0.62      0.62       192
       happy       0.61      0.61      0.61       192
     neutral       0.58      0.55      0.57        96
         sad       0.58      0.57      0.57       192
   surprised       0.65      0.64      0.65       192

    accuracy                           0.65      1440
   macro avg       0.64      0.64      0.64      1440
weighted avg       0.65      0.65      0.65      1440
```

**Reading these numbers:** 65% accuracy on 8-way classification is ~5×
the 12.5% chance baseline, and the highest-risk emotions detect best
(angry F1 0.77, the top class). The runtime stack adds robustness the
raw model doesn't have: silence gating, a <60% confidence gate, and
rolling-majority smoothing across chunks.

### Limitations

- Trained on **acted studio speech** — accuracy on real in-car audio
  (road noise, passengers, phone calls) will be lower and is unmeasured.
- The emotion → behavior mapping (scores, risk levels) is designed, not
  empirically calibrated against driving outcomes.
- No "drowsy" class — RAVDESS contains no drowsy speech. Add labelled
  clips under `data/raw_extra/<class>/*.wav` to extend (see
  `src/train.py` docstring).
- MLP confidences are overconfident (often near 100%); treat them as
  rankings, not probabilities.

## Tech stack

| Layer | Technology |
|---|---|
| ML / audio | Python 3.11, scikit-learn (MLPClassifier + StandardScaler), librosa, soundfile, NumPy, ffmpeg (WebM/OGG/MP3 decode) |
| Experiment tracking | MLflow (params, metrics, model registry) |
| API | FastAPI, Pydantic v2, Uvicorn, Prometheus metrics, loguru, ReportLab + Matplotlib (PDF reports) |
| Frontend | React 19, Vite, Tailwind CSS 4, framer-motion, Chart.js, react-dropzone, react-hot-toast, lucide-react |
| Deployment | Docker, Hugging Face Spaces (combined image), Hugging Face Hub (model hosting) |
| Testing | pytest (features, API, mapping, smoothing) |

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/analyze/voice` | POST | One-shot analysis of an uploaded/recorded clip |
| `/analyze/stream` | POST | One-shot analysis of a short chunk, no session |
| `/session/start` | GET | Start a monitoring session (resets smoothing + baseline) |
| `/session/{id}/chunk` | POST | Analyze a chunk and append it to the session timeline |
| `/session/{id}/report` | GET | Aggregate session report |
| `/session/{id}/stats` | GET | Prediction-quality stats (confidence, stability, distribution) |
| `/report/pdf` | POST | Session report as a downloadable PDF |
| `/predict/debug` | GET | Last 10 predictions + feature stats, for troubleshooting |
| `/model/info`, `/model/reload` | GET / POST | Model metadata, hot-reload after retraining |
| `/health`, `/metrics` | GET | Health check, Prometheus metrics |

Sessions are stored **in-memory** (`api/session_store.py`) — they don't
survive a restart and won't work with multiple uvicorn workers.

## Run locally

```bash
pip install -r requirements.txt
python src/train.py --data-path data/raw              # trains models/driver_model.pkl
uvicorn api.main:app --reload --port 8000             # backend
cd frontend && npm install && npm run dev             # frontend, separate terminal
```

Open the Vite dev server URL (usually http://localhost:5173). WebM
decoding for live monitoring needs **ffmpeg** on the PATH (`winget
install Gyan.FFmpeg` on Windows). Copy `.env.example` to `.env` to serve
the model from the Hugging Face Hub instead of the local file — not
required for local dev.

## Deploy to a Hugging Face Space

```bash
python scripts/push_model_to_hub.py   # uploads models/driver_model.pkl to the Hub
python scripts/deploy_space.py        # creates/updates the Space, wires HF_MODEL_REPO
```

Both need `HF_TOKEN` (write scope) in your environment.

## Architecture

- `src/` — feature extraction (`features.py`), training with MLflow
  (`train.py`), inference + behavior mapping (`predict.py`)
- `api/` — FastAPI backend (`main.py`, `session_store.py`, `report.py`,
  `schemas.py`)
- `frontend/` — React + Vite dashboard (live monitor, voice check,
  monitored-audio playback, smart-car suggestions)
- `tests/` — pytest suite for features, API endpoints, behavior mapping,
  and smoothing
- `docker-compose.yml` / `Dockerfile.space` — local API + MLflow, and
  the combined frontend+backend image used by Hugging Face Spaces
