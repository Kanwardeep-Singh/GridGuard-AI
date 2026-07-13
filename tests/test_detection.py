import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd

from data.generate_synthetic_data import generate_dataset, ATTACK_TYPES
from detection.feature_engineering import build_feature_matrix
from detection.anomaly_pipeline import AnomalyPipeline


def test_generate_dataset_shape_and_labels():
    df = generate_dataset(n_rows=500, seed=1)
    assert len(df) >= 400  # rounding from per-attack split
    assert set(df["attack_type"].unique()) <= {"None", *ATTACK_TYPES}
    assert set(df["label"].unique()) == {"Normal", "Attack"}


def test_feature_matrix_is_numeric_and_aligned():
    df = generate_dataset(n_rows=200, seed=2)
    X, meta = build_feature_matrix(df)
    assert len(X) == len(meta) == len(df)
    assert X.select_dtypes(exclude="number").empty  # everything numeric
    assert not X.isna().any().any()


def test_anomaly_pipeline_flags_more_attacks_than_normal_traffic():
    df = generate_dataset(n_rows=3000, attack_ratio=0.15, seed=3)
    train_df = df.sample(frac=0.7, random_state=3)
    test_df = df.drop(train_df.index)

    pipeline = AnomalyPipeline().fit(train_df)
    results = pipeline.predict(test_df)

    attack_flag_rate = results.loc[results["attack_type"] != "None", "is_anomaly"].mean()
    normal_flag_rate = results.loc[results["attack_type"] == "None", "is_anomaly"].mean()

    # Sanity bound rather than a strict accuracy claim: the detector should
    # flag attack traffic meaningfully more often than normal traffic.
    assert attack_flag_rate > normal_flag_rate


def test_pipeline_handles_unseen_categorical_values_at_inference():
    train_df = generate_dataset(n_rows=300, seed=4)
    pipeline = AnomalyPipeline().fit(train_df)

    new_row = train_df.iloc[[0]].copy()
    new_row["src_asset"] = "Never-Seen-Asset"
    result = pipeline.predict(new_row)
    assert len(result) == 1
