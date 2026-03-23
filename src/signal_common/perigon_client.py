"""Perigon news API client (Bearer auth, paginated article fetch)."""

from __future__ import annotations

from typing import Any

import httpx

from signal_common.config import Settings, get_settings


class PerigonClient:
    """Perigon News API — GET /v1/articles/all (Bearer token)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._key = self.settings.perigon_api_key
        self._url = self.settings.perigon_articles_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}"}

    def _default_params(self) -> dict[str, Any]:
        """Optional filters from settings (e.g. country, language, category)."""
        p: dict[str, Any] = {}
        if self.settings.perigon_country:
            p["country"] = self.settings.perigon_country
        if self.settings.perigon_language:
            p["language"] = self.settings.perigon_language
        if self.settings.perigon_category:
            p["category"] = self.settings.perigon_category
        return p

    async def fetch_page(
        self,
        page: int = 0,
        size: int = 100,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "size": size, **self._default_params()}
        if extra_params:
            params.update(extra_params)
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(self._url, headers=self._headers(), params=params)
            r.raise_for_status()
            return r.json()

    async def fetch_all(
        self,
        size: int | None = None,
        max_pages: int | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        size = size if size is not None else self.settings.perigon_page_size
        max_pages = max_pages if max_pages is not None else self.settings.perigon_max_pages
        out: list[dict[str, Any]] = []
        for p in range(max_pages):
            data = await self.fetch_page(page=p, size=size, extra_params=extra_params)
            batch = data.get("articles") or []
            if not batch:
                break
            out.extend(batch)
            if len(batch) < size:
                break
        return out
