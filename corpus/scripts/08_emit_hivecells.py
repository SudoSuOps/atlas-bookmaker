#!/usr/bin/env python3
"""
08_emit_hivecells.py · final corpus emit · matches aviation hivecell schema.

Reads the merged + deduped + audit-passed corpus, emits as canonical hivecells
JSONL ready for tribunal grading on swarmrails.

Output schema mirrors aviation_hivecells.jsonl · adds `deliverable` field.

Cell ID format: HIVE-BMK-{16-char-hex}

Usage:
    python 08_emit_hivecells.py \
        --input /tmp/swarm-nfs/atlas-bookmaker/v2/raw/bookmaker_corpus_v2_merged_audited.jsonl \
        --output /tmp/swarm-nfs/atlas-bookmaker/v2/hivecells/bookmaker_hivecells_v2.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    inp_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

    with inp_path.open() as f, out_path.open("w") as out_f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            pair = json.loads(line)
            fp = pair.get("fingerprint") or hashlib.sha256(
                json.dumps(pair.get("messages", []), sort_keys=True).encode()
            ).hexdigest()
            cell = {
                "cell_id":     "HIVE-BMK-" + fp[:16],
                "domain":      "bookmaker",
                "stream":      pair.get("deliverable", "?"),
                "deliverable": pair.get("deliverable", "?"),
                "grade":       "honey",  # tribunal will re-tier
                "messages":    pair["messages"],
                "lineage":     pair.get("lineage", {}),
                "fingerprint": fp,
                "created_at":  now_iso,
                "verification_score": None,  # filled by tribunal
                "gate_results": pair.get("gate_results", {}),
            }
            out_f.write(json.dumps(cell) + "\n")
            written += 1

    print(f"\n  ✓ emitted {written:,} hivecells → {out_path}")
    print(f"  next: SCP to swarmrails · run tribunal grading (gemma3:12b + qwen2.5:32b)")


if __name__ == "__main__":
    main()
