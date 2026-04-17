from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

PROCESSED_COUNTER = Counter("worker_processed_messages_total", "Messages processed successfully.")
FAILED_COUNTER = Counter("worker_failed_messages_total", "Messages failed and requeued.")
PROCESS_DURATION = Histogram("worker_message_processing_seconds", "Message processing latency.")
LAST_SUCCESS_TIMESTAMP = Gauge("worker_last_success_unixtime", "Unix timestamp of last successful processing.")

