# AI Voice Assistant

A local-first voice assistant internship project. React/TypeScript provides the dashboard; FastAPI orchestrates local speech recognition, Ollama chat, and local speech synthesis. The app does not use paid hosted inference APIs.

## Current implementation status

- Text chat uses the local Ollama HTTP API (default model `qwen2.5:3b`) and bounded in-memory conversation sessions.
- The voice endpoint runs Faster-Whisper → Ollama → Piper when the local speech models are explicitly installed.
- Browser recording, transcript/answer display, generated WAV playback, connection state, and measured stage timings are integrated in the frontend.
- Real two-turn text inference and conversation recall were verified against local Ollama/Qwen. Automated tests use mocked inference. Real STT/TTS output and full voice-pipeline behavior have not been verified because the speech model files are missing. See [benchmark results](docs/benchmark-results.md).

## Prerequisites

- Windows 11, Python 3.11, Node.js with npm, and Ollama.
- Ollama model `qwen2.5:3b` (or set `OLLAMA_MODEL=gemma2:2b`).
- For voice input/output: a local Faster-Whisper model directory and a Piper voice `.onnx` plus matching `.onnx.json` file.

## Configure and install

From PowerShell at the repository root:

```powershell
cd D:\Trikon-Voice-AI\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Install/run the local chat model (run `ollama serve` in a separate terminal if Ollama is not already serving):

```powershell
ollama serve
ollama list
ollama pull qwen2.5:3b
```

Voice models are optional for text chat and must be downloaded deliberately. See [architecture and model setup](docs/architecture.md) for exact commands and voice licensing notes. Backend startup and tests never download models.

Install the existing frontend dependencies:

```powershell
cd D:\Trikon-Voice-AI\frontend
npm ci
Copy-Item .env.example .env
```

The frontend uses the Vite `/api` proxy by default. Set `VITE_API_BASE_URL` in `frontend/.env` only if FastAPI is hosted at a different origin. Vite variables are public client-side values; never place secrets there.

## Run (three PowerShell terminals)

Terminal 1 (if needed):

```powershell
ollama serve
```

Terminal 2:

```powershell
cd D:\Trikon-Voice-AI\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 3:

```powershell
cd D:\Trikon-Voice-AI\frontend
npm run dev
```

Open `http://localhost:5173`. API docs: `http://127.0.0.1:8000/docs`; health: `http://127.0.0.1:8000/api/health`.

## API outline

- `GET /api/health` — backend, Ollama/model, speech model readiness, configured model names.
- `POST /api/chat` — JSON `{ "message": "Hello", "session_id": "optional-id" }`; returns response, session ID, and timing metrics.
- `GET /api/chat/sessions`, `DELETE /api/chat/{session_id}` — list and delete bounded in-memory sessions.
- `POST /api/voice` — multipart `audio` plus optional `session_id` and language override (`en`, `hi`, `ta`); returns real transcript, LLM response, playback URL, and STT/LLM/TTS/total timing.
- `GET /api/audio/{filename}` — serves generated WAV responses until cleanup (files older than one hour and files beyond the newest 100 are pruned on new synthesis).

## Verification

```powershell
cd D:\Trikon-Voice-AI\backend
python -m pytest
python -m compileall -q app tests

cd D:\Trikon-Voice-AI\frontend
npm test
npm run lint
npm run build
```

Automated tests do not need Ollama, speech model files, downloads, or GPU. Manual real-inference acceptance steps are in [demo script](docs/demo-script.md). For limitations and unmeasured performance, see [benchmarks](docs/benchmark-results.md).

## Data and limitations

Conversation history is held in process memory and resets after a backend restart. Uploaded audio is written to a temporary file and removed after processing; generated response WAVs are retained for playback and pruned after one hour or beyond 100 files on a subsequent synthesis. This development server has no authentication: keep it on localhost/trusted networks. Faster-Whisper defaults to CPU/int8; GPU use is not claimed or measured.
