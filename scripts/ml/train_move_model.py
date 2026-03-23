#!/usr/bin/env python3
"""
Train a small MLP on exported Parquet (time-based train/val split by as_of_date).

Example:
  pip install -e ".[ml]"
  python scripts/ml/export_training_dataset.py \\
    --start-date 2024-01-02 --end-date 2024-12-31 --out-dir artifacts/ml_export
  python scripts/ml/train_move_model.py \\
    --parquet artifacts/ml_export/train.parquet \\
    --manifest artifacts/ml_export/manifest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import pandas as pd
import torch

from signal_common.ml.dataset import MoveParquetDataset, apply_impute, compute_impute_medians, load_manifest
from signal_common.ml.model import MoveMLP
from signal_common.ml.train_loop import fit_mlp, save_checkpoint


def date_split_mask(df: pd.DataFrame, val_ratio: float) -> tuple[np.ndarray, np.ndarray]:
    dates = sorted(df["as_of_date"].unique())
    if len(dates) < 2:
        raise SystemExit("Need at least two distinct as_of_date values for time split.")
    cut = max(1, int(len(dates) * (1.0 - val_ratio)))
    train_dates = set(dates[:cut])
    val_dates = set(dates[cut:])
    tr = df["as_of_date"].isin(train_dates).values
    va = df["as_of_date"].isin(val_dates).values
    return tr, va


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parquet", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("artifacts"))
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--val-ratio", type=float, default=0.2, help="Last fraction of calendar dates for validation")
    p.add_argument("--mode", choices=("regression", "binary"), default="regression")
    p.add_argument("--hidden", type=int, nargs="+", default=[128, 64])
    p.add_argument("--dropout", type=float, default=0.2)
    args = p.parse_args()

    manifest = load_manifest(args.manifest)
    feature_cols = manifest["feature_columns"]
    df = pd.read_parquet(args.parquet)

    tr_mask, va_mask = date_split_mask(df, args.val_ratio)
    train_df = df.loc[tr_mask]
    val_df = df.loc[va_mask]

    medians = compute_impute_medians(train_df, feature_cols)
    X_train = apply_impute(train_df, feature_cols, medians)
    X_val = apply_impute(val_df, feature_cols, medians)

    if args.mode == "regression":
        y_train = train_df["forward_return"].values.astype(np.float32)
        y_val = val_df["forward_return"].values.astype(np.float32)
    else:
        y_train = train_df["label_big_move"].values.astype(np.float32)
        y_val = val_df["label_big_move"].values.astype(np.float32)

    train_ds = MoveParquetDataset(X_train, y_train)
    val_ds = MoveParquetDataset(X_val, y_val)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    hidden_dims = tuple(args.hidden)

    input_dim = X_train.shape[1]
    out_dim = 1
    model = MoveMLP(
        input_dim=input_dim,
        hidden_dims=hidden_dims,
        dropout=args.dropout,
        out_dim=out_dim,
    ).to(device)

    model = fit_mlp(
        model,
        train_ds,
        val_ds,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device=device,
        mode=args.mode,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = args.out_dir / "move_model.pt"
    save_checkpoint(
        ckpt_path,
        model,
        input_dim=input_dim,
        feature_columns=feature_cols,
        impute_medians=medians,
        hidden_dims=hidden_dims,
        dropout=args.dropout,
        mode=args.mode,
        manifest_meta=manifest,
    )

    features_json = {
        "feature_columns": feature_cols,
        "impute_medians": medians,
        "feature_schema_version": manifest.get("feature_schema_version"),
        "mode": args.mode,
    }
    (args.out_dir / "features.json").write_text(json.dumps(features_json, indent=2), encoding="utf-8")
    print(f"Saved {ckpt_path} and features.json")


if __name__ == "__main__":
    main()
