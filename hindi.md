# Hindi quality audit — Trikon Voice AI

Audit date: 24 October 2026. Workspace: `D:\Trikon-Voice-AI`.

## 1. Project and Hindi pipeline overview

The existing React/Vite frontend and FastAPI backend remain in place. No alternate LLM pipeline, factual answer lookup table, wake-word changes, or intro-screen changes were introduced.

The execution path is:

1. `frontend/src/context/VoiceContext.tsx` manages the selected `en`/`hi` language and session. Tap-to-record uses MediaRecorder; `frontend/src/hooks/useHandsFree.ts` handles speech activity, silence, cancellation, and repeated capture. Language selection is persisted to `localStorage`.
2. `frontend/src/lib/api.ts` sends the language and session as multipart fields to `/api/voice` or `/api/voice/stream`. Text uses `/api/chat`. Streaming JSON is decoded with a UTF-8 `TextDecoder`.
3. `backend/app/api/routes/voice.py` validates uploads, writes a temporary file, invokes the pipeline, and removes the file. Errors are HTTP errors or NDJSON `error` events, not invented assistant answers.
4. `backend/app/services/stt.py` loads local Faster-Whisper models. English uses the base model; explicitly selected Hindi uses the configured small multilingual model (`models/faster-whisper-small`). Automatic detection remains available. Segment log-probability and compression-ratio checks reject likely hallucinated or garbled segments before any text reaches the LLM.
5. The STT result goes through NFC Unicode normalization and conservative quality checks. No spelling dictionary or guessed word replacement is used. `language_quality.py` provides shared checks and the Hindi system instruction.
6. `backend/app/services/pipeline.py` resolves response language, serializes a session turn, routes explicit local commands, and builds the system/history/current-question messages. Hindi streaming buffers the complete answer before validation and TTS; English streaming remains incremental.
7. `backend/app/services/llm.py` calls the existing Ollama HTTP API. `session_manager.py` keeps bounded, process-local user/assistant history with per-session locks (up to 12 turns, 500 sessions).
8. Generated text is checked before voice synthesis. Invalid replies are not committed to conversation history or passed to TTS.
9. `backend/app/services/tts.py` selects the Hindi Piper voice (`hi_IN-pratham-medium.onnx`), removes presentation markup, and creates WAV audio.

## 2. Reported incorrect-answer example

Question: `bharat ki rajdhani kya hai?` (भारत की राजधानी क्या है?)

Expected meaning: India's capital is New Delhi — भारत की राजधानी नई दिल्ली है।

Reported failure: `barad ka rajtani namak nam ek vyayam hai jise bard ya bard yatra kaha jata hai.`

The original human microphone recording was not supplied, so the exact acoustic failure cannot be reproduced. The failure class was reproduced without audio: `qwen2.5:3b` returned incorrect cities (Bhopal, Kolkata) and garbled words in fresh Hindi sessions. English consistently returned "The capital of India is New Delhi." This establishes an LLM failure originating in the 3B model's insufficient Hindi knowledge.

## 3. Confirmed root causes and hypotheses

| Finding | Evidence | Status |
|---|---|---|
| **Qwen 2.5 3B inadequate Hindi reliability** | Fresh sessions produce false facts and malformed wording; multiple prompt variations failed to fix it | **Confirmed; fixed by switching to 7B** |
| **80-token voice budget truncated Hindi output** | Earlier replies ended mid-word at cap; Hindi needs more tokens per word than English | **Confirmed; fixed (192 tokens)** |
| Language probability ≠ transcription accuracy | Explicit Hindi returns probability 1 even when words are misrecognized | Confirmed; segment quality checks added |
| Prose initial_prompt contaminated recognition | Parts of a Hindi prose prompt appeared in a computer-question transcript | Observed once; initial_prompt set to None |
| Automatic Hindi did not use multilingual model | Model selection occurred before language detection | Confirmed; now routing correctly |
| Streaming speech escaped before complete answer checked | Every sentence could be spoken before final generation metadata | Confirmed; Hindi now buffers for validation |
| UI mislabeled model errors as connectivity failures | handleError prepended "Could not reach…" to every error | Confirmed; now displays actual guidance |
| Previous English history overrides Hindi facts | Failures also occurred in empty sessions | Possible factor; addressed by prompt design |
| TTS is the sole cause | Typed answers are already incorrect before TTS | Ruled out as sole cause |

