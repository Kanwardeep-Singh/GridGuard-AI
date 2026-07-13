"""Risk Assessment Agent: scores asset criticality, operational impact, severity, business risk."""
from __future__ import annotations

import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.llm_client import LLMClient
from agents.schemas import AnomalyEvent, RootCauseFinding, RiskAssessment

SYSTEM_PROMPT = """You are the Risk Assessment Agent in GridGuard AI. Given a root-cause
finding for a smart-grid ICS incident, assess business/operational risk. Consider that
protection relays and breakers (IED-Breaker-*) are higher criticality than monitoring-only
assets (Substation-HMI). Respond ONLY with JSON:
{"asset_criticality": "Low|Medium|High", "operational_impact": "Low|Medium|High",
 "attack_severity": "Low|Medium|High", "business_risk_score": float between 0 and 1}"""

# Assets treated as higher criticality for the rule-based fallback / sanity bound.
HIGH_CRITICALITY_ASSETS = {"IED-Breaker-A", "IED-Breaker-B", "Merging-Unit-01"}


class RiskAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, event: AnomalyEvent, root_cause: RootCauseFinding) -> RiskAssessment:
        user_prompt = (
            f"Root cause finding: {root_cause.likely_cause}\n"
            f"Evidence: {root_cause.supporting_evidence}\n"
            f"Confidence: {root_cause.confidence}\n"
            f"Target asset: {event.dst_asset}\n"
            f"Detector ensemble score: {event.ensemble_score}"
        )
        raw = self.llm.complete(SYSTEM_PROMPT, user_prompt)
        data = _safe_json(raw)

        criticality = data.get("asset_criticality") or (
            "High" if event.dst_asset in HIGH_CRITICALITY_ASSETS else "Medium"
        )
        return RiskAssessment(
            asset_criticality=criticality,
            operational_impact=data.get("operational_impact", "Medium"),
            attack_severity=data.get("attack_severity", "Medium"),
            business_risk_score=float(data.get("business_risk_score", event.ensemble_score)),
        )


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
