"""
Agent Orchestrator: wires Detection -> ICS Knowledge -> Root Cause -> Risk -> Response
into a LangGraph state graph, matching the README architecture diagram.

Each node is a thin adapter around the corresponding agent class so the
agents themselves stay framework-independent and unit-testable without
LangGraph in the loop.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))

from langgraph.graph import StateGraph, END

from agents.llm_client import get_llm_client, LLMClient
from agents.schemas import (
    AnomalyEvent, DetectionFinding, RootCauseFinding, KnowledgeContext,
    RiskAssessment, ResponsePlan, IncidentReport,
)
from agents.detection_agent import DetectionAgent
from agents.rootcause_agent import RootCauseAgent
from agents.icsknowledge_agent import ICSKnowledgeAgent
from agents.risk_agent import RiskAgent
from agents.response_agent import ResponseAgent
from config.settings import settings


class GraphState(TypedDict, total=False):
    event: AnomalyEvent
    detection: DetectionFinding
    knowledge: KnowledgeContext
    root_cause: RootCauseFinding
    risk: RiskAssessment
    response: ResponsePlan
    report: IncidentReport


IMPACT_BY_SEVERITY = {
    "Low": "Minimal - no operational disruption expected",
    "Medium": "Possible degraded monitoring/control visibility",
    "High": "Communication disruption / potential loss of protective function",
}


class Orchestrator:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or get_llm_client()
        self.detection_agent = DetectionAgent(self.llm)
        self.knowledge_agent = ICSKnowledgeAgent()
        self.rootcause_agent = RootCauseAgent(self.llm)
        self.risk_agent = RiskAgent(self.llm)
        self.response_agent = ResponseAgent(self.llm)
        self.graph = self._build_graph()

    def _build_graph(self):
        g = StateGraph(GraphState)

        g.add_node("detect", self._detect_node)
        g.add_node("retrieve_knowledge", self._knowledge_node)
        g.add_node("root_cause", self._rootcause_node)
        g.add_node("risk", self._risk_node)
        g.add_node("response", self._response_node)
        g.add_node("compile_report", self._compile_report_node)

        g.set_entry_point("detect")
        g.add_edge("detect", "retrieve_knowledge")
        g.add_edge("retrieve_knowledge", "root_cause")
        g.add_edge("root_cause", "risk")
        g.add_edge("risk", "response")
        g.add_edge("response", "compile_report")
        g.add_edge("compile_report", END)

        return g.compile()

    # --- nodes -----------------------------------------------------------
    def _detect_node(self, state: GraphState) -> GraphState:
        finding = self.detection_agent.run(state["event"])
        return {"detection": finding}

    def _knowledge_node(self, state: GraphState) -> GraphState:
        context = self.knowledge_agent.run(state["event"])
        return {"knowledge": context}

    def _rootcause_node(self, state: GraphState) -> GraphState:
        finding = self.rootcause_agent.run(state["event"], state["detection"], state["knowledge"])
        return {"root_cause": finding}

    def _risk_node(self, state: GraphState) -> GraphState:
        risk = self.risk_agent.run(state["event"], state["root_cause"])
        return {"risk": risk}

    def _response_node(self, state: GraphState) -> GraphState:
        plan = self.response_agent.run(state["root_cause"], state["risk"])
        return {"response": plan}

    def _compile_report_node(self, state: GraphState) -> GraphState:
        event, risk, root_cause, response, knowledge = (
            state["event"], state["risk"], state["root_cause"], state["response"], state["knowledge"]
        )
        attack_type = _infer_attack_type(root_cause.likely_cause)
        report = IncidentReport(
            attack_type=attack_type,
            target=event.dst_asset,
            severity=risk.attack_severity,
            confidence=root_cause.confidence,
            impact=IMPACT_BY_SEVERITY.get(risk.attack_severity, "Unknown"),
            recommended_actions=response.recommended_actions,
            root_cause=root_cause.likely_cause,
            knowledge_references=knowledge.references,
        )
        return {"report": report}

    # --- public API --------------------------------------------------------
    def run(self, event: AnomalyEvent) -> IncidentReport:
        final_state = self.graph.invoke({"event": event})
        return final_state["report"]


def _infer_attack_type(text: str) -> str:
    text_lower = text.lower()
    for label, keywords in {
        "Denial of Service": ["dos", "denial of service", "flood"],
        "Man-in-the-Middle": ["mitm", "man-in-the-middle", "man in the middle"],
        "False Data Injection": ["fdi", "false data injection", "spoof"],
        "Replay": ["replay", "duplicate"],
    }.items():
        if any(k in text_lower for k in keywords):
            return label
    return "Unknown"


if __name__ == "__main__":
    from agents.schemas import AnomalyEvent

    event = AnomalyEvent(
        timestamp="2026-01-01T00:00:21",
        src_asset="RTU-02",
        dst_asset="NAN-Gateway",
        mms_service="Read",
        ensemble_score=0.87,
        if_is_anomaly=True,
        lof_is_anomaly=True,
        raw_features={"request_rate": 82, "packet_size": 68},
    )
    orchestrator = Orchestrator()
    report = orchestrator.run(event)
    print(report.model_dump_json(indent=2))
