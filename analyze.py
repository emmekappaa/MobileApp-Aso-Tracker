#!/usr/bin/env python3
"""
AI-powered ASO analysis: turns raw rank-scan JSON into an actionable report
using a local LLM via Ollama (no API key, no cost).
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = f"{OLLAMA_HOST}/api/chat"
DEFAULT_MODEL = "qwen2.5:7b-instruct"

STRONG_RANK = 3   # position <= this is "strong"
WEAK_RANK = 20    # position > this counts as underperforming
BIG_MOVE = 3      # |delta| >= this counts as a notable drop/improvement
STORE_GAP = 10    # |Android pos - iOS pos| >= this counts as a store inconsistency

SYSTEM_PROMPT = """You are an ASO (App Store Optimization) analyst. You receive a set of \
PRE-COMPUTED facts about an app's keyword rankings (underperforming ranked keywords, not-ranked keywords, \
technical scrape errors, strong keywords, big moves vs. the previous scan, and iOS/Android inconsistencies). These facts were already \
verified by code — do not recompute, contradict, or invent any position, delta or ranking \
beyond what is given.

Write a concise, concrete report IN ENGLISH that:
- explains which underperforming ranked keywords might benefit from a metadata change (title, subtitle, description)
- highlights which strong keywords are worth reinforcing (e.g. in the title)
- calls out the notable patterns (drops, improvements, iOS/Android inconsistencies) and what they might mean
- treats not-ranked and technical scrape errors as separate diagnostic categories
- never recommends metadata changes based only on technical scrape errors

Use a short bullet list. No generic filler, no numbers or claims that aren't in the input data. \
If a fact list is empty, skip that section instead of making something up.
"""


def load_results():
    files = sorted(Path("results").glob("scan_*.json"))
    if not files:
        sys.exit("No results found in results/. Run tracker.py first.")
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


def compute_insights(summary):
    underperforming = [r for r in summary if isinstance(r["position"], int) and r["position"] > WEAK_RANK]
    not_ranked = [r for r in summary if r["position"] == "-"]
    scrape_errors = [r for r in summary if r["position"] == "ERROR"]
    strong = [r for r in summary if isinstance(r["position"], int) and r["position"] <= STRONG_RANK]
    drops = [r for r in summary if r["delta"] is not None and r["delta"] <= -BIG_MOVE]
    improvements = [r for r in summary if r["delta"] is not None and r["delta"] >= BIG_MOVE]

    by_keyword_region = defaultdict(dict)
    for r in summary:
        by_keyword_region[(r["keyword"], r["region"])][r["store"]] = r["position"]

    store_inconsistencies = []
    for (keyword, region), positions in by_keyword_region.items():
        android_pos = positions.get("Android")
        ios_pos = positions.get("iOS")
        android_found = isinstance(android_pos, int)
        ios_found = isinstance(ios_pos, int)
        is_gap = android_found != ios_found or (
            android_found and ios_found and abs(android_pos - ios_pos) >= STORE_GAP
        )
        if is_gap:
            store_inconsistencies.append({
                "keyword": keyword,
                "region": region,
                "android_position": android_pos,
                "ios_position": ios_pos,
            })

    return {
        "underperforming_ranked_keywords": underperforming,
        "not_ranked_keywords": not_ranked,
        "technical_scrape_errors": scrape_errors,
        "strong_keywords": strong,
        "notable_drops": drops,
        "notable_improvements": improvements,
        "store_inconsistencies": store_inconsistencies,
    }


def call_ollama(insights, model):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(insights, ensure_ascii=False)},
        ],
        "stream": False,
        "options": {"temperature": 0},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except requests.ConnectionError:
        sys.exit(f"Could not reach Ollama at {OLLAMA_URL}. Is it running? (ollama serve)")
    except (requests.HTTPError, json.JSONDecodeError, KeyError):
        sys.exit(f"Unexpected response from Ollama for model '{model}'. Is it pulled? (ollama pull {model})")


def run_analysis(model):
    latest, previous, latest_name, previous_name = load_results()
    summary = build_summary(latest, previous)
    insights = compute_insights(summary)

    comparison = f"vs {previous_name}" if previous_name else "(no previous scan to compare against)"
    print(f"Analyzing {latest_name} {comparison}")
    print(f"Local model: {model} (Ollama)...\n")

    report = call_ollama(insights, model)

    print("=" * 60)
    print("AI ANALYSIS")
    print("=" * 60)
    print(report)

    out_file = Path("results") / f"analysis_{Path(latest_name).stem.replace('scan_', '')}.txt"
    out_file.write_text(report, encoding="utf-8")
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-powered ASO analysis of the latest scan.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model to use (default: {DEFAULT_MODEL})")
    args = parser.parse_args()
    run_analysis(args.model)
