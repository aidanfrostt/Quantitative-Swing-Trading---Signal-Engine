#!/usr/bin/env python3
"""
Exploratory correlation / lag analysis on time-series CSVs.

This script is for **research only**. Correlation does not imply causation.
Multiple comparisons inflate false positives; use small samples with skepticism.

Example (synthetic demo):

  python scripts/research/correlation_scan.py --demo

Example (your CSV with columns date,col_a,col_b,...):

  python scripts/research/correlation_scan.py --csv /path/to/series.csv

Outputs a Markdown summary to stdout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DISCLAIMER = """## Disclaimer

- Correlations are **descriptive** on the window provided.
- **Spurious** relationships are common; lagged correlations are **exploratory**.
- Not investment advice.
"""


def pearson_safe(a: pd.Series, b: pd.Series) -> float | None:
    if len(a) < 3 or len(b) < 3:
        return None
    if a.std() < 1e-12 or b.std() < 1e-12:
        return None
    return float(a.corr(b))


def correlation_matrix(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].dropna()
    return sub.corr(method="pearson")


def lag_correlations(df: pd.DataFrame, x: str, y: str, max_lag: int = 5) -> list[tuple[int, float | None]]:
    out: list[tuple[int, float | None]] = []
    for lag in range(-max_lag, max_lag + 1):
        if lag == 0:
            r = pearson_safe(df[x], df[y])
            out.append((lag, r))
        elif lag > 0:
            r = pearson_safe(df[x].iloc[:-lag], df[y].iloc[lag:])
            out.append((lag, r))
        else:
            k = -lag
            r = pearson_safe(df[x].iloc[k:], df[y].iloc[:-k])
            out.append((lag, r))
    return out


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 120
    t = pd.date_range("2024-01-01", periods=n, freq="B")
    spy = np.cumsum(rng.normal(0.0005, 0.01, n))
    sentiment = np.roll(spy, 1) * 0.3 + rng.normal(0, 0.02, n)
    etf = spy * 0.9 + rng.normal(0, 0.015, n)
    return pd.DataFrame({"date": t, "spy_cum": spy, "sent_z": sentiment, "etf_cum": etf})


def run_report(df: pd.DataFrame, cols: list[str]) -> str:
    lines = ["# Exploratory correlation report", "", DISCLAIMER, ""]
    lines.append("## Pearson correlation matrix")
    lines.append("")
    cm = correlation_matrix(df, cols)
    try:
        lines.append(cm.to_markdown())
    except Exception:
        lines.append(cm.to_string())
    lines.append("")
    if len(cols) >= 2:
        lines.append("## Example lag scan (first vs second column)")
        lines.append("")
        a, b = cols[0], cols[1]
        for lag, r in lag_correlations(df, a, b, max_lag=3):
            lines.append(f"- lag {lag:+d}: r = {r}")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Inspect rolling correlations for stability before trusting any level.")
    lines.append("- Export sector ETF returns and sentiment series from the DB for real runs.")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Exploratory correlation scan (research only).")
    p.add_argument("--demo", action="store_true", help="Run on synthetic data")
    p.add_argument("--csv", type=Path, help="CSV with numeric columns (and optional date)")
    args = p.parse_args()

    if args.demo:
        df = demo_frame()
        cols = ["spy_cum", "sent_z", "etf_cum"]
        print(run_report(df, cols))
        return

    if args.csv:
        df = pd.read_csv(args.csv)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        num_cols = [c for c in df.columns if c != "date" and pd.api.types.is_numeric_dtype(df[c])]
        if len(num_cols) < 2:
            print("Need at least two numeric columns.", file=sys.stderr)
            sys.exit(1)
        print(run_report(df, num_cols[:8]))
        return

    p.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
