from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(slots=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "worker")
    rabbitmq_host: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rabbitmq_port: int = _int("RABBITMQ_PORT", 5672)
    rabbitmq_username: str = os.getenv("RABBITMQ_USERNAME", "app")
    rabbitmq_password: str = os.getenv("RABBITMQ_PASSWORD", "change-me-rabbitmq")
    rabbitmq_queue: str = os.getenv("RABBITMQ_QUEUE", "task-queue")
    valkey_host: str = os.getenv("VALKEY_HOST", "valkey")
    valkey_port: int = _int("VALKEY_PORT", 6379)
    valkey_password: str = os.getenv("VALKEY_PASSWORD", "change-me-valkey")
    result_key_prefix: str = os.getenv("RESULT_KEY_PREFIX", "task-result")
    processed_counter_key: str = os.getenv("PROCESSED_COUNTER_KEY", "worker:processed_total")
    result_ttl_seconds: int = _int("RESULT_TTL_SECONDS", 86400)
    prefetch_count: int = _int("PREFETCH_COUNT", 10)
    poll_interval_seconds: int = _int("POLL_INTERVAL_SECONDS", 2)
    metrics_port: int = _int("METRICS_PORT", 9100)


def get_settings() -> Settings:
    return Settings()

