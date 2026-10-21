# Trikon Voice AI — Complete Project Guide and Current Status

Last verified: **21 October 2026 (Asia/Calcutta)**

## 1. Executive summary

Trikon Voice AI is a local-first voice assistant. The browser frontend records speech and displays conversations; a FastAPI backend validates requests and coordinates speech recognition, language-model inference, and speech synthesis. All inference stays on the computer:

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Framer Motion.
- **Backend:** Python 3.11, FastAPI, Uvicorn.
- **Speech-to-text (STT):** Faster-Whisper `base` through CTranslate2.
- **Language model (LLM):** `qwen2.5:3b` through the local Ollama HTTP API.
- **Text-to-speech (TTS):** Piper `en_US-norman-medium`.
- **Conversation storage:** bounded in-memory sessions; no database.

The complete project is currently operational. Frontend, backend, Ollama, STT, and TTS were connected and tested together. CUDA acceleration is working for Ollama, but Faster-Whisper CUDA inference is **not** available because the CUDA 12 cuBLAS runtime DLL required by CTranslate2 is missing. Faster-Whisper therefore uses the verified CPU/int8 configuration.

The October 2026 latency/multilingual upgrade adds persistent automatic/manual language control, honest per-language stage readiness, Ollama token streaming, sentence-safe chunked Piper output, configurable VAD behavior, generation-safe cancellation, and optional hands-free barge-in. English is the only installed end-to-end speech language. Hindi and Tamil STT/text paths exist, but their speech output is deliberately blocked until compatible local voices are installed and verified.

## 2. Current verified status

| Component | Current status | Verified configuration |
| --- | --- | --- |
| Frontend | Running and reachable | `http://127.0.0.1:5173` |
| Backend | Running and reachable | `http://127.0.0.1:8000` |
| API documentation | Available | `http://127.0.0.1:8000/docs` |
| Ollama | Ready | Local service at `http://127.0.0.1:11434` |
| LLM | Ready | `qwen2.5:3b` |
| STT model | Ready | `backend/models/faster-whisper-base` |
| STT execution | Verified | CPU with `int8` compute |
| STT CUDA execution | Not verified / unavailable | Missing `cublas64_12.dll` |
| TTS model | Ready | `en_US-norman-medium` on CPU |
| Full voice request | Passed | WAV → Whisper → Qwen → Piper → WAV |
| Incremental voice stream | Passed | NDJSON tokens → sentence-safe Piper chunks |
| English language stages | Ready | STT, LLM and TTS |
| Hindi language stages | Partial | STT and LLM ready; local TTS voice missing |
| Tamil language stages | Partial | STT and LLM ready; local TTS voice missing |
| Backend automated tests | Passed | 29 tests |
| Frontend automated tests | Passed | 18 tests |
| Frontend production build | Passed | TypeScript and Vite build |
| Carrot wake word | Not implemented | No trained/evaluated Carrot model |

The live integration test produced all of the following:

1. Frontend HTTP response: `200`.
2. Backend health status: `ok`.
3. A real Ollama request returned exactly `LOCAL MODEL CONNECTED`.
4. A real audio request was transcribed by Faster-Whisper.
5. Qwen generated the answer.
6. Piper generated a playable WAV response.

The latest full audio integration observation was approximately:

| Stage | Time |
| --- | ---: |
| STT | 13,044.69 ms |
| LLM | 1,721.08 ms |
| TTS | 6,412.27 ms |
| Total | 26,892.80 ms |

This is one real end-to-end observation using a long existing WAV, not a controlled benchmark. Warm short requests are normally faster.

## 3. High-level architecture

```text
Microphone / typed message
          |
          v
React + TypeScript browser application (port 5173)
          |
          |  Vite proxies /api to port 8000
          v
FastAPI backend (port 8000)
          |
          +---------------- Text chat ----------------+
          |                                            |
          |                                     Ollama / Qwen
          |                                            |
          +---------------- Voice request -------------+
                               |
                               v
                    Faster-Whisper (speech to text)
                               |
                               v
                   command router or Ollama / Qwen
                               |
                               v
                       Piper (text to WAV)
                               |
                               v
                 /api/audio/<generated-file>.wav
                               |
                               v
                         Browser playback
```

All three inference engines are loaded or contacted lazily. Backend startup and health checks do not download models and do not perform expensive inference.

## 4. Repository structure

