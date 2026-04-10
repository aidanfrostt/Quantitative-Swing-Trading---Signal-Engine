"""Polygon.io REST client: universe, aggregates, snapshots, and financial endpoints."""

from __future__ import annotations

import asyncio
import time
from datetime import date, datetime
from typing import Any

import httpx

from signal_common.config import Settings, get_settings


class _PolygonSpacingLimiter:
    """Enforce minimum seconds between Polygon calls (Stocks Basic: 5/min → 12s spacing).

    A naive "5 per rolling 60s" window still allows 5 requests in one burst; Polygon
    often rejects that with 429. Spacing approximates one call every ``60/max_per_minute`` s.
    """

    __slots__ = ("_min_interval", "_next_ok", "_lock")

    def __init__(self, max_per_minute: int) -> None:
        m = max(1, max_per_minute)
        self._min_interval = 60.0 / m
        self._next_ok = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = max(0.0, self._next_ok - now)
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_ok = time.monotonic() + self._min_interval


class PolygonClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._base = self.settings.polygon_base_url.rstrip("/")
        self._key = self.settings.polygon_api_key
        cap = self.settings.polygon_max_calls_per_minute
        self._limiter: _PolygonSpacingLimiter | None = (
            _PolygonSpacingLimiter(cap) if cap and cap > 0 else None
        )

    def _headers(self) -> dict[str, str]:
        return {}

    def _params(self) -> dict[str, str]:
        return {"apiKey": self._key}

    async def _acquire_slot(self) -> None:
        if self._limiter:
            await self._limiter.acquire()

    async def get_tickers_page(self, next_url: str | None = None) -> dict[str, Any]:
        """Paginate reference tickers; retries on HTTP 429 with backoff."""
        delay = 2.0
        max_attempts = 12
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(max_attempts):
                await self._acquire_slot()
                if next_url:
                    r = await client.get(next_url)
                else:
                    url = f"{self._base}/v3/reference/tickers"
                    r = await client.get(
                        url,
                        params={**self._params(), "market": "stocks", "active": "true", "limit": "1000"},
                    )
                if r.status_code == 429 and attempt < max_attempts - 1:
                    ra = r.headers.get("Retry-After")
                    try:
                        wait = float(ra) if ra is not None else delay
                    except (TypeError, ValueError):
                        wait = delay
                    await asyncio.sleep(min(max(wait, 1.0), 120.0))
                    delay = min(delay * 2, 60.0)
                    continue
                r.raise_for_status()
                return r.json()

    async def get_snapshot_all(self) -> dict[str, Any]:
        """Convenience snapshot (requires appropriate Polygon plan)."""
        url = f"{self._base}/v2/snapshot/locale/us/markets/stocks/tickers"
        async with httpx.AsyncClient(timeout=120.0) as client:
            await self._acquire_slot()
            r = await client.get(url, params=self._params())
            r.raise_for_status()
            return r.json()

    async def get_snapshot_ticker(self, ticker: str) -> dict[str, Any]:
        url = f"{self._base}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._acquire_slot()
            r = await client.get(url, params=self._params())
            r.raise_for_status()
            return r.json()

    async def get_aggregates(
        self,
        ticker: str,
        multiplier: int,
        timespan: str,
        start: date,
        end: date,
    ) -> dict[str, Any]:
        """timespan: minute, hour, day."""
        if isinstance(start, datetime):
            start_d = start.date()
        else:
            start_d = start
        if isinstance(end, datetime):
            end_d = end.date()
        else:
            end_d = end
        path = f"{start_d.isoformat()}/{end_d.isoformat()}"
        url = f"{self._base}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{path}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            await self._acquire_slot()
            r = await client.get(url, params={**self._params(), "limit": "50000", "sort": "asc"})
            r.raise_for_status()
            return r.json()

    async def get_grouped_daily(self, day: date) -> dict[str, Any]:
        url = f"{self._base}/v2/aggs/grouped/locale/us/market/stocks/{day.isoformat()}"
        delay = 2.0
        max_attempts = 12
        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(max_attempts):
                await self._acquire_slot()
                r = await client.get(url, params=self._params())
                if r.status_code == 429 and attempt < max_attempts - 1:
                    ra = r.headers.get("Retry-After")
                    try:
                        wait = float(ra) if ra is not None else delay
                    except (TypeError, ValueError):
                        wait = delay
                    await asyncio.sleep(min(max(wait, 1.0), 120.0))
                    delay = min(delay * 2, 60.0)
                    continue
                r.raise_for_status()
                return r.json()

    async def get_financial_ratios_v1(self, ticker: str, limit: int = 5) -> dict[str, Any]:
        """Preferred ratios endpoint (plan-dependent). See Polygon/Massive docs."""
        url = f"{self._base}/stocks/financials/v1/ratios"
        params = {**self._params(), "ticker": ticker, "limit": str(limit)}
        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._acquire_slot()
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    async def get_ticker_details_v3(self, ticker: str) -> dict[str, Any]:
        """GET /v3/reference/tickers/{ticker} — sector/SIC, market cap, etc."""
        url = f"{self._base}/v3/reference/tickers/{ticker}"
        delay = 2.0
        max_attempts = 16
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(max_attempts):
                await self._acquire_slot()
                r = await client.get(url, params=self._params())
                if r.status_code == 429 and attempt < max_attempts - 1:
                    ra = r.headers.get("Retry-After")
                    try:
                        wait = float(ra) if ra is not None else delay
                    except (TypeError, ValueError):
                        wait = delay
                    await asyncio.sleep(min(max(wait, 1.0), 120.0))
                    delay = min(delay * 1.75, 60.0)
                    continue
                if r.status_code == 404:
                    return {}
                if r.status_code != 200:
                    return {}
                return r.json()

    async def get_vx_reference_financials(self, ticker: str, limit: int = 1) -> dict[str, Any]:
        """Fallback SEC-derived financials if ratios v1 is unavailable."""
        url = f"{self._base}/vX/reference/financials"
        params = {**self._params(), "ticker": ticker, "limit": str(limit)}
        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._acquire_slot()
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
