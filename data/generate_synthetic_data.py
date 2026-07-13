"""
Synthetic MMS / IEC 61850 traffic generator.

The original thesis used MATLAB/Simulink to generate labeled smart-grid
traffic in a controlled testbed. That path is preserved conceptually (see
README), but it requires a MATLAB license and a simulated substation model
that most people cloning this repo won't have.

This module is the open-source, runs-anywhere substitute: it synthesizes
MMS-like network traffic with realistic feature distributions for normal
operation plus four attack classes, so the rest of the pipeline (feature
engineering -> detection -> agents) can be developed and tested end-to-end
without special infrastructure.

Attack classes modeled (matching the thesis scope):
  - Denial of Service (DoS)       : request-rate spike, small packet size
  - Man-in-the-Middle (MITM)      : elevated latency, jitter, unusual src/dst
  - False Data Injection (FDI)    : value plausible but statistically off-pattern
  - Replay                        : near-duplicate packets, tight periodicity

This is NOT a substitute for real ICS captures or a validated Simulink
model - it is a development/testing aid. Swap in real PCAP-derived
features via `load_real_traffic()` once available.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

RNG_SEED = 42
ATTACK_TYPES = ["DoS", "MITM", "FDI", "Replay"]

MMS_SERVICES = [
    "Read", "Write", "GetNameList", "GetVariableAccessAttributes",
    "Report", "GOOSE", "SampledValues",
]

ASSETS = [
    "RTU-01", "RTU-02", "IED-Breaker-A", "IED-Breaker-B",
    "NAN-Gateway", "Substation-HMI", "Merging-Unit-01",
]


def _base_timestamp(n: int, start: datetime | None = None, interval_s: float = 1.0) -> list[datetime]:
    start = start or datetime(2026, 1, 1)
    return [start + timedelta(seconds=i * interval_s) for i in range(n)]


def _normal_traffic(n: int, rng: np.random.Generator) -> pd.DataFrame:
    return pd.DataFrame({
        "packet_size": rng.normal(180, 25, n).clip(60, 1500),
        "inter_arrival_ms": rng.normal(200, 40, n).clip(5, None),
        "request_rate": rng.normal(5, 1.5, n).clip(0.1, None),
        "latency_ms": rng.normal(12, 3, n).clip(1, None),
        "jitter_ms": rng.normal(1.5, 0.5, n).clip(0, None),
        "duplicate_ratio": rng.beta(1, 30, n),
        "value_deviation": rng.normal(0, 1, n),
        "mms_service": rng.choice(MMS_SERVICES, n, p=[0.25, 0.15, 0.1, 0.1, 0.2, 0.15, 0.05]),
        "src_asset": rng.choice(ASSETS, n),
        "dst_asset": rng.choice(ASSETS, n),
        "label": "Normal",
        "attack_type": "None",
    })


def _dos_traffic(n: int, rng: np.random.Generator) -> pd.DataFrame:
    df = _normal_traffic(n, rng)
    df["packet_size"] = rng.normal(70, 15, n).clip(40, None)
    df["inter_arrival_ms"] = rng.normal(3, 1.5, n).clip(0.1, None)
    df["request_rate"] = rng.normal(80, 20, n).clip(20, None)
    df["latency_ms"] = rng.normal(60, 20, n).clip(5, None)
    df["mms_service"] = rng.choice(["Read", "GetNameList"], n)
    df["label"] = "Attack"
    df["attack_type"] = "DoS"
    return df


def _mitm_traffic(n: int, rng: np.random.Generator) -> pd.DataFrame:
    df = _normal_traffic(n, rng)
    df["latency_ms"] = rng.normal(45, 12, n).clip(10, None)
    df["jitter_ms"] = rng.normal(9, 3, n).clip(1, None)
    df["src_asset"] = rng.choice(ASSETS, n)  # unusual src/dst pairing
    df["dst_asset"] = rng.choice(ASSETS, n)
    df["label"] = "Attack"
    df["attack_type"] = "MITM"
    return df


def _fdi_traffic(n: int, rng: np.random.Generator) -> pd.DataFrame:
    df = _normal_traffic(n, rng)
    df["mms_service"] = rng.choice(["Write", "Report", "SampledValues"], n)
    df["value_deviation"] = rng.normal(0, 1, n) + rng.choice([-1, 1], n) * rng.normal(4, 1.2, n)
    df["label"] = "Attack"
    df["attack_type"] = "FDI"
    return df


def _replay_traffic(n: int, rng: np.random.Generator) -> pd.DataFrame:
    df = _normal_traffic(n, rng)
    df["duplicate_ratio"] = rng.beta(20, 3, n)
    df["inter_arrival_ms"] = rng.normal(200, 2, n).clip(5, None)  # unnaturally tight periodicity
    df["label"] = "Attack"
    df["attack_type"] = "Replay"
    return df


def generate_dataset(
    n_rows: int = 5000,
    attack_ratio: float = 0.12,
    seed: int = RNG_SEED,
) -> pd.DataFrame:
    """Generate a labeled synthetic MMS traffic dataset."""
    rng = np.random.default_rng(seed)
    n_attack = int(n_rows * attack_ratio)
    n_normal = n_rows - n_attack
    per_attack = max(1, n_attack // len(ATTACK_TYPES))

    frames = [_normal_traffic(n_normal, rng)]
    generators = {
        "DoS": _dos_traffic,
        "MITM": _mitm_traffic,
        "FDI": _fdi_traffic,
        "Replay": _replay_traffic,
    }
    for attack in ATTACK_TYPES:
        frames.append(generators[attack](per_attack, rng))

    df = pd.concat(frames, ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    df["timestamp"] = _base_timestamp(len(df))
    cols = ["timestamp"] + [c for c in df.columns if c != "timestamp"]
    return df[cols]


def load_real_traffic(pcap_or_csv_path: str) -> pd.DataFrame:
    """
    Placeholder for ingesting real ICS/MMS captures (e.g. exported from
    Wireshark as CSV, or pre-processed from PCAP). Not implemented here
    since it depends on the specific capture tooling used in the lab.
    """
    raise NotImplementedError(
        "Hook up your real MMS capture pipeline here. "
        "Expected output columns match generate_dataset()."
    )


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = generate_dataset()
    out_path = out_dir / "synthetic_mms_traffic.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    print(df["attack_type"].value_counts())
