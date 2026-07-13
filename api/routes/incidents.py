"""Routes for running the full multi-agent investigation on a flagged anomaly."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Request

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from api.models import InvestigateRequest, InvestigateResponse
from agents.schemas import AnomalyEvent
from automation.power_automate_webhook import send_incident_alert

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/investigate", response_model=InvestigateResponse)
def investigate(payload: InvestigateRequest, request: Request) -> InvestigateResponse:
    orchestrator = request.app.state.orchestrator

    event = AnomalyEvent(
        timestamp=payload.timestamp,
        src_asset=payload.src_asset,
        dst_asset=payload.dst_asset,
        mms_service=payload.mms_service,
        ensemble_score=payload.ensemble_score,
        if_is_anomaly=payload.if_is_anomaly,
        lof_is_anomaly=payload.lof_is_anomaly,
        raw_features=payload.raw_features,
    )
    report = orchestrator.run(event)
    result = send_incident_alert(report)

    return InvestigateResponse(report=report, notified=result["sent"])
