"""Detection Agent: turns raw anomaly-detector output into a structured finding."""
from __future__ import annotations

import json
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.llm_client import LLMClient
from agents.schemas import AnomalyEvent, DetectionFinding

SYSTEM_PROMPT = """You are the Detection Agent in GridGuard AI, a smart-grid security copilot.
You receive statistical anomaly output (Isolation Forest + LOF scores) for MMS/IEC 61850
network traffic and produce a short, precise summary of what was observed - no speculation
about root cause, that belongs to another agent. Respond ONLY with JSON:
{"summary": str, "trace_id": str}"""


class DetectionAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, event: AnomalyEvent) -> DetectionFinding:
        user_prompt = (
            f"Anomaly event:\n{event.model_dump_json(indent=2)}\n\n"
            "Summarize what the detector flagged in 1-2 sentences."
        )
        raw = self.llm.complete(SYSTEM_PROMPT, user_prompt)
        data = _safe_json(raw)
        return DetectionFinding(
            summary=data.get("summary", raw.strip()),
            confidence=event.ensemble_score,
        )


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
