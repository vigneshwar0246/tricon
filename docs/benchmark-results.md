# Benchmark results

Text inference was exercised through the FastAPI chat route on 2026-10-19. Later the same day, the complete local speech pipeline was exercised with a Piper-generated WAV uploaded through `/api/voice`. These are single-run observations, not a repeatable performance benchmark.

| Stage | Result | Configuration / method |
| --- | --- | --- |
| STT, full voice request | 5,719.08 ms | Faster-Whisper base on CPU/int8; first successful API voice request |
| LLM, first request | 293,366.65 ms Ollama-reported; 303,192.10 ms API total | First short prompt; includes cold model load/startup cost |
| LLM, warm follow-up | 150.30 ms Ollama-reported; 178.82 ms API total | Asked the model to recall “orange otter” from the prior turn; it returned the phrase |
| TTS, full voice request | 4,276.38 ms | Piper `en_US-norman-medium` on CPU; response speech synthesized and served as WAV |
| Full voice pipeline | 22,462.98 ms API total; 910.72 ms Ollama-reported LLM time | Uploaded a one-sentence Piper WAV, received a real transcript, Qwen answer, and playable WAV URL |
| Ollama GPU allocation | `qwen2.5:3b` reported `size_vram=2,163,568,803` bytes; `nvidia-smi` sampled 2,163 MiB used and 0% GPU utilization after inference | NVIDIA GeForce RTX 3050 Laptop GPU, 6,144 MiB; post-request snapshot, not a peak-utilization benchmark |

## How to record a real result

Hardware/runtime for this check: Windows 11; user-reported 15.7 GB RAM; NVIDIA GeForce RTX 3050 Laptop GPU with 6 GB VRAM; Ollama 0.40.6; `qwen2.5:3b` reported by Ollama as Qwen 2 3.1B Q4_K_M. The cold first prompt was “Reply with exactly: local inference verified”; a later warm two-turn check asked the model to repeat “orange otter” and it recalled the phrase. The speech test used Python 3.13.9 in an isolated virtual environment, Faster-Whisper 1.2.1 with PyAV 16.0.1, and Piper 1.8.0. The synthesized input said “Hello, this is a test of the local voice assistant.” Faster-Whisper transcribed it, Ollama generated a response, and Piper synthesized a 392,748-byte WAV retrievable with HTTP 200. Timings came from API response metrics; stage timings do not sum to total because total also includes request/session/orchestration overhead. These samples demonstrate the path but are not statistically useful. Ollama previously reported 2,163,568,803 bytes of model VRAM allocation and `nvidia-smi` sampled 2,163 MiB used after inference; GPU utilization during token generation was not sampled. STT defaults to CPU/int8 and Piper CPU.

For a proper speech benchmark, record the returned `metrics` across multiple runs through the real UI, including warm-up behavior and exact model/config details. A browser microphone recording and speaker playback still require interactive device permission and were not part of this automated check. Do not treat mocked test timings or frontend fallback request time as model-stage benchmarks.
