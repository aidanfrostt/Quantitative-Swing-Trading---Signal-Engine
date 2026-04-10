"""Polygon throttle: minimum spacing between calls (Stocks Basic: 5/min ≈ 12s apart)."""

from __future__ import annotations

import asyncio
import time

import pytest

from signal_common.polygon_client import _PolygonSpacingLimiter


@pytest.mark.asyncio
async def test_spacing_limiter_enforces_min_interval() -> None:
    lim = _PolygonSpacingLimiter(10)  # 6s between calls
    t0 = time.monotonic()
    await lim.acquire()
    await lim.acquire()
    assert time.monotonic() - t0 >= 5.9


@pytest.mark.asyncio
async def test_spacing_limiter_parallel_acquires_serialized() -> None:
    lim = _PolygonSpacingLimiter(5)  # 12s between

    async def go() -> None:
        await lim.acquire()

    t0 = time.monotonic()
    await asyncio.gather(go(), go(), go())
    assert time.monotonic() - t0 >= 23.0
