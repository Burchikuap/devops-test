from __future__ import annotations

from dataclasses import dataclass

import redis

from .config import Settings
from .queue import RabbitMQPublisher


@dataclass(slots=True)
class StatsCollector:
    settings: Settings
    publisher: RabbitMQPublisher

    def _redis(self) -> redis.Redis:
        return redis.Redis(
            host=self.settings.valkey_host,
            port=self.settings.valkey_port,
            password=self.settings.valkey_password,
            decode_responses=True,
        )

    def snapshot(self) -> dict[str, int]:
        client = self._redis()
        keys_count = int(client.dbsize())
        processed_raw = client.get(self.settings.processed_counter_key) or 0
        queue_backlog = self.publisher.get_queue_depth()
        return {
            "valkey_keys_count": keys_count,
            "queue_backlog": int(queue_backlog),
            "worker_processed_count": int(processed_raw),
        }

