"""
REST API for the execution bot: blends technicals, news sentiment, fundamentals,
and regime into conviction scores. Exposes grouped long/short/watchlist lists;
optional persistence to `signal_runs` for audit.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from signal_common.config import Settings, get_settings
from signal_common.db import create_pool, parse_polygon_ticker, run_migrations
from signal_common.market_calendar import current_nyse_date, is_nyse_trading_day
from signal_common.schemas import (
    EvidenceItem,
    Horizon,
    MarketContext,
    MoveAttribution,
    PositionIntent,
    SectorSentimentPayload,
    SectorSentimentRow,
    SignalAction,
    SignalRecord,
    SignalsPayload,
)
from signal_common.signal_logic import (
    apply_regime,
    blend_scores,
    build_move_attribution_narrative,
    build_thesis,
    classify_action_intent,
    confidence_tier,
    evidence_items,
    technical_z_score,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Signal Generation API", version="0.1.0")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_init_settings = get_settings()
_cors = [o.strip() for o in _init_settings.cors_allowed_origins.split(",") if o.strip()]
if _cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors,
        allow_credentials=False,
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["*"],
    )


def _web_root() -> Path:
    if os.environ.get("WEB_ROOT"):
        return Path(os.environ["WEB_ROOT"])
    base = Path(__file__).resolve().parent
    if (base / "web").is_dir():
        return base / "web"
    return base.parent.parent / "web"

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await create_pool()
        await run_migrations(_pool)
    return _pool


def verify_key(key: str | None, settings: Settings) -> None:
    if not key or key not in settings.api_key_list():
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def require_auth(
    x_api_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    verify_key(x_api_key, settings)


async def require_public_ui_enabled(settings: Settings = Depends(get_settings)) -> None:
    if not settings.enable_public_signal_ui:
        raise HTTPException(status_code=404, detail="Not found")


async def _fetch_return_5d_map(conn: asyncpg.Connection, symbol_ids: list[int]) -> dict[int, float | None]:
    """Approximate ~1-week return using the latest daily close vs the 5th prior bar (trading days)."""
    if not symbol_ids:
        return {}
    rows = await conn.fetch(
        """
        WITH ranked AS (
            SELECT symbol_id, close,
                   ROW_NUMBER() OVER (PARTITION BY symbol_id ORDER BY bar_time DESC) AS rn
            FROM ohlcv
            WHERE interval = '1d' AND symbol_id = ANY($1::bigint[])
        )
        SELECT symbol_id,
               MAX(CASE WHEN rn = 1 THEN close END) AS c1,
               MAX(CASE WHEN rn = 5 THEN close END) AS c5
        FROM ranked
        WHERE rn <= 5
        GROUP BY symbol_id
        """,
        symbol_ids,
    )
    out: dict[int, float | None] = {}
    for r in rows:
        sid = int(r["symbol_id"])
        c1, c5 = r["c1"], r["c5"]
        if c1 and c5 and float(c5) != 0:
            out[sid] = (float(c1) - float(c5)) / float(c5)
        else:
            out[sid] = None
    return out


async def _fetch_sentiment_map(conn: asyncpg.Connection, tickers: list[str]) -> dict[str, tuple[float, int]]:
    """
    Weighted avg sentiment per ticker; publisher influence is clamped to [0.25, 2.0] to avoid runaway multipliers.
    Noise sources down-weight to 0.25x.
    """
    if not tickers:
        return {}
    rows = await conn.fetch(
        """
        SELECT s2.ticker AS ticker,
               AVG(
                 ns.score
                 * LEAST(GREATEST(COALESCE(ps.influence_score, 1.0), 0.25), 2.0)
                 * CASE WHEN ps.is_noise THEN 0.25 ELSE 1.0 END
               ) AS s,
               COUNT(*)::int AS n
        FROM news_article_symbols nas
        JOIN news_articles na ON na.id = nas.news_id
        JOIN news_sentiment ns ON ns.news_id = na.id
        LEFT JOIN publisher_scores ps ON ps.source = na.source AND ps.window_days = 90
        JOIN symbols s2 ON s2.id = nas.symbol_id
        WHERE s2.ticker = ANY($1::text[]) AND na.published_at >= NOW() - INTERVAL '14 days'
        GROUP BY s2.ticker
        """,
        tickers,
    )
    return {
        r["ticker"]: (max(-1.0, min(1.0, float(r["s"] or 0.0))), int(r["n"] or 0))
        for r in rows
    }


def _opt_float(row: Any, key: str) -> float | None:
    v = row[key]
    return float(v) if v is not None else None


async def _fetch_sector_sentiment_latest(conn: asyncpg.Connection) -> list[SectorSentimentRow]:
    """Latest `sector_sentiment_snapshot` rows (one `as_of_date` across all sectors)."""
    rows = await conn.fetch(
        """
        SELECT as_of_date::text AS as_of_date,
               sector_key,
               benchmark_etf,
               article_count,
               weighted_sentiment_avg,
               sentiment_std,
               etf_return_5d,
               etf_return_20d,
               sentiment_z_cross_sector,
               performance_sentiment_spread,
               divergence_flag
        FROM sector_sentiment_snapshot
        WHERE as_of_date = (SELECT MAX(as_of_date) FROM sector_sentiment_snapshot)
        ORDER BY sector_key
        """
    )
    out: list[SectorSentimentRow] = []
    for r in rows:
        df = r["divergence_flag"]
        out.append(
            SectorSentimentRow(
                as_of_date=str(r["as_of_date"]),
                sector_key=str(r["sector_key"]),
                benchmark_etf=str(r["benchmark_etf"]) if r["benchmark_etf"] else None,
                article_count=int(r["article_count"] or 0),
                weighted_sentiment_avg=_opt_float(r, "weighted_sentiment_avg"),
                sentiment_std=_opt_float(r, "sentiment_std"),
                etf_return_5d=_opt_float(r, "etf_return_5d"),
                etf_return_20d=_opt_float(r, "etf_return_20d"),
                sentiment_z_cross_sector=_opt_float(r, "sentiment_z_cross_sector"),
                performance_sentiment_spread=_opt_float(r, "performance_sentiment_spread"),
                divergence_flag=bool(df) if df is not None else None,
            )
        )
    return out


async def _fetch_attribution_map(conn: asyncpg.Connection, symbol_ids: list[int]) -> dict[int, MoveAttribution]:
    """Latest `attribution_snapshot` row per symbol, joined with benchmark ETF ticker."""
    if not symbol_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (a.symbol_id)
            a.symbol_id,
            a.ret_spy_5d,
            a.ret_sector_etf_5d,
            a.beta_spy_60d,
            a.market_component_5d,
            a.sector_component_5d,
            a.residual_5d,
            a.peer_percentile_5d,
            a.data_quality,
            s.benchmark_etf
        FROM attribution_snapshot a
        JOIN symbols s ON s.id = a.symbol_id
        WHERE a.symbol_id = ANY($1::bigint[])
        ORDER BY a.symbol_id, a.as_of_date DESC
        """,
        symbol_ids,
    )
    out: dict[int, MoveAttribution] = {}
    for r in rows:
        sid = int(r["symbol_id"])
        out[sid] = MoveAttribution(
            spy_return_5d=float(r["ret_spy_5d"]) if r["ret_spy_5d"] is not None else None,
            sector_etf=str(r["benchmark_etf"]) if r["benchmark_etf"] else None,
            sector_etf_return_5d=float(r["ret_sector_etf_5d"]) if r["ret_sector_etf_5d"] is not None else None,
            beta_spy=float(r["beta_spy_60d"]) if r["beta_spy_60d"] is not None else None,
            market_explained_5d=float(r["market_component_5d"]) if r["market_component_5d"] is not None else None,
            sector_component_5d=float(r["sector_component_5d"]) if r["sector_component_5d"] is not None else None,
            residual_5d=float(r["residual_5d"]) if r["residual_5d"] is not None else None,
            peer_percentile_sector=float(r["peer_percentile_5d"]) if r["peer_percentile_5d"] is not None else None,
            data_quality=str(r["data_quality"]) if r["data_quality"] else None,
            narrative="",
        )
    return out


