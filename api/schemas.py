"""Pydantic request/response schemas for the Driver Safety Monitor API."""

from typing import List, Optional, Tuple
from pydantic import BaseModel


class DriverStateResponse(BaseModel):
    emotion: str
    smoothed: str
    confidence: float
    safety_score: int
    risk_level: str          # SAFE / CAUTION / DANGER / CALIBRATING
    driver_state: str
    emoji: str
    headline: str
    description: str
    suggestion: str
    car_actions: list[str]
    all_scores: dict[str, float]   # all 8 emotion probabilities
    is_stable: bool
    alert_triggered: bool
    latency_ms: Optional[float] = None
    rms_energy: float = 0.0


class DebugInfo(BaseModel):
    feature_shape: Tuple[int, ...]
    feature_min: float
    feature_max: float
    has_nan: bool
    rms_energy: float
    confidence_raw: float


class SessionStartResponse(BaseModel):
    session_id: str
    started_at: str


class TimelineEntry(BaseModel):
    timestamp: str
    state: str
    confidence: float
    safety_score: int
    alert_triggered: bool


class SessionReport(BaseModel):
    session_id: str
    duration_seconds: int
    timeline: List[TimelineEntry]
    dominant_state: str
    average_safety_score: float
    risk_events: List[TimelineEntry]
    overall_verdict: str


class PdfReportRequest(BaseModel):
    session_id: str