```text
Trikon-Voice-AI/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # health, diagnostics, chat and voice HTTP routes
│   │   ├── core/             # settings and logging
│   │   ├── schemas/          # Pydantic request/response contracts
│   │   ├── services/         # Ollama, STT, TTS, sessions and orchestration
│   │   └── main.py           # FastAPI construction and service lifecycle
│   ├── models/               # local Whisper and Piper model files
│   ├── generated_audio/      # temporary generated response WAV files
│   ├── tests/                # backend test suite
│   ├── wakeword/             # future Carrot training/evaluation workbench
│   ├── .env                  # active backend configuration (local only)
│   └── requirements.txt
├── frontend/
│   ├── public/               # static assets
│   ├── src/
│   │   ├── components/       # voice controls, conversation and status UI
│   │   ├── context/          # shared voice/conversation state
│   │   ├── hooks/            # hands-free microphone controller
│   │   ├── lib/              # API and audio-detection helpers
│   │   └── pages/            # intro, dashboard, conversations, settings, about
│   ├── package.json
│   └── vite.config.ts
├── docs/                     # architecture, benchmark and demo documentation
├── README.md                 # quick setup and usage guide
└── all.md                    # this complete guide
```

## 5. Startup and dependency workflow

### Prerequisites

- Windows 11.
- Python 3.11.
- Node.js and npm.
- Ollama.
- NVIDIA GPU is optional. CPU mode is fully functional.

Versions observed during the latest verification:

- Python: `3.11.9`
- Node.js: `22.19.0`
- npm: `10.9.3`
- Ollama: `0.40.7`
- NVIDIA driver: `581.57`
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, 6 GB VRAM

### First-time backend setup

Run from PowerShell:

```powershell
cd D:\Trikon-Voice-AI\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The current `backend/.venv` is installed and working. The application dependencies include FastAPI, Uvicorn, HTTPX, Faster-Whisper, CTranslate2, PyAV 16, Piper, pytest, and pytest-asyncio.

### First-time frontend setup

```powershell
cd D:\Trikon-Voice-AI\frontend
npm ci
Copy-Item .env.example .env
```

`frontend/.env` is optional when using the standard Vite proxy. Its default empty `VITE_API_BASE_URL` makes the browser call same-origin `/api`, which Vite proxies to FastAPI.

### Install and start the local language model

```powershell
ollama serve
ollama list
ollama pull qwen2.5:3b
```

Installed models observed on this machine:

- `qwen2.5:3b` — active default chat model.
- `gemma2:2b` — installed alternative.
- `nomic-embed-text:latest` — installed embedding model, not used by this application.

### Start the complete application

Use three PowerShell terminals.

Terminal 1, only if Ollama is not already running:

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
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173` and allow microphone access when prompted.

## 6. Frontend workflow

### Routing and screens

The React application has these routes:

- `/intro` — standalone introduction screen.
- `/` — main voice dashboard; first-time session visitors are redirected to `/intro`.
- `/conversations` — conversation view.
- `/settings` — hands-free and assistant settings.
- `/about` — project information.

The intro-seen flag is held in browser `sessionStorage`; it is not a user account or permanent profile.

### Text chat flow

1. The user enters a message.
2. `frontend/src/lib/api.ts` sends JSON to `POST /api/chat`.
3. The request carries the current `session_id`, if one exists.
4. FastAPI returns the assistant response, session ID, timestamp, and timing metrics.
5. React updates the shared conversation state and displays the turn.

### Manual voice flow

1. The browser asks for microphone permission.
2. `MediaRecorder` captures a browser-supported audio format, normally WebM.
3. The frontend creates multipart form data containing the recording, session ID, and optional language.
4. It sends the data to `POST /api/voice`.
5. The backend returns the transcript, assistant text, action, metrics, and an `/api/audio/...` URL.
6. The UI shows both text sides of the turn and plays the generated WAV.

### Continuous hands-free flow

Hands-free mode is page-local, not a system background service:

1. The user explicitly enables hands-free mode.
2. The browser opens one microphone stream with echo cancellation and noise suppression.
3. A Web Audio analyser samples 512-sample frames every 10 ms.
4. A zero-gain output node keeps the audio graph active without playing microphone audio through the speakers.
5. Local energy-based voice activity detection estimates speech against a rolling noise floor.
6. Capture ends after the selected post-speech silence, at the maximum duration, or is discarded after the no-speech timeout.
7. The captured turn is uploaded to `/api/voice`.
8. With barge-in disabled, capture waits until playback completes. With barge-in enabled, the analyser remains active during playback and requires sustained speech onset before interrupting.
9. A confirmed interruption stops audio, aborts the stale stream, invalidates old callbacks, and immediately starts a new capture.
10. Echo cancellation and multi-frame onset reduce self-triggering, but real full-duplex behavior still depends on the microphone, speakers, browser, and room.
11. The loop rearms after playback unless muted or stopped.