## 4. Changes implemented and why

### Code changes

- **`backend/app/services/language_quality.py`** (new): Shared Hindi instruction (`HINDI_INSTRUCTION`), NFC normalization, and conservative quality checks for empty/malformed text, control tokens, and repeated-phrase loops.
- **`backend/app/services/stt.py`**: Removed prose `initial_prompt`, added segment avg_logprob/compression_ratio checks, routed confidently auto-detected Hindi through the multilingual model.
- **`backend/app/services/pipeline.py`**: Centralized prompt construction. Latest question takes priority. Hindi token budget raised to 192. Hindi streaming validates before emitting text/audio.
- **`backend/app/services/llm.py`**: Malformed streaming messages, upstream errors, and missing completion events raise service errors.
- **`backend/app/api/routes/chat.py`**: Preserves actionable model error details.
- **`frontend/src/context/VoiceContext.tsx`**: Displays actual error message without claiming all errors mean the backend is offline.
- **`backend/tests/test_hindi_quality.py`** (new): A-G deterministic contract tests plus failure guards.
- **`backend/scripts/check_hindi_quality.py`** (new): Opt-in live semantic checks against running API.

### Model configuration change

- **`backend/.env` `OLLAMA_MODEL`**: Changed from `qwen2.5:3b` to `qwen2.5:7b`.

**Reason**: `qwen2.5:3b` consistently produced incorrect Hindi facts (Bhopal, Kolkata, garbled words) across multiple prompt variations. `qwen2.5:7b` (already installed, 4.7 GB Q4_K_M) passed all six test cases (A-F) with grammatically correct Devanagari responses in a live run. No model was downloaded.

| Path | Purpose |
|---|---|
| `backend/app/services/language_quality.py` | Shared Hindi instruction and conservative text checks |
| `backend/app/services/stt.py` | Recognition quality checks, normalization, automatic Hindi routing |
| `backend/app/services/llm.py` | Response validation and malformed/incomplete stream handling |
| `backend/app/services/pipeline.py` | Shared prompts, validation before Hindi speech/history, token allowance |
| `backend/app/core/config.py`, `backend/app/main.py` | Wire voice_hi_num_predict |
| `backend/app/api/routes/chat.py` | Preserve actionable model error details |
| `frontend/src/context/VoiceContext.tsx` | Display actual recognition/model error |
| `backend/tests/test_hindi_quality.py` | Hindi A-G contracts and failure checks |
| `backend/tests/test_multilingual_streaming.py`, `backend/tests/test_llm_client.py` | Updated decoder and stream regression tests |
| `frontend/src/lib/api.test.ts` | Hindi selection and split UTF-8 stream test |
| `backend/scripts/check_hindi_quality.py` | Opt-in real-service semantic checks |
| `backend/.env` | Updated OLLAMA_MODEL from qwen2.5:3b to qwen2.5:7b |
| `docs/hindi-audit-results.json` | Running actual observations, not fabricated outputs |
| `README.md`, `hindi.md` | Running guidance and audit |

## 5. Hindi detection and transcription behavior

Explicit `language=hi` remains authoritative; `language=en` remains English. With neither a request language nor `STT_LANGUAGE`, Faster-Whisper detects automatically. Confident Hindi detection (>=55% probability) re-decodes with the small multilingual model; English and uncertain detections are not forced to Hindi.

Segment `avg_logprob < -1.0` or `compression_ratio > 2.4` produces a "please repeat or type" error. These detect poor decoder output, not factual accuracy. Confidently wrong words can still pass. No automatic word substitution is performed.

**Confirmed STT limitation**: Piper TTS to Faster-Whisper round-trips showed misrecognitions: raajdhani became raajdaani, nai dilli became nahin dili, and Chennai was completely misrecognized. These errors occur with Piper-synthesized speech and may not reflect real microphone accuracy. Removing `initial_prompt` did not fix these examples.

