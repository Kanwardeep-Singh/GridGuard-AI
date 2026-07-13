"""Local Outlier Factor anomaly detector."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor


class LOFDetector:
    """
    Note: sklearn's LOF only supports novelty=True (predict on new data)
    when explicitly configured, and is fit once on a reference set. We use
    novelty=True so this can score unseen traffic after a training fit,
    matching how it's used in the rest of the pipeline.
    """

    def __init__(self, n_neighbors: int = 20, contamination: float = 0.1):
        self.model = LocalOutlierFactor(
            n_neighbors=n_neighbors,
            contamination=contamination,
            novelty=True,
        )
        self._fitted = False

    def fit(self, X: pd.DataFrame) -> "LOFDetector":
        self.model.fit(X)
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("Call .fit() before .predict()")
        raw_pred = self.model.predict(X)                 # 1 = normal, -1 = anomaly
        raw_score = self.model.decision_function(X)       # higher = more normal

        return pd.DataFrame({
            "lof_is_anomaly": raw_pred == -1,
            "lof_score": _normalize(-raw_score),
        }, index=X.index)


def _normalize(arr: np.ndarray) -> np.ndarray:
    lo, hi = arr.min(), arr.max()
    if hi - lo < 1e-9:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)
