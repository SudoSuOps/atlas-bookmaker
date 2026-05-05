#!/usr/bin/env python3
"""
06_strict_input_audit.py · THE FIRM-DOCTRINE GATE

For every Bookmaker training pair, verify that every numeric / dollar / percentage
token in the assistant content also appears in the user content. Pairs that fabricate
numbers get REJECTED (not "fixed").

This is the firm's hardest gate. v1 Bookmaker shipped with hallucinated SF / NOI / DSCR
because the training corpus was 95% Hack-analytical work. v2 enforces: numbers in
output ⊆ numbers in input.

Runs at THREE points in the pipeline:
  1. Corpus build (this script · this file)
  2. Smoke eval after cook (to confirm Granite-4.1-8B QLoRA didn't regress)
  3. Inference time (deterministic gate in agent/tools/strict_input_check.py)

Usage:
    python 06_strict_input_audit.py --input bookmaker_corpus_v2.jsonl --output audit_report.jsonl

Exit codes:
    0   all pairs pass
    1   1+ fabrications detected — pairs need regeneration
    2   schema error · not a JSONL file
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator


# Numeric token patterns the Bookmaker should ONLY use if also in input.
# These are CRE-specific token shapes — extend if a deliverable needs more.
NUMERIC_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("dollar_amount", re.compile(r"\$[\d,]+(?:\.\d+)?[MKB]?")),
    ("percent",       re.compile(r"\d+(?:\.\d+)?%")),
    ("cap_band",      re.compile(r"\d+\.\d+(?:\s*[-–]\s*\d+\.\d+)?%?")),
    ("year",          re.compile(r"\b(?:19|20)\d{2}\b")),
    ("sf",            re.compile(r"\b\d{1,3}(?:,\d{3})*\s*SF\b", re.IGNORECASE)),
    ("acres",         re.compile(r"\b\d+(?:\.\d+)?\s*acres?\b", re.IGNORECASE)),
    ("dscr",          re.compile(r"\bDSCR[:\s]+\d+(?:\.\d+)?x?\b", re.IGNORECASE)),
    ("term_yr",       re.compile(r"\b\d{1,2}-?\s*yr\b", re.IGNORECASE)),
    ("term_year",     re.compile(r"\b\d{1,2}\s+years?\s+remaining\b", re.IGNORECASE)),
    ("noi",           re.compile(r"\bNOI[:\s]+\$[\d,]+(?:\.\d+)?[MKB]?\b", re.IGNORECASE)),
    ("escalation",    re.compile(r"\b\d{1,2}(?:\.\d+)?%\s+(?:bumps?|escalation)\b", re.IGNORECASE)),
]

# Tokens always allowed in output (universal, not deal-specific)
ALWAYS_ALLOWED = {
    "0.0.10291838",   # Hedera deed anchor topic
    "0.0.10291827",   # Hedera operator
    "$0.0008",        # publish cost (firm constant)
    "$0.0052",        # cost-to-mint per deed (firm constant)
    "1031",           # exchange code
    "5",              # MAGIC has 5 letters etc.
    "10",             # 10 deliverables
    "2026",           # current year (don't flag year-of-publication tokens)
}


def extract_numeric_tokens(text: str) -> set[str]:
    """Pull all numeric tokens from a string · normalized for comparison."""
    tokens: set[str] = set()
    for _name, pat in NUMERIC_PATTERNS:
        for m in pat.findall(text):
            # Normalize whitespace · uppercase · strip stray punct
            t = re.sub(r"\s+", " ", m.strip().upper())
            tokens.add(t)
    return tokens


def normalize(token: str) -> str:
    """Light normalization to compare tokens across input/output."""
    return re.sub(r"\s+", "", token.upper().replace(",", "").replace("$", "$"))


def check_pair(pair: dict) -> dict:
    """Return audit result dict per pair."""
    msgs = pair.get("messages") or []
    if len(msgs) < 3:
        return {"status": "schema_error", "reason": "missing_messages"}

    user_text = next((m["content"] for m in msgs if m["role"] == "user"), "")
    asst_text = next((m["content"] for m in msgs if m["role"] == "assistant"), "")

    user_tokens = extract_numeric_tokens(user_text)
    user_norm = {normalize(t) for t in user_tokens} | {normalize(t) for t in ALWAYS_ALLOWED}

    asst_tokens = extract_numeric_tokens(asst_text)
    fabricated: list[str] = []
    for t in asst_tokens:
        if normalize(t) not in user_norm:
            # Allow if appears in [TBD: ...] or near "TBD"
            ctx_window = 30
            asst_idx = asst_text.upper().find(t.upper())
            if asst_idx >= 0:
                ctx = asst_text[max(0, asst_idx - ctx_window):asst_idx + ctx_window].upper()
                if "TBD" in ctx:
                    continue
            fabricated.append(t)

    return {
        "status": "fabricated" if fabricated else "pass",
        "user_token_count": len(user_tokens),
        "asst_token_count": len(asst_tokens),
        "fabricated_tokens": fabricated,
        "fabricated_count": len(fabricated),
    }


def iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  required=True, help="Path to bookmaker corpus JSONL")
    ap.add_argument("--output", required=True, help="Path to write audit report JSONL")
    ap.add_argument("--reject", default=None, help="Optional: write REJECTED pairs (with fabrications) to this JSONL")
    ap.add_argument("--accept", default=None, help="Optional: write ACCEPTED pairs (no fabrications) to this JSONL")
    args = ap.parse_args()

    inp, out = Path(args.input), Path(args.output)
    if not inp.exists():
        print(f"input not found: {inp}", file=sys.stderr)
        sys.exit(2)

    rej_f = open(args.reject, "w") if args.reject else None
    acc_f = open(args.accept, "w") if args.accept else None

    counts: Counter = Counter()
    total = 0
    fabrication_examples: list[dict] = []

    with out.open("w") as out_f:
        for pair in iter_jsonl(inp):
            total += 1
            result = check_pair(pair)
            counts[result["status"]] += 1
            entry = {
                "fingerprint": pair.get("fingerprint"),
                "deliverable": pair.get("deliverable"),
                **result,
            }
            out_f.write(json.dumps(entry) + "\n")

            if result["status"] == "fabricated":
                if rej_f:
                    rej_f.write(json.dumps(pair) + "\n")
                if len(fabrication_examples) < 5:
                    fabrication_examples.append({
                        "fingerprint": pair.get("fingerprint")[:16] + "..." if pair.get("fingerprint") else "?",
                        "fabricated": result["fabricated_tokens"][:5],
                    })
            elif result["status"] == "pass":
                if acc_f:
                    acc_f.write(json.dumps(pair) + "\n")

    if rej_f: rej_f.close()
    if acc_f: acc_f.close()

    pass_count = counts.get("pass", 0)
    fab_count = counts.get("fabricated", 0)
    err_count = counts.get("schema_error", 0)

    print(f"\n══════════════════════════════════════════════════════")
    print(f"  STRICT-INPUT AUDIT · {inp.name}")
    print(f"══════════════════════════════════════════════════════")
    print(f"  total pairs     : {total:>6,}")
    print(f"  ✓ pass          : {pass_count:>6,}  ({pass_count*100/total:.1f}%)")
    print(f"  ✗ fabricated    : {fab_count:>6,}  ({fab_count*100/total:.1f}%)")
    print(f"  ! schema_error  : {err_count:>6,}")

    if fabrication_examples:
        print(f"\n  first {len(fabrication_examples)} fabrication examples:")
        for ex in fabrication_examples:
            print(f"    {ex['fingerprint']}  ·  {ex['fabricated']}")

    print(f"\n  audit report → {out}")
    if args.accept:
        print(f"  ✓ accepted    → {args.accept}")
    if args.reject:
        print(f"  ✗ rejected    → {args.reject}")
    print(f"══════════════════════════════════════════════════════")

    # Exit code: 0 all pass · 1 fabrications · 2 schema errors
    if err_count > 0 and pass_count == 0 and fab_count == 0:
        sys.exit(2)
    sys.exit(1 if fab_count > 0 else 0)


if __name__ == "__main__":
    main()
