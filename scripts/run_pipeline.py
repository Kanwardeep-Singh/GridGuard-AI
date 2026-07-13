"""
Convenience script: generate synthetic traffic -> train detector -> flag
anomalies -> run the full agent pipeline on each flagged event -> print
incident reports and (optionally) send alerts.

Run: python scripts/run_pipeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from data.generate_synthetic_data import generate_dataset
from detection.anomaly_pipeline import AnomalyPipeline
from agents.orchestrator import Orchestrator
from agents.schemas import AnomalyEvent
from automation.power_automate_webhook import send_incident_alert


def main(n_events_to_investigate: int = 3) -> None:
    print("Generating synthetic MMS traffic...")
    df = generate_dataset(n_rows=4000)
    train_df = df.sample(frac=0.7, random_state=42)
    test_df = df.drop(train_df.index)

    print("Training anomaly detection pipeline (Isolation Forest + LOF)...")
    pipeline = AnomalyPipeline().fit(train_df)
    results = pipeline.predict(test_df)

    anomalies = results[results["is_anomaly"]].sort_values("ensemble_score", ascending=False)
    print(f"Flagged {len(anomalies)} / {len(results)} records as anomalous.\n")

    orchestrator = Orchestrator()

    for i, row in anomalies.head(n_events_to_investigate).iterrows():
        # ensemble output doesn't carry asset/service labels forward from meta,
        # so pull those back from the original test_df by matching index.
        original = test_df.loc[i] if i in test_df.index else None
        event = AnomalyEvent(
            timestamp=str(row["timestamp"]),
            src_asset=original["src_asset"] if original is not None else None,
            dst_asset=original["dst_asset"] if original is not None else None,
            mms_service=original["mms_service"] if original is not None else None,
            ensemble_score=float(row["ensemble_score"]),
            if_is_anomaly=bool(row["if_is_anomaly"]),
            lof_is_anomaly=bool(row["lof_is_anomaly"]),
            raw_features=original.to_dict() if original is not None else {},
        )

        print(f"--- Investigating anomaly at {event.timestamp} (score={event.ensemble_score:.2f}) ---")
        report = orchestrator.run(event)
        print(report.model_dump_json(indent=2))

        result = send_incident_alert(report)
        print(f"Alert dispatch: {result}\n")


if __name__ == "__main__":
    main()
