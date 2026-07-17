from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_db_status() -> None:
    """No live DB is guaranteed in the unit-test environment, so only assert the
    endpoint responds with a well-formed status rather than a specific outcome."""
    response = client.get("/ready")

    assert response.status_code in (200, 503)
    assert response.json()["status"] in ("ready", "not ready")
