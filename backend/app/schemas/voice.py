"""Voice pipeline request/response models."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chat import MetricsResponse


class VoiceResponse(BaseModel):
    session_id: str
    transcript: str = Field(min_length=1)
    response: str = Field(min_length=1)
    audio_url: str | None = None
    action: str | None = None
    metrics: MetricsResponse
    created_at: datetime
    language: str | None = None
    language_confidence: float | None = None
