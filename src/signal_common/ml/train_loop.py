"""Training loop utilities for MoveMLP."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import torch
from torch import nn
from torch.utils.data import DataLoader

from signal_common.ml.dataset import MoveParquetDataset
from signal_common.ml.model import MoveMLP


def fit_mlp(
    model: MoveMLP,
    train_ds: MoveParquetDataset,
    val_ds: MoveParquetDataset | None,
    *,
    epochs: int,
    batch_size: int,
    lr: float,
    device: torch.device,
    mode: Literal["regression", "binary"],
    weight_decay: float = 1e-4,
) -> MoveMLP:
    model = model.to(device)
    if mode == "regression":
        loss_fn = nn.MSELoss()
    else:
        loss_fn = nn.BCEWithLogitsLoss()

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = (
        DataLoader(val_ds, batch_size=batch_size, shuffle=False) if val_ds is not None else None
    )

    for epoch in range(epochs):
        model.train()
        total = 0.0
        n = 0
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            opt.zero_grad()
            pred = model(xb).squeeze(-1)
            if mode == "binary":
                loss = loss_fn(pred, yb.float())
            else:
                loss = loss_fn(pred, yb)
            loss.backward()
            opt.step()
            total += loss.item() * xb.size(0)
            n += xb.size(0)
        if val_loader is not None:
            model.eval()
            vloss = 0.0
            vn = 0
            with torch.no_grad():
                for xb, yb in val_loader:
                    xb = xb.to(device)
                    yb = yb.to(device)
                    pred = model(xb).squeeze(-1)
                    if mode == "binary":
                        loss = loss_fn(pred, yb.float())
                    else:
                        loss = loss_fn(pred, yb)
                    vloss += loss.item() * xb.size(0)
                    vn += xb.size(0)
            # noqa: T201 — training script diagnostic
            print(
                f"epoch {epoch + 1}/{epochs} train_loss={total / max(n, 1):.6f} val_loss={vloss / max(vn, 1):.6f}"
            )
        else:
            print(f"epoch {epoch + 1}/{epochs} train_loss={total / max(n, 1):.6f}")

    return model


def save_checkpoint(
    path: Path,
    model: MoveMLP,
    *,
    input_dim: int,
    feature_columns: list[str],
    impute_medians: dict[str, float],
    hidden_dims: tuple[int, ...],
    dropout: float,
    mode: str,
    manifest_meta: dict,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "feature_columns": feature_columns,
            "impute_medians": impute_medians,
            "input_dim": input_dim,
            "hidden_dims": hidden_dims,
            "dropout": dropout,
            "mode": mode,
            "manifest_meta": manifest_meta,
        },
        path,
    )


def load_checkpoint(path: Path, device: torch.device) -> tuple[MoveMLP, dict]:
    ckpt = torch.load(path, map_location=device, weights_only=False)
    input_dim = int(ckpt.get("input_dim", len(ckpt["feature_columns"])))
    hidden_dims = tuple(ckpt.get("hidden_dims", (128, 64)))
    dropout = float(ckpt.get("dropout", 0.2))
    out_dim = 1
    model = MoveMLP(
        input_dim=input_dim,
        hidden_dims=hidden_dims,
        dropout=dropout,
        out_dim=out_dim,
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    return model, ckpt
