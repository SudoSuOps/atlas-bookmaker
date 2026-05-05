#!/usr/bin/env python3
"""
03_bookmaker_grinder.py · synthetic Bookmaker pair generator.

Source C of the v2 corpus · 4,000 pairs target · 400 per deliverable type
× 10 types = 4,000 stratified.

Forks aviation_grinder.py (3-mode: ENRICH/NARRATIVE/TEXTBOOK) into Bookmaker-
shape (TEMPLATE-FILL / BRAND-VOICE / REWRITE).

Teachers:
  - Default: Granite-4.1-8B via local vLLM (smash:8089) · sovereign · free · fast
  - Diversity sampler: Claude Opus 4.x (~20% of pairs) to break Granite-loop
    (only if ANTHROPIC_API_KEY set with credit balance)
  - Atlas-70B (when it ships Wed PM) · best brand-voice match · free local

Modes:
  1. TEMPLATE-FILL — given a deliverable template + deal_highlights, fill the slots
  2. BRAND-VOICE   — given a generic creative output, rewrite in firm voice
  3. REWRITE       — given a public OM / REIT deck page, restyle for our brand

Usage:
    python 03_bookmaker_grinder.py --target 4000 --teacher granite --output ...
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# 10 deliverable templates · 400 pairs each · stratified
DELIVERABLE_TARGETS = {
    "om_pdf":         400,
    "landing_page":   400,
    "eblast":         400,
    "costar_listing": 400,
    "social_card":    400,
    "flier":          400,
    "investor_toc":   400,
    "map_caption":    400,
    "comp_callout":   400,
    "photo_brief":    400,
}

# ─── Deal-context generators (varied inputs) ─────────────────────────────────


ASSET_CLASSES = [
    "Dollar General STNL", "Walgreens corner", "CVS pharmacy",
    "QSR ground lease (McDonald's)", "Wendy's NNN", "AutoZone retail",
    "O'Reilly Auto Parts", "Tractor Supply", "Family Dollar STNL",
    "7-Eleven c-store", "Aaron's furniture", "industrial flex (multi-tenant)",
    "industrial cold storage", "self-storage", "multifamily (Sun Belt)",
    "multifamily (Class B)", "medical office (MOB)", "veterinary clinic",
    "credit-tenant retail strip", "auto dealership ground lease",
    "Burger King ground lease", "Starbucks drive-thru",
    "Chick-fil-A ground lease", "FedEx Ground last-mile",
    "Amazon last-mile facility",
]
MARKETS = [
    "Tampa FL", "Orlando FL", "Jacksonville FL", "Dallas TX", "Houston TX",
    "Austin TX", "San Antonio TX", "Phoenix AZ", "Charlotte NC",
    "Nashville TN", "Atlanta GA", "Memphis TN", "Birmingham AL",
    "Las Vegas NV", "Indianapolis IN",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=4000)
    ap.add_argument("--teacher", default="granite", choices=["granite", "claude", "atlas70b"])
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    print(f"NOTE: 03_bookmaker_grinder.py is the synth generator · v0.1 skeleton")
    print(f"      · target: {args.target} pairs · 10 deliverables × 400 each")
    print(f"      · teacher: {args.teacher}")
    print(f"      · output: {args.output}")
    print(f"      · see agent/prompts/system_v2.yaml for deliverable_templates")
    print(f"      · see docs/PIPELINE.md for the synth recipe")
    print(f"")
    print(f"      Skeleton exits 0 — wire the 3-mode generator Wed AM.")
    sys.exit(0)


if __name__ == "__main__":
    main()
