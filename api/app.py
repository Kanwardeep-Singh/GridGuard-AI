"""
GridGuard AI - FastAPI application.

Run locally:
    uvicorn api.app:app --reload --port 8000

Then see interactive docs at http://localhost:8000/docs
"""
from __future__ import annotations

import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI

from api.routes import detect, incidents
from detection.anomaly_pipeline import AnomalyPipeline
from data.generate_synthetic_data import generate_dataset
from agents.orchestrator import Orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Train the anomaly pipeline on synthetic data at startup so the API is
    # usable out of the box. In production, load a pipeline persisted via
    # AnomalyPipeline.save() from a real-traffic training run instead.
    train_df = generate_dataset(n_rows=3000)
    app.state.anomaly_pipeline = AnomalyPipeline().fit(train_df)
    app.state.orchestrator = Orchestrator()
    yield


app = FastAPI(
    title="GridGuard AI",
    description="Multi-agent smart grid security copilot - anomaly detection + LLM agent investigation.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(detect.router)
app.include_router(incidents.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
