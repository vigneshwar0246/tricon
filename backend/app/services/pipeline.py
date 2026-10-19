"""Orchestration for text chat and the full local voice pipeline."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from app.services.llm import OllamaClient, ollama_client
from app.services.commands import route_command
from app.services.session_manager import SessionManager, session_manager
from app.services.stt import SpeechToTextService, stt_service
from app.services.tts import TextToSpeechService, tts_service


@dataclass
class PipelineResult:
    session_id: str
    transcript: str
    response: str
    audio_path: Path
    metrics: dict[str, float | None]
    created_at: datetime
    action: str | None = None


@dataclass
class ChatResult:
    session_id: str
    response: str
    metrics: dict[str, float]
    created_at: datetime


class VoicePipeline:
    def __init__(
        self,
        llm: OllamaClient | None = None,
        sessions: SessionManager | None = None,
        stt: SpeechToTextService | None = None,
        tts: TextToSpeechService | None = None,
    ) -> None:
        self.llm = llm or ollama_client
        self.sessions = sessions or session_manager
        self.stt = stt or stt_service
        self.tts = tts or tts_service

    async def chat(self, message: str, session_id: str | None = None) -> ChatResult:
        started = perf_counter()
        async with self.sessions.conversation(session_id) as session:
            messages = self.sessions.history(session)
            messages.append({"role": "user", "content": message})
            response_text, metadata = await self.llm.chat(messages)
            llm_ms = round((metadata.get("total_duration", 0) or 0) / 1_000_000, 2)
            # Some Ollama-compatible servers omit timing fields. Measure the client call in that case.
            if llm_ms <= 0:
                llm_ms = round((perf_counter() - started) * 1000, 2)
            self.sessions.add_exchange(session, message, response_text)
        return ChatResult(
            session_id=session.session_id,
            response=response_text,
            metrics={"llm_ms": llm_ms, "total_ms": round((perf_counter() - started) * 1000, 2)},
            created_at=datetime.now(timezone.utc),
        )

    async def voice(self, audio_path: str | Path, session_id: str | None = None, language: str | None = None) -> PipelineResult:
        overall_started = perf_counter()
        async with self.sessions.conversation(session_id) as session:
            stt_started = perf_counter()
            transcript, _transcription_details = await asyncio.to_thread(self.stt.transcribe, audio_path, language)
            stt_ms = round((perf_counter() - stt_started) * 1000, 2)
            last_response = next((item.content for item in reversed(session.messages) if item.role == "assistant"), None)
            command = route_command(transcript, last_response)
            if command:
                response_text = command.response
                llm_ms = None
            else:
                messages: list[dict[str, Any]] = self.sessions.history(session)
                messages.append({"role": "user", "content": transcript})
                llm_started = perf_counter()
                response_text, metadata = await self.llm.chat(messages)
                measured_llm_ms = round((perf_counter() - llm_started) * 1000, 2)
                reported_llm_ms = round((metadata.get("total_duration", 0) or 0) / 1_000_000, 2)
                llm_ms = reported_llm_ms if reported_llm_ms > 0 else measured_llm_ms

            audio_output, tts_ms = await asyncio.to_thread(self.tts.synthesize_to_file, response_text)
            if command and command.action == "clear_conversation":
                session.messages.clear()
            else:
                self.sessions.add_exchange(session, transcript, response_text)

        return PipelineResult(
            session_id=session.session_id,
            transcript=transcript,
            response=response_text,
            audio_path=audio_output,
            metrics={
                "stt_ms": stt_ms,
                "llm_ms": llm_ms,
                "tts_ms": tts_ms,
                "total_ms": round((perf_counter() - overall_started) * 1000, 2),
            },
            created_at=datetime.now(timezone.utc),
            action=command.action if command else None,
        )


voice_pipeline = VoicePipeline()
