"""
FinBERT sentiment for `news_articles` missing `news_sentiment`; optional Kafka consumer if NLP_KAFKA=1.

Requires `pip install -e ".[ml]"`. Heavy deps (torch/transformers).
"""

from __future__ import annotations

import asyncio
import logging
import os

import asyncpg

from signal_common.config import get_settings
from signal_common.db import create_pool, run_migrations
from signal_common.kafka_bus import TOPIC_NEWS_RAW, make_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def score_from_finbert(pipe, text: str) -> float:
    """Map FinBERT tone output to [-1, 1]."""
    if not text or not text.strip():
        return 0.0
    out = pipe(text[:2048])[0]
    label = (out.get("label") or "").lower()
    score = float(out.get("score") or 0.5)
    if "positive" in label:
        return score
    if "negative" in label:
        return -score
    return 0.0


async def process_backlog(pool: asyncpg.Pool, pipe) -> None:
    settings = get_settings()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT na.id, na.headline, na.body FROM news_articles na
            LEFT JOIN news_sentiment ns ON ns.news_id = na.id
            WHERE ns.news_id IS NULL
            ORDER BY na.published_at DESC
            LIMIT 500
            """
        )

    for r in rows:
        nid = int(r["id"])
        text = (r["headline"] or "") + ". " + (r["body"] or "")
        try:
            s = score_from_finbert(pipe, text)
        except Exception as e:
            logger.warning("NLP failed for news %s: %s", nid, e)
            s = 0.0
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO news_sentiment (news_id, score, model)
                VALUES ($1, $2, $3)
                ON CONFLICT (news_id) DO UPDATE SET score = EXCLUDED.score, model = EXCLUDED.model, updated_at = NOW()
                """,
                nid,
                s,
                settings.finbert_model,
            )
        logger.info("Sentiment news_id=%s score=%.3f", nid, s)


async def kafka_loop(pool: asyncpg.Pool, pipe) -> None:
    settings = get_settings()
    consumer = await make_consumer(TOPIC_NEWS_RAW, group_id=settings.kafka_consumer_group + "-nlp")
    try:
        async for msg in consumer:
            val = msg.value
            if not val:
                continue
            news_id = val.get("news_id")
            if not news_id:
                continue
            text = (val.get("headline") or "") + ". " + (val.get("body") or "")
            try:
                s = score_from_finbert(pipe, text)
            except Exception as e:
                logger.warning("NLP kafka: %s", e)
                s = 0.0
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO news_sentiment (news_id, score, model)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (news_id) DO UPDATE SET score = EXCLUDED.score, updated_at = NOW()
                    """,
                    int(news_id),
                    s,
                    settings.finbert_model,
                )
    finally:
        await consumer.stop()


async def run() -> None:
    settings = get_settings()
    pool = await create_pool()
    await run_migrations(pool)

    from transformers import pipeline

    pipe = pipeline("sentiment-analysis", model=settings.finbert_model, tokenizer=settings.finbert_model)

    await process_backlog(pool, pipe)

    if os.environ.get("NLP_KAFKA", "").lower() in ("1", "true", "yes"):
        await kafka_loop(pool, pipe)

    await pool.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
