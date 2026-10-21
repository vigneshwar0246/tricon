"""Chat request and response models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    language: Literal["en", "hi", "ta"] | None = None


class MetricsResponse(BaseModel):
    stt_ms: float | None = None
    llm_ms: float | None = None
    tts_ms: float | None = None
    total_ms: float
    first_token_ms: float | None = None
    first_audio_ms: float | None = None
    audio_duration_ms: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    metrics: MetricsResponse
    created_at: datetime


class SessionSummary(BaseModel):
    session_id: str
    message_count: int
    updated_at: datetime


class SessionDeleteResponse(BaseModel):
    session_id: str
    deleted: bool


class HealthService(BaseModel):
    available: bool | None = None
    status: Literal["ready", "unavailable", "not_configured", "unknown"]
    model: str | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    backend: HealthService
    ollama: HealthService
    services: dict[str, bool | None]
    models: dict[str, str]
    language_support: dict[str, dict[str, bool]] = Field(default_factory=dict)
