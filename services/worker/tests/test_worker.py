from __future__ import annotations

import json
from types import SimpleNamespace

from app.config import Settings
from app.worker import TaskWorker


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    def incr(self, key: str) -> int:
        current = int(self.store.get(key, "0")) + 1
        self.store[key] = str(current)
        return current


class FakeChannel:
    def __init__(self) -> None:
        self.acked: list[int] = []
        self.nacked: list[int] = []

    def basic_ack(self, delivery_tag: int) -> None:
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        self.nacked.append(delivery_tag)


def test_process_message_persists_result_and_acks() -> None:
    fake_redis = FakeRedis()
    worker = TaskWorker(Settings(), redis_client=fake_redis)
    channel = FakeChannel()
    method = SimpleNamespace(delivery_tag=99)
    body = json.dumps({"task_id": "task-1", "payload": {"value": 5}}).encode()

    worker.process_message(channel, method, None, body)

    assert channel.acked == [99]
    assert fake_redis.store["worker:processed_total"] == "1"
    stored = json.loads(fake_redis.store["task-result:task-1"])
    assert stored["status"] == "processed"
    assert stored["processor_version"] == "v1"


def test_process_message_nacks_on_bad_payload() -> None:
    fake_redis = FakeRedis()
    worker = TaskWorker(Settings(), redis_client=fake_redis)
    channel = FakeChannel()
    method = SimpleNamespace(delivery_tag=42)

    try:
        worker.process_message(channel, method, None, b"{bad-json")
    except Exception:
        pass

    assert channel.nacked == [42]

