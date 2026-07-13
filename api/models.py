"""API request/response models. Reuses agent schemas where possible."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

from agents.schemas import IncidentReport


class TrafficRecord(BaseModel):
    """One row of MMS traffic submitted for detection, matching generate_synthetic_data output."""
    timestamp: str
    packet_size: float
    inter_arrival_ms: float
    request_rate: float
    latency_ms: float
    jitter_ms: float
    duplicate_ratio: float
    value_deviation: float
    mms_service: str
    src_asset: str
    dst_asset: str


class DetectRequest(BaseModel):
    records: list[TrafficRecord]


class DetectResponseItem(BaseModel):
    timestamp: str
    is_anomaly: bool
    ensemble_score: float


class DetectResponse(BaseModel):
    results: list[DetectResponseItem]
    anomaly_count: int


class InvestigateRequest(BaseModel):
    timestamp: str
    src_asset: Optional[str] = None
    dst_asset: Optional[str] = None
    mms_service: Optional[str] = None
    ensemble_score: float
    if_is_anomaly: bool = True
    lof_is_anomaly: bool = True
    raw_features: dict = {}


class InvestigateResponse(BaseModel):
    report: IncidentReport
    notified: bool
