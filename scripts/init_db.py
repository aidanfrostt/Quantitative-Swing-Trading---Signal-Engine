#!/usr/bin/env python3
"""Apply ordered SQL files in `migrations/` using `DATABASE_URL` (idempotent via `schema_migrations`)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from signal_common.db import create_pool, run_migrations


async def main() -> None:
    pool = await create_pool()
    try:
        await run_migrations(pool)
        print("Migrations applied.")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
