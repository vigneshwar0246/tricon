from pathlib import Path
from unittest.mock import Mock

import pytest

from app.services.pipeline import VoicePipeline
from app.services.session_manager import SessionManager


@pytest.mark.asyncio
async def test_voice_uses_spoken_style_prompt_and_bounded_generation(tmp_path: Path) -> None:
    class FakeLlm:
        messages = None
        num_predict = None

        async def chat(self, messages, *, num_predict):
            self.messages = messages
            self.num_predict = num_predict
            return "A concise spoken reply.", {"total_duration": 200_000_000}

    llm = FakeLlm()
    stt = Mock(transcribe=Mock(return_value=("Explain AI simply", {})))
    tts = Mock(synthesize_to_file=Mock(return_value=(tmp_path / "reply.wav", 5.0)))
    pipeline = VoicePipeline(llm=llm, sessions=SessionManager(), stt=stt, tts=tts, voice_num_predict=64)

    result = await pipeline.voice(tmp_path / "input.wav", "voice-style")

    assert result.response == "A concise spoken reply."
    assert llm.messages[0]["role"] == "system"
    assert "Do not use markdown" in llm.messages[0]["content"]
    assert llm.messages[-1] == {"role": "user", "content": "Explain AI simply"}
    assert llm.num_predict == 64