**Not verified**: Real human microphone recordings, native-speaker pronunciation review, or physical speaker playback.

## 6. LLM prompts, model evaluation, and answer checks

The `HINDI_INSTRUCTION` requests natural Devanagari, a direct concise answer, relevant history only, no invented facts, and clarification when needed. Names, numbers, technical terms, and explicit translation requests remain allowed. There is no rule rejecting content containing English words.

### Model evaluation results (24 October 2026)

| Model | Hindi A-F Result | Notes |
|---|---|---|
| `qwen2.5:3b` (Q4_K_M, 1.9 GB) | **All FAIL** — Bhopal, Kolkata, garbled | Multiple prompt variants; could not be fixed |
| `gemma2:2b` (Q4_0, 1.6 GB) | Partially correct but unstable | Answered English queries in Hindi; not adopted |
| `qwen2.5:7b` (Q4_K_M, 4.7 GB) | **All PASS** — correct Devanagari | Adopted; verified in live run |
| `llama3.2:3b` (Q4_K_M, 2.0 GB) | Correct facts, romanized output | Responds romanized when given romanized input |

**Current configuration**: `qwen2.5:7b`. Backend `.env` updated. No model was downloaded.

**Answer checks detect structural failures, not truth**: Repetition check, truncation detection, and control-token detection cannot guarantee Hindi grammar, spelling, factuality, or relevance.

## 7. Hindi TTS compatibility and verification

Configured files: `backend/models/piper/hi_IN-pratham-medium.onnx` and `hi_IN-pratham-medium.onnx.json`. `TextToSpeechService` maps `hi` to these files; it does not substitute the English voice.

Three independent synthesis checks produced non-empty mono 22,050 Hz WAVs:
1. "bharat ki rajdhani nai dilli hai." (Hindi) -> 46,336 frames (~2.1 s), 241 ms synthesis
2. "Chennai tamilnadu ki rajdhani hai." (Hindi) -> 51,456 frames (~2.3 s), 110 ms synthesis  
3. "Python 3.11 mein do failen hain." (mixed) -> 59,648 frames (~2.7 s), 124 ms synthesis

`to_spoken_text` preserved plain Hindi inputs and punctuation exactly. Unit tests verify that the answer sent to TTS matches the displayed text and uses the Hindi voice.

**Verified**: Hindi model compatibility, text integrity, and successful waveform generation.
**Not verified**: Pronunciation quality, physical speaker playback, native listener review.

## 8. Regression tests

### Backend (`backend/tests/test_hindi_quality.py`)

- **Test A**: "bharat ki rajdhani kya hai" (Hindi) -> nai dilli preserved; Hindi TTS and 192-token limit verified.
- **Test B**: "bharat ki rajdhani ka naam kya hai" -> same semantic check.
- **Test C**: "Chennai kis rajya ki rajdhani hai" -> tamilnadu preserved.
- **Test D**: Explicit Hindi instruction -> Hindi voice and Devanagari system prompt verified.
- **Test E**: "What is the capital of India?" -> English voice and 80-token limit.
- **Test F**: English turn then Hindi question -> context preserved, Hindi system prompt active.
- **Test G**: Poor transcription (TranscriptionError) -> LLM never called, TTS never called, history not committed.
- Repeated-phrase and truncation rejection before TTS/history.
- Valid Hindi streaming: text and audio use same buffered answer; TTS called once.
- Model timeout: TTS not called, history not committed.
- Low-quality STT segments: TranscriptionError raised.
- Auto-detection routing: confident Hindi re-decoded with multilingual model; low-confidence falls through.

### Frontend (`frontend/src/lib/api.test.ts`)

- Split-UTF-8 stream reconstruction preserves exact Hindi Devanagari text.
- `language=hi` form field forwarded correctly to `/api/voice/stream`.

Additional unchanged coverage: English pipeline, session management, CUDA fallback, cancellation, hands-free, and intro-screen tests.

## 9. Windows PowerShell verification commands

Backend:

