"""Simple regression / classification metrics (numpy)."""

from __future__ import annotations

import numpy as np


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def direction_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Fraction where sign(y_true) == sign(y_pred), ignoring zeros."""
    mask = y_true != 0
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.sign(y_true[mask]) == np.sign(y_pred[mask])))


def binary_auc_roc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    """Rank-based AUC; returns None if single class."""
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score).astype(float)
    pos = y_true == 1
    neg = y_true == 0
    n_pos, n_neg = pos.sum(), neg.sum()
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(y_score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1)
    return (ranks[pos].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
