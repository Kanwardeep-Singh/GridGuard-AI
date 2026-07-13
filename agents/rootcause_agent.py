"""Root Cause Agent: investigates likely causes of the flagged anomaly."""
from __future__ import annotations

import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.llm_client import LLMClient
from agents.schemas import AnomalyEvent, DetectionFinding, RootCauseFinding, KnowledgeContext

SYSTEM_PROMPT = """You are the Root Cause Agent in GridGuard AI. Given a detection finding
and relevant ICS knowledge-base context (NIST ICS guidance, MITRE ATT&CK for ICS techniques),
determine the most likely root cause: a specific attack technique, or a benign operational
explanation (e.g. misconfiguration, maintenance window). Be evidence-based, not speculative.
Respond ONLY with JSON:
{"likely_cause": str, "supporting_evidence": [str, ...], "confidence": float}"""


class RootCauseAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(
        self,
        event: AnomalyEvent,
        detection: DetectionFinding,
        knowledge: KnowledgeContext,
    ) -> RootCauseFinding:
        user_prompt = (
            f"Detection finding: {detection.summary}\n\n"
            f"Anomaly event:\n{event.model_dump_json(indent=2)}\n\n"
            f"Relevant knowledge base context:\n" + "\n".join(f"- {r}" for r in knowledge.references)
        )
        raw = self.llm.complete(SYSTEM_PROMPT, user_prompt)
        data = _safe_json(raw)
        return RootCauseFinding(
            likely_cause=data.get("likely_cause", "Unable to determine root cause from available context."),
            supporting_evidence=data.get("supporting_evidence", []),
            confidence=float(data.get("confidence", 0.5)),
        )


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
