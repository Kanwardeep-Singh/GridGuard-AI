"""
Feature engineering for MMS/IEC 61850 traffic.

Turns raw per-packet/per-transaction records into the numeric feature
matrix consumed by the anomaly detection models. Mirrors the thesis
approach of combining temporal features (inter-arrival timing, jitter)
with network-level features (packet size, request rate, service type).
"""
from __future__ import annotations

import pandas as pd
import numpy as np

NUMERIC_FEATURES = [
    "packet_size",
    "inter_arrival_ms",
    "request_rate",
    "latency_ms",
    "jitter_ms",
    "duplicate_ratio",
    "value_deviation",
]

CATEGORICAL_FEATURES = ["mms_service", "src_asset", "dst_asset"]


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling-window features that capture short-term traffic dynamics."""
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["rolling_request_rate_mean"] = (
        df["request_rate"].rolling(window=10, min_periods=1).mean()
    )
    df["rolling_latency_std"] = (
        df["latency_ms"].rolling(window=10, min_periods=1).std().fillna(0)
    )
    df["packet_size_zscore"] = (
        (df["packet_size"] - df["packet_size"].mean()) / (df["packet_size"].std() + 1e-6)
    )
    return df


def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode categorical protocol fields."""
    return pd.get_dummies(df, columns=CATEGORICAL_FEATURES, prefix=CATEGORICAL_FEATURES)


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Full feature pipeline.

    Returns:
        X: feature matrix (numeric, model-ready)
        meta: non-feature columns (timestamp, label, attack_type) kept
              alongside for evaluation/reporting, aligned by index.
    """
    df = add_temporal_features(df)
    meta_cols = [c for c in ["timestamp", "label", "attack_type"] if c in df.columns]
    meta = df[meta_cols].copy()

    engineered = df.drop(columns=meta_cols, errors="ignore")
    encoded = encode_categoricals(engineered)

    # Ensure everything left is numeric.
    X = encoded.select_dtypes(include=[np.number]).fillna(0)
    return X, meta
