from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import redis
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, make_asgi_app

from .auth import verify_jwt_token
from .config import Settings, get_settings
from .queue import RabbitMQPublisher
from .stats import StatsCollector

REQUEST_COUNTER = Counter("api_requests_total", "Total HTTP requests handled by the API.", ["endpoint", "method", "status"])
TASK_COUNTER = Counter("api_tasks_published_total", "Published tasks.")
REQUEST_LATENCY = Histogram("api_request_duration_seconds", "API request latency.", ["endpoint"])


class TaskRequest(BaseModel):
    task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


def create_app(
    settings: Settings | None = None,
    publisher: RabbitMQPublisher | None = None,
    stats_collector: StatsCollector | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    publisher = publisher or RabbitMQPublisher(settings)
    stats_collector = stats_collector or StatsCollector(settings=settings, publisher=publisher)

    app = FastAPI(title="DevOps Test API", version="1.0.0")
    app.mount("/metrics", make_asgi_app())
    app.state.settings = settings
    app.state.publisher = publisher
    app.state.stats = stats_collector

    @app.post("/task")
    def create_task(payload: TaskRequest, authorization: str | None = Header(default=None)) -> JSONResponse:
        started = time.perf_counter()
        try:
            token = _extract_bearer_token(authorization)
            claims = verify_jwt_token(token, settings)
            task_id = payload.task_id or str(uuid4())
            message = {"task_id": task_id, "payload": payload.payload, "submitted_by": claims.get("sub", "unknown")}
            publisher.publish(message)
            TASK_COUNTER.inc()
            REQUEST_COUNTER.labels(endpoint="/task", method="POST", status="202").inc()
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": "accepted", "task_id": task_id})
        finally:
            REQUEST_LATENCY.labels(endpoint="/task").observe(time.perf_counter() - started)

    @app.get("/stats")
    def get_stats() -> dict[str, int]:
        started = time.perf_counter()
        try:
            snapshot = stats_collector.snapshot()
            REQUEST_COUNTER.labels(endpoint="/stats", method="GET", status="200").inc()
            return snapshot
        finally:
            REQUEST_LATENCY.labels(endpoint="/stats").observe(time.perf_counter() - started)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        REQUEST_COUNTER.labels(endpoint="/healthz", method="GET", status="200").inc()
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        started = time.perf_counter()
        try:
            redis_client = redis.Redis(
                host=settings.valkey_host,
                port=settings.valkey_port,
                password=settings.valkey_password,
                decode_responses=True,
            )
            redis_client.ping()
            publisher.get_queue_depth()
            REQUEST_COUNTER.labels(endpoint="/readyz", method="GET", status="200").inc()
            return {"status": "ready"}
        except Exception as exc:
            REQUEST_COUNTER.labels(endpoint="/readyz", method="GET", status="503").inc()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        finally:
            REQUEST_LATENCY.labels(endpoint="/readyz").observe(time.perf_counter() - started)

    @app.get("/")
    def root() -> dict[str, str]:
        REQUEST_COUNTER.labels(endpoint="/", method="GET", status="200").inc()
        return {"service": settings.service_name}

    return app


app = create_app()