Important limits:

- This is simple energy-based speech endpointing, not a neural VAD.
- Room noise and microphone gain can affect detection.
- Browsers may suspend background tabs.
- Browser autoplay and microphone permissions still apply.
- A real microphone/speaker check must be performed interactively on the target device.

### Carrot wake word

The word **Carrot is not an active wake word**. There is no trained Carrot ONNX model, licensed training dataset, held-out evaluation result, backend streaming detector, or browser-to-detector audio stream. The `backend/wakeword` directory is only a future training and evaluation workbench. Installing openWakeWord alone would not complete this feature.

## 7. Backend request workflow

### Application lifecycle

At startup, `backend/app/main.py` creates:

- one reusable async Ollama client;
- one bounded session manager;
- one lazy Faster-Whisper service;
- one lazy Piper service;
- one voice pipeline orchestrator.

The Ollama HTTP client closes during application shutdown. Speech models are not loaded during import or health checks; they load on the first relevant request.

### Text chat processing

1. Pydantic validates `message` and `session_id`.
2. The session manager creates or finds the session.
3. A per-session async lock serializes concurrent turns in the same conversation.
4. Bounded prior user/assistant messages are copied into the Ollama prompt.
5. Text chat calls Ollama `/api/chat` with non-streaming mode; voice streaming uses Ollama's NDJSON streaming mode.
6. Ollama uses the configured temperature, context size, output-token limit, and 15-minute keep-alive.
7. The exchange is stored only after a successful answer.
8. The API returns the response with measured timing.

### Voice processing

1. FastAPI checks the file extension and content type.
2. The upload is streamed to a temporary file in 1 MB chunks.
3. The request is rejected if it exceeds the configured size limit or is empty.
4. Faster-Whisper decodes and transcribes the local file.
5. The pipeline checks for exact allowlisted local commands.
6. Ordinary language is sent to Qwen with a short spoken-response system prompt and an 80-token voice limit.
7. Piper converts the answer to a WAV file.
8. Only after the entire voice turn succeeds is the conversation exchange committed.
9. The uploaded temporary file is always deleted in the route's `finally` block.
10. The response returns the transcript, text answer, optional action, stage timings, and local audio URL.

The `/api/voice/stream` variant emits a transcript event, token deltas, ordered audio events synthesized at complete sentence/phrase boundaries, and a final completion/metrics event. Piper receives complete chunks and is therefore **chunked synthesis, not native streaming TTS**. If the client cancels, the incomplete assistant response is not committed to session history.

### Local command routing

The following exact spoken intents can bypass the LLM:

- Current time.
- System/assistant status.
- Repeat the last response.
- Clear the conversation.
- Stop listening.

Potentially destructive or system-changing verbs such as open, launch, run, execute, delete, and remove are explicitly refused. The voice assistant does not execute shell commands or manipulate files.

### TTS preparation and storage

Before Piper receives text, the backend removes markdown, links, URLs, code blocks, emoji, and symbols that would sound unnatural. Piper uses a `0.92` length scale for a slightly faster natural voice.

Generated WAV files live in `backend/generated_audio`. On later synthesis calls, the service removes files older than one hour and files beyond the newest 100. These files are temporary application output, not permanent history.

## 8. Sessions, state, and concurrency

- Sessions are stored only in backend process memory.
- They disappear whenever FastAPI restarts.
- The default maximum is 500 sessions.
- The default history is 12 user/assistant turns per session.
- Every session has a lock so two requests cannot corrupt ordering.
- When capacity is reached, the oldest idle session is evicted.
- A busy session is not evicted.
- If every slot is busy, the backend returns HTTP 429.
- Deleting a session waits safely for active work and prevents new work from entering that session.
- There is no login, authentication, database, cross-device synchronization, or durable history.

## 9. API reference

### `GET /api/health`

Lightweight readiness report. It checks FastAPI, Ollama reachability, configured LLM presence, and local STT/TTS files. It does not run inference.

### `GET /api/diagnostics`

Reports configured and active STT devices, compute type, last successful STT device, CPU fallback reason, CUDA device count and DLL detection, whether CUDA STT inference has actually succeeded, and Ollama-loaded model VRAM allocation.

### `POST /api/chat`

Request:

```json
{
  "message": "Explain local AI simply",
  "session_id": "optional-session-id"
}
```

`message` accepts 1–8,000 characters. `session_id` accepts 1–128 characters.

