from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.main import app
from app.services.stt import SpeechModelNotInstalledError
import app.api.routes.voice as voice_route


def test_voice_rejects_unsupported_audio_type() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/voice",
            files={"audio": ("recording.txt", b"not audio", "text/plain")},
        )

    assert response.status_code == 415


def test_voice_rejects_empty_audio() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/voice",
            files={"audio": ("recording.wav", b"", "audio/wav")},
        )

    assert response.status_code == 422


def test_voice_rejects_unsupported_language_override() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/voice",
            files={"audio": ("recording.wav", b"audio", "audio/wav")},
            data={"language": "fr"},
        )

    assert response.status_code == 422


def test_voice_reports_missing_speech_model_and_removes_temporary_upload(monkeypatch) -> None:
    saved_path = None
    original_factory = voice_route.tempfile.NamedTemporaryFile

    def capture_upload(*args, **kwargs):
        nonlocal saved_path
        handle = original_factory(*args, **kwargs)
        saved_path = handle.name
        return handle

    monkeypatch.setattr(voice_route.tempfile, "NamedTemporaryFile", capture_upload)
    with TestClient(app) as client:
        app.state.pipeline.voice = AsyncMock(
            side_effect=SpeechModelNotInstalledError("Faster-Whisper model is not installed.")
        )
        response = client.post(
            "/api/voice",
            files={"audio": ("recording.wav", b"valid-container-not-required-by-this-mocked-test", "audio/wav")},
        )

    assert response.status_code == 503
    assert "not installed" in response.json()["detail"]
    assert saved_path is not None
    assert not Path(saved_path).exists()
