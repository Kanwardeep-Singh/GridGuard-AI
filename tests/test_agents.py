import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import os
os.environ["LLM_PROVIDER"] = "mock"

import pytest

from agents.llm_client import get_llm_client, MockClient
from agents.schemas import AnomalyEvent
from agents.detection_agent import DetectionAgent
from agents.rootcause_agent import RootCauseAgent
from agents.icsknowledge_agent import ICSKnowledgeAgent
from agents.risk_agent import RiskAgent
from agents.response_agent import ResponseAgent
from agents.orchestrator import Orchestrator


@pytest.fixture
def sample_event() -> AnomalyEvent:
    return AnomalyEvent(
        timestamp="2026-01-01T00:00:21",
        src_asset="RTU-02",
        dst_asset="IED-Breaker-A",
        mms_service="Read",
        ensemble_score=0.9,
        if_is_anomaly=True,
        lof_is_anomaly=True,
        raw_features={"request_rate": 82, "packet_size": 68},
    )


def test_mock_llm_client_selected_by_default():
    client = get_llm_client("mock")
    assert isinstance(client, MockClient)


def test_detection_agent_produces_summary(sample_event):
    agent = DetectionAgent(get_llm_client("mock"))
    finding = agent.run(sample_event)
    assert finding.summary
    assert 0 <= finding.confidence <= 1


def test_knowledge_agent_returns_references(sample_event):
    agent = ICSKnowledgeAgent()
    context = agent.run(sample_event)
    assert len(context.references) > 0


def test_rootcause_agent_infers_dos_from_high_request_rate(sample_event):
    detection_agent = DetectionAgent(get_llm_client("mock"))
    knowledge_agent = ICSKnowledgeAgent()
    rootcause_agent = RootCauseAgent(get_llm_client("mock"))

    detection = detection_agent.run(sample_event)
    knowledge = knowledge_agent.run(sample_event)
    root_cause = rootcause_agent.run(sample_event, detection, knowledge)

    assert "denial of service" in root_cause.likely_cause.lower()


def test_risk_agent_flags_breaker_as_high_criticality(sample_event):
    rootcause_agent = RootCauseAgent(get_llm_client("mock"))
    knowledge_agent = ICSKnowledgeAgent()
    risk_agent = RiskAgent(get_llm_client("mock"))

    detection = DetectionAgent(get_llm_client("mock")).run(sample_event)
    knowledge = knowledge_agent.run(sample_event)
    root_cause = rootcause_agent.run(sample_event, detection, knowledge)
    risk = risk_agent.run(sample_event, root_cause)

    assert risk.asset_criticality == "High"  # IED-Breaker-A is in HIGH_CRITICALITY_ASSETS


def test_response_agent_returns_actions():
    from agents.schemas import RootCauseFinding, RiskAssessment

    root_cause = RootCauseFinding(likely_cause="DoS", supporting_evidence=[], confidence=0.8)
    risk = RiskAssessment(asset_criticality="High", operational_impact="High",
                           attack_severity="High", business_risk_score=0.9)
    plan = ResponseAgent(get_llm_client("mock")).run(root_cause, risk)
    assert len(plan.recommended_actions) > 0


def test_orchestrator_end_to_end_produces_report(sample_event):
    orchestrator = Orchestrator(llm=get_llm_client("mock"))
    report = orchestrator.run(sample_event)

    assert report.attack_type in {
        "Denial of Service", "Man-in-the-Middle", "False Data Injection", "Replay", "Unknown"
    }
    assert report.severity in {"Low", "Medium", "High"}
    assert 0 <= report.confidence <= 1
    assert len(report.recommended_actions) > 0
