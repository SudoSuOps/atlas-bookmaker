#!/usr/bin/env python3
"""
01_extract_marketing.py · Source A · pull from marketing honey.

Reuses the firm's existing marketing creative corpus:
  - swarmmarket_honey.jsonl  (53 MB · ~30K records)
  - swarmmarket_v2.jsonl     (36 MB · ~20K records)

These pairs ARE creative-production work (LinkedIn / X / email / ad copy /
video scripts) — exactly the Bookmaker role · just with a fintech/AI brand
context instead of CRE. We:
  1. Filter to streams that map to Bookmaker deliverables (drop campaign-
     planning · competitive-intel · multi-deliverable strategy)
  2. Drop low-quality (score <50 · length <500 · role drift)
  3. Rewrite system prompt to v2 Bookmaker (firm voice consistency)
  4. Tag deliverable type per stream
  5. Emit Bookmaker-shaped pair JSONL

The fintech/AI content in the assistant outputs is noise during training but
the structural patterns (LinkedIn hook / X thread shape / email drip / etc.)
are the valuable signal · brand voice gets re-baked via the system prompt.

Target: 3,000 pairs.

Usage:
    python 01_extract_marketing.py \
        --honey   /tmp/swarm-nfs/swarm-and-bee-datasets/marketing/swarmmarket_honey.jsonl \
        --v2      /tmp/swarm-nfs/swarm-and-bee-datasets/marketing/swarmmarket_v2.jsonl \
        --target  3000 \
        --output  /tmp/swarm-nfs/atlas-bookmaker/v2/raw/source_a_marketing.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

# ─── Stream → Bookmaker deliverable mapping ──────────────────────────────────


STREAM_TO_DELIVERABLE = {
    # Direct fits
    "linkedin_post":       "social_card",
    "linkedin_post_strategy": "social_card",
    "x_post":              "social_card",
    "x_thread":            "social_card",
    "twitter_post":        "social_card",
    "instagram_caption":   "social_card",
    "instagram_post":      "social_card",
    "email_drip":          "eblast",
    "email_marketing":     "eblast",
    "eblast":              "eblast",
    "newsletter":          "eblast",
    "meta_ads":            "social_card",
    "google_ads":          "social_card",
    "x_ads":               "social_card",
    "facebook_ads":        "social_card",
    "tiktok_script":       "photo_brief",     # creative direction
    "short_form_video":    "photo_brief",
    "video_script":        "photo_brief",
    "video_hook":          "photo_brief",
    "hook_specialist":     "photo_brief",
    "blog_seo":            "landing_page",    # body copy for landing
    "blog_post":           "landing_page",
    "pr_release":          "eblast",
}

# Skip these · not mappable to Bookmaker deliverables (multi-asset / analytical)
SKIP_STREAMS = {
    "content_calendar",
    "marketing_campaign",
    "competitive_intelligence",
    "product_launch",
    "campaign_strategy",
    "social_strategy",
}


# ─── v2 Bookmaker system prompt · re-target every pair ───────────────────────


V2_SYSTEM_PROMPT = """You are Atlas-Bookmaker — the AI Marketing Coordinator for Swarm & Bee LLC, a Florida-licensed AI-native commercial real estate brokerage.

You are NOT a broker. You are a $60K/yr creative production hire. You take a Hack's curated deal-highlights and produce shipable creative — OM PDF booklets, landing pages, e-blast teasers, CoStar/LoopNet listings, social cards, brokerage fliers, investor packets, map captions, comp callouts, photo briefs.

Strict input rule: you DO NOT compute or generate numbers. Every number in your output MUST appear in the user's deal_highlights JSON input. If a value is missing, write [TBD: <field>] instead. The Hack already underwrote the deal; your job is to write the document AROUND the given values, never to invent the missing ones.

Voice: tight, dense, broker-grade. No fluff. No "as an AI". You quote cap rates, lease terms, NNN structure, tenant credit (BBB / IG / sub-IG) WHEN GIVEN. You sell the trophy. You speak to BUYERS, not to underwriters. The MAGIC framework is the floor: Meetings · Appraisals · Grind · Ink · Close. Every output you produce can carry a Defendable receipt anchored to Hedera HCS topic 0.0.10291838.

We don't ship slop. Fitness-for-purpose > voice fidelity."""


# ─── Quality filters ─────────────────────────────────────────────────────────


def passes_quality(record: dict, min_score: int = 50, min_assistant_len: int = 500) -> bool:
    """Drop low-quality pairs · firm doctrine."""
    msgs = record.get("messages") or []
    if len(msgs) < 3:
        return False

    asst = next((m for m in msgs if m.get("role") == "assistant"), None)
    if not asst:
        return False
    asst_content = asst.get("content", "")
    if len(asst_content) < min_assistant_len or len(asst_content) > 8000:
        return False

    # Score check (if metadata has it)
    meta = record.get("metadata") or {}
    score = meta.get("score")
    if score is not None and score < min_score:
        return False

    # Drop role-drift signals (analytical content leaking into creative pairs)
    asst_lower = asst_content.lower()
    if any(p in asst_lower for p in [
        "as an ai", "i cannot", "i'm sorry", "i'd be happy",
        "<think>", "</think>", "<reasoning>",
    ]):
        return False

    return True


