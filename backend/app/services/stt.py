"""Lazy Faster-Whisper speech recognition with local-only model loading."""

import logging
import threading
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class SpeechModelNotInstalledError(RuntimeError):
    pass


class TranscriptionError(RuntimeError):
    pass


class SpeechToTextService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model: Any = None
        self._model_lock = threading.Lock()
        self.last_successful_device: str | None = None

    @property
    def available(self) -> bool:
        model_path = self.settings.stt_model_path
        return (
            model_path.is_dir()
            and (model_path / "model.bin").is_file()
            and (model_path / "config.json").is_file()
            and ((model_path / "vocabulary.txt").is_file() or (model_path / "vocabulary.json").is_file())
            and find_spec("faster_whisper") is not None
        )

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is None:
                model_path = self.settings.stt_model_path
                if not self.available:
                    raise SpeechModelNotInstalledError(
                        f"Faster-Whisper package or required model files (model.bin, config.json, vocabulary) are missing at '{model_path}'. Follow docs/architecture.md."
                    )
                try:
                    from faster_whisper import WhisperModel
                except ImportError as exc:
                    raise SpeechModelNotInstalledError("faster-whisper is not installed in this environment.") from exc
                # A directory is passed intentionally: CTranslate2 loads local files and does not contact Hugging Face.
                self._model = WhisperModel(
                    str(model_path),
                    device=self.settings.stt_device,
                    compute_type=self.settings.stt_compute_type,
                )
        return self._model

    def transcribe(self, audio_path: str | Path, language: str | None = None) -> tuple[str, dict[str, Any]]:
        try:
            model = self._get_model()
            segments, info = model.transcribe(
                str(audio_path),
                language=language or self.settings.stt_language,
                beam_size=5,
                vad_filter=True,
            )
            duration = getattr(info, "duration", None)
            if duration is not None and duration > self.settings.audio_max_duration_seconds:
                raise TranscriptionError(
                    f"Audio is longer than the {self.settings.audio_max_duration_seconds}-second limit."
                )
            # Segment iteration performs inference, so keep it inside this service call.
            text = " ".join(segment.text.strip() for segment in segments).strip()
        except TranscriptionError:
            raise
        except SpeechModelNotInstalledError:
            raise
        except Exception as exc:  # decoder errors vary by uploaded container/codec
            logger.exception("Speech transcription failed")
            raise TranscriptionError("The audio could not be transcribed. Use a supported audio file and try again.") from exc
        if not text:
            raise TranscriptionError("No speech was detected in the uploaded audio.")
        self.last_successful_device = self.settings.stt_device
        return text, {
            "language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
        }


stt_service = SpeechToTextService()
