from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import Settings
from app.services.commands import route_command
from app.services.pipeline import VoicePipeline
from app.services.session_manager import SessionManager


def test_allowlisted_commands_and_unsupported_system_actions() -> None:
    assert route_command("What time is it?", now=datetime(2026, 10, 20, 9, 5)).response == "The current time is 9:05 AM."
    assert route_command("Repeat that", "Previous answer.").response == "Previous answer."
    assert route_command("Stop listening!").action == "stop_listening"
    assert route_command("Open PowerShell").response.startswith("That system action is not supported")
    assert route_command("Explain AI simply") is None


@pytest.mark.parametrize("phrase", [
    "System status",
    "Tell me the current system status.",
    "Is everything working?",
    "Check all services",
    "Are the voice models ready?",
    "Check whether the AI assistant is ready",
    "Check the system requirements",
])
def test_natural_status_phrases_share_one_command(phrase: str) -> None:
    assert route_command(phrase).action == "system_status"


@pytest.mark.asyncio
async def test_voice_time_command_never_calls_llm(tmp_path: Path) -> None:
    llm = Mock(chat=AsyncMock())
    stt = Mock(transcribe=Mock(return_value=("What time is it?", {})))
    tts = Mock(synthesize_to_file=Mock(return_value=(tmp_path / "speech.wav", 10.0)))
    pipeline = VoicePipeline(llm=llm, sessions=SessionManager(), stt=stt, tts=tts)

    result = await pipeline.voice(tmp_path / "input.wav", "test-command")

    assert "current time" in result.response
    assert result.metrics["llm_ms"] is None
    llm.chat.assert_not_called()
    tts.synthesize_to_file.assert_called_once_with(result.response)


@pytest.mark.asyncio
async def test_voice_status_uses_real_service_flags_without_generating_text(tmp_path: Path) -> None:
    llm = Mock(
        list_models=AsyncMock(return_value=["qwen2.5:3b"]),
        loaded_models=AsyncMock(return_value=[]),
        chat=AsyncMock(return_value=("READY", {})),
    )
    stt = Mock(
        transcribe=Mock(return_value=("System status", {})), available=True,
        settings=Settings(), active_device="cpu", active_compute_type="int8",
        last_successful_device=None, fallback_reason=None,
    )
    tts = Mock(
        synthesize_to_file=Mock(return_value=(tmp_path / "speech.wav", 10.0)),
        available=False, available_for=Mock(return_value=False),
    )
    pipeline = VoicePipeline(llm=llm, sessions=SessionManager(), stt=stt, tts=tts)

    result = await pipeline.voice(tmp_path / "input.wav")

    assert "Ollama: PASS" in result.response
    assert "Qwen model: PASS" in result.response
    assert "speech recognition: PASS" in result.response
    assert "speech output: FAIL" in result.response
    assert result.action == "system_status"
    llm.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_typed_status_uses_the_same_live_diagnostics() -> None:
    llm = Mock(
        list_models=AsyncMock(return_value=["qwen2.5:3b"]),
        loaded_models=AsyncMock(return_value=[]),
        chat=AsyncMock(return_value=("READY", {})),
    )
    stt = Mock(
        available=True, settings=Settings(), active_device="cpu", active_compute_type="int8",
        last_successful_device=None, fallback_reason=None,
    )
    tts = Mock(available=True, available_for=Mock(return_value=True))
    result = await VoicePipeline(llm=llm, sessions=SessionManager(), stt=stt, tts=tts).chat(
        "Is everything working?", "typed-status"
    )

    assert "Backend: PASS" in result.response
    assert "model inference: PASS" in result.response
    assert result.metrics["llm_ms"] is None
