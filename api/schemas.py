"""Pydantic request/response schemas for the Driver Safety Monitor API."""

from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class DriverStateResponse(BaseModel):
    state: str = Field(..., example="alert")
    confidence: float = Field(..., ge=0, le=100, example=87.5)
    all_scores: Dict[str, float] = Field(
        ..., example={"alert": 87.5, "drowsy": 2.0, "stressed": 6.5, "angry": 4.0}
    )
    safety_score: int = Field(..., ge=0, le=100, example=92)
    risk_level: str = Field(..., example="SAFE")
    alert_triggered: bool = Field(..., example=False)
    recommendation: str = Field(..., example="You're driving in a focused, alert state.")
    latency_ms: float = Field(..., example=42.3)
    smoothed_state: str = Field("calibrating", example="alert")
    is_stable: bool = Field(False, example=True)
    raw_emotion: Optional[str] = Field(None, example="alert")
    rms_energy: float = Field(0.0, ge=0, example=0.043)


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
