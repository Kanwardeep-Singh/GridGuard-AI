"""Routes for running anomaly detection on submitted traffic records."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from api.models import DetectRequest, DetectResponse, DetectResponseItem

router = APIRouter(prefix="/detect", tags=["detection"])


@router.post("", response_model=DetectResponse)
def detect(payload: DetectRequest, request: Request) -> DetectResponse:
    pipeline = request.app.state.anomaly_pipeline

    df = pd.DataFrame([r.model_dump() for r in payload.records])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    results = pipeline.predict(df)

    items = [
        DetectResponseItem(
            timestamp=str(row["timestamp"]),
            is_anomaly=bool(row["is_anomaly"]),
            ensemble_score=float(row["ensemble_score"]),
        )
        for _, row in results.iterrows()
    ]
    return DetectResponse(results=items, anomaly_count=sum(i.is_anomaly for i in items))
