#!/usr/bin/env python3
"""
07_think_tag_scan.py · contamination side-gate

Kill-switch for <think> tag leakage from teacher LLMs. Per firm doctrine
(data_quality_protocol.md): >1% contamination kills the batch — entire cook is
re-run after fixing the teacher prompt.

Aviation precedent (Mar 14 2026): teacher model leaked <think>...</think> into
12,728 cooked pairs · entire batch quarantined to sb-ava-quarantine.

This script SCANS but does not auto-fix. If contamination >1%, rebuild from
sources A-D with stricter teacher prompts that suppress reasoning traces.

Usage:
    python 07_think_tag_scan.py --input bookmaker_corpus_v2.jsonl --report scan_report.json

Exit codes:
    0   contamination ≤1% · proceed
    1   contamination >1% · KILL the batch · rebuild
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

THINK_PATTERNS = [
    re.compile(r"<think>", re.IGNORECASE),
    re.compile(r"</think>", re.IGNORECASE),
    re.compile(r"<thinking>", re.IGNORECASE),
    re.compile(r"</thinking>", re.IGNORECASE),
    re.compile(r"<reasoning>", re.IGNORECASE),
    re.compile(r"</reasoning>", re.IGNORECASE),
    re.compile(r"\[REASONING\]", re.IGNORECASE),
    re.compile(r"\[/REASONING\]", re.IGNORECASE),
    re.compile(r"\bThinking:\s*\n", re.IGNORECASE),  # CoT prefix leak
]

KILL_THRESHOLD = 0.01  # 1% contamination kills the batch


def scan_text(text: str) -> bool:
    return any(p.search(text) for p in THINK_PATTERNS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    inp, rep = Path(args.input), Path(args.report)
    total = 0
    contaminated = 0
    examples = []

    with inp.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                pair = json.loads(line)
            except Exception:
                continue
            asst = next((m.get("content", "") for m in pair.get("messages", []) if m.get("role") == "assistant"), "")
            if scan_text(asst):
                contaminated += 1
                if len(examples) < 10:
                    # show 80-char window around first hit
                    for p in THINK_PATTERNS:
                        m = p.search(asst)
                        if m:
                            ctx = asst[max(0, m.start() - 40):m.end() + 40]
                            examples.append({
                                "fingerprint": pair.get("fingerprint", "?")[:16] + "...",
                                "deliverable": pair.get("deliverable"),
                                "context": ctx.replace("\n", "  "),
                            })
                            break

    rate = contaminated / total if total else 0.0
    rep_data = {
        "total": total,
        "contaminated": contaminated,
        "contamination_rate": rate,
        "kill_threshold": KILL_THRESHOLD,
        "verdict": "KILL" if rate > KILL_THRESHOLD else "PASS",
        "examples": examples,
    }
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps(rep_data, indent=2))

    print(f"\n══════════════════════════════════════════════════════")
    print(f"  THINK-TAG CONTAMINATION SCAN · {inp.name}")
    print(f"══════════════════════════════════════════════════════")
    print(f"  total           : {total:>6,}")
    print(f"  contaminated    : {contaminated:>6,}  ({rate*100:.3f}%)")
    print(f"  kill threshold  : {KILL_THRESHOLD*100:.1f}%")
    print(f"  verdict         : {rep_data['verdict']}")
    if examples:
        print(f"\n  first {len(examples)} examples:")
        for ex in examples:
            print(f"    {ex['fingerprint']}  ·  {ex['deliverable']}")
            print(f"      {ex['context'][:120]}")
    print(f"\n  report → {rep}")
    print(f"══════════════════════════════════════════════════════")

    sys.exit(1 if rate > KILL_THRESHOLD else 0)


if __name__ == "__main__":
    main()
