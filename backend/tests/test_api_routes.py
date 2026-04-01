from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_adobe_status() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "adobe" in payload


def test_audit_rejects_oversized_batch(monkeypatch) -> None:
    from app.api.routes import _job_managers
    from app.core.config import get_settings

    _job_managers.clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "audit_max_batch_size", 1)
    response = client.post("/audit", json={"urls": ["https://example.com/a.pdf", "https://example.com/b.pdf"]})
    assert response.status_code == 400


def test_audit_start_returns_job_id(monkeypatch) -> None:
    from app.api.routes import _job_managers
    from app.services.audit_job_service import JobManager

    async def fake_run_job(self, state):  # type: ignore[no-untyped-def]
        return None

    _job_managers.clear()
    monkeypatch.setattr(JobManager, "_run_job", fake_run_job)
    response = client.post("/audit", json={"urls": ["https://example.com/a.pdf"], "use_adobe": False})
    assert response.status_code == 200
    assert "job_id" in response.json()


def test_status_404_for_missing_job() -> None:
    response = client.get("/audit/missing/status")
    assert response.status_code == 404


def test_report_404_for_missing_job() -> None:
    response = client.get("/audit/missing/report")
    assert response.status_code == 404
