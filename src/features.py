"""
Feature extraction for the Driver Safety Monitor's voice classifier.
Extracts MFCC + delta + delta-delta, Chroma, Mel Spectrogram, Zero-Crossing
Rate, RMS Energy, and Spectral Centroid from audio files.
"""

import numpy as np
import librosa
import soundfile as sf
import io
from collections import deque
from pathlib import Path
from loguru import logger
from typing import Optional

# Rolling record of the most recent feature extractions, surfaced by the
# GET /predict/debug endpoint for troubleshooting bad predictions.
LAST_FEATURE_STATS = deque(maxlen=10)


# Maps RAVDESS filename code → raw emotion name
# Train on all 8 original classes — no grouping, no information loss
RAVDESS_EMOTIONS = {
    "01": "neutral",
    "02": "calm",
    "03": "happy",
    "04": "sad",
    "05": "angry",
    "06": "fearful",
    "07": "disgust",
    "08": "surprised",
}

# All 8 classes used in training
OBSERVED_EMOTIONS = [
    "neutral", "calm", "happy", "sad",
    "angry", "fearful", "disgust", "surprised"
]


def _ensure_ffmpeg_on_path() -> None:
    """
    librosa/audioread shell out to the ffmpeg binary for WebM/OGG/MP3.
    On Windows, a PATH change (e.g. from `winget install`) only applies to
    processes started after the change — a backend launched from a terminal
    opened earlier won't see it no matter how many times ffmpeg is
    reinstalled. Search common install locations and patch this process's
    PATH directly so decoding works regardless of the launching shell's PATH.
    """
    import os
    import glob
    import shutil

    if shutil.which("ffmpeg"):
        return

    candidates = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates += glob.glob(
            os.path.join(
                local_appdata, "Microsoft", "WinGet", "Packages",
                "Gyan.FFmpeg_*", "ffmpeg-*", "bin", "ffmpeg.exe",
            )
        )
    candidates += [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
    ]

    for exe in candidates:
        if os.path.exists(exe):
            ffmpeg_dir = os.path.dirname(exe)
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            logger.info(f"ffmpeg not on PATH — found at {exe}, patched PATH for this process")
            return

    logger.warning(
        "ffmpeg not found on PATH or in common install locations — "
        "WebM/OGG/MP3 decoding will fail until it's installed."
    )


_ensure_ffmpeg_on_path()


def _guess_suffix(raw: bytes) -> str:
    """Guess file extension from magic bytes so ffmpeg picks the right decoder."""
    if raw[:4] == b"RIFF":                              return ".wav"
    if raw[:4] == b"fLaC":                              return ".flac"
    if raw[:4] == b"OggS":                              return ".ogg"
    if raw[:3] == b"ID3" or raw[:2] in (b"\xff\xfb",
                                         b"\xff\xf3",
                                         b"\xff\xf2"): return ".mp3"
    if len(raw) > 8 and raw[4:8] == b"ftyp":           return ".m4a"
    return ".webm"   # browser MediaRecorder default