def detect_stream(record: dict) -> str | None:
    """Pull stream from metadata · validate it's a known/mappable type."""
    stream = (record.get("metadata") or {}).get("stream", "").strip().lower()
    if not stream:
        # Try inferring from system prompt
        msgs = record.get("messages") or []
        sys_msg = next((m for m in msgs if m.get("role") == "system"), None)
        if sys_msg:
            sp = sys_msg.get("content", "")[:200].lower()
            if "linkedin" in sp:        return "linkedin_post"
            if "x/twitter" in sp or "twitter" in sp: return "x_post"
            if "tiktok" in sp or "reels" in sp: return "tiktok_script"
            if "instagram" in sp:       return "instagram_caption"
            if "email" in sp:           return "email_drip"
            if "blog" in sp:            return "blog_seo"
            if "press release" in sp or "pr communications" in sp: return "pr_release"
            if "google ads" in sp:      return "google_ads"
            if "meta" in sp and "ad" in sp: return "meta_ads"
        return None
    return stream


# ─── Re-target pair to Bookmaker shape ───────────────────────────────────────


def refit(record: dict) -> dict | None:
    """Convert a marketing_honey record into a Bookmaker training pair."""
    if not passes_quality(record):
        return None
    stream = detect_stream(record)
    if not stream or stream in SKIP_STREAMS:
        return None
    deliverable = STREAM_TO_DELIVERABLE.get(stream)
    if not deliverable:
        return None

    msgs = record["messages"]
    user_msg = next((m for m in msgs if m.get("role") == "user"), None)
    asst_msg = next((m for m in msgs if m.get("role") == "assistant"), None)
    if not user_msg or not asst_msg:
        return None

    # Re-targeted system prompt · v2 Bookmaker firm voice
    refit_msgs = [
        {"role": "system",    "content": V2_SYSTEM_PROMPT},
        {"role": "user",      "content": user_msg["content"]},
        {"role": "assistant", "content": asst_msg["content"]},
    ]
    fp_payload = "|".join(m["role"] + ":" + m["content"] for m in refit_msgs)
    fingerprint = hashlib.sha256(fp_payload.encode("utf-8", errors="ignore")).hexdigest()

    meta_orig = record.get("metadata") or {}
    return {
        "messages":    refit_msgs,
        "deliverable": deliverable,
        "domain":      "bookmaker",
        "stream":      stream,
        "grade":       meta_orig.get("tier", "honey"),
        "verification_score": meta_orig.get("score"),
        "lineage": {
            "source":         "A",
            "source_pair_id": meta_orig.get("pair_id", ""),
            "source_stream":  stream,
            "gen_model":      meta_orig.get("model", ""),
            "cook_script":    "01_extract_marketing.py",
            "cook_run":       "atlas-bookmaker-v2-2026-05-08",
        },
        "fingerprint": fingerprint,
        "created_at":  meta_orig.get("timestamp"),
    }


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--honey",  default="/tmp/swarm-nfs/swarm-and-bee-datasets/marketing/swarmmarket_honey.jsonl")
    ap.add_argument("--v2",     default="/tmp/swarm-nfs/swarm-and-bee-datasets/marketing/swarmmarket_v2.jsonl")
    ap.add_argument("--target", type=int, default=3000)
    ap.add_argument("--output", required=True)
    ap.add_argument("--min-score", type=int, default=50)
    ap.add_argument("--min-len",   type=int, default=500)
    args = ap.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sources = [Path(args.honey), Path(args.v2)]
    for s in sources:
        if not s.exists():
            print(f"  ! source missing: {s}", file=sys.stderr)

    seen_fp: set[str] = set()
    by_deliverable: Counter = Counter()
    by_stream: Counter = Counter()
    total_scanned = 0
    written = 0

    out_f = out_path.open("w")
    try:
        for src in sources:
            if not src.exists():
                continue
            with src.open() as f:
                for line in f:
                    if written >= args.target:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    total_scanned += 1
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    refit_rec = refit(rec)
                    if refit_rec is None:
                        continue
                    if refit_rec["fingerprint"] in seen_fp:
                        continue
                    seen_fp.add(refit_rec["fingerprint"])
                    out_f.write(json.dumps(refit_rec) + "\n")
                    by_deliverable[refit_rec["deliverable"]] += 1
                    by_stream[refit_rec["stream"]] += 1
                    written += 1
    finally:
        out_f.close()

    print(f"\n══════════════════════════════════════════════════════")
    print(f"  SOURCE A · marketing extract")
    print(f"══════════════════════════════════════════════════════")
    print(f"  scanned         : {total_scanned:,}")
    print(f"  written         : {written:,}")
    print(f"  target          : {args.target:,}")
    print(f"  output          : {out_path}")
    print(f"\n  by deliverable:")
    for d, n in by_deliverable.most_common():
        print(f"    {d:25s}  {n:>5,}")
    print(f"\n  by stream:")
    for s, n in by_stream.most_common(15):
        print(f"    {s:30s}  {n:>5,}")


if __name__ == "__main__":
    main()
