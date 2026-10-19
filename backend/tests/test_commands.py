from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.commands import route_command
from app.services.pipeline import VoicePipeline
from app.services.session_manager import SessionManager


def test_allowlisted_commands_and_unsupported_system_actions() -> None:
    assert route_command("What time is it?", now=datetime(2026, 10, 20, 9, 5)).response == "The current time is 9:05 AM."
    assert route_command("Repeat that", "Previous answer.").response == "Previous answer."
    assert route_command("Stop listening!").action == "stop_listening"
    assert route_command("Open PowerShell").response.startswith("That system action is not supported")
    assert route_command("Explain AI simply") is None


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
