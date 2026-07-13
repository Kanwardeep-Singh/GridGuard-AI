import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import os
os.environ["LLM_PROVIDER"] = "mock"

from fastapi.testclient import TestClient

from api.app import app


def test_health_endpoint():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_detect_endpoint():
    with TestClient(app) as client:
        payload = {
            "records": [
                {
                    "timestamp": "2026-01-01T00:00:00",
                    "packet_size": 70, "inter_arrival_ms": 3, "request_rate": 85,
                    "latency_ms": 55, "jitter_ms": 2, "duplicate_ratio": 0.05,
                    "value_deviation": 0.1, "mms_service": "Read",
                    "src_asset": "RTU-01", "dst_asset": "NAN-Gateway",
                },
            ]
        }
        resp = client.post("/detect", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert len(body["results"]) == 1


def test_investigate_endpoint():
    with TestClient(app) as client:
        payload = {
            "timestamp": "2026-01-01T00:00:21",
            "src_asset": "RTU-02",
            "dst_asset": "IED-Breaker-A",
            "mms_service": "Read",
            "ensemble_score": 0.9,
            "raw_features": {"request_rate": 85},
        }
        resp = client.post("/incidents/investigate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "report" in body
        assert body["report"]["severity"] in {"Low", "Medium", "High"}
