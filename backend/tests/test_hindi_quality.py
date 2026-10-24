from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import Settings
from app.services.language_quality import normalize_text, text_quality_error
from app.services.llm import OllamaResponseError, OllamaUnavailableError
from app.services.pipeline import VoicePipeline
from app.services.session_manager import SessionManager
from app.services.stt import SpeechToTextService, TranscriptionError
from app.services.tts import to_spoken_text


CASES = [
    ("भारत की राजधानी क्या है?", "hi", "भारत की राजधानी नई दिल्ली है।", "नई दिल्ली"),
    ("भारत की राजधानी का नाम क्या है?", "hi", "नई दिल्ली भारत की राजधानी है।", "नई दिल्ली"),
    ("चेन्नई किस राज्य की राजधानी है?", "hi", "चेन्नई तमिलनाडु की राजधानी है।", "तमिलनाडु"),
    ("मुझे हिंदी में जवाब दीजिए। भारत की राजधानी क्या है?", "hi", "भारत की राजधानी नई दिल्ली है।", "नई दिल्ली"),
    ("What is the capital of India?", "en", "India's capital is New Delhi.", "New Delhi"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("question,language,answer,meaning", CASES)
async def test_factual_answer_passes_unchanged_to_display_and_correct_voice(question, language, answer, meaning):
    # Contract test, not evidence that a real model knows these facts.
    llm = Mock(chat=AsyncMock(return_value=(answer, {"done_reason": "stop"})))
    stt = Mock(transcribe=Mock(return_value=(question, {"language": language, "language_probability": 1})))
    tts = Mock(synthesize_to_file=Mock(return_value=(Path("reply.wav"), 1)), available_for=Mock(return_value=True))
    pipeline = VoicePipeline(llm=llm, stt=stt, tts=tts, sessions=SessionManager())
    result = await pipeline.voice("input.wav", language=language)
    assert meaning.casefold() in result.response.casefold()
    assert result.transcript == question
    assert llm.chat.await_args.args[0][-1]["content"] == question
    assert tts.synthesize_to_file.call_args.args[0] == result.response
    if language == "hi":
        assert tts.synthesize_to_file.call_args.args[1] == "hi"
        assert "Devanagari" in llm.chat.await_args.args[0][0]["content"]
        assert llm.chat.await_args.kwargs["num_predict"] == 192
    else:
        assert llm.chat.await_args.kwargs["num_predict"] == 80


@pytest.mark.asyncio
async def test_language_switch_preserves_context_but_prioritizes_latest_question():
    llm = Mock(chat=AsyncMock(side_effect=[("Exercise can improve fitness.", {}), ("भारत की राजधानी नई दिल्ली है।", {})]))
    pipeline = VoicePipeline(llm=llm, sessions=SessionManager())
    await pipeline.chat("Tell me about exercise", "mixed", "en")
    result = await pipeline.chat(CASES[0][0], "mixed", "hi")
    messages = llm.chat.await_args.args[0]
    assert messages[-1]["content"] == CASES[0][0]
    assert "latest question" in messages[0]["content"]
    assert "Devanagari" in messages[0]["content"]
    assert any(m["content"] == "Exercise can improve fitness." for m in messages)
    assert "नई दिल्ली" in result.response


@pytest.mark.asyncio
async def test_typed_hindi_without_override_is_not_locked_to_previous_english():
    llm = Mock(chat=AsyncMock(return_value=("उत्तर", {})))
    pipeline = VoicePipeline(llm=llm, sessions=SessionManager())
    await pipeline.chat("Hello", "auto", "en")
    await pipeline.chat(CASES[0][0], "auto")
    assert "Devanagari" in llm.chat.await_args.args[0][0]["content"]


@pytest.mark.parametrize("text", ["", "बार बार बार बार", "यह सही है यह सही है यह सही है यह सही है", "उत्तर\ufffd", "<|im_start|>assistant"])
def test_obvious_bad_text_is_rejected(text):
    assert text_quality_error(text)


@pytest.mark.parametrize("text", ["नई दिल्ली।", "Python 3.11 में 2 files हैं।", "NASA का मिशन 2026 में है।", "New Delhi", "42", "चेन्नई तमिलनाडु की राजधानी है।"])
def test_names_numbers_and_mixed_language_are_allowed(text):
    assert text_quality_error(text) is None
    assert to_spoken_text(text) == text


def test_normalization_preserves_devanagari_marks_and_punctuation():
    assert normalize_text("  भारत की\nराजधानी नई दिल्ली है।  ") == "भारत की राजधानी नई दिल्ली है।"


@pytest.mark.asyncio
@pytest.mark.parametrize("answer,metadata", [("बार " * 8, {}), ("अधूरा उत्तर", {"done_reason": "length"}), ("", {})])
async def test_invalid_hindi_stream_never_reaches_tts_or_history(answer, metadata):
    class Llm:
        async def chat_stream(self, messages, *, num_predict):
            yield {"token": answer}
            yield {"done": True, "metadata": metadata}
    stt = Mock(transcribe=Mock(return_value=(CASES[0][0], {"language": "hi"})))
    tts = Mock(available_for=Mock(return_value=True))
    sessions = SessionManager()
    pipeline = VoicePipeline(llm=Llm(), stt=stt, tts=tts, sessions=sessions)
    events = []
    with pytest.raises(OllamaResponseError):
        async for event in pipeline.voice_stream("input.wav", "invalid", "hi"):
            events.append(event)
    assert [event["type"] for event in events] == ["transcript"]
    tts.synthesize_to_file.assert_not_called()
    assert (await sessions.list_sessions())[0][1] == 0


@pytest.mark.asyncio
async def test_valid_hindi_stream_uses_same_answer_for_text_and_speech():
    answer = "भारत की राजधानी नई दिल्ली है।"
    class Llm:
        async def chat_stream(self, messages, *, num_predict):
            yield {"token": "भारत की राजधानी "}
            yield {"token": "नई दिल्ली है।", "done": True, "metadata": {"done_reason": "stop"}}
    stt = Mock(transcribe=Mock(return_value=(CASES[0][0], {"language": "hi"})))
    tts = Mock(available_for=Mock(return_value=True), synthesize_to_file=Mock(return_value=(Path("reply.wav"), 1)))
    pipeline = VoicePipeline(llm=Llm(), stt=stt, tts=tts, sessions=SessionManager())
    events = [event async for event in pipeline.voice_stream("input.wav", language="hi")]
    assert events[-1]["response"] == answer
    assert "".join(e["delta"] for e in events if e["type"] == "text") == answer
    tts.synthesize_to_file.assert_called_once_with(answer, "hi")


@pytest.mark.asyncio
async def test_model_timeout_does_not_speak_or_commit_history():
    llm = Mock(chat=AsyncMock(side_effect=OllamaUnavailableError("Timed out; please retry.")))
    tts = Mock()
    stt = Mock(transcribe=Mock(return_value=(CASES[0][0], {"language": "hi"})))
    pipeline = VoicePipeline(llm=llm, stt=stt, tts=tts, sessions=SessionManager())
    with pytest.raises(OllamaUnavailableError):
        await pipeline.voice("input.wav", "timeout", "hi")
    tts.synthesize_to_file.assert_not_called()
    assert (await pipeline.sessions.list_sessions())[0][1] == 0


@pytest.mark.asyncio
async def test_uncertain_transcript_never_reaches_model_or_tts():
    stt = Mock(transcribe=Mock(side_effect=TranscriptionError("Please repeat clearly.")))
    llm, tts = Mock(), Mock()
    pipeline = VoicePipeline(llm=llm, stt=stt, tts=tts, sessions=SessionManager())
    with pytest.raises(TranscriptionError, match="repeat"):
        await pipeline.voice("input.wav", "uncertain", "hi")
    llm.chat.assert_not_called()
    tts.synthesize_to_file.assert_not_called()
    assert (await pipeline.sessions.list_sessions())[0][1] == 0


@pytest.mark.parametrize("logprob,compression", [(-1.5, 1.1), (-0.2, 3.0)])
def test_low_quality_stt_rejected_even_with_explicit_hindi(logprob, compression):
    service = SpeechToTextService(Settings())
    model = Mock()
    model.transcribe.return_value = ([SimpleNamespace(text="संदिग्ध", avg_logprob=logprob, compression_ratio=compression)], SimpleNamespace(duration=1))
    with pytest.raises(TranscriptionError, match="uncertain"):
        service._transcribe_with_model(model, "audio.wav", "hi")


@pytest.mark.parametrize("language,probability,expected_calls", [("hi", 0.95, 2), ("hi", 0.2, 1), ("en", 0.99, 1)])
def test_auto_detection_only_routes_confident_hindi_to_hindi_model(language, probability, expected_calls):
    service = SpeechToTextService(Settings(stt_multilingual_model_path=Path("small")))
    service._get_model_for_language = Mock(return_value=object())
    service._transcribe_with_model = Mock(return_value=("speech", SimpleNamespace(language=language, language_probability=probability)))
    service.transcribe("input.wav")
    assert service._get_model_for_language.call_count == expected_calls
    assert service._get_model_for_language.call_args.args[0] == ("hi" if expected_calls == 2 else None)
