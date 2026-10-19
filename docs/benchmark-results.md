# Benchmark results

Text inference was exercised through the FastAPI chat route on 2026-10-19. The complete speech pipeline was not measurable because Faster-Whisper and Piper voice files were absent at the configured paths.

| Stage | Result | Configuration / method |
| --- | --- | --- |
| STT | Not measured | Faster-Whisper model files absent at configured path |
| LLM, first request | 293,366.65 ms Ollama-reported; 303,192.10 ms API total | First short prompt; includes cold model load/startup cost |
| LLM, warm follow-up | 150.30 ms Ollama-reported; 178.82 ms API total | Asked the model to recall “orange otter” from the prior turn; it returned the phrase |
| TTS | Not measured | Piper voice model not verified locally |
| Full voice pipeline | Not measured | Requires installed STT and TTS models in addition to working Ollama |
| Ollama GPU allocation | `qwen2.5:3b` reported `size_vram=2,163,568,803` bytes; `nvidia-smi` sampled 2,163 MiB used and 0% GPU utilization after inference | NVIDIA GeForce RTX 3050 Laptop GPU, 6,144 MiB; post-request snapshot, not a peak-utilization benchmark |

## How to record a real result

Hardware/runtime for this check: Windows 11; user-reported 15.7 GB RAM; NVIDIA GeForce RTX 3050 Laptop GPU with 6 GB VRAM; Ollama 0.40.6; `qwen2.5:3b` reported by Ollama as Qwen 2 3.1B Q4_K_M. The cold first prompt was “Reply with exactly: local inference verified”; a later warm two-turn check asked the model to repeat “orange otter” and it recalled the phrase. Timings came from the backend response's Ollama `total_duration` and backend `total_ms` fields. These samples demonstrate the path but are not a statistically useful benchmark. Ollama reported 2,163,568,803 bytes of model VRAM allocation and `nvidia-smi` sampled 2,163 MiB used after inference; GPU utilization during token generation was not sampled. STT defaults to CPU/int8 and Piper CPU.

For a speech benchmark, install and verify both local speech models, ensure `/api/health` reports each required service ready, send a short known audio clip through the real UI, and record the returned `metrics` across multiple runs. Include warm-up behavior and exact model/config details. Do not treat mocked test timings or frontend fallback request time as model-stage benchmarks.
