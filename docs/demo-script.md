# AI Voice Assistant — demo script

## Before the demo

1. From the repo root, start Ollama in a terminal with `ollama serve` if it is not already running.
2. Confirm the configured LLM exists with `ollama list`. If needed, explicitly install it with `ollama pull qwen2.5:3b` (this is a local model download, not a cloud API).
3. Start the backend from `backend/` using `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` and start the existing Vite frontend on port 5173.
4. Open `http://127.0.0.1:8000/api/health`. Check the `ollama`, `services.llm`, `services.stt`, and `services.tts` fields. A missing speech model means voice is not ready; do not describe it as working until the relevant model is installed.
5. For a voice demo, ensure the Faster-Whisper directory configured by `STT_MODEL_PATH` contains its model files and the Piper `TTS_MODEL_PATH` plus matching JSON config are present. Installation steps are in [architecture.md](architecture.md).

## Walkthrough

1. Introduce the app as a local-first voice assistant using an Ollama-hosted open-weight model; no paid cloud AI API is used.
2. Send a short text question. Point out that the response includes a session ID and timings, and ask a follow-up using that ID to demonstrate conversation context.
3. Open `/api/chat/sessions` to show the current bounded, in-memory session list; delete a test session with `DELETE /api/chat/{session_id}` if useful.
4. If both speech models are ready, upload a short supported recording to `POST /api/voice` with multipart field `audio` and optional `session_id`. Show the transcript, generated answer, measured stage latencies, and returned WAV playback URL.
5. Explain that sessions live in memory and reset when the API process restarts. Speech output files are stored under `backend/generated_audio`.

## Honest fallback

If Ollama is offline or Qwen is missing, show the health response and the API's explicit unavailable error rather than inventing an answer. If speech models are not installed, demonstrate text chat and explain that the voice route returns a clear setup error. Health checks do not download models or claim GPU readiness.

## Manual acceptance checklist

1. Open the UI and confirm the status card reflects `/api/health`; it must not show STT/TTS ready until their local files exist.
2. Send a text prompt, then a follow-up; confirm an actual model response appears and performance shows measured LLM/total timing.
3. Clear the conversation; confirm the messages disappear and the backend session deletion request succeeds.
4. With speech models installed, click the main microphone, grant permission, speak a short sentence, then click stop. Confirm the actual transcript and assistant response appear, STT/LLM/TTS metrics populate, and the WAV playback control works.
5. Refresh health after stopping Ollama or pointing at a missing model; confirm errors/readiness update without a fabricated response.
