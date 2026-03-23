"""Kafka/Redpanda helpers: JSON-valued topics for OHLCV and raw news."""

from __future__ import annotations

import json
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from signal_common.config import Settings, get_settings

TOPIC_OHLCV_1M = "ohlcv.1m"
TOPIC_OHLCV_1H = "ohlcv.1h"
TOPIC_OHLCV_1D = "ohlcv.1d"
TOPIC_NEWS_RAW = "news.raw"


def json_serializer(obj: Any) -> bytes:
    return json.dumps(obj, default=str).encode("utf-8")


def json_deserializer(raw: bytes | memoryview) -> Any:
    return json.loads(raw.decode("utf-8"))


async def make_producer(settings: Settings | None = None) -> AIOKafkaProducer:
    settings = settings or get_settings()
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=json_serializer,
    )
    await producer.start()
    return producer


async def make_consumer(
    *topics: str,
    group_id: str | None = None,
    settings: Settings | None = None,
) -> AIOKafkaConsumer:
    settings = settings or get_settings()
    gid = group_id or settings.kafka_consumer_group
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=gid,
        value_deserializer=json_deserializer,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    return consumer
