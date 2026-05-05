#!/usr/bin/env python3
"""
04_reit_listing_extract.py · pull Source D · public REIT decks + listing copy.

Source D · ~1,500 pairs · real-world ground truth.

Sources:
  - Realty Income (NYSE: O) investor decks · STNL/NNN focus
  - Spirit Realty Capital (NYSE: SRC) decks
  - NNN REIT Inc (formerly National Retail Properties)
  - Agree Realty (NYSE: ADC)
  - Public CoStar / LoopNet listing patterns (synthetic-pattern · NEVER verbatim)

For REIT decks: SEC EDGAR is the canonical public source · 10-K filings + 8-K
attachments contain investor presentations.

For listing copy: ONLY pattern-style synthetic rewrites · the Granite teacher
generates the pattern, never the verbatim listing. Avoid copyright exposure.

Pipeline:
  1. Fetch PDFs from public IR pages (REIT) or scrape patterns (listings)
  2. Docling-parse each PDF → markdown_doc
  3. Extract deal-highlights from each page (Granite-Vision-4.1-4B · 94.4% KVP)
  4. Pair the deal_highlights with the surrounding creative copy
  5. Tag deliverable type · emit JSONL

Usage:
    python 04_reit_listing_extract.py --target 1500 --output ...
"""

from __future__ import annotations

import argparse
import sys


PUBLIC_REIT_IR_PAGES = [
    "https://www.realtyincome.com/investors",
    "https://www.spiritrealty.com/investor-relations/financial-information",
    "https://www.nnnreit.com/investors/financial-info",
    "https://investors.agreerealty.com/financial-information",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1500)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    print(f"NOTE: 04_reit_listing_extract.py · v0.1 skeleton")
    print(f"      · target: {args.target} pairs from public REIT IR + listing patterns")
    print(f"      · uses Granite-Docling-258M for PDF parse · Granite-Vision for KVP extract")
    print(f"      · CoStar/LoopNet pattern-only · NO verbatim copy (copyright)")
    print(f"      · see docs/PIPELINE.md for source-D recipe")
    sys.exit(0)


if __name__ == "__main__":
    main()
