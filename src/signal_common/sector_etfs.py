"""
Map free-text sector / SIC descriptions to a liquid sector ETF ticker.

Fallback is broad market (SPY) when no keyword matches; `benchmark_etf` may be null if unset.
"""

from __future__ import annotations

import re

# Order matters: first substring match wins (case-insensitive).
_KEYWORD_ETF: list[tuple[str, str]] = [
    ("technology", "XLK"),
    ("software", "XLK"),
    ("semiconductor", "XLK"),
    ("health care", "XLV"),
    ("healthcare", "XLV"),
    ("pharmaceutical", "XLV"),
    ("biotechnology", "XLV"),
    ("financial", "XLF"),
    ("bank", "XLF"),
    ("insurance", "XLF"),
    ("consumer cyclical", "XLY"),
    ("consumer discretionary", "XLY"),
    ("retail", "XLY"),
    ("automotive", "XLY"),
    ("consumer defensive", "XLP"),
    ("consumer staples", "XLP"),
    ("food", "XLP"),
    ("household", "XLP"),
    ("industrial", "XLI"),
    ("aerospace", "XLI"),
    ("machinery", "XLI"),
    ("energy", "XLE"),
    ("oil", "XLE"),
    ("gas", "XLE"),
    ("utilities", "XLU"),
    ("electric", "XLU"),
    ("materials", "XLB"),
    ("chemical", "XLB"),
    ("metals", "XLB"),
    ("mining", "XLB"),
    ("real estate", "XLRE"),
    ("reit", "XLRE"),
    ("communication", "XLC"),
    ("telecom", "XLC"),
    ("media", "XLC"),
    ("entertainment", "XLC"),
]


def normalize_sector_key(label: str | None) -> str:
    if not label:
        return "unknown"
    s = re.sub(r"[^a-z0-9]+", "_", label.lower().strip())
    return s[:120] or "unknown"


def benchmark_etf_from_description(description: str | None) -> tuple[str | None, str | None]:
    """
    Returns (benchmark_etf, sector_label_for_display).
    Uses keyword scan on Polygon `sic_description` or similar free text.
    """
    if not description or not str(description).strip():
        return None, None
    d = str(description).lower().strip()
    for kw, etf in _KEYWORD_ETF:
        if kw in d:
            return etf, description.strip()[:200]
    return "SPY", description.strip()[:200]


def sector_from_polygon_result(results: dict) -> tuple[str, str | None, str | None]:
    """
    Map Polygon v3 `results` object to (sector_key, sector_label, benchmark_etf).
    """
    if not isinstance(results, dict):
        return "unknown", None, None
    label = (
        results.get("sic_description")
        or results.get("sector")
        or results.get("industry")
        or ""
    )
    label = str(label).strip() if label else ""
    if not label:
        return "unknown", None, None
    etf, display = benchmark_etf_from_description(label)
    key = normalize_sector_key(display or label)
    return key, (display or label)[:200], etf


# All ETFs we need OHLCV for (plus SPY/QQQ for context).
def all_benchmark_tickers() -> list[str]:
    etfs = {etf for _, etf in _KEYWORD_ETF}
    etfs.add("SPY")
    etfs.add("QQQ")
    return sorted(etfs)


def merged_benchmark_tickers(extra_csv: str) -> list[str]:
    """Base sector ETFs + SPY/QQQ + optional comma-separated extras from settings."""
    out = set(all_benchmark_tickers())
    for part in (extra_csv or "").split(","):
        t = part.strip().upper()
        if t:
            out.add(t)
    return sorted(out)
