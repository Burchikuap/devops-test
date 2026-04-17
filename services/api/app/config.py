from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(slots=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "api")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _int("PORT", 8000)
    rabbitmq_host: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rabbitmq_port: int = _int("RABBITMQ_PORT", 5672)
    rabbitmq_username: str = os.getenv("RABBITMQ_USERNAME", "app")
    rabbitmq_password: str = os.getenv("RABBITMQ_PASSWORD", "change-me-rabbitmq")
    rabbitmq_queue: str = os.getenv("RABBITMQ_QUEUE", "task-queue")
    valkey_host: str = os.getenv("VALKEY_HOST", "valkey")
    valkey_port: int = _int("VALKEY_PORT", 6379)
    valkey_password: str = os.getenv("VALKEY_PASSWORD", "change-me-valkey")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-dev-secret")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "devops-clients")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "devops-test-suite")
    result_key_prefix: str = os.getenv("RESULT_KEY_PREFIX", "task-result")
    processed_counter_key: str = os.getenv("PROCESSED_COUNTER_KEY", "worker:processed_total")
    result_ttl_seconds: int = _int("RESULT_TTL_SECONDS", 86400)
    rabbitmq_heartbeat: int = _int("RABBITMQ_HEARTBEAT", 30)
    rabbitmq_blocked_connection_timeout: int = _int("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", 30)


def get_settings() -> Settings:
    return Settings()

