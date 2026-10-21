"""Orchestration for text chat and the full local voice pipeline."""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, AsyncIterator

from app.services.llm import OllamaClient, OllamaResponseError, OllamaUnavailableError, ollama_client
from app.services.commands import Command, route_command
from app.services.session_manager import SessionManager, session_manager
from app.services.stt import SpeechToTextService, TranscriptionError, stt_service
from app.services.tts import TextToSpeechService, VoiceModelNotInstalledError, tts_service

VOICE_SYSTEM_PROMPT = (
    "You are a friendly voice assistant speaking to one person. Answer directly in one or two short, natural sentences, "
    "usually under 35 words. Use plain spoken language. Do not use markdown, headings, bullets, emoji, code, URLs, "
    "formatting, or raw symbol characters. Never read out punctuation or symbol names. Explain technical ideas simply. "
    "Give more detail only when the user asks for it. If the request is unclear, ask one concise clarifying question."
)

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "ta": "Tamil"}


@dataclass
class PipelineResult:
    session_id: str
    transcript: str
    response: str
    audio_path: Path
    metrics: dict[str, float | None]
    created_at: datetime
    action: str | None = None
    language: str | None = None
    language_confidence: float | None = None


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
        voice_num_predict: int = 80,
    ) -> None:
        self.llm = llm or ollama_client
        self.sessions = sessions or session_manager
        self.stt = stt or stt_service
        self.tts = tts or tts_service
        self.voice_num_predict = voice_num_predict

    async def chat(self, message: str, session_id: str | None = None, language: str | None = None) -> ChatResult:
        started = perf_counter()
        async with self.sessions.conversation(session_id) as session:
            if language:
                session.language = language
            messages = self.sessions.history(session)
            if session.language:
                messages.insert(0, {
                    "role": "system",
                    "content": f"Reply naturally and concisely in {LANGUAGE_NAMES[session.language]} unless the user explicitly requests another language.",
                })
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
            transcript, transcription_details = await asyncio.to_thread(self.stt.transcribe, audio_path, language)
            stt_ms = round((perf_counter() - stt_started) * 1000, 2)
            detected_language = str(transcription_details.get("language") or "")
            confidence_value = transcription_details.get("language_probability")
            language_confidence = float(confidence_value) if isinstance(confidence_value, (int, float)) else None
            response_language = language or detected_language or session.language or "en"
            if response_language not in LANGUAGE_NAMES:
                raise TranscriptionError(
                    "The detected language is not supported for voice output. Select English, Hindi, or Tamil and try again."
                )
            if language is None and language_confidence is not None and language_confidence < self.stt.settings.stt_language_confidence_threshold:
                raise TranscriptionError(
                    f"Language detection was uncertain ({language_confidence:.0%}). Select English, Hindi, or Tamil and try again."
                )
            session.language = response_language
            if hasattr(self.tts, "available_for") and not self.tts.available_for(response_language):
                raise VoiceModelNotInstalledError(
                    f"Transcription supports {LANGUAGE_NAMES[response_language]}, but a compatible local "
                    f"{LANGUAGE_NAMES[response_language]} speech voice is not installed. No English or cloud fallback was used."
                )
            last_response = next((item.content for item in reversed(session.messages) if item.role == "assistant"), None)
            if transcript.lower().strip(" ?.!") in {"system status", "assistant status", "check status", "are you working"}:
                try:
                    llm_ready = await self.llm.model_available()
                except (OllamaUnavailableError, OllamaResponseError):
                    llm_ready = False
                command = Command(
                    f"Backend is responding. Ollama model is {'available' if llm_ready else 'unavailable'}. "
                    f"Speech recognition is {'available' if self.stt.available else 'unavailable'}. "
                    f"Speech output is {'available' if self.tts.available else 'unavailable'}. "
                    "Microphone status is shown in the browser."
                )
            else:
                command = route_command(transcript, last_response)
            if command:
                response_text = command.response
                llm_ms = None
            else:
                messages: list[dict[str, Any]] = [
                    {
                        "role": "system",
                        "content": f"{VOICE_SYSTEM_PROMPT} Reply in {LANGUAGE_NAMES[response_language]}. "
                        "Preserve that language unless the user explicitly asks to switch. If recognition seems ambiguous, ask one short clarification question.",
                    },
                    *self.sessions.history(session),
                ]
                messages.append({"role": "user", "content": transcript})
                llm_started = perf_counter()
                response_text, metadata = await self.llm.chat(messages, num_predict=self.voice_num_predict)
                measured_llm_ms = round((perf_counter() - llm_started) * 1000, 2)
                reported_llm_ms = round((metadata.get("total_duration", 0) or 0) / 1_000_000, 2)
                llm_ms = reported_llm_ms if reported_llm_ms > 0 else measured_llm_ms

            if response_language == "en":
                audio_output, tts_ms = await asyncio.to_thread(self.tts.synthesize_to_file, response_text)
            else:
                audio_output, tts_ms = await asyncio.to_thread(self.tts.synthesize_to_file, response_text, response_language)
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
            language=response_language,
            language_confidence=language_confidence,
        )

    @staticmethod
    def _take_speakable_chunk(buffer: str, *, final: bool = False) -> tuple[str | None, str]:
        """Take a sentence/phrase boundary without splitting arbitrary short word groups."""
        if final:
            return (buffer.strip() or None), ""
        matches = list(re.finditer(r"[.!?\u0964\u0965](?:\s+|$)", buffer))
        if matches and matches[-1].end() >= 8:
            end = matches[-1].end()
            return buffer[:end].strip(), buffer[end:]
        if len(buffer) >= 180:
            split_at = max(buffer.rfind(", ", 80), buffer.rfind("; ", 80), buffer.rfind(" ", 120))
            if split_at > 0:
                return buffer[:split_at + 1].strip(), buffer[split_at + 1:]
        return None, buffer

    async def voice_stream(
        self, audio_path: str | Path, session_id: str | None = None, language: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream text tokens and sentence-safe Piper WAV chunks for one voice turn."""
        overall_started = perf_counter()
        async with self.sessions.conversation(session_id) as session:
            stt_started = perf_counter()
            transcript, details = await asyncio.to_thread(self.stt.transcribe, audio_path, language)
            stt_ms = round((perf_counter() - stt_started) * 1000, 2)
            detected = str(details.get("language") or "")
            probability = details.get("language_probability")
            confidence = float(probability) if isinstance(probability, (int, float)) else None
            response_language = language or detected or session.language or "en"
            if response_language not in LANGUAGE_NAMES:
                raise TranscriptionError("Select English, Hindi, or Tamil; the detected language is not supported.")
            if language is None and confidence is not None and confidence < self.stt.settings.stt_language_confidence_threshold:
                raise TranscriptionError(
                    f"Language detection was uncertain ({confidence:.0%}). Select English, Hindi, or Tamil and try again."
                )
            session.language = response_language
            if not self.tts.available_for(response_language):
                raise VoiceModelNotInstalledError(
                    f"A compatible local {LANGUAGE_NAMES[response_language]} speech voice is not installed. "
                    "No English or cloud fallback was used."
                )
            yield {
                "type": "transcript", "session_id": session.session_id, "transcript": transcript,
                "language": response_language, "language_confidence": confidence, "stt_ms": stt_ms,
            }

            last_response = next((item.content for item in reversed(session.messages) if item.role == "assistant"), None)
            command = route_command(transcript, last_response)
            if command:
                response_text = command.response
                audio_path_out, tts_ms = await asyncio.to_thread(
                    self.tts.synthesize_to_file, response_text, response_language
                )
                yield {"type": "text", "delta": response_text}
                yield {"type": "audio", "url": f"/api/audio/{audio_path_out.name}", "text": response_text, "index": 0}
                if command.action == "clear_conversation":
                    session.messages.clear()
                else:
                    self.sessions.add_exchange(session, transcript, response_text)
                yield {
                    "type": "done", "session_id": session.session_id, "response": response_text,
                    "action": command.action, "language": response_language,
                    "metrics": {"stt_ms": stt_ms, "llm_ms": None, "tts_ms": tts_ms,
                                "first_token_ms": None, "first_audio_ms": round((perf_counter() - overall_started) * 1000, 2),
                                "total_ms": round((perf_counter() - overall_started) * 1000, 2)},
                }
                return

            messages: list[dict[str, Any]] = [{
                "role": "system",
                "content": f"{VOICE_SYSTEM_PROMPT} Reply in {LANGUAGE_NAMES[response_language]}. Preserve that language unless asked to switch.",
            }, *self.sessions.history(session), {"role": "user", "content": transcript}]
            llm_started = perf_counter()
            first_token_ms: float | None = None
            first_audio_ms: float | None = None
            tts_ms = 0.0
            response_text = ""
            buffer = ""
            audio_index = 0
            reported_llm_ms: float | None = None
            async for event in self.llm.chat_stream(messages, num_predict=self.voice_num_predict):
                token = event.get("token")
                if isinstance(token, str) and token:
                    if first_token_ms is None:
                        first_token_ms = round((perf_counter() - llm_started) * 1000, 2)
                    response_text += token
                    buffer += token
                    yield {"type": "text", "delta": token}
                    chunk, buffer = self._take_speakable_chunk(buffer)
                    if chunk:
                        chunk_path, chunk_ms = await asyncio.to_thread(
                            self.tts.synthesize_to_file, chunk, response_language
                        )
                        tts_ms += chunk_ms
                        if first_audio_ms is None:
                            first_audio_ms = round((perf_counter() - overall_started) * 1000, 2)
                        yield {"type": "audio", "url": f"/api/audio/{chunk_path.name}", "text": chunk, "index": audio_index}
                        audio_index += 1
                if event.get("done") and isinstance(event.get("metadata"), dict):
                    duration_ns = event["metadata"].get("total_duration", 0)
                    if isinstance(duration_ns, (int, float)) and duration_ns > 0:
                        reported_llm_ms = round(duration_ns / 1_000_000, 2)
            final_chunk, _ = self._take_speakable_chunk(buffer, final=True)
            if final_chunk:
                chunk_path, chunk_ms = await asyncio.to_thread(
                    self.tts.synthesize_to_file, final_chunk, response_language
                )
                tts_ms += chunk_ms
                if first_audio_ms is None:
                    first_audio_ms = round((perf_counter() - overall_started) * 1000, 2)
                yield {"type": "audio", "url": f"/api/audio/{chunk_path.name}", "text": final_chunk, "index": audio_index}
            response_text = response_text.strip()
            if not response_text:
                raise OllamaResponseError("Ollama returned an empty streaming reply.")
            llm_ms = reported_llm_ms or round((perf_counter() - llm_started) * 1000, 2)
            self.sessions.add_exchange(session, transcript, response_text)
            yield {
                "type": "done", "session_id": session.session_id, "response": response_text,
                "action": None, "language": response_language,
                "metrics": {"stt_ms": stt_ms, "llm_ms": llm_ms, "tts_ms": round(tts_ms, 2),
                            "first_token_ms": first_token_ms, "first_audio_ms": first_audio_ms,
                            "total_ms": round((perf_counter() - overall_started) * 1000, 2)},
            }


voice_pipeline = VoicePipeline()
