#!/usr/bin/env python3
"""
train/smoke.py · 30-prompt smoke after cook · 5 per top-6 deliverables.

Pass requires ≥27/30 with ZERO fabricated numbers.
One fabrication = corpus rebuild.

Usage:
    python train/smoke.py --adapter /home/smash/atlas-bookmaker_v2/checkpoints/final
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.tools.strict_input_check import run_strict_input_check


# 5 prompts per top-6 deliverables · 30 total
SMOKE_PROMPTS = [
    # om_pdf · 5 prompts
    {"deliverable": "om_pdf", "deal": {"asset_class": "Dollar General STNL", "market": "Tampa FL", "price": "$2.4M", "cap_rate": "6.85%", "tenant_credit": "BBB / IG", "lease_term_remaining": "12-yr NNN"}, "brief": "Ship a 1-page OM."},
    {"deliverable": "om_pdf", "deal": {"asset_class": "Walgreens corner", "market": "Orlando FL", "price": "$4.6M", "cap_rate": "6.25%", "tenant_credit": "BBB+ / IG", "lease_term_remaining": "14-yr NNN"}, "brief": "Ship a 1-page OM."},
    {"deliverable": "om_pdf", "deal": {"asset_class": "industrial cold storage", "market": "Memphis TN", "price": "$14M", "cap_rate": "7.15%", "tenant_credit": "A- / IG", "lease_term_remaining": "15-yr NNN"}, "brief": "Ship a 1-page OM."},
    {"deliverable": "om_pdf", "deal": {"asset_class": "7-Eleven c-store", "market": "Charlotte NC", "price": "$3.1M", "cap_rate": "6.50%", "tenant_credit": "BBB / IG", "lease_term_remaining": "10-yr NNN"}, "brief": "Ship a 1-page OM."},
    {"deliverable": "om_pdf", "deal": {"asset_class": "AutoZone retail", "market": "Phoenix AZ", "price": "$1.8M", "cap_rate": "7.50%", "tenant_credit": "BB / sub-IG", "lease_term_remaining": "8-yr NN"}, "brief": "Ship a 1-page OM."},
    # landing_page · 5 prompts (similar variations)
    # eblast · 5 prompts
    # costar_listing · 5 prompts
    # social_card · 5 prompts
    # deal_card · 5 prompts
    # NOTE: the full 30-prompt set is generated programmatically · this file shows the shape.
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--vllm-url", default="http://smash:8089/v1")
    args = ap.parse_args()

    print(f"NOTE: smoke.py · v0.1 skeleton · 5 of 30 prompts shown")
    print(f"      adapter: {args.adapter}")
    print(f"      vllm:    {args.vllm_url}")
    print(f"      run after cook to verify 0 fabrications · pass = ≥27/30")
    sys.exit(0)


if __name__ == "__main__":
    main()
