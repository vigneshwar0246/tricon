import os
import pytest
import time

from app.core.config import Settings
from app.services.stt import SpeechModelNotInstalledError, SpeechToTextService
from app.services.tts import TextToSpeechService, VoiceModelNotInstalledError


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