### `GET /api/chat/sessions`

Lists current in-memory session IDs, message counts, and last update times.

### `DELETE /api/chat/{session_id}`

Safely clears one in-memory session.

### `POST /api/voice`

Multipart fields:

- `audio` — required audio file.
- `session_id` — optional, maximum 128 characters.
- `language` — optional: `en`, `hi`, or `ta`.

Supported filename types include WAV, MP3, M4A, OGG, WebM, MP4, FLAC, MPEG, and MPGA. Defaults limit uploads to 25 MB and five minutes.

### `POST /api/voice/stream`

Accepts the same multipart fields and returns `application/x-ndjson` events: `transcript`, `text`, `audio`, `done`, or `error`. Audio events are ordered local WAV URLs. Completion metrics distinguish first token, first synthesized audio availability, total LLM, accumulated TTS, STT, and total server time.

### `GET /api/audio/{filename}`

Serves locally generated response WAV files.

### Error behavior

- `4xx` — invalid message, unsupported/empty/oversized audio, no detected speech, capacity limit.
- `503` — Ollama, configured LLM, Whisper model, or Piper model unavailable.
- `502` — invalid upstream model response or synthesis failure.
- `500` — unexpected voice pipeline error; inspect backend logs.

## 10. Configuration reference

Backend configuration is read from `backend/.env`. Relative paths resolve from `backend/`.

| Variable | Purpose | Current/default value |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Chat model | `qwen2.5:3b` |
| `OLLAMA_TIMEOUT_SECONDS` | Generation timeout | `120` |
| `OLLAMA_TEMPERATURE` | Sampling temperature | `0.7` |
| `OLLAMA_NUM_CTX` | Context window requested from Ollama | `4096` |
| `OLLAMA_NUM_PREDICT` | Text-chat output ceiling | backend default `160` |
| `VOICE_NUM_PREDICT` | Voice output ceiling | `80` |
| `STT_MODEL_PATH` | Local Whisper model directory | `models/faster-whisper-base` |
| `STT_DEVICE` | Whisper device | `cpu` |
| `STT_COMPUTE_TYPE` | Whisper precision/quantization | `int8` |
| `STT_BEAM_SIZE` | Whisper search beam size | `5` |
| `STT_LANGUAGE_CONFIDENCE_THRESHOLD` | Auto-detection confirmation threshold | `0.55` |
| `STT_LANGUAGE` | Forced language or auto detection | omitted / auto |
| `AUDIO_MAX_SIZE_MB` | Upload size limit | `25` |
| `AUDIO_MAX_DURATION_SECONDS` | Audio duration limit | `300` |
| `TTS_MODEL_PATH` | Piper ONNX voice | `models/piper/en_US-norman-medium.onnx` |
| `TTS_CONFIG_PATH` | Piper voice JSON | inferred as `<model>.json` |
| `TTS_HI_MODEL_PATH` / `TTS_HI_CONFIG_PATH` | Hindi Piper voice files | not configured |
| `TTS_TA_MODEL_PATH` / `TTS_TA_CONFIG_PATH` | Tamil Piper voice files | not configured |
| `TTS_USE_CUDA` | Piper CUDA request | `false` |
| `AUDIO_OUTPUT_DIR` | Generated response files | `generated_audio` |
| `SESSION_MAX_TURNS` | Retained exchanges per session | `12` |
| `SESSION_MAX_COUNT` | Maximum in-memory sessions | `500` |
| `LOG_LEVEL` | Backend logging level | `INFO` |

Frontend configuration uses `VITE_API_BASE_URL`. Leave it empty for Vite's proxy. Never store secrets in a `VITE_*` value because Vite embeds it into public browser JavaScript.

## 11. CUDA status and exact failure explanation

### What works on the GPU

The NVIDIA GPU and driver are functioning:

- `nvidia-smi` detects one NVIDIA GeForce RTX 3050 Laptop GPU.
- Driver version is `581.57`.
- `nvidia-smi` displays CUDA capability/version `13.0`.
- CTranslate2 enumerates one CUDA device.
- Ollama has loaded `qwen2.5:3b` and reports `2,163,568,803` bytes of model VRAM allocation, about 2.16 GB.
- The active Ollama `llama-server.exe` process is visible as a GPU compute process.

Therefore, saying “CUDA is completely broken” would be incorrect. GPU inference is working for Ollama.

### What fails

Faster-Whisper GPU inference is not verified and previously failed with:

```text
Library cublas64_12.dll is not found or cannot be loaded
```

Current diagnostics report:

```text
configured_device: cpu
active_device: cpu
compute_type: int8
last_successful_device: cpu
CUDA device_count: 1
cublas12_found: false
cudnn9_found: true
inference_verified: false
```

`where.exe cublas64_12.dll` also returns no matching file.

### Why it fails

There are three separate layers that are easy to confuse:

1. **NVIDIA display/compute driver:** installed and healthy; this is what `nvidia-smi` primarily proves.
2. **CUDA user-space runtime libraries:** DLLs such as cuBLAS and cuDNN needed by an application.
3. **The Python inference engine:** CTranslate2/Faster-Whisper, compiled against specific runtime-library major versions.

The driver reports CUDA 13.0 compatibility, but that does **not** install every CUDA toolkit/runtime DLL and does not supply the specifically named CUDA 12 library `cublas64_12.dll`. The installed CTranslate2 build used by Faster-Whisper expects CUDA 12 cuBLAS and cuDNN 9. cuDNN 9 is currently discoverable, but cuBLAS 12 is not. GPU enumeration and even model construction are insufficient proof; the missing library is needed when real matrix computation begins during transcription.

This is why the project can simultaneously have:

- a visible GPU;
- a healthy NVIDIA driver;
- Ollama running its own GPU stack successfully;
- and Faster-Whisper CUDA failing due to its separate missing runtime dependency.

### Current safe behavior

`STT_DEVICE=cpu` and `STT_COMPUTE_TYPE=int8` are deliberately configured. This is the verified path and was used successfully in the full voice integration test.

The STT service also contains a defensive fallback. If CUDA is configured and CUDA model loading or CUDA inference raises a CUDA-specific error, the service records a short failure reason, loads CPU/int8, retries that transcription once, and reports the device that actually succeeded. It does not falsely claim GPU success.

### How to enable and verify CUDA STT

Install compatible **CUDA 12 cuBLAS** and **cuDNN 9** runtime libraries for the installed CTranslate2/Faster-Whisper combination. Do not assume the newest toolkit is automatically compatible with a binary expecting a different DLL major version. Follow the official CTranslate2/Faster-Whisper requirements and NVIDIA Windows installation instructions.

After installation, open a new PowerShell terminal and verify:

```powershell
where.exe cublas64_12.dll
where.exe cudnn64_9.dll
```

Then temporarily configure:

```dotenv
STT_DEVICE=cuda
STT_COMPUTE_TYPE=float16
```

Restart FastAPI and submit a real short audio clip. Finally inspect:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/diagnostics | ConvertTo-Json -Depth 10
```

CUDA STT is verified only when all of these are true:

- the request returns a non-empty, correct transcript;
- `last_successful_device` is `cuda`;
- `inference_verified` is `true`;
- no CPU fallback reason is present.

Do not make CUDA the default merely because `nvidia-smi`, device enumeration, or model loading succeeds. A real transcription is the acceptance test.

### Piper CUDA status

Piper currently runs on CPU. `TTS_USE_CUDA=false` is intentional. The installed ONNX Runtime setup does not provide a verified CUDA execution provider for this TTS path. Installing STT's CUDA libraries does not automatically accelerate Piper.

## 12. Local models and data handling

### Model files

The project already contains:

- Faster-Whisper base model files: `config.json`, `model.bin`, tokenizer, and vocabulary.
- Piper `en_US-norman-medium.onnx` and matching `.onnx.json`.
- Ollama's `qwen2.5:3b` in Ollama's separate local model store.

The backend never downloads a model automatically. This prevents hidden network usage and unexpected startup delays.

### Data lifecycle

- Uploaded voice data is written to a temporary file and deleted after the request, including error paths.
- Generated response WAV files are retained temporarily and pruned opportunistically.
- Conversation text remains only in FastAPI process memory.
- Nothing is persisted to a database.
- No hosted inference API is used by the application.
- The service has no authentication; keep it bound to localhost or a trusted development network.

## 13. Testing and verification

### Backend

```powershell
cd D:\Trikon-Voice-AI\backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m compileall -q app tests
```

On this machine, the standard Windows user temp pytest directory had an access-control problem. The application tests themselves pass when pytest receives a writable temporary directory. One working verification command is:

```powershell
New-Item -ItemType Directory -Force .test-tmp | Out-Null
$env:TEMP=(Resolve-Path .test-tmp).Path
$env:TMP=$env:TEMP
python -m pytest -q -p no:cacheprovider
```

Result: **29 passed**. The temp-directory permission error is an operating-system/test-runner environment issue, not a backend logic failure.

### Frontend

```powershell
cd D:\Trikon-Voice-AI\frontend
npm test
npm run lint
npm run build
```

Latest verified results:

- Tests: **18 passed across 4 test files**.
- Production build: **passed**.
- Vite transformed 2,107 modules and produced the `dist` bundle.

The jsdom test warning that `HTMLMediaElement.play()` is not implemented is expected for a simulated browser and did not fail the suite.

### Manual API checks

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health | ConvertTo-Json -Depth 10
```

