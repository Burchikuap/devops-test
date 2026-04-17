from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class FakePublisher:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def publish(self, message: dict) -> None:
        self.messages.append(message)

    def get_queue_depth(self) -> int:
        return len(self.messages)


class FakeStats:
    def snapshot(self) -> dict[str, int]:
        return {
            "valkey_keys_count": 3,
            "queue_backlog": 1,
            "worker_processed_count": 2,
        }


def settings() -> Settings:
    return Settings(
        jwt_secret="test-secret-0123456789abcdef012345",
        jwt_audience="tests",
        jwt_issuer="unit-tests",
    )


def test_post_task_requires_valid_jwt() -> None:
    app = create_app(settings=settings(), publisher=FakePublisher(), stats_collector=FakeStats())
    client = TestClient(app)

    response = client.post("/task", json={"payload": {"x": 1}})
    assert response.status_code == 401


def test_post_task_accepts_valid_jwt() -> None:
    app_settings = settings()
    publisher = FakePublisher()
    app = create_app(settings=app_settings, publisher=publisher, stats_collector=FakeStats())
    client = TestClient(app)

    import jwt

    token = jwt.encode(
        {"sub": "tester", "aud": "tests", "iss": "unit-tests"},
        "test-secret-0123456789abcdef012345",
        algorithm="HS256",
    )
    response = client.post(
        "/task",
        json={"task_id": "task-1", "payload": {"x": 1}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    assert response.json()["task_id"] == "task-1"
    assert publisher.messages[0]["submitted_by"] == "tester"


def test_stats_endpoint_returns_expected_shape() -> None:
    app = create_app(settings=settings(), publisher=FakePublisher(), stats_collector=FakeStats())
    client = TestClient(app)

    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json() == {
        "valkey_keys_count": 3,
        "queue_backlog": 1,
        "worker_processed_count": 2,
    }
