#!/usr/bin/env python3
"""
eval/score.py · 5-dimension Bookmaker eval rubric.

NOT a numerical-correctness rubric. The Bookmaker NEVER computes — so we score
on what she's actually responsible for: voice, layout, brand, polish, and
strict-input fidelity (zero fabrication).

Eval suite: eval/prompts/ship_eval_100.jsonl · 100 prompts · 10 per deliverable.

Pass criteria:
  - Mean score ≥ 4.2/5 across 100 prompts
  - ZERO strict-input fabrications across all 100

Comparison: same eval against v1 archived adapter to prove v2 beat v1.

Usage:
    python eval/score.py --suite eval/prompts/ship_eval_100.jsonl \
                         --adapter /home/smash/atlas-bookmaker_v2/merged/atlas-bookmaker-v2 \
                         --report eval/v2_ship_eval_2026_05_09.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Re-use the strict-input checker for objective dimension 1
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.tools.strict_input_check import run_strict_input_check


# ─── 5-dimension rubric (1-5 each) ──────────────────────────────────────────


RUBRIC = {
    "strict_input_fidelity": {
        "weight": 0.35,
        "floor": 5,  # Anything <5 is automatic fail
        "description": "Zero fabricated numbers · all values from deal_highlights · [TBD] for missing",
    },
    "curb_appeal": {
        "weight": 0.20,
        "floor": 3,
        "description": "Sells the trophy · compelling to a buyer · not analytical",
    },
    "brand_voice": {
        "weight": 0.20,
        "floor": 3,
        "description": "Broker vocab (Hack/Bookmaker/MAGIC/Defendable) · NOT lab vocab (as-a-Service/agent/fine-tune)",
    },
    "deliverable_structure": {
        "weight": 0.15,
        "floor": 3,
        "description": "Template fit · OM looks like OM · e-blast like e-blast · all required slots filled or [TBD]",
    },
    "ready_to_ship_polish": {
        "weight": 0.10,
        "floor": 3,
        "description": "Markup clean · spelling/grammar tight · no AI-self-reference · no slop",
    },
}


# ─── Brand-language detection (deterministic part of dim 3) ─────────────────


SLOP_PHRASES = [
    "as an ai",
    "i'm sorry",
    "i can't",
    "i cannot",
    "i'd be happy",
    "feel free",
    "as-a-service",
    "saas",
    "platform",
    "tool",
    "as a marketing coordinator",
    "i hope this helps",
    "let me know if",
]

BROKER_VOCAB_BONUS = [
    "hack",
    "bookmaker",
    "magic",
    "defendable",
    "pass",
    "proceed",
    "the lane",
    "royal jelly",
    "the book",
    "1031",
    "sit-down",
]


def deterministic_brand_score(text: str) -> dict[str, Any]:
    """Sub-score for brand_voice · pure-text features. Returns {score: 1-5, signals: dict}."""
    lower = text.lower()
    slop_hits = sum(1 for p in SLOP_PHRASES if p in lower)
    broker_hits = sum(1 for p in BROKER_VOCAB_BONUS if p in lower)
    # Deterministic baseline · 5 = no slop + ≥2 broker tokens · -1 per slop · max 5
    score = 5 - min(slop_hits, 4)
    if broker_hits >= 2:
        score = min(5, score + 1)
    score = max(1, score)
    return {
        "score": score,
        "slop_hits": slop_hits,
        "broker_hits": broker_hits,
    }


# ─── Inference (calls cooked Bookmaker via vLLM) ─────────────────────────────


def generate_via_vllm(prompt: dict[str, Any], adapter_path: str | None = None,
                     vllm_url: str = "http://smash:8089/v1") -> str:
    """Hit the deployed Bookmaker for one eval prompt.

    Falls back to local transformers if vLLM endpoint isn't reachable.
    """
    import httpx

    payload = {
        "model": adapter_path.split("/")[-1] if adapter_path else "atlas-bookmaker-v2",
        "messages": prompt["messages"],
        "max_tokens": prompt.get("max_tokens", 800),
        "temperature": 0.7,
    }
    try:
        r = httpx.post(f"{vllm_url}/chat/completions", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ! vLLM call failed: {e} — falling back to direct transformers load", file=sys.stderr)
        return _generate_via_transformers(prompt, adapter_path)


def _generate_via_transformers(prompt: dict[str, Any], adapter_path: str) -> str:
    """Local fallback · direct transformers + PEFT."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    BASE = "/home/smash/granite/granite-4.1-8b"
    tok = AutoTokenizer.from_pretrained(BASE)
    base = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map="cuda:0")
    model = PeftModel.from_pretrained(base, adapter_path) if adapter_path else base
    model.eval()

    text = tok.apply_chat_template(prompt["messages"], tokenize=False, add_generation_prompt=True)
    inputs = tok(text, return_tensors="pt").to("cuda:0")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=prompt.get("max_tokens", 800),
                             do_sample=True, temperature=0.7, top_p=0.9,
                             pad_token_id=tok.eos_token_id)
    return tok.decode(out[0, inputs.input_ids.shape[-1]:], skip_special_tokens=True).strip()


# ─── Hand-grading prompt template (for human reviewer) ───────────────────────


