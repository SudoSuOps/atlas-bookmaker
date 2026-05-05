#!/usr/bin/env python3
"""
02_flip_cre_to_strict_input.py · Source B · CRE Hack pairs → Bookmaker input

THE LOAD-BEARING TRANSFORMATION. Per Plan agent's risk register: this script
alone determines whether ~30% of v2 corpus is usable. Hand-validate first 50
pairs before scaling. If <80% clean, drop target to 1,500.

What it does:
  1. Read cre_honey_stamped.jsonl pairs (filter task_type IN {underwriting,
     comp_analysis, valuation, rent_roll, debt_analysis, exchange_1031})
  2. Extract structured deal data from the USER prompt (well-formatted in the
     firm's IC-memo template)
  3. Build a deal_highlights JSON (the input the Hack hands the Bookmaker)
  4. Choose a target deliverable type (stratified across the 7 CRE-specific ones
     Source A doesn't cover: om_pdf · landing_page · costar_listing · flier ·
     investor_toc · map_caption · comp_callout)
  5. Emit a seed record · ready for Phase B teacher cooking

Phase B (separate script · 02_flip_cook.py) takes seed records and uses
Granite-4.1-8B teacher to generate the Bookmaker assistant content.

Target: 3,500 seed records.

Usage:
    python 02_flip_cre_to_strict_input.py \
        --source /tmp/swarm-nfs/swarm-and-bee-datasets/cre/cre_honey_stamped.jsonl \
        --target 3500 \
        --output /tmp/swarm-nfs/atlas-bookmaker/v2/raw/source_b_seeds.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

random.seed(42)


# ─── Regex extraction patterns (cre_honey_stamped IC-memo format) ────────────


PATTERNS = {
    "property":     re.compile(r"Property:\s*(.+?)(?:\n|$)"),
    "type":         re.compile(r"Type:\s*(.+?)(?:\n|$)"),
    "location":     re.compile(r"Location:\s*(.+?)(?:\n|$)"),
    "year_built":   re.compile(r"Year built:\s*(\d{4})"),
    "size_sf":      re.compile(r"(\d{1,3}(?:,\d{3})*)\s*SF\s+(?:cold storage|industrial|office|retail|multifamily|building|facility|flex|warehouse|MOB|medical|self-storage)", re.IGNORECASE),
    "noi":          re.compile(r"NOI:\s*\$?([\d,]+)"),
    "cap_rate":     re.compile(r"Cap rate:\s*([\d.]+)%?"),
    "value":        re.compile(r"Value:\s*\$?([\d,]+)"),
    "purchase":     re.compile(r"Purchase price:\s*\$?([\d,]+)"),
    "debt":         re.compile(r"Debt:\s*([^\n,]+?)\s*[—\-]\s*\$?([\d,]+)"),
    "dscr":         re.compile(r"DSCR:\s*([\d.]+)x?"),
    "ltv":          re.compile(r"LTV:\s*([\d.]+)%?"),
    "tenant_line":  re.compile(r"-\s*([^:\n]+?):\s*([\d,]+)\s*SF,\s*\$([\d.]+)/SF,\s*(NNN|NN|N|MG|FSG|Gross),\s*expires?\s+(\d{4})-?(\d{0,2})-?(\d{0,2})", re.IGNORECASE),
    "lease_expires": re.compile(r"expires?\s+(\d{4})", re.IGNORECASE),
}

ASSET_CLASS_KEYWORDS = {
    "cold storage": "industrial cold storage",
    "warehouse": "industrial flex",
    "industrial": "industrial flex",
    "flex": "industrial flex",
    "office": "office",
    "retail": "credit-tenant retail strip",
    "strip": "credit-tenant retail strip",
    "multifamily": "multifamily",
    "apartment": "multifamily",
    "MOB": "medical office (MOB)",
    "medical office": "medical office (MOB)",
    "self-storage": "self-storage",
    "dollar general": "Dollar General STNL",
    "dollar tree": "Dollar Tree STNL",
    "family dollar": "Family Dollar STNL",
    "walgreens": "Walgreens corner",
    "cvs": "CVS pharmacy",
    "starbucks": "Starbucks drive-thru",
    "mcdonald": "QSR ground lease (McDonald's)",
    "wendy": "Wendy's NNN",
    "chick-fil-a": "Chick-fil-A ground lease",
    "burger king": "Burger King ground lease",
    "autozone": "AutoZone retail",
    "o'reilly": "O'Reilly Auto Parts",
    "tractor supply": "Tractor Supply",
    "7-eleven": "7-Eleven c-store",
}


def fmt_money(amount: int | float) -> str:
    """Format raw int/float as '$2.4M' / '$145K' style for deal_highlights."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M".rstrip("0").rstrip(".") + ("M" if "M" not in f"${amount / 1_000_000:.2f}M".rstrip("0").rstrip(".") else "")
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:.0f}"


