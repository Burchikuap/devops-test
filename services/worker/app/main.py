from __future__ import annotations

import signal

from prometheus_client import start_http_server

from .config import get_settings
from .worker import TaskWorker


def main() -> None:
    settings = get_settings()
    start_http_server(settings.metrics_port)
    worker = TaskWorker(settings)

    def _shutdown(signum, frame) -> None:  # noqa: ANN001
        worker.stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    worker.run()


if __name__ == "__main__":
    main()

