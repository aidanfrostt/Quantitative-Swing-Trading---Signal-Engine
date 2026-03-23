#!/usr/bin/env python3
"""
Evaluate a trained move_model.pt on a Parquet slice (held-out dates or same export).

Writes metrics to stdout and optional --report markdown file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import pandas as pd
import torch

from signal_common.ml.dataset import apply_impute, load_manifest
from signal_common.ml.metrics import binary_auc_roc, direction_accuracy, mae, rmse
from signal_common.ml.train_loop import load_checkpoint


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, default=Path("artifacts/move_model.pt"))
    p.add_argument("--parquet", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--report", type=Path, default=None, help="Optional Markdown report path")
    args = p.parse_args()

    manifest = load_manifest(args.manifest)
    feature_cols = manifest["feature_columns"]
    df = pd.read_parquet(args.parquet)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, ckpt = load_checkpoint(args.checkpoint, device)

    medians = ckpt["impute_medians"]
    X = apply_impute(df, feature_cols, medians)
    x_t = torch.from_numpy(X).to(device)

    with torch.no_grad():
        pred = model(x_t).squeeze(-1).cpu().numpy()

    mode = ckpt.get("mode", "regression")
    lines = [
        "# Move model evaluation",
        "",
        f"- rows: {len(df)}",
        f"- mode: {mode}",
        "",
    ]
    if mode == "binary":
        y_bin = df["label_big_move"].values.astype(np.int64)
        prob = 1.0 / (1.0 + np.exp(-np.clip(pred, -30.0, 30.0)))
        auc = binary_auc_roc(y_bin, prob)
        acc = float(np.mean((prob >= 0.5).astype(np.int64) == y_bin))
        lines.extend(
            [
                "## Binary label (label_big_move)",
                "",
                f"- AUC: {auc}",
                f"- accuracy @0.5 threshold: {acc:.4f}",
                "",
            ]
        )
        y_reg = df["forward_return"].values.astype(np.float64)
        lines.extend(
            [
                "## Sanity: regression metrics if treating logits as return forecast (not recommended)",
                "",
                f"- MAE vs forward_return: {mae(y_reg, pred):.6f}",
                "",
            ]
        )
    else:
        y = df["forward_return"].values.astype(np.float64)
        lines.extend(
            [
                "## Regression vs realized forward_return",
                "",
                f"- MAE: {mae(y, pred):.6f}",
                f"- RMSE: {rmse(y, pred):.6f}",
                f"- direction accuracy (sign match): {direction_accuracy(y, pred):.4f}",
                "",
            ]
        )

    text = "\n".join(lines)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
