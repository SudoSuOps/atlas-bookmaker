#!/usr/bin/env python3
"""
05_merge_dedup.py · concatenate sources A+B+C+D, dedup by fingerprint.

Per data_quality_protocol.md: dedup MANDATORY before tribunal grading.
Atlas v1's 56% dupe disaster (45K pairs reported, 19.8K unique) is in firm
memory. Never skip.

Fingerprint: SHA-256 of concat(system, user, assistant) content.

Output: /tmp/swarm-nfs/atlas-bookmaker/v2/raw/bookmaker_corpus_v2_merged.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


def fingerprint(pair: dict) -> str:
    msgs = pair.get("messages", [])
    payload = "|".join((m.get("role", "") + ":" + m.get("content", "")) for m in msgs)
    return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="Source JSONL files (A+B+C+D)")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    seen: set[str] = set()
    written = 0
    duplicates = 0
    by_source: Counter = Counter()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w") as out_f:
        for inp in args.inputs:
            inp_path = Path(inp)
            if not inp_path.exists():
                print(f"  ! skip · not found: {inp}", file=sys.stderr)
                continue
            count = 0
            with inp_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pair = json.loads(line)
                    except Exception:
                        continue
                    fp = fingerprint(pair)
                    if fp in seen:
                        duplicates += 1
                        continue
                    seen.add(fp)
                    pair["fingerprint"] = fp
                    out_f.write(json.dumps(pair) + "\n")
                    count += 1
            by_source[inp_path.name] = count
            print(f"  ✓ {inp_path.name}: {count:,} unique pairs")
            written += count

    print(f"\n══════════════════════════════════════════════════════")
    print(f"  MERGE + DEDUP")
    print(f"══════════════════════════════════════════════════════")
    print(f"  pairs written  : {written:,}")
    print(f"  duplicates     : {duplicates:,}")
    print(f"  dedup rate     : {duplicates*100/(written+duplicates):.2f}%" if (written + duplicates) else "  dedup rate     : 0.00%")
    print(f"  output         : {args.output}")
    print(f"\n  by source:")
    for name, cnt in by_source.most_common():
        print(f"    {name:50s}  {cnt:>6,}")


if __name__ == "__main__":
    main()