def extract_deal_highlights(user_content: str) -> dict | None:
    """Extract structured deal data from a Hack pair's USER prompt.

    Returns None if extraction yields too few fields (under quality bar).
    """
    out: dict[str, str] = {}

    # Property name
    if m := PATTERNS["property"].search(user_content):
        out["property_name"] = m.group(1).strip()

    # Asset class · pull from Type field, normalize via keyword map
    if m := PATTERNS["type"].search(user_content):
        type_str = m.group(1).strip().lower()
        for kw, normalized in ASSET_CLASS_KEYWORDS.items():
            if kw in type_str:
                out["asset_class"] = normalized
                break
        else:
            out["asset_class"] = m.group(1).strip()

    # Size SF
    if m := PATTERNS["size_sf"].search(user_content):
        out["size_sf"] = m.group(1).replace(",", "") + " SF"
    elif m := re.search(r"(\d{1,3}(?:,\d{3})*)\s*SF", user_content):
        out["size_sf"] = m.group(1).replace(",", "") + " SF"

    # Market
    if m := PATTERNS["location"].search(user_content):
        loc = m.group(1).strip()
        # Convert "Chandler/Gilbert, Phoenix" → "Phoenix AZ" if state inferable
        out["market"] = loc

    # Year built
    if m := PATTERNS["year_built"].search(user_content):
        out["year_built"] = m.group(1)

    # NOI
    if m := PATTERNS["noi"].search(user_content):
        try:
            out["noi"] = "$" + f"{int(m.group(1).replace(',', '')):,}"
        except ValueError:
            pass

    # Cap rate
    if m := PATTERNS["cap_rate"].search(user_content):
        out["cap_rate"] = m.group(1) + "%"

    # Price
    price = None
    if m := PATTERNS["value"].search(user_content):
        try:
            price = int(m.group(1).replace(",", ""))
        except ValueError:
            pass
    elif m := PATTERNS["purchase"].search(user_content):
        try:
            price = int(m.group(1).replace(",", ""))
        except ValueError:
            pass
    if price is not None:
        out["price"] = fmt_money(price)
        out["_price_raw"] = price

    # DSCR
    if m := PATTERNS["dscr"].search(user_content):
        out["dscr"] = m.group(1) + "x"

    # LTV
    if m := PATTERNS["ltv"].search(user_content):
        out["ltv"] = m.group(1) + "%"

    # Tenant info (multi-tenant possible · grab the largest)
    tenants = PATTERNS["tenant_line"].findall(user_content)
    if tenants:
        # tenants is list of (name, sf, rent_per_sf, lease_type, year, month, day)
        largest = max(tenants, key=lambda t: int(t[1].replace(",", "")) if t[1].replace(",", "").isdigit() else 0)
        out["tenant_brand"] = largest[0].strip()
        out["lease_term_remaining"] = f"{largest[3]} expires {largest[4]}"
    elif m := PATTERNS["lease_expires"].search(user_content):
        # Calculate years remaining (from 2026)
        try:
            years_remain = int(m.group(1)) - 2026
            if years_remain > 0:
                out["lease_term_remaining"] = f"{years_remain}-yr remaining"
        except ValueError:
            pass

    # Quality gate: must have at least 4 of the key fields
    key_fields = {"asset_class", "market", "price", "cap_rate", "noi", "size_sf"}
    have = key_fields & set(out.keys())
    if len(have) < 4:
        return None

    return out


# ─── Deliverable selection · stratified across the 7 CRE-specific ones ─────


# Source A covers social_card · eblast · photo_brief
# Source B covers the CRE-specific 7
SOURCE_B_DELIVERABLES = [
    "om_pdf",
    "landing_page",
    "costar_listing",
    "flier",
    "investor_toc",
    "map_caption",
    "comp_callout",
]


def pick_deliverable(deal: dict, counts: Counter) -> str:
    """Stratified pick · favor under-represented deliverables."""
    # Sort deliverables by current count (lowest first · prioritize coverage)
    sorted_options = sorted(SOURCE_B_DELIVERABLES, key=lambda d: counts[d])
    # Among the 3 lowest, pick randomly (some randomness for variety)
    return random.choice(sorted_options[:3])


