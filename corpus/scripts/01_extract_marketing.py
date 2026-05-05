#!/usr/bin/env python3
"""
01_extract_marketing.py · pull Source A from existing marketing honey.

Source A:
  - /tmp/swarm-nfs/swarm-and-bee-datasets/marketing/swarmmarket_honey.jsonl  (10,027 pairs)
  - /tmp/swarm-nfs/swarm-and-bee-datasets/marketing/swarmmarket_v2.jsonl     (5,447 pairs)

Target: ~3,000 keepers · highest signal · these are direct creative copy
(LinkedIn posts, e-blast bodies, content strategy).

Filter rules:
  - drop pairs <500 chars (too short for v2)
  - drop role drift (no underwriting / no analytical content)
  - rewrite system prompt to v2 Bookmaker (agent/prompts/system_v2.yaml)
  - tag with deliverable type per content shape
"""

from __future__ import annotations

import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--swarmmarket-honey", default="/tmp/swarm-nfs/swarm-and-bee-datasets/marketing/swarmmarket_honey.jsonl")
    ap.add_argument("--swarmmarket-v2",    default="/tmp/swarm-nfs/swarm-and-bee-datasets/marketing/swarmmarket_v2.jsonl")
    ap.add_argument("--target", type=int, default=3000)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    print(f"NOTE: 01_extract_marketing.py · v0.1 skeleton")
    print(f"      · target: {args.target} pairs from existing marketing honey")
    print(f"      · output: {args.output}")
    print(f"      · see docs/PIPELINE.md for source-A filter rules")
    sys.exit(0)


if __name__ == "__main__":
    main()
