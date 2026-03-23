"""
Ingest Perigon articles: dedupe by (provider, article_id), link tickers via uppercase tokens in text.

Ticker matching requires symbols to exist (run universe cron first). Skips on non-NYSE days.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

import asyncpg

from signal_common.config import get_settings
from signal_common.db import create_pool, parse_polygon_ticker, run_migrations
from signal_common.job_guards import exit_if_not_nyse_trading_day
from signal_common.kafka_bus import TOPIC_NEWS_RAW, make_producer
from signal_common.perigon_client import PerigonClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROVIDER = "perigon"


def parse_pub_date(s: str | None) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def tickers_from_text(text: str, allowed_upper: set[str]) -> list[str]:
    """Match 2–5 letter all-caps tokens that exist in our symbol table."""
    if not text or not allowed_upper:
        return []
    found: set[str] = set()
    for m in re.finditer(r"\b([A-Z]{2,5})\b", text):
        t = m.group(1)
        if t in allowed_upper:
            found.add(t)
    return sorted(found)


async def load_symbol_ticker_set(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch("SELECT upper(ticker) AS t FROM symbols WHERE is_active IS NOT FALSE")
    return {r["t"] for r in rows if r["t"]}


def perigon_article_to_record(
    art: dict,
    allowed_tickers: set[str],
) -> tuple[str, str, str, str, str, str, datetime, list[str]]:
    aid = str(art.get("articleId") or art.get("id") or "")
    title = art.get("title") or ""
    desc = art.get("description") or ""
    content = art.get("content") or ""
    body = content if len(content) > len(desc) else desc
    if not body:
        body = desc or title
    author = art.get("authorsByline") or ""
    src = ""
    if isinstance(art.get("source"), dict):
        src = str(art["source"].get("domain") or "")
    url = art.get("url") or ""
    pub = parse_pub_date(art.get("pubDate"))
    text_blob = f"{title}\n{desc}\n{content}"[:50000]
    tickers = [parse_polygon_ticker(t) for t in tickers_from_text(text_blob, allowed_tickers)]
    return aid, title, body, author, src, url, pub, tickers


async def run() -> None:
    exit_if_not_nyse_trading_day()
    settings = get_settings()
    if not settings.perigon_api_key:
        raise RuntimeError("PERIGON_API_KEY is required")

    pool = await create_pool()
    await run_migrations(pool)
    client = PerigonClient()
    producer = await make_producer()

    async with pool.acquire() as conn:
        allowed = await load_symbol_ticker_set(conn)

    items = await client.fetch_all()
    logger.info("Fetched %d articles from Perigon", len(items))

    async with pool.acquire() as conn:
        for art in items:
            aid, headline, body, author, source, url, pub, tickers = perigon_article_to_record(
                art, allowed
            )
            if not aid:
                continue

            row = await conn.fetchrow(
                """
                INSERT INTO news_articles (provider, article_id, headline, body, published_at, author, source, url, raw)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                ON CONFLICT (provider, article_id) DO UPDATE SET
                    headline = EXCLUDED.headline,
                    body = EXCLUDED.body,
                    raw = EXCLUDED.raw
                RETURNING id
                """,
                PROVIDER,
                aid,
                headline,
                body,
                pub,
                author,
                source,
                url,
                json.dumps(art),
            )
            if not row:
                continue
            news_id = int(row["id"])

            for t in tickers:
                sid = await conn.fetchval("SELECT id FROM symbols WHERE upper(ticker) = upper($1)", t)
                if sid:
                    await conn.execute(
                        """
                        INSERT INTO news_article_symbols (news_id, symbol_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                        """,
                        news_id,
                        sid,
                    )

            await producer.send_and_wait(
                TOPIC_NEWS_RAW,
                value={
                    "news_id": news_id,
                    "article_id": aid,
                    "headline": headline,
                    "body": body[:8000],
                    "published_at": pub.isoformat(),
                    "author": author,
                    "source": source,
                    "tickers": tickers,
                },
            )

    await producer.stop()
    await pool.close()
    logger.info("News ingest complete")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
