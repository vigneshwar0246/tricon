"""Repeat real /api/voice requests and report honest per-language latency/WER JSON.

Manifest format: [{"path":"samples/en-short.wav","language":"en","reference":"hello"}]
The backend and all configured local models must already be running. No mocks or downloads.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import subprocess
import time
from pathlib import Path

import httpx


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, min(len(ordered) - 1, int((len(ordered) * fraction + 0.999999) - 1)))], 2)


def summary(values: list[float]) -> dict[str, float | None]:
    return {
        "p50": round(statistics.median(values), 2) if values else None,
        "p95": percentile(values, 0.95),
        "min": round(min(values), 2) if values else None,
        "max": round(max(values), 2) if values else None,
    }


def normalize(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", text.casefold(), flags=re.UNICODE).split()


def word_error_rate(reference: str, hypothesis: str) -> float | None:
    expected, actual = normalize(reference), normalize(hypothesis)
    if not expected:
        return None
    previous = list(range(len(actual) + 1))
    for row, expected_word in enumerate(expected, 1):
        current = [row]
        for column, actual_word in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (expected_word != actual_word)))
        previous = current
    return round(previous[-1] / len(expected), 4)


def hardware() -> dict[str, str]:
    result = {"platform": platform.platform(), "processor": platform.processor()}
    try:
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10, check=False,
        ).stdout.strip()
        if gpu:
            result["gpu"] = gpu
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    entries = json.loads(args.manifest.read_text(encoding="utf-8"))
    observations: list[dict[str, object]] = []
    with httpx.Client(timeout=300) as client:
        health = client.get(f"{args.base_url}/api/health").json()
        diagnostics = client.get(f"{args.base_url}/api/diagnostics").json()
        for entry in entries:
            path = (args.manifest.parent / entry["path"]).resolve()
            for run in range(args.runs):
                started = time.perf_counter()
                try:
                    with path.open("rb") as audio:
                        response = client.post(
                            f"{args.base_url}/api/voice",
                            files={"audio": (path.name, audio, "audio/wav")},
                            data={"language": entry.get("language", ""),
                                  "session_id": f"benchmark-{entry.get('language', 'auto')}-{run}"},
                        )
                    response.raise_for_status()
                    payload = response.json()
                    observations.append({
                        "success": True, "cold_candidate": run == 0, "language": entry.get("language", "auto"),
                        "sample": entry["path"], "audio_duration_seconds": entry.get("audio_duration_seconds"),
                        "wall_ms": round((time.perf_counter() - started) * 1000, 2),
                        "metrics": payload.get("metrics", {}), "transcript": payload.get("transcript"),
                        "wer": word_error_rate(entry["reference"], payload.get("transcript", ""))
                        if entry.get("reference") else None,
                    })
                except Exception as exc:
                    observations.append({"success": False, "cold_candidate": run == 0,
                                         "language": entry.get("language", "auto"), "sample": entry["path"],
                                         "audio_duration_seconds": entry.get("audio_duration_seconds"),
                                         "error": str(exc)})
    grouped: dict[str, object] = {}
    for language in sorted({str(item["language"]) for item in observations}):
        language_rows = [item for item in observations if item["language"] == language]
        rows = [item for item in language_rows if item["success"]]
        samples: dict[str, object] = {}
        for sample in sorted({str(item["sample"]) for item in language_rows}):
            sample_rows = [item for item in language_rows if item["sample"] == sample]
            successful = [item for item in sample_rows if item["success"]]
            warm = [item for item in successful if not item["cold_candidate"]]
            samples[sample] = {
                "audio_duration_seconds": next((item.get("audio_duration_seconds") for item in sample_rows), None),
                "successful_runs": len(successful), "failed_runs": len(sample_rows) - len(successful),
                "cold_candidate": next((item for item in successful if item["cold_candidate"]), None),
                "warm_wall_ms": summary([float(item["wall_ms"]) for item in warm]),
                "stt_ms": summary([float(item["metrics"]["stt_ms"]) for item in successful if item["metrics"].get("stt_ms") is not None]),
                "llm_ms": summary([float(item["metrics"]["llm_ms"]) for item in successful if item["metrics"].get("llm_ms") is not None]),
                "tts_ms": summary([float(item["metrics"]["tts_ms"]) for item in successful if item["metrics"].get("tts_ms") is not None]),
                "wer": summary([float(item["wer"]) for item in successful if item.get("wer") is not None]),
            }
        grouped[language] = {
            "successful_runs": len(rows),
            "failed_runs": len(language_rows) - len(rows),
            "samples": samples,
            "warm_wall_ms": summary([float(item["wall_ms"]) for item in rows if not item["cold_candidate"]]),
            "stt_ms": summary([float(item["metrics"]["stt_ms"]) for item in rows if item["metrics"].get("stt_ms") is not None]),
            "llm_ms": summary([float(item["metrics"]["llm_ms"]) for item in rows if item["metrics"].get("llm_ms") is not None]),
            "tts_ms": summary([float(item["metrics"]["tts_ms"]) for item in rows if item["metrics"].get("tts_ms") is not None]),
            "wer": summary([float(item["wer"]) for item in rows if item.get("wer") is not None]),
        }
    report = {"generated_at_epoch": time.time(), "hardware": hardware(), "health": health,
              "diagnostics": diagnostics, "runs_per_sample": args.runs, "languages": grouped,
              "observations": observations}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
