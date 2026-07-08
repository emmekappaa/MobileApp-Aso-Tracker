#!/usr/bin/env python3
"""
AI-powered ASO analysis: turns raw rank-scan JSON into an actionable report
using a local LLM via Ollama (no API key, no cost).
"""
import json
import sys
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b-instruct"

SYSTEM_PROMPT = """You are an ASO (App Store Optimization) analyst. You receive ranking data \
for an app across keywords, stores (iOS/Android) and countries, comparing the current scan to \
the previous one (when available). Write a concise, concrete report IN ENGLISH covering:

- which keywords are underperforming and might benefit from a metadata change (title, subtitle, description)
- which keywords are strong and worth reinforcing (e.g. in the title)
- notable patterns: sudden drops in a specific country or store, inconsistencies between iOS and Android

Base your analysis only on the provided data, no generic filler. Use a short bullet list.
Note: "-" means the keyword was not found in the results, "ERROR" means the scan failed for that \
row; a lower position number = better ranking. A positive "delta" means improvement vs. the previous scan.
"""


def load_results():
    files = sorted(Path("results").glob("scan_*.json"))
    if not files:
        sys.exit("Nessun risultato in results/. Esegui prima tracker.py.")
    latest = json.loads(files[-1].read_text(encoding="utf-8"))
    previous = json.loads(files[-2].read_text(encoding="utf-8")) if len(files) > 1 else None
    return latest, previous, files[-1].name, (files[-2].name if previous else None)


def build_summary(latest, previous):
    def row_key(row):
        return (row["store"], row["region"], row["keyword"])

    prev_map = {row_key(r): r["position"] for r in previous} if previous else {}

    summary = []
    for row in latest:
        pos = row["position"]
        prev_pos = prev_map.get(row_key(row))
        delta = prev_pos - pos if isinstance(pos, int) and isinstance(prev_pos, int) else None
        summary.append({
            "store": row["store"],
            "region": row["region"],
            "keyword": row["keyword"],
            "position": pos,
            "previous_position": prev_pos,
            "delta": delta,
        })
    return summary


def call_ollama(summary):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(summary, ensure_ascii=False)},
        ],
        "stream": False,
        "options": {"temperature": 0},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
        resp.raise_for_status()
    except requests.ConnectionError:
        sys.exit(f"Impossibile contattare Ollama su {OLLAMA_URL}. È in esecuzione? (ollama serve)")
    return resp.json()["message"]["content"]


def run_analysis():
    latest, previous, latest_name, previous_name = load_results()
    summary = build_summary(latest, previous)

    comparison = f"vs {previous_name}" if previous_name else "(nessuno scan precedente per il confronto)"
    print(f"Analisi di {latest_name} {comparison}")
    print(f"Modello locale: {MODEL} (Ollama)...\n")

    report = call_ollama(summary)

    print("=" * 60)
    print("AI ANALYSIS")
    print("=" * 60)
    print(report)

    out_file = Path("results") / f"analysis_{Path(latest_name).stem.replace('scan_', '')}.txt"
    out_file.write_text(report, encoding="utf-8")
    print(f"\nSalvato in {out_file}")


if __name__ == "__main__":
    run_analysis()