def _load_audio(source) -> tuple:
    """
    Load audio from a file path, raw bytes, or a pre-loaded (samples, sr)
    tuple → (samples float32, sample_rate).

    Four strategies tried in order — no single dependency required:
      1. soundfile   — fast, handles PCM WAV / FLAC natively (no ffmpeg)
      2. wave module — Python built-in, covers all standard WAV files
      3. librosa     — uses ffmpeg via audioread for WebM / OGG / MP3
      4. Raises RuntimeError with a clear install hint

    Python 3 scoping note:
      Exception variables are deleted after their except block.
      We collect messages in a plain list instead.
    """
    import os, tempfile, wave as wave_module, warnings

    # Already-decoded audio (e.g. an in-memory augmented signal) — no
    # container format to sniff, so skip straight past the encode/decode
    # round trip that raw PCM bytes can't survive (no WAV header to parse).
    if (
        isinstance(source, tuple)
        and len(source) == 2
        and isinstance(source[0], np.ndarray)
    ):
        samples, sr = source
        return samples.astype(np.float32), sr

    errors   = []
    tmp_path = None

    try:
        # ── Materialise bytes as a temp file with the right extension ─────
        if isinstance(source, (bytes, bytearray)):
            raw    = bytes(source)
            suffix = _guess_suffix(raw)
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, "wb") as fh:
                fh.write(raw)
            src = tmp_path
        else:
            src = str(source)

        # ── Strategy 1: soundfile (fast, no ffmpeg, handles WAV/FLAC) ────
        try:
            with sf.SoundFile(src) as f:
                X  = f.read(dtype="float32")
                sr = f.samplerate
            if X.ndim > 1:
                X = X.mean(axis=1)
            logger.debug("soundfile decoded successfully")
            return X.astype(np.float32), sr
        except Exception as e:
            errors.append(f"soundfile  : {e}")
            logger.debug(f"soundfile failed — {e}")

        # ── Strategy 2: Python built-in wave module (WAV only, zero deps) ─
        try:
            with wave_module.open(src, "rb") as wf:
                n_ch   = wf.getnchannels()
                sw     = wf.getsampwidth()
                sr     = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
            dtype_map = {1: np.uint8, 2: np.int16, 4: np.int32}
            dtype = dtype_map.get(sw, np.int16)
            X = np.frombuffer(frames, dtype=dtype).astype(np.float32)
            # Normalise to [-1, 1]
            X /= float(np.iinfo(dtype).max) if sw > 1 else 128.0
            if sw == 1:
                X -= 1.0          # uint8 is 0-255, shift to -1..+1
            if n_ch > 1:
                X = X.reshape(-1, n_ch).mean(axis=1)
            logger.debug("wave module decoded successfully")
            return X, sr
        except Exception as e:
            errors.append(f"wave module: {e}")
            logger.debug(f"wave module failed — {e}")

        # ── Strategy 3: librosa (needs ffmpeg for WebM/OGG/MP3) ──────────
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")   # suppress FutureWarning noise
                X, sr = librosa.load(src, sr=None, mono=True)
            logger.debug("librosa decoded successfully")
            return X.astype(np.float32), sr
        except Exception as e:
            errors.append(f"librosa    : {e}")
            logger.debug(f"librosa failed — {e}")

        # ── All strategies failed ─────────────────────────────────────────
        raise RuntimeError(
            "Could not decode audio.  All strategies failed:\n  " +
            "\n  ".join(errors) +
            "\n\nFor WAV files   → check the file is not corrupted."
            "\nFor browser recordings (WebM/OGG/MP3) → install ffmpeg:"
            "\n  winget install Gyan.FFmpeg          (Windows)"
            "\n  brew install ffmpeg                 (macOS)"
            "\n  sudo apt install ffmpeg             (Linux)"
        )

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def extract_feature(
    source,
    mfcc: bool = True,
    chroma: bool = True,
    mel: bool = True,
    n_mfcc: int = 40,
    pre_emphasis: bool = False,
) -> np.ndarray:
    """
    Extract acoustic features relevant to driver vocal state from a file
    path, raw bytes, or an in-memory (samples, sample_rate) tuple.

    Feature set (263-dim with defaults):
      - MFCC (40)               — timbral/spectral envelope
      - Delta MFCC (40)         — rate of change → speech-rate shifts (drowsy)
      - Delta-delta MFCC (40)   — acceleration of change → slurring (drowsy)
      - Chroma (12)             — pitch-class energy
      - Mel Spectrogram (128)   — perceptual frequency envelope (centroid
                                   shift is a known drowsy-speech cue)
      - Zero Crossing Rate (1)  — separates voiced/yawn-like noisy segments
      - RMS Energy (1)          — volume spikes → anger / stress
      - Spectral Centroid (1)   — brightness; shifts down in drowsy speech

    `pre_emphasis` applies X = append(X[0], X[1:] - 0.97*X[:-1]) before
    extraction. It defaults to OFF because both shipped models
    (driver_model.pkl / ser_model.pkl) were trained on features WITHOUT
    pre-emphasis — enabling it at inference time would feed the model
    out-of-distribution inputs. Only turn it on together with a retrain.

    Returns:
        1-D numpy array of concatenated features.
    """
    X, sample_rate = _load_audio(source)

    # _load_audio already downmixes stereo, but guard against callers that
    # pass a pre-loaded multi-channel (samples, sr) tuple directly.
    if X.ndim > 1:
        X = X.mean(axis=1)

    if pre_emphasis:
        X = np.append(X[0], X[1:] - 0.97 * X[:-1]).astype(np.float32)

    result = np.array([])

    if chroma or mfcc:
        stft = np.abs(librosa.stft(X)) if chroma else None

    if mfcc:
        mfcc_matrix = librosa.feature.mfcc(y=X, sr=sample_rate, n_mfcc=n_mfcc)
        result = np.hstack((result, np.mean(mfcc_matrix.T, axis=0)))

        delta1 = librosa.feature.delta(mfcc_matrix, order=1)
        result = np.hstack((result, np.mean(delta1.T, axis=0)))

        delta2 = librosa.feature.delta(mfcc_matrix, order=2)
        result = np.hstack((result, np.mean(delta2.T, axis=0)))

    if chroma:
        chroma_feat = np.mean(
            librosa.feature.chroma_stft(S=stft, sr=sample_rate).T, axis=0
        )
        result = np.hstack((result, chroma_feat))

    if mel:
        mel_feat = np.mean(
            librosa.feature.melspectrogram(y=X, sr=sample_rate).T, axis=0
        )
        result = np.hstack((result, mel_feat))

    zcr = np.mean(librosa.feature.zero_crossing_rate(X))
    result = np.hstack((result, zcr))

    rms = np.mean(librosa.feature.rms(y=X))
    result = np.hstack((result, rms))

    centroid = np.mean(librosa.feature.spectral_centroid(y=X, sr=sample_rate))
    result = np.hstack((result, centroid))

    # Very short / degenerate chunks can produce NaN or Inf in the averaged
    # features (e.g. all-zero frames in chroma normalisation) — the model
    # then returns garbage with high confidence. Zero them out instead.
    result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)

    print(
        f"[features] shape={result.shape} "
        f"min={result.min():.3f} max={result.max():.3f} "
        f"zeros={(result == 0).sum()} sample={np.round(result[:3], 3)}"
    )
    LAST_FEATURE_STATS.append({
        "shape": list(result.shape),
        "min": float(result.min()),
        "max": float(result.max()),
        "zeros": int((result == 0).sum()),
    })

    return result


