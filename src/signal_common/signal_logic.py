"""
Pure functions for conviction, thesis, and fundamental scoring.

Threshold order must stay: signal_short_threshold <= signal_exit_threshold (e.g. -0.65 <= -0.40).
"""

from __future__ import annotations

from typing import Any

from signal_common.config import Settings
from signal_common.schemas import ConfidenceTier, EvidenceItem, MoveAttribution, PositionIntent, SignalAction


def blend_scores(
    tech: float,
    sentiment: float,
    fundamental: float | None,
    settings: Settings,
) -> float:
    wf = settings.weight_fundamental
    wt = settings.weight_technical
    ws = settings.weight_sentiment
    if fundamental is None:
        # Redistribute fundamental weight to tech/sentiment proportionally.
        total = wt + ws
        if total <= 0:
            return max(-1.0, min(1.0, (tech + sentiment) / 2))
        wt2, ws2 = wt / total, ws / total
        return max(-1.0, min(1.0, wt2 * tech + ws2 * sentiment))
    return max(-1.0, min(1.0, wt * tech + ws * sentiment + wf * fundamental))


def apply_regime(raw: float, damp: float) -> float:
    if raw > 0:
        return max(-1.0, min(1.0, raw * damp))
    return max(-1.0, min(1.0, raw))


def technical_z_score(
    rsi: float | None,
    macd: float | None,
    close: float,
    bb_u: float | None,
    bb_l: float | None,
) -> float:
    """Map RSI / MACD / Bollinger position to approximately [-1, 1] for blending."""
    parts: list[float] = []
    if rsi is not None:
        parts.append((rsi - 50.0) / 50.0)
    if macd is not None:
        parts.append(max(-1.0, min(1.0, macd / 5.0)))
    if bb_u is not None and bb_l is not None and bb_u != bb_l:
        bbp = (close - bb_l) / (bb_u - bb_l)
        parts.append(max(-1.0, min(1.0, (bbp - 0.5) * 2)))
    if not parts:
        return 0.0
    return max(-1.0, min(1.0, sum(parts) / len(parts)))


def classify_action_intent(
    conviction: float,
    settings: Settings,
) -> tuple[SignalAction, PositionIntent]:
    """Map master conviction to action and position intent."""
    if conviction >= settings.signal_buy_threshold:
        return SignalAction.BUY, PositionIntent.LONG
    if conviction <= settings.signal_short_threshold:
        return SignalAction.SELL, PositionIntent.SHORT
    if conviction <= settings.signal_exit_threshold:
        return SignalAction.SELL, PositionIntent.REDUCE_LONG
    return SignalAction.HOLD, PositionIntent.FLAT


def confidence_tier(
    conviction: float,
    has_fundamentals: bool,
    settings: Settings,
) -> ConfidenceTier:
    ac = abs(conviction)
    if not has_fundamentals and ac >= settings.signal_buy_threshold - 0.05:
        return ConfidenceTier.medium
    if ac >= 0.72:
        return ConfidenceTier.high
    if ac >= 0.45:
        return ConfidenceTier.medium
    return ConfidenceTier.low


def build_move_attribution_narrative(m: MoveAttribution) -> str:
    """One plain-English block for move attribution (explanatory, not a forecast)."""
    parts: list[str] = []
    if m.spy_return_5d is not None:
        parts.append(f"SPY 5d return ~{100.0 * m.spy_return_5d:.1f}%.")
    if m.beta_spy is not None and m.market_explained_5d is not None:
        parts.append(
            f"Beta vs SPY ({m.beta_spy:.2f}) implies ~{100.0 * m.market_explained_5d:.1f}% of the 5d move "
            "aligned with SPY (co-movement proxy)."
        )
    if m.residual_5d is not None:
        parts.append(f"Stock-specific residual vs SPY-beta strip ~{100.0 * m.residual_5d:.1f}% 5d.")
    if m.sector_etf and m.sector_etf_return_5d is not None:
        parts.append(f"{m.sector_etf} 5d ~{100.0 * m.sector_etf_return_5d:.1f}%.")
    if m.peer_percentile_sector is not None:
        parts.append(
            f"Versus same-sector peers in this universe: {m.peer_percentile_sector:.0f}th percentile on 5d return."
        )
    return " ".join(parts) if parts else ""