Diagnostics:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/diagnostics | ConvertTo-Json -Depth 10
```

Text chat:

```powershell
$body = @{ message='Hello'; session_id='manual-test' } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/chat `
  -Method Post -ContentType 'application/json' -Body $body
```

Voice:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/voice `
  -F "audio=@.\sample.wav;type=audio/wav" `
  -F "session_id=manual-voice-test" `
  -F "language=en"
```

## 14. Performance behavior

- Cold requests can include model loading and are much slower than warm requests.
- Ollama keeps the selected model resident for 15 minutes, trading VRAM use for lower later latency.
- The LLM client reuses one async HTTP connection.
- Voice replies use a short spoken-style prompt and an 80-token cap to reduce generation and TTS time.
- The incremental voice endpoint exposes Ollama tokens immediately and starts Piper when a complete sentence or safe long phrase is ready.
- Piper itself still generates a complete WAV per chunk; this is not native sample streaming.
- A one-sentence answer may still finish LLM generation before its only safe TTS chunk exists, so streaming primarily improves multi-sentence answers.
- CPU Whisper is reliable but is currently the largest avoidable latency source for short clips.
- Existing measurements are samples, not statistically controlled benchmarks.

For a proper benchmark, record cold and warm requests separately, use the same audio clips, run multiple repetitions, report median and p95, and measure browser end-of-speech to first audible playback on real hardware.

## 15. Security and production limitations

This is a local development/demo application, not a production multi-user service.

- There is no authentication or authorization.
- CORS allows the local Vite origins only.
- FastAPI is intended to bind to `127.0.0.1`.
- Sessions and generated audio are not user-isolated.
- Generated files are accessible by their URL while retained.
- There is no database, encryption-at-rest layer, rate limiter, reverse proxy, TLS setup, audit log, or backup process.
- Uploaded content is validated by extension/content type and decoded by media libraries, but a production upload service would require additional isolation and hardening.
- Voice system actions are allowlisted and never invoke a shell.
- Environment files must remain uncommitted. Do not place secrets in frontend variables.

Before exposing this beyond localhost, add authentication, explicit user-level data isolation, durable storage policy, HTTPS/reverse proxy configuration, stricter rate and resource controls, observability, and a threat-model review.

## 16. Known limitations and next steps

1. **CUDA STT:** install the compatible CUDA 12 cuBLAS runtime, retain cuDNN 9, and verify with a real transcription before enabling it.
2. **Carrot wake word:** collect licensed diverse data, train and evaluate a real model, implement streaming detection, and keep the UI marked unavailable until held-out evaluation passes.
3. **Physical audio acceptance:** test microphone permission, different browsers, speaker playback, echo, and noisy rooms interactively.
4. **Persistence:** add a database only if durable sessions are a real requirement.
5. **Streaming:** Ollama token streaming and sentence-safe chunked Piper playback are implemented. Native Piper sample streaming is not implemented.
6. **Production readiness:** authentication, HTTPS, rate limiting, per-user isolation, deployment supervision, and monitoring are absent.
7. **Benchmarking:** current timing samples demonstrate functionality but do not establish stable p50/p95 performance.

## 17. Troubleshooting checklist

### Frontend does not open

- Confirm Vite is listening on port 5173.
- Run `npm ci`, then `npm run dev` from `frontend/`.
- Check `frontend/server.stderr.log` if using the background launch setup.

### Backend health fails

- Activate `backend/.venv`.
- Reinstall `requirements.txt`.
- Start Uvicorn from the `backend/` directory.
- Inspect `backend/server.stderr.log` if using the background launch setup.

### LLM is unavailable

```powershell
ollama list
ollama serve
ollama pull qwen2.5:3b
```

Confirm `OLLAMA_MODEL` matches an installed tag exactly.

### STT is unavailable

Confirm `backend/models/faster-whisper-base` contains `model.bin`, `config.json`, and a vocabulary file, and that Faster-Whisper is installed in the active environment.

### CUDA STT fails

