"""Parquet-backed tabular dataset for move models."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


def load_manifest(manifest_path: Path | str) -> dict:
    return json.loads(Path(manifest_path).read_text(encoding="utf-8"))


def compute_impute_medians(df: pd.DataFrame, feature_cols: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for c in feature_cols:
        s = pd.to_numeric(df[c], errors="coerce")
        out[c] = float(s.median()) if s.notna().any() else 0.0
    return out


def apply_impute(df: pd.DataFrame, feature_cols: list[str], medians: dict[str, float]) -> np.ndarray:
    rows = []
    for c in feature_cols:
        s = pd.to_numeric(df[c], errors="coerce").fillna(medians[c])
        rows.append(s.values.astype(np.float32))
    return np.stack(rows, axis=1)


class MoveParquetDataset(Dataset):
    """Rows from export parquet + manifest feature columns."""

    def __init__(
        self,
        features: np.ndarray,
        targets: np.ndarray,
    ) -> None:
        self.features = torch.from_numpy(features)
        self.targets = torch.from_numpy(targets)

    def __len__(self) -> int:
        return self.features.shape[0]

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.targets[idx]
