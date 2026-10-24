"""Opt-in live checks against the running API; never downloads or installs models.

Run from backend/: .venv/Scripts/python.exe scripts/check_hindi_quality.py
These limited semantic markers are test oracles, never runtime answer substitutions.
"""

import argparse
import json
from pathlib import Path

import httpx


CASES = [
    ("A", "भारत की राजधानी क्या है?", "hi", ("नई दिल्ली", "नयी दिल्ली")),
    ("B", "भारत की राजधानी का नाम क्या है?", "hi", ("नई दिल्ली", "नयी दिल्ली")),
    ("C", "चेन्नई किस राज्य की राजधानी है?", "hi", ("तमिलनाडु", "तमिल नाडु", "तमिल नादु", "tamil nadu", "tamilnadu")),
    ("D", "मुझे हिंदी में जवाब दीजिए। भारत की राजधानी क्या है?", "hi", ("नई दिल्ली", "नयी दिल्ली")),
    ("E", "What is the capital of India?", "en", ("new delhi",)),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("../.run/hindi-quality-live.json"))
    args = parser.parse_args()
    results = []
    with httpx.Client(base_url=args.base_url, timeout=180) as client:
        for case, question, language, expected in CASES:
            response = client.post("/api/chat", json={"message": question, "language": language})
            data = response.json()
            answer = data.get("response", "")
            passed = response.is_success and any(word in answer.casefold() for word in expected)
            results.append({"case": case, "question": question, "result": "PASS" if passed else "FAIL",
                            "status": response.status_code, "response": data})
        first = client.post("/api/chat", json={"message": "Explain exercise briefly.", "language": "en"})
        first.raise_for_status()
        response = client.post("/api/chat", json={"message": CASES[0][1], "language": "hi", "session_id": first.json()["session_id"]})
        data = response.json()
        passed = response.is_success and any(word in data.get("response", "") for word in CASES[0][3])
        results.append({"case": "F", "result": "PASS" if passed else "FAIL", "status": response.status_code, "response": data})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in results:
        print(f"{row['case']}: {row['result']} (HTTP {row['status']})")
    print(f"Saved actual responses to {args.output}. Semantic markers require human review for contradictions.")
    return 1 if any(row["result"] == "FAIL" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
