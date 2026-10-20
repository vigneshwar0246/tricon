import os
import pytest
import time
from types import SimpleNamespace
from unittest.mock import Mock

from app.core.config import Settings
from app.services.stt import SpeechModelNotInstalledError, SpeechToTextService
from app.services.tts import TextToSpeechService, VoiceModelNotInstalledError, to_spoken_text


def test_speech_engines_report_missing_local_models_without_loading_or_downloading(tmp_path) -> None:
    settings = Settings(
        stt_model_path=tmp_path / "missing-whisper",
        tts_model_path=tmp_path / "missing-voice.onnx",
        audio_output_dir=tmp_path / "audio",
    )
    stt = SpeechToTextService(settings)
    tts = TextToSpeechService(settings)

    assert stt.available is False
    assert tts.available is False
    with pytest.raises(SpeechModelNotInstalledError):
        stt._get_model()
    with pytest.raises(VoiceModelNotInstalledError):
        tts._get_voice()
    assert not (tmp_path / "audio").exists()


def test_stt_does_not_report_ready_without_vocabulary(tmp_path) -> None:
    model = tmp_path / "incomplete-whisper"
    model.mkdir()
    (model / "model.bin").touch()
    (model / "config.json").touch()
    service = SpeechToTextService(Settings(stt_model_path=model))

    assert service.available is False
    with pytest.raises(SpeechModelNotInstalledError):
        service._get_model()


def test_tts_prunes_expired_and_excess_generated_audio(tmp_path) -> None:
    output = tmp_path / "audio"
    output.mkdir()
    now = time.time()
    for index in range(101):
        path = output / f"cached-{index:03}.wav"
        path.touch()
        os.utime(path, (now + index, now + index))
    expired = output / "expired.wav"
    expired.touch()
    os.utime(expired, (now - 7200, now - 7200))

    service = TextToSpeechService(Settings(audio_output_dir=output))
    service._remove_expired_audio()

    files = list(output.glob("*.wav"))
    assert len(files) == 100
    assert not expired.exists()
    assert (output / "cached-100.wav").exists()


def test_tts_removes_markup_urls_and_code_instead_of_reading_symbols() -> None:
    spoken = to_spoken_text(
        "## Answer\nA **rainbow** has *many* colors. See [the guide](https://example.com).\n`x_y + 2`"
    )

    assert spoken == "Answer A rainbow has many colors. See the guide. I've included the code in the text response."


def test_tts_uses_a_slightly_faster_natural_speaking_rate(tmp_path) -> None:
    class RecordingVoice:
        text = ""
        config = None

        def synthesize_wav(self, text, wav_file, *, syn_config):
            self.text = text
            self.config = syn_config
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\0\0")

    service = TextToSpeechService(Settings(audio_output_dir=tmp_path))
    voice = RecordingVoice()
    service._voice = voice
    service.synthesize_to_file("Hello, **there**.")

    assert voice.text == "Hello, there."
    assert voice.config.length_scale == 0.92


def test_cuda_initialization_failure_falls_back_to_cpu_int8(tmp_path) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    for name in ("model.bin", "config.json", "vocabulary.txt"):
        (model_dir / name).touch()
    service = SpeechToTextService(Settings(
        stt_model_path=model_dir,
        stt_device="cuda",
        stt_compute_type="float16",
    ))
    cpu_model = object()
    loads = []

    def load_model(device: str, compute_type: str):
        loads.append((device, compute_type))
        if device == "cuda":
            raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
        service.active_device = device
        service.active_compute_type = compute_type
        return cpu_model

    service._load_model = load_model

    assert service._get_model() is cpu_model
    assert loads == [("cuda", "float16"), ("cpu", "int8")]
    assert service.active_device == "cpu"
    assert "cublas64_12.dll" in service.fallback_reason


def test_cuda_transcription_failure_retries_once_on_cpu(tmp_path) -> None:
    service = SpeechToTextService(Settings(
        stt_model_path=tmp_path / "model",
        stt_device="cuda",
        stt_compute_type="float16",
    ))
    cuda_model = Mock()
    cuda_model.transcribe.side_effect = RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
    cpu_model = Mock()
    cpu_model.transcribe.return_value = (
        [SimpleNamespace(text=" What time is it? ")],
        SimpleNamespace(language="en", language_probability=0.99, duration=1.2),
    )
    service._model = cuda_model
    service.active_device = "cuda"
    loads = []

    def load_model(device: str, compute_type: str):
        loads.append((device, compute_type))
        service.active_device = device
        service.active_compute_type = compute_type
        return cpu_model

    service._load_model = load_model
    text, details = service.transcribe(tmp_path / "clip.wav", language="en")

    assert text == "What time is it?"
    assert details == {"language": "en", "language_probability": 0.99}
    assert loads == [("cpu", "int8")]
    assert cpu_model.transcribe.call_count == 1
    assert service.last_successful_device == "cpu"