async def _fetch_fundamentals_map(conn: asyncpg.Connection, symbol_ids: list[int]) -> dict[int, asyncpg.Record]:
    """Latest row per symbol from `fundamentals_snapshot` (Polygon ingest may be partial)."""
    if not symbol_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (symbol_id)
            symbol_id, pe_ratio, return_on_equity, debt_to_equity, revenue_growth_yoy,
            fundamental_score, as_of_date
        FROM fundamentals_snapshot
        WHERE symbol_id = ANY($1::bigint[])
        ORDER BY symbol_id, as_of_date DESC
        """,
        symbol_ids,
    )
    return {int(r["symbol_id"]): r for r in rows}


async def build_signals(
    conn: asyncpg.Connection,
    settings: Settings,
    horizon: Horizon,
    limit: int,
) -> SignalsPayload:
    """
    Build scored rows: blend tech/sentiment/fundamental, apply regime dampening on positive conviction only,
    classify BUY / SELL+SHORT / SELL+reduce / HOLD, then split into long/short/watchlist lists.
    """
    nyse_d = current_nyse_date()
    trading = is_nyse_trading_day(nyse_d)
    market_session = {
        "nyse_calendar_date": str(nyse_d),
        "nyse_trading_day": trading,
        "timezone": "America/New_York",
    }

    if settings.signals_only_on_trading_days and not trading:
        raise HTTPException(
            status_code=503,
            detail="Signals are configured to be served only on NYSE trading days.",
        )

    universe_version = str(await conn.fetchval("SELECT MAX(as_of_date)::text FROM filtered_universe") or "unknown")

    rows = await conn.fetch(
        """
        SELECT s.ticker, s.id AS symbol_id, tf.rsi_14, tf.macd, tf.bb_upper, tf.bb_lower, tf.bb_mid, tf.vwap_daily,
               o.close AS last_close
        FROM technical_features tf
        JOIN symbols s ON s.id = tf.symbol_id
        LEFT JOIN LATERAL (
            SELECT close FROM ohlcv
            WHERE symbol_id = tf.symbol_id AND interval = '1d'
            ORDER BY bar_time DESC LIMIT 1
        ) o ON TRUE
        WHERE tf.as_of_date = (SELECT MAX(as_of_date) FROM technical_features)
        LIMIT 500
        """
    )

    symbol_ids = [int(r["symbol_id"]) for r in rows]
    tickers = [r["ticker"] for r in rows]
    ret_map = await _fetch_return_5d_map(conn, symbol_ids)
    sent_map = await _fetch_sentiment_map(conn, tickers)
    fund_map = await _fetch_fundamentals_map(conn, symbol_ids)
    attr_map = await _fetch_attribution_map(conn, symbol_ids)

    regime_row = await conn.fetchrow(
        "SELECT buy_dampening_factor, spy_below_ma200, vix_close FROM regime_snapshot ORDER BY as_of_date DESC LIMIT 1"
    )
    damp = float(regime_row["buy_dampening_factor"]) if regime_row else 1.0
    reasons_regime: list[str] = []
    if regime_row and regime_row["spy_below_ma200"]:
        reasons_regime.append("spy_below_200dma")
    if regime_row and regime_row["vix_close"] and float(regime_row["vix_close"]) >= settings.regime_vix_threshold:
        reasons_regime.append("vix_elevated")

    regime_note = ""
    if reasons_regime:
        regime_note = "Regime: " + ", ".join(reasons_regime)

    spy_ctx_id = await conn.fetchval(
        "SELECT id FROM symbols WHERE ticker = $1",
        parse_polygon_ticker(settings.benchmark_symbol),
    )
    qqq_ctx_id = await conn.fetchval("SELECT id FROM symbols WHERE ticker = $1", "QQQ")
    ctx_ids = [int(i) for i in (spy_ctx_id, qqq_ctx_id) if i]
    ret_ctx = await _fetch_return_5d_map(conn, ctx_ids) if ctx_ids else {}
    market_context = MarketContext(
        spy_return_5d=ret_ctx.get(int(spy_ctx_id)) if spy_ctx_id else None,
        qqq_return_5d=ret_ctx.get(int(qqq_ctx_id)) if qqq_ctx_id else None,
        vix_close=float(regime_row["vix_close"]) if regime_row and regime_row["vix_close"] is not None else None,
        regime_buy_dampening=float(regime_row["buy_dampening_factor"]) if regime_row else None,
    )

    sector_context = await _fetch_sector_sentiment_latest(conn)

    all_records: list[SignalRecord] = []
    for r in rows:
        ticker = r["ticker"]
        sid = int(r["symbol_id"])
        close = float(r["last_close"] or 0) or 0.0
        rsi = float(r["rsi_14"]) if r["rsi_14"] is not None else None
        macd = float(r["macd"]) if r["macd"] is not None else None
        bb_u = float(r["bb_upper"]) if r["bb_upper"] is not None else None
        bb_l = float(r["bb_lower"]) if r["bb_lower"] is not None else None

        tech = technical_z_score(rsi, macd, close, bb_u, bb_l)

        sent_t = sent_map.get(ticker, (0.0, 0))
        sentiment = sent_t[0]
        news_n = sent_t[1]

        fr = fund_map.get(sid)
        fund_val: float | None = None
        pe = roe = de = None
        if fr:
            fund_val = float(fr["fundamental_score"]) if fr["fundamental_score"] is not None else None
            pe = float(fr["pe_ratio"]) if fr["pe_ratio"] is not None else None
            roe = float(fr["return_on_equity"]) if fr["return_on_equity"] is not None else None
            de = float(fr["debt_to_equity"]) if fr["debt_to_equity"] is not None else None

        blended = blend_scores(tech, sentiment, fund_val, settings)
        conviction = apply_regime(blended, damp)

        action, intent = classify_action_intent(conviction, settings)

        reasons = list(reasons_regime)
        if action == SignalAction.BUY:
            reasons.append("conviction_above_buy")
        elif intent == PositionIntent.SHORT:
            reasons.append("conviction_at_or_below_short_threshold")
        elif intent == PositionIntent.REDUCE_LONG:
            reasons.append("conviction_exit_band")

        ret_5d = ret_map.get(sid)
        ma_base = attr_map.get(sid)
        ma_for_record = None
        if ma_base:
            ma_for_record = ma_base.model_copy(update={"narrative": build_move_attribution_narrative(ma_base)})
        thesis = build_thesis(
            ticker,
            tech,
            sentiment,
            fund_val,
            rsi,
            macd,
            regime_note,
            move_attribution=ma_for_record,
        )
        ev = evidence_items(rsi, macd, close, ret_5d, pe, roe, de)
        if news_n:
            ev.append(EvidenceItem(label="news_articles_14d", value=news_n))

        tier = confidence_tier(conviction, fr is not None, settings)

        metrics = {
            "rsi_14": rsi,
            "macd": macd,
            "last_close": close,
            "return_5d": ret_5d,
            "news_articles_14d": news_n,
            "blended_pre_regime": blended,
        }
        if ma_for_record:
            metrics["attribution"] = ma_for_record.model_dump()

        all_records.append(
            SignalRecord(
                ticker=ticker,
                action=action,
                horizon=horizon,
                conviction=conviction,
                master_conviction=conviction,
                technical_score=tech,
                sentiment_score=sentiment,
                fundamental_score=fund_val,
                regime_adjustment=damp if blended > 0 else 1.0,
                position_intent=intent,
                reason_codes=reasons,
                metrics=metrics,
                thesis=thesis,
                confidence_tier=tier,
                evidence=ev,
                move_attribution=ma_for_record,
            )
        )

    all_sorted = sorted(all_records, key=lambda x: abs(x.master_conviction), reverse=True)
    flat = all_sorted[:limit]

    long_cand = [x for x in all_sorted if x.action == SignalAction.BUY][:limit]
    short_cand = [x for x in all_sorted if x.position_intent == PositionIntent.SHORT][:limit]
    watch = [
        x
        for x in all_sorted
        if x.action == SignalAction.HOLD and abs(x.master_conviction) >= settings.watchlist_abs_conviction_min
    ][:limit]

    payload = SignalsPayload(
        generated_at=datetime.now(timezone.utc),
        universe_version=universe_version,
        market_session=market_session,
        long_candidates=long_cand,
        short_candidates=short_cand,
        watchlist=watch,
        signals=flat,
        market_context=market_context,
        sector_context=sector_context,
    )

    if settings.persist_signal_runs:
        try:
            await conn.execute(
                """
                INSERT INTO signal_runs (universe_version, horizon, payload)
                VALUES ($1, $2, $3::jsonb)
                """,
                universe_version,
                horizon.value,
                json.dumps(payload.model_dump(mode="json")),
            )
        except Exception as e:
            logger.warning("signal_runs insert failed: %s", e)

    return payload


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready(pool: asyncpg.Pool = Depends(get_pool)) -> dict[str, str]:
    await pool.fetchval("SELECT 1")
    return {"status": "ready"}


@app.get("/v1/sector-sentiment", response_model=SectorSentimentPayload)
async def get_sector_sentiment(
    _: None = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool),
) -> SectorSentimentPayload:
    async with pool.acquire() as conn:
        rows = await _fetch_sector_sentiment_latest(conn)
        as_of = rows[0].as_of_date if rows else None
        return SectorSentimentPayload(as_of_date=as_of, rows=rows)


@app.get("/v1/signals", response_model=SignalsPayload)
async def get_signals(
    horizon: Horizon = Query(default=Horizon.d1),
    limit: int = Query(default=50, ge=1, le=200),
    _: None = Depends(require_auth),
    settings: Settings = Depends(get_settings),
    pool: asyncpg.Pool = Depends(get_pool),
) -> SignalsPayload:
    async with pool.acquire() as conn:
        return await build_signals(conn, settings, horizon, limit)


@app.get("/public/v1/signals", response_model=SignalsPayload)
async def get_signals_public(
    horizon: Horizon = Query(default=Horizon.d1),
    limit: int = Query(default=50, ge=1, le=200),
    _: None = Depends(require_public_ui_enabled),
    settings: Settings = Depends(get_settings),
    pool: asyncpg.Pool = Depends(get_pool),
) -> SignalsPayload:
    async with pool.acquire() as conn:
        return await build_signals(conn, settings, horizon, limit)


@app.get("/public/v1/sector-sentiment", response_model=SectorSentimentPayload)
async def get_sector_sentiment_public(
    _: None = Depends(require_public_ui_enabled),
    pool: asyncpg.Pool = Depends(get_pool),
) -> SectorSentimentPayload:
    async with pool.acquire() as conn:
        rows = await _fetch_sector_sentiment_latest(conn)
        as_of = rows[0].as_of_date if rows else None
        return SectorSentimentPayload(as_of_date=as_of, rows=rows)


_web_dir = _web_root()
if _web_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="static")
else:
    logger.warning("Static UI directory missing at %s — skipping StaticFiles mount", _web_dir)


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
