import asyncio
import time
import uuid
import pytest
import jwt
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import Settings, get_settings
from app.dependencies import get_fetcher
from app.models.responses import ScoringJobResult, CallScoreResult
from app.services.job_store import JobStore, job_store


def _make_valid_token(tenant_id: str) -> str:
    payload = {"tenant": tenant_id, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, "secret", algorithm="HS256")


def _make_settings_with_template():
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o",
        tenant_summary_template="Summarize key points and action items.",
        summary_field_name="generated_summary",
        environment="prod",
        cors_origins=["http://localhost:4200"],
    )


@pytest.fixture(autouse=True)
def reset_job_store():
    job_store._store.clear()
    yield
    job_store._store.clear()


@pytest.fixture
def client_with_template():
    settings = _make_settings_with_template()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_fetcher] = lambda: AsyncMock()
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_valid_post_returns_202(client_with_template):
    token = _make_valid_token("acme-corp")
    response = client_with_template.post(
        "/v1/scoring/run",
        json={"tenant_id": "acme-corp", "jwt_token": token},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"
    assert data["tenant_id"] == "acme-corp"


def test_get_completed_job(client_with_template):
    job_id = "score_test001"
    job_store._store[job_id] = {
        "job_id": job_id,
        "tenant_id": "acme-corp",
        "status": "completed",
        "overall_score": 7.5,
        "window_start": "2026-03-16T17:17:00Z",
        "window_end": "2026-03-17T17:17:00Z",
        "calls_scored": 8,
        "calls_missing_summary": 2,
        "calls_unscored": 0,
        "computed_at": "2026-03-17T17:17:30Z",
        "calls": [],
    }
    response = client_with_template.get(f"/v1/scoring/run/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["overall_score"] == 7.5
    assert data["status"] == "completed"


def test_invalid_jwt_returns_401(client_with_template):
    response = client_with_template.post(
        "/v1/scoring/run",
        json={"tenant_id": "acme-corp", "jwt_token": "invalid-token"},
    )
    assert response.status_code == 401


def test_unknown_job_id_returns_404(client_with_template):
    response = client_with_template.get("/v1/scoring/run/nonexistent_job_id")
    assert response.status_code == 404


def test_post_without_template_returns_422():
    settings = Settings(
        openai_api_key="test-key",
        tenant_summary_template="",  # empty
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_fetcher] = lambda: AsyncMock()
    client = TestClient(app)

    token = _make_valid_token("acme-corp")
    response = client.post(
        "/v1/scoring/run",
        json={"tenant_id": "acme-corp", "jwt_token": token},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_two_posts_return_distinct_job_ids(client_with_template):
    token = _make_valid_token("acme-corp")
    r1 = client_with_template.post(
        "/v1/scoring/run",
        json={"tenant_id": "acme-corp", "jwt_token": token},
    )
    r2 = client_with_template.post(
        "/v1/scoring/run",
        json={"tenant_id": "acme-corp", "jwt_token": token},
    )
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["job_id"] != r2.json()["job_id"]
