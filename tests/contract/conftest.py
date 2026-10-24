import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app

MOCKS = Path(__file__).resolve().parents[2] / "api" / "mocks"


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("SLOT_TO_STOP_DATA", "mock")
    return TestClient(create_app())


@pytest.fixture
def maria_request() -> dict:
    """Synthetic patient 'Maria' (fictional composite). See api/mocks/plan_request_maria.json."""
    data = json.loads((MOCKS / "plan_request_maria.json").read_text(encoding="utf-8"))
    data.pop("_mock_notice")
    return data
