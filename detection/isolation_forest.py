"""Isolation Forest anomaly detector."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class IsolationForestDetector:
    def __init__(self, n_estimators: int = 200, contamination: float = 0.1, random_state: int = 42):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
        )
        self._fitted = False

    def fit(self, X: pd.DataFrame) -> "IsolationForestDetector":
        self.model.fit(X)
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """Returns a DataFrame with is_anomaly (bool) and anomaly_score (higher = more anomalous)."""
        if not self._fitted:
            raise RuntimeError("Call .fit() before .predict()")
        raw_pred = self.model.predict(X)          # 1 = normal, -1 = anomaly
        raw_score = self.model.decision_function(X)  # higher = more normal

        return pd.DataFrame({
            "if_is_anomaly": raw_pred == -1,
            # flip sign + normalize roughly to [0,1] so higher = more anomalous
            "if_score": _normalize(-raw_score),
        }, index=X.index)


def _normalize(arr: np.ndarray) -> np.ndarray:
    lo, hi = arr.min(), arr.max()
    if hi - lo < 1e-9:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)