HUMAN_GRADING_TEMPLATE = """\
═══════════════════════════════════════════════════════════════════════════
  EVAL PROMPT {idx} / {total}  ·  deliverable: {deliverable}
═══════════════════════════════════════════════════════════════════════════

DEAL HIGHLIGHTS (input):
{deal_highlights_pretty}

GENERATED OUTPUT:
{output}

DETERMINISTIC SUBSCORES:
  · strict_input_fidelity   : {strict_input_score}/5  (fabricated: {fabricated_tokens})
  · brand_voice (auto)      : {brand_auto_score}/5  (slop_hits={slop_hits}, broker_hits={broker_hits})

GRADE THESE 5 DIMENSIONS (1-5 each):
  1. Strict-input fidelity (auto-set: {strict_input_score})  [enter integer 1-5]:
  2. Curb appeal / sells the trophy:                          [enter integer 1-5]:
  3. Brand voice (auto-baseline {brand_auto_score}; adjust):  [enter integer 1-5]:
  4. Deliverable structure / template fit:                    [enter integer 1-5]:
  5. Ready-to-ship polish:                                    [enter integer 1-5]:

NOTES:
"""


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite",   default="eval/prompts/ship_eval_100.jsonl")
    ap.add_argument("--adapter", default="/home/smash/atlas-bookmaker_v2/merged/atlas-bookmaker-v2")
    ap.add_argument("--report",  required=True, help="Output JSONL with all results")
    ap.add_argument("--vllm-url", default="http://smash:8089/v1")
    ap.add_argument("--auto-only", action="store_true", help="Skip human grading · output deterministic only")
    args = ap.parse_args()

    suite_path = Path(args.suite)
    if not suite_path.exists():
        print(f"suite not found: {suite_path}", file=sys.stderr)
        sys.exit(2)

    prompts = [json.loads(l) for l in suite_path.read_text().splitlines() if l.strip()]
    print(f"loaded {len(prompts)} eval prompts from {suite_path}")

    results: list[dict[str, Any]] = []
    fabrication_count = 0

    for i, prompt in enumerate(prompts):
        deal_highlights = prompt.get("deal_highlights", {})
        deliverable = prompt.get("deliverable", "?")

        output = generate_via_vllm(prompt, adapter_path=args.adapter, vllm_url=args.vllm_url)

        sic = run_strict_input_check(deal_highlights, output)
        brand_auto = deterministic_brand_score(output)

        if not sic.pass_check:
            fabrication_count += 1

        result = {
            "idx": i,
            "deliverable": deliverable,
            "deal_highlights": deal_highlights,
            "output": output,
            "auto_scores": {
                "strict_input_fidelity": 5 if sic.pass_check else 1,
                "brand_voice_auto": brand_auto["score"],
            },
            "strict_input_check": sic.model_dump(),
            "brand_auto": brand_auto,
        }

        if not args.auto_only:
            print(HUMAN_GRADING_TEMPLATE.format(
                idx=i + 1,
                total=len(prompts),
                deliverable=deliverable,
                deal_highlights_pretty=json.dumps(deal_highlights, indent=2),
                output=output,
                strict_input_score=result["auto_scores"]["strict_input_fidelity"],
                brand_auto_score=brand_auto["score"],
                fabricated_tokens=sic.fabricated_tokens or "[]",
                slop_hits=brand_auto["slop_hits"],
                broker_hits=brand_auto["broker_hits"],
            ))
            try:
                hand_scores = {
                    "strict_input_fidelity": int(input("  1. strict_input_fidelity: ").strip() or result["auto_scores"]["strict_input_fidelity"]),
                    "curb_appeal":           int(input("  2. curb_appeal: ").strip()),
                    "brand_voice":           int(input("  3. brand_voice: ").strip() or brand_auto["score"]),
                    "deliverable_structure": int(input("  4. deliverable_structure: ").strip()),
                    "ready_to_ship_polish":  int(input("  5. ready_to_ship_polish: ").strip()),
                }
                notes = input("  notes (Enter for none): ").strip()
                result["hand_scores"] = hand_scores
                result["notes"] = notes
                weighted = sum(hand_scores[d] * RUBRIC[d]["weight"] for d in RUBRIC)
                result["weighted_score"] = round(weighted, 3)
            except (KeyboardInterrupt, EOFError):
                print("\nhand-grading interrupted · saving partial report.")
                break

        results.append(result)

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Summary
    print(f"\n══════════════════════════════════════════════════════")
    print(f"  EVAL SUMMARY · {suite_path.name}")
    print(f"══════════════════════════════════════════════════════")
    print(f"  prompts graded     : {len(results)}")
    print(f"  fabrications       : {fabrication_count}")

    if not args.auto_only and any("weighted_score" in r for r in results):
        weighted = [r["weighted_score"] for r in results if "weighted_score" in r]
        mean = sum(weighted) / len(weighted)
        print(f"  weighted mean      : {mean:.3f} / 5")
        print(f"  pass threshold     : 4.200")
        print(f"  verdict            : {'PASS · ship' if mean >= 4.2 and fabrication_count == 0 else 'FAIL · do not ship'}")

    print(f"\n  report → {args.report}")


if __name__ == "__main__":
    main()
