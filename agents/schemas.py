"""Shared data structures passed through the agent pipeline."""
from __future__ import annotations

from typing import Optional, Any
from pydantic import BaseModel, Field


class AnomalyEvent(BaseModel):
    """Input to the agent pipeline: one flagged record from the detection pipeline."""
    timestamp: str
    src_asset: Optional[str] = None
    dst_asset: Optional[str] = None
    mms_service: Optional[str] = None
    ensemble_score: float
    if_is_anomaly: bool
    lof_is_anomaly: bool
    raw_features: dict[str, Any] = Field(default_factory=dict)


class DetectionFinding(BaseModel):
    summary: str
    confidence: float


class RootCauseFinding(BaseModel):
    likely_cause: str
    supporting_evidence: list[str]
    confidence: float


class KnowledgeContext(BaseModel):
    references: list[str]


class RiskAssessment(BaseModel):
    asset_criticality: str
    operational_impact: str
    attack_severity: str
    business_risk_score: float


class ResponsePlan(BaseModel):
    recommended_actions: list[str]


class IncidentReport(BaseModel):
    """Final artifact produced by the orchestrator - matches the README sample."""
    attack_type: str
    protocol: str = "MMS"
    target: Optional[str] = None
    severity: str
    confidence: float
    impact: str
    recommended_actions: list[str]
    root_cause: Optional[str] = None
    knowledge_references: list[str] = Field(default_factory=list)
