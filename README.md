# AI Voice Assistant

A local-first voice assistant internship project. React/TypeScript provides the dashboard; FastAPI orchestrates local speech recognition, Ollama chat, and local speech synthesis. The app does not use paid hosted inference APIs.

## Current implementation status

- Text chat uses the local Ollama HTTP API (default model `qwen2.5:3b`) and bounded in-memory conversation sessions.
- The voice endpoint runs Faster-Whisper → Ollama → Piper when the local speech models are explicitly installed.
- Browser recording, transcript/answer display, ordered chunked-WAV playback, connection state, and measured stage timings are integrated in the frontend.
- Three dedicated English/Hindi/Tamil buttons persist the selected language in the browser and session. The interface remains English. English and Hindi have local speech input/output; Tamil input and Tamil-script text replies work, while Tamil speech output remains unavailable until a compatible local voice is configured.
- The incremental `/api/voice/stream` path streams Ollama tokens and synthesizes complete sentence/phrase chunks with Piper. Piper itself is not native-streaming. Optional hands-free barge-in stops playback, aborts the stale request, and captures the new turn.
- Real local Qwen text inference and a full Faster-Whisper → Ollama → Piper voice request were verified. The browser also has optional clap-activated hands-free capture while its page remains open; microphone and speaker hardware still need an interactive check. See [benchmark results](docs/benchmark-results.md).
- The custom “Carrot” wake word is **not active**: no trained, validated Carrot detector model is installed or integrated. The interface says so rather than reporting a false wake-word status.

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

For Hindi/Tamil speech output, configure the corresponding model/config paths with verified local voices. The active development installation already has Hindi Pratham configured and verified. The app never substitutes the English voice or a cloud service. Readiness for each stage/language is returned by `/api/health`.

Piper 1.8.0 currently lists Hindi voices but no Tamil voice. To reproduce the local Hindi Pratham installation, run this from `backend/`, configure its two paths in `.env`, and restart FastAPI:

```powershell
python -m piper.download_voices hi_IN-pratham-medium --download-dir models\piper
```

Review the downloaded voice's model card/license and verify Hindi synthesis before marking it ready on another machine. Tamil voice output remains blocked; do not configure an invented filename or use the English voice.

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

Open `http://localhost:5173`. API docs: `http://127.0.0.1:8000/docs`; health: `http://127.0.0.1:8000/api/health`; runtime diagnostics: `http://127.0.0.1:8000/api/diagnostics`.

## Browser hands-free mode

On Home, select **Enable hands-free**, grant browser microphone permission, and leave the page open. By default two claps (about 0.25–0.9 seconds apart) activate command capture. A short tone acknowledges activation. Speak after the tone; capture ends after 0.9 seconds of detected silence, after 12 seconds maximum, or discards an empty command after five seconds. The app transcribes only that captured clip, plays the real generated answer, then rearms. **Mute** stops activation without releasing the microphone; **Stop hands-free** releases the device and cancels a pending browser request. You can adjust clap sensitivity, one/two-clap mode, and silence duration. Use headphones or quiet speakers to reduce feedback. Clap detection is a heuristic and may react to sharp keyboard/impact sounds; test and tune it in your room.

This is page-local behavior, not a system-wide background assistant. A browser can suspend timers/audio when the tab is inactive, and automatic playback may be blocked by browser policy. Browser microphone and speaker behavior has not been physically verified on this machine. Custom “Carrot” requires a separately trained model and a dedicated local detector integration; see [architecture.md](docs/architecture.md).
Stopping hands-free aborts the browser request and playback immediately; a FastAPI/Ollama request already underway may still finish on the server, so this is not a guaranteed GPU-compute cancellation.

## API outline

- `GET /api/health` — backend, Ollama/model, speech model readiness, configured model names.
- `GET /api/diagnostics` — configured STT device, last successful STT device, CUDA library check, and Ollama's currently loaded model/VRAM report.
- `POST /api/chat` — JSON `{ "message": "Hello", "session_id": "optional-id" }`; returns response, session ID, and timing metrics.
- `GET /api/chat/sessions`, `DELETE /api/chat/{session_id}` — list and delete bounded in-memory sessions.
- `POST /api/voice` — multipart `audio` plus optional `session_id` and language override (`en`, `hi`, `ta`); returns real transcript, response, playback URL, STT/LLM/TTS/total timing, and an optional allowlisted command action. Exact spoken commands for local time, system status, repeat, clear conversation, and stop listening bypass the LLM; unsupported system actions are rejected.
- `POST /api/voice/stream` — NDJSON transcript, token delta, ordered Piper audio-chunk, completion, and timing events. Client cancellation prevents an incomplete assistant turn from being committed.
- `GET /api/audio/{filename}` — serves generated WAV responses until cleanup (files older than one hour and files beyond the newest 100 are pruned on new synthesis).

## Verification

```powershell
cd D:\Trikon-Voice-AI\backend
python -m pytest
python -m compileall -q app tests
python scripts/benchmark_voice.py scripts/multilingual-manifest.example.json --runs 5 --output benchmark.json

cd D:\Trikon-Voice-AI\frontend
npm test
npm run lint
npm run build
```

Automated tests do not need Ollama, speech model files, downloads, or GPU. Manual real-inference acceptance steps are in [demo script](docs/demo-script.md). For limitations and unmeasured performance, see [benchmarks](docs/benchmark-results.md).

The latest real English short/long measurements are in [docs/benchmark-2026-10-21.json](docs/benchmark-2026-10-21.json). Interpretation, WER normalization, and limitations are recorded in [docs/benchmark-results.md](docs/benchmark-results.md).

## Data and limitations

Conversation history is held in process memory and resets after a backend restart. Uploaded audio is written to a temporary file and removed after processing; generated response WAVs are retained for playback and pruned after one hour or beyond 100 files on a subsequent synthesis. This development server has no authentication: keep it on localhost/trusted networks. Faster-Whisper uses CUDA/float16 in the local configuration. CUDA 12.4 runtime libraries are loaded from the virtual environment, and `/api/diagnostics` reports GPU STT as verified only after a successful transcription; CPU/int8 remains the automatic fallback.
