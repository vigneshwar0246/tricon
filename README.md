# AI Voice Assistant

A React and TypeScript frontend for a local-first voice assistant powered by open-weight models.

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

Vite serves the app at `http://localhost:5173` and proxies `/api` requests to `http://localhost:8000` during development. Set `VITE_API_BASE_URL` to use another API origin.

## Verify the frontend

```powershell
npm run lint
npm test
npm run build
```

## Backend contract

- `GET /api/health` — health information for `stt`, `llm`, `tts`, and `api` under a `services` or `components` object.
- `POST /api/chat` — JSON with `message` and `session_id`.
- `POST /api/voice` — multipart form data with `audio` and `session_id`.

Chat and voice responses may return assistant text as `response`, `message`, `text`, or `assistant_text`. Voice responses may include `transcript`. Audio can be returned as `audio_url`, `audio.url`, or `tts_url`.

Performance data is never fabricated. The interface reads optional `stt_ms`, `llm_ms`, `tts_ms`, and `total_ms` values from the root, `metrics`, or `timings` response object. When the backend does not provide a metric, the UI displays `Not measured`.