def rms_energy(source) -> float:
    """Mean RMS energy of a clip — cheap loudness measure for gating."""
    X, _ = _load_audio(source)
    if X.ndim > 1:
        X = X.mean(axis=1)
    if len(X) == 0:
        return 0.0
    return float(np.mean(librosa.feature.rms(y=X)))


def is_speech(source, threshold: float = 0.01) -> bool:
    """
    True if the clip's RMS energy clears `threshold` — i.e. someone is
    probably speaking. Silence / faint cabin noise stays below it, letting
    the API skip classification instead of hallucinating a confident state
    from an empty chunk.
    """
    return rms_energy(source) > threshold


def augment_audio(y: np.ndarray, sr: int) -> list:
    """
    Return a list of augmented copies of an audio signal.
    Includes original + noise injection, pitch shift, time stretch.
    """
    augmented = [y]

    # Gaussian noise
    noise = y + 0.005 * np.random.randn(len(y))
    augmented.append(noise.astype(np.float32))

    # Pitch shift up
    try:
        shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=2)
        augmented.append(shifted)
    except Exception:
        pass

    # Time stretch (slower)
    try:
        stretched = librosa.effects.time_stretch(y, rate=0.9)
        augmented.append(stretched)
    except Exception:
        pass

    return augmented


def get_emotion_from_filename(file_name: str):
    """
    Parse RAVDESS filename and return the raw emotion label.
    Format: 03-01-05-01-02-01-12.wav
    3rd segment (index 2) = emotion code.
    Returns None if unparseable.
    """
    try:
        code = Path(file_name).stem.split("-")[2]
        return RAVDESS_EMOTIONS.get(code)
    except (IndexError, AttributeError):
        return None
