"""Response Agent: generates remediation actions and incident response recommendations."""
from __future__ import annotations

import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.llm_client import LLMClient
from agents.schemas import RootCauseFinding, RiskAssessment, ResponsePlan

SYSTEM_PROMPT = """You are the Response Agent in GridGuard AI. Given a root-cause finding
and risk assessment for a smart-grid ICS incident, generate 2-5 concrete, prioritized
remediation actions a control-room operator or SOC analyst could execute immediately.
Be specific to ICS operations (not generic IT security advice). Respond ONLY with JSON:
{"recommended_actions": [str, ...]}"""


class ResponseAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, root_cause: RootCauseFinding, risk: RiskAssessment) -> ResponsePlan:
        user_prompt = (
            f"Root cause: {root_cause.likely_cause}\n"
            f"Risk: criticality={risk.asset_criticality}, impact={risk.operational_impact}, "
            f"severity={risk.attack_severity}, business_risk_score={risk.business_risk_score}"
        )
        raw = self.llm.complete(SYSTEM_PROMPT, user_prompt)
        data = _safe_json(raw)
        actions = data.get("recommended_actions") or [
            "Escalate to on-call ICS security engineer for manual review."
        ]
        return ResponsePlan(recommended_actions=actions)


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
