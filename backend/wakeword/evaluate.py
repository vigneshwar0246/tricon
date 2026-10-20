"""Evaluate a local openWakeWord ONNX model against labeled 16 kHz mono WAV clips.

Positive clips should contain one naturally spoken "Carrot". Negative clips
should contain ordinary speech/noise without that wake word. Keep evaluation
speakers and recordings separate from training data.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import statistics
import sys
import time
import wave
from pathlib import Path
from typing import Any

FRAME_SAMPLES = 1280  # openWakeWord's recommended 80 ms frame at 16 kHz


def process_memory_bytes() -> tuple[int | None, int | None]:
    """Return current and peak process working set without adding a dependency."""
    if sys.platform == "win32":
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        ok = psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        if ok:
            return int(counters.WorkingSetSize), int(counters.PeakWorkingSetSize)
    else:
        try:
            import resource

            peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            if sys.platform != "darwin":
                peak *= 1024
            return None, peak
        except (ImportError, OSError):
            pass
    return None, None


def read_wav(path: Path) -> tuple[Any, int]:
    import numpy as np

    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1 or source.getframerate() != 16000 or source.getsampwidth() != 2:
            raise ValueError(f"{path} must be mono, 16 kHz, signed 16-bit PCM WAV")
        audio = np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16).copy()
    return audio, len(audio)


def score_clip(model: Any, path: Path, threshold: float) -> tuple[bool, int | None, int]:
    audio, _ = read_wav(path)
    model.reset()
    previous_above = False
    first_detection_ms: int | None = None
    activations = 0
    for offset in range(0, len(audio), FRAME_SAMPLES):
        frame = audio[offset : offset + FRAME_SAMPLES]
        if len(frame) < FRAME_SAMPLES:
            break
        scores = model.predict(frame)
        score = max(float(value) for value in scores.values())
        above = score >= threshold
        if above and not previous_above:
            activations += 1
            if first_detection_ms is None:
                first_detection_ms = round(offset * 1000 / 16000)
        previous_above = above
    model.reset()
    return first_detection_ms is not None, first_detection_ms, activations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path, help="Trained local .onnx model")
    parser.add_argument("--positive", required=True, type=Path, help="Directory of positive Carrot WAV clips")
    parser.add_argument("--negative", required=True, type=Path, help="Directory of ordinary speech/noise WAV clips")
    parser.add_argument("--threshold", type=float, required=True, help="Threshold selected using separate validation data")
    args = parser.parse_args()
    if not args.model.is_file() or not 0.0 < args.threshold < 1.0:
        parser.error("model must exist and threshold must be between 0 and 1")

    positives = sorted(args.positive.glob("*.wav"))
    negatives = sorted(args.negative.glob("*.wav"))
    if not positives or not negatives:
        parser.error("positive and negative directories must each contain WAV clips")

    try:
        from openwakeword.model import Model
    except ImportError as exc:
        print("Install the optional wake-word inference dependencies first.", file=sys.stderr)
        raise SystemExit(2) from exc

    setup_started = time.perf_counter()
    model = Model(wakeword_models=[str(args.model)], inference_framework="onnx")
    model_load_seconds = time.perf_counter() - setup_started
    working_set_after_load, peak_working_set_after_load = process_memory_bytes()
    latencies: list[int] = []
    false_activations = 0
    negative_seconds = 0
    false_clip_count = 0
    inference_started = time.perf_counter()
    cpu_started = time.process_time()
    for path in positives:
        detected, latency, _ = score_clip(model, path, args.threshold)
        if detected and latency is not None:
            latencies.append(latency)
    for path in negatives:
        detected, _, activations = score_clip(model, path, args.threshold)
        if detected:
            false_clip_count += 1
        false_activations += activations
        _, samples = read_wav(path)
        negative_seconds += samples / 16000
    inference_seconds = time.perf_counter() - inference_started
    cpu_seconds = time.process_time() - cpu_started
    working_set_after_eval, peak_working_set_after_eval = process_memory_bytes()

    report = {
        "threshold": args.threshold,
        "positive_clips": len(positives),
        "negative_clips": len(negatives),
        "recall": len(latencies) / len(positives),
        "false_positive_clip_rate": false_clip_count / len(negatives),
        "false_activations": false_activations,
        "negative_audio_hours": negative_seconds / 3600,
        "false_activations_per_hour": false_activations / (negative_seconds / 3600) if negative_seconds else None,
        "detection_latency_ms_median": statistics.median(latencies) if latencies else None,
        "model_load_seconds": round(model_load_seconds, 3),
        "inference_wall_seconds": round(inference_seconds, 3),
        "inference_process_cpu_seconds": round(cpu_seconds, 3),
        "inference_cpu_percent_one_core_average": round(cpu_seconds / inference_seconds * 100, 1) if inference_seconds else None,
        "working_set_bytes_after_model_load": working_set_after_load,
        "peak_working_set_bytes_after_model_load": peak_working_set_after_load,
        "working_set_bytes_after_evaluation": working_set_after_eval,
        "peak_working_set_bytes_after_evaluation": peak_working_set_after_eval,
        "cpu_count_visible": os.cpu_count(),
        "model_size_bytes": args.model.stat().st_size,
        "latency_note": "Latency is measured from the beginning of each positive clip, so include known leading silence for a useful estimate.",
        "limitations": "Clip-level evaluation only; memory is process working set, CPU percent is averaged relative to one core. Report speaker count, environment/noise, and threshold-selection split alongside this output.",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