# ─── Buyer segment + brand pack heuristics ───────────────────────────────────


def pick_buyer_segment(deal: dict) -> str:
    asset = (deal.get("asset_class") or "").lower()
    market = (deal.get("market") or "").lower()
    if "fl" in market or "florida" in market:
        return "1031-fl-stnl-buyers"
    if "stnl" in asset or "ground lease" in asset or any(
        b in asset for b in ["dollar", "walgreens", "cvs", "starbucks"]
    ):
        return "mid-market-stnl-buyers"
    if "industrial" in asset or "cold storage" in asset:
        return "industrial-portfolio-buyers"
    if "multifamily" in asset:
        return "Sun-Belt-MF-syndicators"
    return "open-air"


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/tmp/swarm-nfs/swarm-and-bee-datasets/cre/cre_honey_stamped.jsonl")
    ap.add_argument("--target", type=int, default=3500)
    ap.add_argument("--output", required=True)
    ap.add_argument("--task-types", default="underwriting,comp_analysis,valuation,rent_roll,debt_analysis,exchange_1031",
                    help="Comma-separated cre_honey_stamped task_types to mine")
    ap.add_argument("--max-scan", type=int, default=200000, help="Max records to scan from source")
    args = ap.parse_args()

    valid_tasks = {t.strip() for t in args.task_types.split(",")}
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    by_deliverable: Counter = Counter()
    extraction_pass = 0
    extraction_fail = 0
    seen_fp: set[str] = set()
    written = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    out_f = out_path.open("w")
    try:
        with open(args.source) as f:
            for i, line in enumerate(f):
                if i >= args.max_scan or written >= args.target:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("task_type") not in valid_tasks:
                    continue
                msgs = rec.get("messages") or []
                user = next((m["content"] for m in msgs if m.get("role") == "user"), "")
                if not user:
                    continue
                deal = extract_deal_highlights(user)
                if deal is None:
                    extraction_fail += 1
                    continue
                extraction_pass += 1

                # Strip internal-only keys
                deal.pop("_price_raw", None)

                # Pick deliverable · buyer · brand
                deliverable = pick_deliverable(deal, by_deliverable)
                deal["buyer_segment"] = pick_buyer_segment(deal)
                deal["deliverable_type"] = deliverable
                deal["brand_pack_id"] = "swarm_and_bee"

                # Fingerprint
                fp_payload = json.dumps(deal, sort_keys=True)
                fp = hashlib.sha256(fp_payload.encode("utf-8", errors="ignore")).hexdigest()
                if fp in seen_fp:
                    continue
                seen_fp.add(fp)

                # Emit seed record · NO assistant content yet
                # (Phase B teacher script generates that from this seed)
                seed = {
                    "deal_highlights": deal,
                    "deliverable":     deliverable,
                    "domain":          "bookmaker",
                    "stream":          deliverable,
                    "lineage": {
                        "source":         "B",
                        "source_pair_id": (rec.get("metadata") or {}).get("pair_id", ""),
                        "source_task_type": rec.get("task_type"),
                        "cook_script":    "02_flip_cre_to_strict_input.py",
                        "cook_run":       "atlas-bookmaker-v2-2026-05-08",
                    },
                    "fingerprint":   fp,
                    "created_at":    now_iso,
                    "stage":         "seed",  # Phase B will upgrade to "cooked"
                }
                out_f.write(json.dumps(seed) + "\n")
                by_deliverable[deliverable] += 1
                written += 1
    finally:
        out_f.close()

    total_attempts = extraction_pass + extraction_fail
    print(f"\n══════════════════════════════════════════════════════")
    print(f"  SOURCE B · CRE strict-input flip · seed extraction")
    print(f"══════════════════════════════════════════════════════")
    print(f"  scanned attempts  : {total_attempts:,}")
    print(f"  extraction passed : {extraction_pass:,}  ({extraction_pass*100/max(1,total_attempts):.1f}%)")
    print(f"  extraction failed : {extraction_fail:,}")
    print(f"  written seeds     : {written:,}")
    print(f"  target            : {args.target:,}")
    print(f"  output            : {out_path}")
    print(f"\n  by deliverable (stratified):")
    for d, n in by_deliverable.most_common():
        print(f"    {d:25s}  {n:>5,}")
    print(f"\n  next: 02_flip_cook.py runs Granite-4.1-8B teacher on smash to")
    print(f"        generate Bookmaker assistant content from these seeds.")


if __name__ == "__main__":
    main()
