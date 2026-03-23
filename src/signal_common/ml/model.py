"""Small MLP for tabular forward-return or move classification."""

from __future__ import annotations

import torch
from torch import nn


class MoveMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dims: tuple[int, ...] = (128, 64),
        dropout: float = 0.2,
        out_dim: int = 1,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        d = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(d, h))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            d = h
        layers.append(nn.Linear(d, out_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
