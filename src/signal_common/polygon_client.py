"""Polygon.io REST client: universe, aggregates, snapshots, and financial endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx

from signal_common.config import Settings, get_settings


class PolygonClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._base = self.settings.polygon_base_url.rstrip("/")
        self._key = self.settings.polygon_api_key

    def _headers(self) -> dict[str, str]:
        return {}

    def _params(self) -> dict[str, str]:
        return {"apiKey": self._key}

    async def get_tickers_page(self, next_url: str | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if next_url:
                r = await client.get(next_url)
            else:
                url = f"{self._base}/v3/reference/tickers"
                r = await client.get(
                    url,
                    params={**self._params(), "market": "stocks", "active": "true", "limit": "1000"},
                )
            r.raise_for_status()
            return r.json()

    async def get_snapshot_all(self) -> dict[str, Any]:
        """Convenience snapshot (requires appropriate Polygon plan)."""
        url = f"{self._base}/v2/snapshot/locale/us/markets/stocks/tickers"
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.get(url, params=self._params())
            r.raise_for_status()
            return r.json()

    async def get_snapshot_ticker(self, ticker: str) -> dict[str, Any]:
        url = f"{self._base}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
        async with httpx.AsyncClient(timeout=60.0) as client:
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
            r = await client.get(url, params={**self._params(), "limit": "50000", "sort": "asc"})
            r.raise_for_status()
            return r.json()

    async def get_grouped_daily(self, day: date) -> dict[str, Any]:
        url = f"{self._base}/v2/aggs/grouped/locale/us/market/stocks/{day.isoformat()}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.get(url, params=self._params())
            r.raise_for_status()
            return r.json()

    async def get_financial_ratios_v1(self, ticker: str, limit: int = 5) -> dict[str, Any]:
        """Preferred ratios endpoint (plan-dependent). See Polygon/Massive docs."""
        url = f"{self._base}/stocks/financials/v1/ratios"
        params = {**self._params(), "ticker": ticker, "limit": str(limit)}
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    async def get_ticker_details_v3(self, ticker: str) -> dict[str, Any]:
        """GET /v3/reference/tickers/{ticker} — sector/SIC, market cap, etc."""
        url = f"{self._base}/v3/reference/tickers/{ticker}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(url, params=self._params())
            if r.status_code != 200:
                return {}
            return r.json()

    async def get_vx_reference_financials(self, ticker: str, limit: int = 1) -> dict[str, Any]:
        """Fallback SEC-derived financials if ratios v1 is unavailable."""
        url = f"{self._base}/vX/reference/financials"
        params = {**self._params(), "ticker": ticker, "limit": str(limit)}
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
