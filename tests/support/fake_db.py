"""
Minimal asyncpg stand-ins for testing `build_signals` without a real database.

`build_signals` issues a fixed sequence of `fetchval` / `fetch` / `fetchrow` / `execute` calls.
Use `FakeConnection.from_queue` with responses in that order (see tests/test_build_signals.py).
"""

from __future__ import annotations

from collections import deque
from typing import Any


class FakeConnection:
    def __init__(self, queue: deque[Any]) -> None:
        self._q = queue

    @classmethod
    def from_queue(cls, responses: list[Any]) -> FakeConnection:
        return cls(deque(responses))

    def _pop(self, kind: str) -> Any:
        if not self._q:
            raise RuntimeError(f"FakeConnection exhausted on {kind}")
        return self._q.popleft()

    async def fetch(self, query: str, *args: Any) -> list[Any]:
        return self._pop("fetch")

    async def fetchrow(self, query: str, *args: Any) -> Any:
        return self._pop("fetchrow")

    async def fetchval(self, query: str, *args: Any) -> Any:
        return self._pop("fetchval")

    async def execute(self, query: str, *args: Any) -> str:
        return self._pop("execute")


class FakePool:
    """asyncpg pool stub: `async with pool.acquire() as conn`."""

    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn

    def acquire(self) -> _AcquireConn:
        return _AcquireConn(self._conn)


class _AcquireConn:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> FakeConnection:
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        return None