```powershell
cd D:\Trikon-Voice-AI\backend
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider --basetemp="../.run/pytest-quality-bbe66913-096d-4129-bbcd-75af69d6de4e"
```

Frontend:

```powershell
cd D:\Trikon-Voice-AI\frontend
npm test -- --pool=threads --maxWorkers=1
npm run lint
npm run build
```

Opt-in live checks (requires Ollama and backend running):

```powershell
cd D:\Trikon-Voice-AI\backend
.\.venv\Scripts\python.exe scripts/check_hindi_quality.py --output ../.run/hindi-quality-live.json
```

## 10. Actual test results

### Automated unit/integration tests (24 October 2026)

| Suite | Passed | Failed | Skipped |
|---|---|---|---|
| Backend (77 tests) | **77** | 0 | 0 |
| Frontend (20 tests) | **20** | 0 | 0 |
| ESLint | PASS | - | - |
| TypeScript/Vite build | PASS | - | - |

One existing AnyIO deprecation warning from starlette; not caused by this code. No tests failed or were skipped.

### Live semantic checks — qwen2.5:3b (before model change)

| Case | Result | Actual Response |
|---|---|---|
| A - bharat ki rajdhani kya hai | **FAIL** | bharat ki rajdhani bhopal hai |
| B - bharat ki rajdhani ka naam kya hai | **FAIL** | bharat ki rajdhani nainayal hai |
| C - Chennai kis rajya ki rajdhani hai | **FAIL** | tAMIL-naadu (garbled mixed-case) |
| D - explicit Hindi instruction | **FAIL** | bharat ki rajdhani bhopal hai |
| E - What is the capital of India? | PASS | The capital of India is New Delhi. |
| F - context isolation | **FAIL** | bharat ki rajdhani bhopal hai |

### Live semantic checks — qwen2.5:7b (verified 24 October 2026)

| Case | Result | Actual Response |
|---|---|---|
| A - bharat ki rajdhani kya hai | **PASS** | nai dilli hai bharat ki rajdhani. |
| B - bharat ki rajdhani ka naam kya hai | **PASS** | nai dilli sarkar ki rajdhani hai. |
| C - Chennai kis rajya ki rajdhani hai | **PASS** | Chennai tamilnadu ki rajdhani hai. |
| D - explicit Hindi instruction | **PASS** | bharat ki rajdhani nai dilli hai. |
| E - What is the capital of India? | **PASS** | The capital of India is New Delhi. |
| F - context isolation (English then Hindi) | **PASS** | bharat ki rajdhani nai dilli hai. |

All responses are saved in `docs/hindi-audit-results.json` under `hindi-7b-verified-2026-10-24`.

**Not run**: real human microphone recordings, native-listener pronunciation review, physical speaker playback, or validated wake-word inference.

## 11. Remaining limitations and next steps

1. **Factual accuracy depends on model knowledge**: Formatting and structural checks cannot establish truth. Other domains were not tested.
2. **Hindi speech recognition accuracy**: The small multilingual Whisper model misrecognizes some Hindi sounds from Piper TTS output. Real microphone behavior was not tested because the original failure audio was unavailable. A native-speaker microphone evaluation is the next step.
3. **First response latency with 7B**: Case A required 16 seconds (cold start). Subsequent requests averaged ~1.7 seconds. GPU inference would reduce this.
4. **Hindi streaming latency**: Hindi complete-answer buffering increases time to first audio. This is a deliberate quality-over-speed tradeoff.
5. **Conversation history in memory**: History resets on backend restart. No destructive history or Git operation was performed.
6. **Hindi command vocabulary**: Existing local commands retain English vocabulary. Hindi equivalents were not implemented.
7. **Existing Git changes preserved**: No commit, reset, or model deletion was performed.
8. **Qwen 2.5 7B stability**: Earlier audit noted instability (asking for clarification or Chinese in some tests). The current run (6 fresh sessions, all passing) did not reproduce that failure. Continued monitoring recommended.
9. **Model configuration not in repository**: `backend/.env` is in `.gitignore`. Changes to `OLLAMA_MODEL` must be reapplied after cloning. The `backend/.env.example` documents the correct value.
