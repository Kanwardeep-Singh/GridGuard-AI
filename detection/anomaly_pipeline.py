"""
End-to-end anomaly detection pipeline: feature engineering -> ensemble of
Isolation Forest + Local Outlier Factor -> unified anomaly verdict.

This is the "Anomaly Detection" box in the README architecture diagram,
feeding the Agent Orchestrator.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from detection.feature_engineering import build_feature_matrix
from detection.isolation_forest import IsolationForestDetector
from detection.lof_detector import LOFDetector
from config.settings import settings


class AnomalyPipeline:
    def __init__(self, cfg: dict | None = None):
        cfg = cfg or settings.cfg["detection"]
        self.if_detector = IsolationForestDetector(**cfg["isolation_forest"])
        self.lof_detector = LOFDetector(**cfg["lof"])
        self.strategy = cfg["ensemble"]["strategy"]
        self.threshold = cfg["ensemble"]["score_threshold"]
        self._feature_columns: list[str] | None = None

    def fit(self, df: pd.DataFrame) -> "AnomalyPipeline":
        X, _ = build_feature_matrix(df)
        self._feature_columns = list(X.columns)
        self.if_detector.fit(X)
        self.lof_detector.fit(X)
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        X, meta = build_feature_matrix(df)
        X = self._align_columns(X)

        if_out = self.if_detector.predict(X)
        lof_out = self.lof_detector.predict(X)

        result = pd.concat([meta.reset_index(drop=True), if_out.reset_index(drop=True),
                             lof_out.reset_index(drop=True)], axis=1)

        result["ensemble_score"] = (result["if_score"] + result["lof_score"]) / 2

        if self.strategy == "union":
            result["is_anomaly"] = result["if_is_anomaly"] | result["lof_is_anomaly"]
        else:  # intersection
            result["is_anomaly"] = result["if_is_anomaly"] & result["lof_is_anomaly"]

        # score threshold can additionally elevate borderline cases
        result["is_anomaly"] = result["is_anomaly"] | (result["ensemble_score"] >= self.threshold)
        return result

    def _align_columns(self, X: pd.DataFrame) -> pd.DataFrame:
        """Ensure inference-time features match training-time columns (handles unseen categories)."""
        if self._feature_columns is None:
            return X
        for col in self._feature_columns:
            if col not in X.columns:
                X[col] = 0
        return X[self._feature_columns]

    def save(self, path: str) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "AnomalyPipeline":
        return joblib.load(path)


if __name__ == "__main__":
    from data.generate_synthetic_data import generate_dataset

    df = generate_dataset(n_rows=2000)
    train_df = df.sample(frac=0.7, random_state=1)
    test_df = df.drop(train_df.index)

    pipeline = AnomalyPipeline().fit(train_df)
    results = pipeline.predict(test_df)

    print(results[["timestamp", "attack_type", "ensemble_score", "is_anomaly"]].head(10))
    print("\nDetected anomaly rate:", results["is_anomaly"].mean())
    print("True attack rate:", (results["attack_type"] != "None").mean())
