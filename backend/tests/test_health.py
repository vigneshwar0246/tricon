from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.llm import OllamaUnavailableError


def test_health_reports_backend_and_model_availability() -> None:
    expected_model = get_settings().ollama_model
    with TestClient(app) as client:
        app.state.ollama.list_models = AsyncMock(return_value=[expected_model, "gemma2:2b"])
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["backend"]["available"] is True
    assert body["ollama"]["available"] is True
    assert body["services"]["api"] is True
    assert body["services"]["llm"] is True
    assert body["models"]["llm"] == expected_model
    assert isinstance(body["services"]["stt"], bool)
    assert isinstance(body["services"]["tts"], bool)


def test_health_reports_ollama_offline_without_failing_api() -> None:
    with TestClient(app) as client:
        app.state.ollama.list_models = AsyncMock(side_effect=OllamaUnavailableError("offline"))
        response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["api"] is True
    assert body["services"]["llm"] is False
    assert body["ollama"]["status"] == "unavailable"


def test_diagnostics_does_not_claim_cuda_from_device_presence() -> None:
    configured_model = get_settings().ollama_model
    with TestClient(app) as client:
        app.state.ollama.list_models = AsyncMock(return_value=[configured_model])
        app.state.ollama.loaded_models = AsyncMock(return_value=[{"name": configured_model, "size_vram_bytes": 100}])
        response = client.get("/api/diagnostics")

    assert response.status_code == 200
    body = response.json()
    assert body["stt"]["configured_device"] == app.state.stt.settings.stt_device
    assert body["cuda"]["inference_verified"] is False
    assert body["ollama_loaded_models"][0]["name"] == configured_model
    assert set(body["languages"]) == {"en", "hi"}
    assert "system" in body and "checks" in body
