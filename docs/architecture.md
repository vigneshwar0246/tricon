# AI Voice Assistant — backend architecture

The backend is a local-first FastAPI service. It does not call paid cloud AI APIs and does not automatically download models during startup, health checks, tests, or requests.

## Request flow

- `GET /api/health` checks the API and probes the local Ollama `/api/tags` endpoint. It reports configured model names separately from readiness, so an installed Ollama service with a missing Qwen model is not presented as ready. The overall health is `degraded` when the configured LLM model is unavailable; `services.api` still shows whether FastAPI itself is responding. STT and TTS are ready only when their packages and required local model files are present. This lightweight check does not run inference.
- `POST /api/chat` accepts `{ "message": "...", "session_id": "optional-id" }`. The service serializes requests for a session, sends bounded prior turns to Ollama's local `/api/chat` endpoint, and appends the new exchange only after a successful response. Omit `session_id` to create a new session; the response returns its ID. `GET /api/chat/sessions` lists in-memory sessions and `DELETE /api/chat/{session_id}` clears one.
- `POST /api/voice` accepts multipart form data with `audio`, optional `session_id`, and optional `language` (`en`, `hi`, or `ta`). The request is size/type/duration checked, transcribed by Faster-Whisper, answered by Ollama using the same session history, and synthesized by Piper. It returns transcript, answer, session ID, measured stage timings, and an `audio_url` that serves the generated WAV from this backend. History is committed only when the full voice turn succeeds.

Conversation state is held in memory: it is bounded by maximum sessions and turns, and does not survive a restart. Audio uploads are written to a temporary file and removed after processing. Synthesized WAVs are written to `backend/generated_audio`; files older than one hour and files beyond the newest 100 are opportunistically pruned when another response is synthesized. This development service has no authentication and should only be exposed to trusted local clients.

## Local model and platform choices

- LLM: Ollama HTTP API, configured to `qwen2.5:3b` by default. Ollama must be running and the model pulled separately. The backend checks model presence and never pulls it on behalf of a request.
- STT: Faster-Whisper is imported/lazy-loaded only on the first valid transcription. The default device is CPU with `int8`; no CUDA or GPU inference is claimed. Uploads are limited to 25 MB and five minutes by default (configurable). The configured model directory must already contain `model.bin`, `config.json`, and a vocabulary file. If these are absent, the voice route returns a clear service-unavailable error. `av==16.0.1` is pinned because Faster-Whisper 1.2.1 still passes a decoder argument removed in PyAV 19; [the upstream issue](https://github.com/SYSTRAN/faster-whisper/issues/1589) documents the compatibility break.
- TTS: Piper is selected because its `piper-tts` package publishes a Windows x64-compatible wheel. The default voice is `en_US-norman-medium`; its ONNX file and matching `.onnx.json` config are required. Piper's software is GPL-3.0 and voice/model licenses vary, so check the specific voice's terms before redistributing it. Norman's [model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/norman/medium/MODEL_CARD) lists its voice data as public domain and model repository as MIT. Piper is loaded lazily and configured for CPU by default.

The async Ollama client uses non-streaming requests and configurable timeouts. Health-check timeouts are shorter than generation timeouts. Errors map offline/missing models to HTTP 503, invalid/unsupported audio to 4xx, and upstream/protocol errors to appropriate gateway errors; messages do not contain environment secrets.

## Configuration

Copy `backend/.env.example` to `backend/.env` to override defaults. Important variables include `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (including `gemma2:2b` as an alternative), `STT_MODEL_PATH`, `STT_DEVICE`, `STT_COMPUTE_TYPE`, `AUDIO_MAX_SIZE_MB`, `AUDIO_MAX_DURATION_SECONDS`, `TTS_MODEL_PATH`, `TTS_CONFIG_PATH`, and `AUDIO_OUTPUT_DIR`. Relative paths resolve from the backend directory. Keep `.env` local; never commit credentials or secrets.

The Vite origins `http://localhost:5173` and `http://127.0.0.1:5173` are enabled by default. This is a development CORS setup, not a production deployment policy.

## Windows setup (PowerShell)

Run these commands from the repository root. Use Python 3.11 as specified for the project:

```powershell
cd D:\Trikon-Voice-AI\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On this machine, the previous Python 3.11 virtual environment points to an inaccessible interpreter. The verified runtime was created separately with the available Python 3.13.9: `python -m venv backend/.venv-run` from the repository root, then `uv pip install --python backend/.venv-run/Scripts/python.exe -r backend/requirements.txt`. The `.venv-run` directory is ignored by Git; the old `.venv` was left untouched. Python 3.11 remains the recommended setup when available.

Start Ollama in a separate terminal if it is not already running. Then check and install the configured chat model explicitly:

```powershell
ollama serve
ollama list
ollama pull qwen2.5:3b
```

The LLM works once Ollama is reachable and the selected model is present. Speech models are optional for text chat, but required for the full voice route. The following are explicit downloads (they are not performed by app startup):

```powershell
New-Item -ItemType Directory -Force models\faster-whisper-base | Out-Null
hf download Systran/faster-whisper-base --local-dir models/faster-whisper-base
New-Item -ItemType Directory -Force models\piper | Out-Null
python -m piper.download_voices en_US-norman-medium --download-dir models\piper
```

If PowerShell cannot find `hf`, use `python -m pip install huggingface-hub` in the active environment and reopen the terminal (or invoke the installed `hf.exe` from `.venv\Scripts`). Review model/voice terms before use. Start FastAPI from `backend/`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Interactive API docs are at `http://127.0.0.1:8000/docs`; health at `/api/health`. For frontend development, run the existing Vite app at port 5173.

## API examples

Text chat:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat `
  -ContentType 'application/json' `
  -Body '{"message":"Explain local AI simply","session_id":"demo-session"}'
```

Voice upload (provide an existing supported recording):

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/voice `
  -F "audio=@.\sample.wav;type=audio/wav" `
  -F "session_id=demo-session"
```

The JSON voice result contains the actual transcript and model answer, metrics, and a local `audio_url`. The UI uses the returned path to play the WAV. Health is informative even when services are offline; `services.api`, `services.llm`, `services.stt`, and `services.tts` must be read independently.

## Verification without model inference

From `backend/`, run `python -m pytest`. Tests replace inference with fakes or assert validation/errors; they do not download or load speech models and do not require Ollama to be running. A complete voice request requires both speech models to be installed, a reachable Ollama, and a configured local chat model. Browser microphone access requires a secure browser context (localhost qualifies) and the user's permission.

## Troubleshooting and limits

- `services.llm: false`: start Ollama, check `ollama list`, then pull the configured chat model explicitly.
- `services.stt: false`: ensure `STT_MODEL_PATH` contains the Faster-Whisper model files; no model is fetched automatically.
- `services.tts: false`: ensure the Piper `.onnx` and same-name `.onnx.json` exist at the configured paths.
- Browser microphone errors: open the Vite app on localhost, allow microphone permission, and use a browser with `MediaRecorder` support.
- If response WAVs are removed, synthesize a new response; generated audio retention is temporary.
- Conversation sessions are process-local and are lost on restart. This is a local internship/demo app, not an authenticated multi-user deployment.
- Inference performance, model VRAM use, and CUDA operation are not yet measured. See [benchmark-results.md](benchmark-results.md).