Check `/api/diagnostics`, then `where.exe cublas64_12.dll` and `where.exe cudnn64_9.dll`. Keep CPU/int8 enabled until a real CUDA transcription succeeds.

### TTS is unavailable

Confirm both of these files exist:

```text
backend/models/piper/en_US-norman-medium.onnx
backend/models/piper/en_US-norman-medium.onnx.json
```

### Microphone does not work

- Use `localhost` or `127.0.0.1`.
- Grant browser microphone permission.
- Confirm the device is not exclusively held by another program.
- Use a browser supporting `MediaRecorder`, `AudioContext`, and `getUserMedia`.
- Stop and restart hands-free mode after changing devices.

### Voice request is slow

- Separate cold and warm behavior.
- Check returned `stt_ms`, `llm_ms`, `tts_ms`, and `total_ms`.
- Keep answers short.
- Avoid very long recordings.
- Verify whether Ollama is loaded on the GPU with `/api/diagnostics`.
- Do not enable CUDA Whisper until its runtime dependencies pass real inference.

## 18. Definition of “fully working” for this project

The project is working completely in its currently implemented scope when:

- Vite returns HTTP 200 on port 5173.
- FastAPI returns `status: ok` on `/api/health`.
- `services.api`, `services.llm`, `services.stt`, and `services.tts` are true.
- A text request returns a real local Qwen answer.
- A browser or uploaded recording produces a transcript.
- The same request produces assistant text and a playable local WAV.
- Session continuation and clearing work.
- The automated backend and frontend suites pass.

Those conditions have been verified. CUDA STT and the Carrot wake word are optional/unimplemented enhancements and are not part of the currently verified working path. The accurate current claim is:

> **The local English voice assistant is operational using GPU-backed Ollama, CPU/int8 Faster-Whisper, and CPU Piper, including chunked output and optional barge-in logic. Hindi and Tamil end-to-end speech remain blocked by missing compatible local voices and lawful evaluation recordings. Faster-Whisper CUDA acceleration is not operational because CUDA 12 cuBLAS is missing, and the Carrot wake word is not implemented.**

## 19. Master-prompt upgrade report and acceptance matrix

### Implemented changes

- Language selection supports auto, English, Hindi, and Tamil. Manual choice persists in `localStorage`, is sent for text and voice turns, and is retained in backend session language state.
- Automatic mode uses the current Whisper result and confidence. Unsupported or low-confidence detection produces an actionable error instead of an invented language decision.
- Health now reports STT, LLM, and TTS readiness separately for every supported language.
- TTS has independent English/Hindi/Tamil model mappings. Missing Hindi/Tamil voices never fall back to the English voice or cloud speech.
- Voice prompts tell Qwen to answer concisely in the active language. Real text checks produced the requested Hindi phrase and a Tamil-script response; this is qualitative, not a multilingual quality benchmark.
- Ollama has a cancellable NDJSON token-stream client.
- `/api/voice/stream` converts complete sentence/phrase buffers into ordered local Piper WAV chunks and flushes the final buffer.
- The browser reads incremental events, queues audio in order, and prevents stale turn callbacks through a turn generation ID and `AbortController`.
- Hands-free VAD retains adaptive noise-floor estimation and adds configurable threshold/minimum-speech/maximum-duration hooks plus multi-frame interruption onset.
- Optional barge-in monitors during playback, stops current playback, aborts the HTTP stream, invalidates stale work, and starts capturing a new utterance.
- Latency output now distinguishes STT, first LLM token, total LLM, first server audio chunk, accumulated TTS, browser capture/VAD, browser playback start, and total server time where the selected path can measure them.
- `backend/scripts/benchmark_voice.py` runs repeated real requests from a user-supplied multilingual manifest, reports success/failure, cold candidates, p50/p95/min/max stage timings, WER when exact references exist, health, diagnostics, model/device facts, and hardware.

The installed Piper 1.8.0 catalog check listed `hi_IN-pratham-medium`, `hi_IN-priyamvada-medium`, and `hi_IN-rohan-medium`; it listed no `ta_*` voice. No model was downloaded. A deliberate Hindi setup is `python -m piper.download_voices hi_IN-pratham-medium --download-dir models\piper`, followed by configuring the matching `.onnx` and `.onnx.json` paths and performing a real synthesis/license review. Tamil requires evaluation of another genuinely local engine before integration and remains blocked.

### Latest real streaming observation

One real English WAV was sent through `/api/voice/stream` after the upgrade:

| Metric | Observed value |
| --- | ---: |
| STT | 9,770.62 ms |
| First LLM token | 8,851.47 ms after LLM start |
| Total LLM phase, including chunk synthesis pauses | 33,267.29 ms |
| Piper synthesis | 3,160.92 ms |
| First audio chunk available from request start | 43,023.64 ms |
| Total server request | 43,044.97 ms |

The answer contained one sentence, so no safe audio boundary existed before the final sentence completed. This run verifies protocol and real model integration, not a latency improvement. It is not comparable to the earlier request because the input audio and prompt differed. No before/after speedup is claimed.

### Required manual verification matrix

| Test | Status | Evidence / blocker |
| --- | --- | --- |
| English voice conversation | PASS | Real WAV completed STT → streamed local Qwen → English Piper WAV. |
| Hindi voice conversation | BLOCKED | Hindi STT/LLM code paths exist, but no compatible Hindi Piper voice or lawful recorded test set is installed. |
| Tamil voice conversation | BLOCKED | Tamil STT/LLM code paths exist, but no compatible Tamil Piper voice or lawful recorded test set is installed. |
| English → Hindi | BLOCKED | Real text switching works qualitatively; end-to-end voice cannot pass without Hindi TTS. |
| Hindi → Tamil | BLOCKED | Session switching is implemented; both required TTS voices are missing. |
| Tamil → English | BLOCKED | Session switching is implemented; starting Tamil speech output is unavailable. |
| Multi-turn context | PASS | Existing session tests and real same-session text requests preserve ordered context/language. |
| Hands-free listening | NOT TESTED | Automated state tests pass; real microphone/room endpointing was not physically exercised in this run. |
| Noise handling | NOT TESTED | Adaptive logic is tested at unit level; no representative room-noise recording set was supplied. |
| Barge-in | NOT TESTED | Cancellation/state logic is implemented; real speaker-to-microphone interruption latency needs interactive hardware measurement. |
| Streaming | PASS | Real NDJSON token and ordered Piper audio events were observed. Piper is chunked, not native streaming. |
| Local inference | PASS | All observed inference used local Faster-Whisper, Ollama, and Piper. |
| Performance p50/p95 | PASS | Ten real English runs produced per-sample p50/p95; Hindi/Tamil benchmarking remains blocked by recordings/voices. |
| CPU fallback | PASS | Real STT succeeded on CPU/int8; CUDA-specific fallback behavior is covered by tests. |
| Missing voice/model | PASS | Health marks Hindi/Tamil TTS false and requests fail clearly without English/cloud fallback. |

### Repeatable multilingual benchmark

Copy `backend/scripts/multilingual-manifest.example.json`, replace every placeholder with paths to lawful recordings and exact reference transcripts, then run:

```powershell
cd D:\Trikon-Voice-AI\backend
.\.venv\Scripts\Activate.ps1
python scripts\benchmark_voice.py scripts\my-multilingual-manifest.json --runs 5 --output multilingual-benchmark.json
```

For Hindi and Tamil WER, the script normalizes with Unicode-aware case folding, removes punctuation to spaces, splits on whitespace, and calculates word-level Levenshtein distance. Preserve the original reference text in the manifest so the reported value is auditable. Code-switched and qualitative samples without reliable references should omit `reference`; the script then reports no WER instead of inventing one.

### Repeated English benchmark — 21 October 2026

Ten real `/api/voice` runs completed successfully: five using a 3.843-second local short clip and five using a 15.569-second locally synthesized long clip. The local stack was CPU/int8 Faster-Whisper base, Ollama `qwen2.5:3b` using the RTX 3050, and CPU Piper Norman. The full machine-readable report is `docs/benchmark-2026-10-21.json`.

| Sample | Runs | First/cold-candidate wall | Warm wall p50 | Warm wall p95 | STT p50 | LLM p50 | TTS p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| English short, 3.843 s | 5/5 | 4,356.57 ms | 4,086.86 ms | 4,813.11 ms | 2,383.66 ms | 790.05 ms | 976.91 ms |
| English long, 15.569 s | 5/5 | 7,076.62 ms | 6,902.12 ms | 7,541.01 ms | 3,202.08 ms | 1,253.89 ms | 2,497.37 ms |

The long sample had an exact known reference and produced WER `0.1739` on every run under the documented normalization. Whisper consistently heard “longer” as “Lombard”, “Trikon” as “trekking”, and rendered spoken numbers as digits; the WER counts those normalized word substitutions. The short clip had no independently reliable reference, so no WER is reported. These are generated clean-English samples, not microphone/noise or multilingual accuracy evidence. “Cold candidate” means the first run for that sample in this process; it does not prove a fully unloaded OS/GPU cache.
