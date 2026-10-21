"""Lazy Faster-Whisper speech recognition with local-only model loading."""

import logging
import threading
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

LANGUAGE_PROMPTS = {
    "hi": "यह हिंदी भाषा में देवनागरी लिपि का स्पष्ट वाक्य है।",
    "ta": "இது தமிழ் எழுத்தில் பேசப்பட்ட தெளிவான தமிழ் வாக்கியம்.",
}


class SpeechModelNotInstalledError(RuntimeError):
    pass


class TranscriptionError(RuntimeError):
    pass


class SpeechToTextService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model: Any = None
        self._language_models: dict[str, Any] = {}
        self._model_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self.active_device = self.settings.stt_device
        self.active_compute_type = self.settings.stt_compute_type
        self.fallback_reason: str | None = None
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
                if self.settings.stt_device.lower() == "cuda":
                    try:
                        self._model = self._load_model("cuda", self.settings.stt_compute_type)
                    except Exception as exc:
                        self._fallback_to_cpu(exc)
                else:
                    self._model = self._load_model(self.settings.stt_device, self.settings.stt_compute_type)
        return self._model

    def _get_model_for_language(self, language: str | None) -> Any:
        path = self.settings.stt_multilingual_model_path
        if language not in {"hi", "ta"} or path is None:
            return self._get_model()
        if language in self._language_models:
            return self._language_models[language]
        with self._model_lock:
            if language not in self._language_models:
                required = (path / "model.bin", path / "config.json")
                if not all(item.is_file() for item in required):
                    raise SpeechModelNotInstalledError(
                        f"The configured multilingual Faster-Whisper model is incomplete at '{path}'."
                    )
                try:
                    from faster_whisper import WhisperModel
                    self._language_models[language] = WhisperModel(
                        str(path), device=self.active_device, compute_type=self.active_compute_type
                    )
                except Exception as exc:
                    if self.active_device != "cuda":
                        raise
                    self._fallback_to_cpu(exc)
                    self._language_models[language] = WhisperModel(str(path), device="cpu", compute_type="int8")
        return self._language_models[language]

    def _load_model(self, device: str, compute_type: str) -> Any:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise SpeechModelNotInstalledError("faster-whisper is not installed in this environment.") from exc
        # A directory is passed intentionally: CTranslate2 loads local files and does not contact Hugging Face.
        model = WhisperModel(
            str(self.settings.stt_model_path),
            device=device,
            compute_type=compute_type,
        )
        self.active_device = device
        self.active_compute_type = compute_type
        return model

    def _fallback_to_cpu(self, reason: Exception) -> None:
        self.fallback_reason = f"{type(reason).__name__}: {reason}"[:300]
        logger.warning("CUDA STT failed; retrying with CPU/int8: %s", self.fallback_reason)
        self._model = self._load_model("cpu", "int8")

    @staticmethod
    def _is_cuda_runtime_error(error: Exception) -> bool:
        detail = str(error).lower()
        return any(token in detail for token in (
            "cuda", "cublas", "cudnn", "gpu driver", "no kernel image",
        ))

    def _transcribe_with_model(self, model: Any, audio_path: str | Path, language: str | None) -> tuple[str, Any]:
        selected_language = language or self.settings.stt_language
        segments, info = model.transcribe(
            str(audio_path),
            language=selected_language,
            beam_size=self.settings.stt_beam_size,
            vad_filter=True,
            initial_prompt=LANGUAGE_PROMPTS.get(selected_language),
            condition_on_previous_text=False,
        )
        duration = getattr(info, "duration", None)
        if duration is not None and duration > self.settings.audio_max_duration_seconds:
            raise TranscriptionError(
                f"Audio is longer than the {self.settings.audio_max_duration_seconds}-second limit."
            )
        # Segment iteration performs inference, so keep it inside this service call.
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            raise TranscriptionError("No speech was detected in the uploaded audio.")
        return text, info

    def transcribe(self, audio_path: str | Path, language: str | None = None) -> tuple[str, dict[str, Any]]:
        try:
            with self._inference_lock:
                model = self._get_model_for_language(language or self.settings.stt_language)
                try:
                    text, info = self._transcribe_with_model(model, audio_path, language)
                except Exception as exc:
                    if self.active_device != "cuda" or not self._is_cuda_runtime_error(exc):
                        raise
                    self._fallback_to_cpu(exc)
                    text, info = self._transcribe_with_model(self._model, audio_path, language)
        except TranscriptionError:
            raise
        except SpeechModelNotInstalledError:
            raise
        except Exception as exc:  # decoder errors vary by uploaded container/codec
            logger.exception("Speech transcription failed")
            raise TranscriptionError("The audio could not be transcribed. Use a supported audio file and try again.") from exc
        self.last_successful_device = self.active_device
        return text, {
            "language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
        }


stt_service = SpeechToTextService()
