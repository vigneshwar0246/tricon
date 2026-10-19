"""Lazy local Piper speech synthesis. Voice files are never downloaded here."""

import logging
import threading
import time
import wave
from importlib.util import find_spec
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class VoiceModelNotInstalledError(RuntimeError):
    pass


class SpeechSynthesisError(RuntimeError):
    pass


class TextToSpeechService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._voice = None
        self._voice_lock = threading.Lock()

    @property
    def available(self) -> bool:
        model_path = self.settings.tts_model_path
        config_path = self.settings.tts_config_path or Path(f"{model_path}.json")
        return model_path.is_file() and config_path.is_file() and find_spec("piper") is not None

    def _get_voice(self):
        if self._voice is not None:
            return self._voice
        with self._voice_lock:
            if self._voice is None:
                model_path = self.settings.tts_model_path
                config_path = self.settings.tts_config_path or Path(f"{model_path}.json")
                if not model_path.is_file() or not config_path.is_file():
                    raise VoiceModelNotInstalledError(
                        f"Piper voice files were not found at '{model_path}'. Follow the voice setup instructions in docs/architecture.md."
                    )
                try:
                    from piper import PiperVoice
                except ImportError as exc:
                    raise VoiceModelNotInstalledError("piper-tts is not installed in this environment.") from exc
                try:
                    self._voice = PiperVoice.load(
                        model_path,
                        config_path=config_path,
                        use_cuda=self.settings.tts_use_cuda,
                        download_dir=self.settings.audio_output_dir,
                    )
                except Exception as exc:
                    logger.exception("Could not load the configured Piper voice")
                    raise VoiceModelNotInstalledError("The Piper voice could not be loaded. Check its model and config files.") from exc
        return self._voice

    def synthesize_to_file(self, text: str) -> tuple[Path, float]:
        """Create one WAV file and return its path and measured synthesis time."""
        from time import perf_counter

        self.settings.audio_output_dir.mkdir(parents=True, exist_ok=True)
        voice = self._get_voice()
        self._remove_expired_audio()
        output_path = self.settings.audio_output_dir / f"{uuid4().hex}.wav"
        started = perf_counter()
        try:
            with wave.open(str(output_path), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
        except Exception as exc:
            output_path.unlink(missing_ok=True)
            logger.exception("Piper speech synthesis failed")
            raise SpeechSynthesisError("The local TTS engine could not synthesize this response.") from exc
        return output_path, round((perf_counter() - started) * 1000, 2)

    def _remove_expired_audio(self) -> None:
        """Prune expired and excess generated WAVs to keep the local cache bounded."""
        cutoff = time.time() - 3600
        files = []
        for path in self.settings.audio_output_dir.glob("*.wav"):
            try:
                if path.is_file():
                    files.append((path.stat().st_mtime, path))
            except OSError:
                logger.warning("Could not inspect generated audio file")
        for index, (modified_at, path) in enumerate(sorted(files, key=lambda item: item[0], reverse=True)):
            try:
                if index >= 100 or modified_at < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove expired generated audio file")


tts_service = TextToSpeechService()
