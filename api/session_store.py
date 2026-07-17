"""
In-memory session timeline store for live driver-monitoring sessions.

Single-process, not persisted — sessions are lost on restart/redeploy or
when running multiple uvicorn workers. That's an intentional simplification
for this prototype; swap for Redis/a database if durability or horizontal
scaling are ever needed.
"""

import uuid
from collections import Counter
from datetime import datetime
from typing import Dict, List


class SessionNotFoundError(KeyError):
    """Raised when a session_id has no matching session (unknown or expired)."""


_sessions: Dict[str, dict] = {}


def _now() -> datetime:
    # Naive UTC, to match the timestamps api/main.py stamps onto each chunk
    # (datetime.utcnow().isoformat()) — mixing naive/aware datetimes raises
    # TypeError on subtraction.
    return datetime.utcnow()


def create_session() -> dict:
    session_id = uuid.uuid4().hex
    started_at = _now()
    _sessions[session_id] = {
        "started_at": started_at,
        "timeline": [],
        "prediction_log": [],
    }
    return {"session_id": session_id, "started_at": started_at.isoformat()}


def add_chunk(session_id: str, entry: dict) -> None:
    session = _sessions.get(session_id)
    if session is None:
        raise SessionNotFoundError(session_id)
    session["timeline"].append(entry)


def add_prediction(session_id: str, entry: dict) -> None:
    """
    Append a raw prediction record for accuracy troubleshooting. Expected
    keys: timestamp, raw_emotion, smoothed_state, confidence, safety_score,
    rms_energy, is_stable.
    """
    session = _sessions.get(session_id)
    if session is None:
        raise SessionNotFoundError(session_id)
    session["prediction_log"].append(entry)


def get_accuracy_stats(session_id: str) -> dict:
    """
    Aggregate quality stats over a session's prediction log — how often the
    system was uncertain ("calibrating"), how stable the rolling predictions
    were, and how the detected states were distributed.
    """
    session = _sessions.get(session_id)
    if session is None:
        raise SessionNotFoundError(session_id)

    log: List[dict] = session["prediction_log"]
    total = len(log)
    if total == 0:
        return {
            "total_chunks": 0,
            "calibrating_chunks": 0,
            "state_distribution": {},
            "average_confidence": 0.0,
            "stable_percentage": 0.0,
        }

    calibrating = sum(1 for e in log if e.get("smoothed_state") == "calibrating")
    distribution = dict(Counter(e.get("smoothed_state", "unknown") for e in log))
    avg_confidence = sum(e.get("confidence", 0.0) for e in log) / total
    stable = sum(1 for e in log if e.get("is_stable"))

    return {
        "total_chunks": total,
        "calibrating_chunks": calibrating,
        "state_distribution": distribution,
        "average_confidence": round(avg_confidence, 1),
        "stable_percentage": round(stable / total * 100, 1),
    }


def build_report(session_id: str) -> dict:
    session = _sessions.get(session_id)
    if session is None:
        raise SessionNotFoundError(session_id)

    timeline: List[dict] = session["timeline"]

    if not timeline:
        return {
            "session_id": session_id,
            "duration_seconds": int((_now() - session["started_at"]).total_seconds()),
            "timeline": [],
            "dominant_state": "unknown",
            "average_safety_score": 0.0,
            "risk_events": [],
            "overall_verdict": "NO DATA",
        }

    last_timestamp = datetime.fromisoformat(timeline[-1]["timestamp"])
    duration_seconds = max(int((last_timestamp - session["started_at"]).total_seconds()), 0)

    states = [entry["state"] for entry in timeline]
    dominant_state = Counter(states).most_common(1)[0][0]

    avg_score = sum(entry["safety_score"] for entry in timeline) / len(timeline)
    risk_events = [entry for entry in timeline if entry["alert_triggered"]]

    if avg_score >= 80:
        overall_verdict = "SAFE TO DRIVE"
    elif avg_score >= 50:
        overall_verdict = "TAKE A BREAK"
    else:
        overall_verdict = "STOP NOW"

    return {
        "session_id": session_id,
        "duration_seconds": duration_seconds,
        "timeline": timeline,
        "dominant_state": dominant_state,
        "average_safety_score": round(avg_score, 1),
        "risk_events": risk_events,
        "overall_verdict": overall_verdict,
    }
