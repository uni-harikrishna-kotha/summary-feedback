import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.config import Settings
from app.services.job_store import job_store


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_settings():
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o",
        conversations_grpc_host="localhost",
        conversations_grpc_port=50051,
        tenant_summary_template="Summarize key points and action items.",
        summary_field_name="generated_summary",
        environment="prod",
    )
