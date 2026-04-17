from __future__ import annotations

import json
from dataclasses import dataclass

import pika

from .config import Settings


@dataclass(slots=True)
class RabbitMQPublisher:
    settings: Settings

    def _parameters(self) -> pika.ConnectionParameters:
        credentials = pika.PlainCredentials(
            username=self.settings.rabbitmq_username,
            password=self.settings.rabbitmq_password,
        )
        return pika.ConnectionParameters(
            host=self.settings.rabbitmq_host,
            port=self.settings.rabbitmq_port,
            credentials=credentials,
            heartbeat=self.settings.rabbitmq_heartbeat,
            blocked_connection_timeout=self.settings.rabbitmq_blocked_connection_timeout,
        )

    def publish(self, message: dict) -> None:
        connection = pika.BlockingConnection(self._parameters())
        try:
            channel = connection.channel()
            channel.queue_declare(queue=self.settings.rabbitmq_queue, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=self.settings.rabbitmq_queue,
                body=json.dumps(message).encode("utf-8"),
                properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
            )
        finally:
            connection.close()

    def get_queue_depth(self) -> int:
        connection = pika.BlockingConnection(self._parameters())
        try:
            channel = connection.channel()
            result = channel.queue_declare(queue=self.settings.rabbitmq_queue, durable=True, passive=True)
            return int(result.method.message_count)
        finally:
            connection.close()