def build_thesis(
    ticker: str,
    tech: float,
    sentiment: float,
    fund: float | None,
    rsi: float | None,
    macd: float | None,
    regime_note: str,
    move_attribution: MoveAttribution | None = None,
) -> str:
    parts = [f"{ticker}:"]
    if rsi is not None:
        parts.append(f"RSI(14)={rsi:.1f}")
    if macd is not None:
        parts.append(f"MACD={macd:.3f}")
    parts.append(f"technical={tech:+.2f}")
    parts.append(f"sentiment={sentiment:+.2f}")
    if fund is not None:
        parts.append(f"fundamental={fund:+.2f}")
    if regime_note:
        parts.append(regime_note)
    if move_attribution:
        nar = build_move_attribution_narrative(move_attribution)
        if nar:
            parts.append(nar)
    return "; ".join(parts) + "."


def evidence_items(
    rsi: float | None,
    macd: float | None,
    last_close: float | None,
    ret_5d: float | None,
    pe: float | None,
    roe: float | None,
    de: float | None,
) -> list[EvidenceItem]:
    out: list[EvidenceItem] = []
    if rsi is not None:
        out.append(EvidenceItem(label="rsi_14", value=round(rsi, 4)))
    if macd is not None:
        out.append(EvidenceItem(label="macd", value=round(macd, 6)))
    if last_close is not None:
        out.append(EvidenceItem(label="last_close", value=round(last_close, 4)))
    if ret_5d is not None:
        out.append(EvidenceItem(label="return_5d", value=round(ret_5d, 6)))
    if pe is not None:
        out.append(EvidenceItem(label="pe_ratio", value=round(pe, 4)))
    if roe is not None:
        out.append(EvidenceItem(label="return_on_equity", value=round(roe, 6)))
    if de is not None:
        out.append(EvidenceItem(label="debt_to_equity", value=round(de, 6)))
    return out


def fundamental_score_from_metrics(
    pe: float | None,
    roe: float | None,
    debt_to_equity: float | None,
    revenue_growth_yoy: float | None,
) -> float:
    """Map headline ratios to [-1, 1] (heuristic, not investment advice)."""
    score = 0.0
    n = 0
    if roe is not None:
        n += 1
        score += max(-1.0, min(1.0, roe * 4.0))
    if pe is not None and pe > 0:
        n += 1
        if pe < 15:
            score += 0.5
        elif pe < 28:
            score += 0.15
        elif pe > 55:
            score -= 0.4
        else:
            score += 0.0
    if debt_to_equity is not None and debt_to_equity >= 0:
        n += 1
        if debt_to_equity < 0.5:
            score += 0.35
        elif debt_to_equity < 1.2:
            score += 0.1
        else:
            score -= 0.35
    if revenue_growth_yoy is not None:
        n += 1
        score += max(-1.0, min(1.0, revenue_growth_yoy * 3.0))
    if n == 0:
        return 0.0
    return max(-1.0, min(1.0, score / n))


def extract_ratios_from_polygon_payload(data: dict[str, Any]) -> dict[str, float | None]:
    """Best-effort parse Polygon financials v1 ratios (shape may vary)."""
    out: dict[str, float | None] = {
        "pe_ratio": None,
        "price_to_book": None,
        "return_on_equity": None,
        "debt_to_equity": None,
        "revenue_growth_yoy": None,
    }
    results = data.get("results") or data.get("data") or []
    if not results:
        return out
    row = results[0] if isinstance(results, list) else results
    if not isinstance(row, dict):
        return out

    def pick(*keys: str) -> float | None:
        for k in keys:
            v = row.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    continue
        return None

    out["pe_ratio"] = pick("price_to_earnings", "pe_ratio", "pe", "priceToEarningsRatio")
    out["price_to_book"] = pick("price_to_book", "pb", "priceToBookRatio")
    out["return_on_equity"] = pick("return_on_equity", "roe", "returnOnEquity")
    out["debt_to_equity"] = pick("debt_to_equity", "debtToEquity", "total_debt_to_equity")
    out["revenue_growth_yoy"] = pick(
        "revenue_growth_yoy",
        "revenueGrowthYoY",
        "revenue_growth",
    )
    return out
