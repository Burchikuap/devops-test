from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from threading import Event

import pika
import redis

from .config import Settings
from .metrics import FAILED_COUNTER, LAST_SUCCESS_TIMESTAMP, PROCESS_DURATION, PROCESSED_COUNTER


class TaskWorker:
    def __init__(self, settings: Settings, redis_client: redis.Redis | None = None) -> None:
        self.settings = settings
        self.stop_event = Event()
        self.redis = redis_client or redis.Redis(
            host=settings.valkey_host,
            port=settings.valkey_port,
            password=settings.valkey_password,
            decode_responses=True,
        )
        self.connection: pika.BlockingConnection | None = None
        self.channel = None

    def _connect(self) -> None:
        if self.connection and self.channel and self.connection.is_open:
            return
        credentials = pika.PlainCredentials(self.settings.rabbitmq_username, self.settings.rabbitmq_password)
        parameters = pika.ConnectionParameters(
            host=self.settings.rabbitmq_host,
            port=self.settings.rabbitmq_port,
            credentials=credentials,
            heartbeat=30,
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.settings.rabbitmq_queue, durable=True)
        self.channel.basic_qos(prefetch_count=self.settings.prefetch_count)

    def process_message(self, channel, method, properties, body: bytes) -> None:  # noqa: ANN001
        started = time.perf_counter()
        try:
            message = json.loads(body.decode("utf-8"))
            task_id = message["task_id"]
            result = {
                "task_id": task_id,
                "status": "processed",
                "payload": message.get("payload", {}),
                "processor_version": "v1",
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            redis_key = f"{self.settings.result_key_prefix}:{task_id}"
            self.redis.set(redis_key, json.dumps(result), ex=self.settings.result_ttl_seconds)
            self.redis.incr(self.settings.processed_counter_key)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            PROCESSED_COUNTER.inc()
            LAST_SUCCESS_TIMESTAMP.set(time.time())
        except Exception:
            FAILED_COUNTER.inc()
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            raise
        finally:
            PROCESS_DURATION.observe(time.perf_counter() - started)

    def run(self) -> None:
        self._connect()
        assert self.channel is not None
        while not self.stop_event.is_set():
            method, properties, body = self.channel.basic_get(queue=self.settings.rabbitmq_queue, auto_ack=False)
            if method is None:
                time.sleep(self.settings.poll_interval_seconds)
                continue
            try:
                self.process_message(self.channel, method, properties, body)
            except Exception:
                time.sleep(1)

    def stop(self) -> None:
        self.stop_event.set()
        if self.channel is not None and getattr(self.channel, "is_open", False):
            self.channel.close()
        if self.connection is not None and self.connection.is_open:
            self.connection.close()
