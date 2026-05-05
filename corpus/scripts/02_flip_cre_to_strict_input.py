#!/usr/bin/env python3
"""
02_flip_cre_to_strict_input.py · THE LOAD-BEARING TRANSFORMATION.

The most fragile and most important script in v2. Per the Plan agent risk register,
this script alone determines whether ~30% of the corpus is usable.

What it does:
  Takes Hack-analytical pairs from cre_honey_stamped.jsonl and "flips" them into
  Bookmaker strict-input pairs. The numerical answers in the original assistant
  content become the deal_highlights JSON in the new user prompt. The new
  assistant output is creative copy that REFERENCES those numbers without computing.

Source pairs (from inventory):
  - 297,646 underwriting        (richest deal data)
  - 114,304 comp_analysis       (good comp data)
  - 107,675 valuation           (price + cap)
  -  72,873 debt_analysis       (some debt-relevant pairs)
  -  59,189 rent_roll           (size + tenant data)
  -   2,065 lease_analysis      (term + structure)

Filter: task_type IN {"underwriting", "comp_analysis", "valuation", "rent_roll", "lease_analysis"}
Sample: stratified · 3,500 total target

Pair shape AFTER flip:
    {
      "messages": [
        {"role": "system",    "content": <Bookmaker v2 system prompt>},
        {"role": "user",      "content": "<deal_highlights JSON> + <deliverable brief>"},
        {"role": "assistant", "content": "<creative copy referencing input numbers>"}
      ],
      "deliverable": "<one of 10 types · stratified>",
      "domain": "bookmaker",
      "lineage": {"source": "B", "source_pair_id": "<original cell_id>"},
      ...
    }

Risk: extracting numbers from natural-language IC-memo prose is regex-fragile.
Hand-validate 50 transformed pairs before scaling. If <80% clean, drop target
to 1,500 (per Plan agent risk register).

Usage:
    python 02_flip_cre_to_strict_input.py \
        --source /tmp/swarm-nfs/swarm-and-bee-datasets/cre/cre_honey_stamped.jsonl \
        --target 3500 \
        --output /tmp/swarm-nfs/atlas-bookmaker/v2/raw/source_b_flipped.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from collections import Counter

# TODO: implement extraction logic per Plan agent's mining recipe (see docs/PIPELINE.md)
# Skeleton functions below define the contract · real impl in next commit.


def extract_deal_highlights(user_content: str, assistant_content: str) -> dict | None:
    """Extract structured deal data from a Hack pair.

    Per Explore agent's mining sketch:
        deal_highlights = {
            "asset_class":   extract_asset_class(user_content),
            "market":        extract_market(user_content),
            "price":         extract_number(r"Value:\\s?\\$?([\\d,.]+)", user_content),
            "cap_rate":      extract_number(r"Cap rate:\\s?([\\d.]+)%?", user_content),
            "term_years":    extract_number(r"expires? (\\d{4})", user_content) - current_year,
            "credit_score":  "NNN" if "NNN" in user_content else "Triple Net",
            "noi":           extract_number(r"NOI:\\s?\\$?([\\d,.]+)", user_content),
            "dscr":          extract_number(r"DSCR:\\s?([\\d.]+)", user_content),
            "sf":            extract_number(r"(\\d+(?:,\\d{3})*)\\s*SF", user_content),
        }
    """
    # TODO · real implementation
    raise NotImplementedError("flip extraction · land in next commit · see docs/PIPELINE.md")


def synthesize_bookmaker_response(
    deal_highlights: dict,
    deliverable: str,
    teacher_response: str | None = None,
) -> str:
    """Generate creative output that references deal_highlights without computing.

    For Source B, we have the Hack's analytical answer to mine creative angles
    from — but the OUTPUT we cook into must be Bookmaker creative, NOT the
    analytical answer. So this function calls a teacher LLM (Granite-4.1-8B
    via local vLLM at smash:8089, or Atlas-70B once it ships) to rewrite the
    Hack content into Bookmaker shape.
    """
    # TODO · real implementation
    raise NotImplementedError("synthesize · uses Granite-4.1-8B teacher")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="cre_honey_stamped.jsonl path")
    ap.add_argument("--target", type=int, default=3500, help="Target output pair count")
    ap.add_argument("--output", required=True, help="Where to write flipped pairs")
    args = ap.parse_args()

    print(f"NOTE: 02_flip_cre_to_strict_input.py is the load-bearing transform · v0.1 skeleton")
    print(f"      · real impl writes the (deal_highlights JSON IN, creative copy OUT) pairs")
    print(f"      · hand-validate 50 pairs before scaling · drop to 1,500 if <80% clean")
    print(f"      · target: {args.target} pairs from {args.source}")
    print(f"      · output: {args.output}")
    print(f"      · see docs/PIPELINE.md for the full mining recipe")
    print(f"")
    print(f"      Skeleton exits 0 — wire the real impl as the first work item Wed AM.")
    sys.exit(0)


if __name__ == "__main__":
    main()
