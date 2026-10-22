"""Render the real browser demo answers with the project's configured Piper voice."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.tts import tts_service


root = Path(__file__).resolve().parents[2]
artifacts = root / "artifacts" / "demo"
events = json.loads((artifacts / "browser-demo-results.json").read_text(encoding="utf-8"))
manifest = []
for index, event in enumerate(item for item in events if item.get("kind") == "question"):
    answer = event["detail"].removeprefix("AI Voice Assistant ").strip()
    source, _ = tts_service.synthesize_to_file(answer, "hi" if any("\u0900" <= char <= "\u097f" for char in event["step"]) else "en")
    destination = artifacts / f"assistant-{index:02d}.wav"
    shutil.copyfile(source, destination)
    manifest.append({"file": destination.name, "offset_ms": event["offset_ms"], "text": answer})
(artifacts / "assistant-audio-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
