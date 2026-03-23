"""Tiny forward pass for MoveMLP (requires torch)."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from signal_common.ml.model import MoveMLP  # noqa: E402


def test_move_mlp_forward_and_loss_step():
    model = MoveMLP(input_dim=8, hidden_dims=(16, 8), dropout=0.0, out_dim=1)
    x = torch.randn(4, 8)
    y = torch.randn(4)
    pred = model(x).squeeze(-1)
    loss = torch.nn.functional.mse_loss(pred, y)
    loss.backward()
    assert pred.shape == (4,)
    assert not torch.isnan(loss)


def test_move_mlp_binary_logits():
    model = MoveMLP(input_dim=4, hidden_dims=(8,), dropout=0.0, out_dim=1)
    x = torch.randn(8, 4)
    logits = model(x).squeeze(-1)
    loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, torch.zeros(8))
    loss.backward()
    assert logits.shape == (8,)
