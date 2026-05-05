# eval/

5-dimension Bookmaker eval rubric · NOT numerical-correctness eval. The Bookmaker NEVER computes — so we score on what she's actually responsible for.

## Eval suite

`prompts/ship_eval_100.jsonl` — 100 prompts · 10 per deliverable type · curated from realistic deal-highlights inputs.

## 5-dimension rubric

| Dim | Weight | Floor | Description |
|---|---|---|---|
| Strict-input fidelity | 35% | **5/5 floor** (any <5 fails the prompt) | Zero fabricated numbers · all values from `deal_highlights` · `[TBD]` for missing |
| Curb appeal | 20% | 3 | Sells the trophy · compelling to a buyer · not analytical |
| Brand voice | 20% | 3 | Broker vocab (Hack/Bookmaker/MAGIC/Defendable) · NOT lab vocab |
| Deliverable structure | 15% | 3 | Template fit · OM looks like OM · all required slots filled or `[TBD]` |
| Ready-to-ship polish | 10% | 3 | Markup clean · spelling/grammar tight · no AI-self-reference · no slop |

## Pass criteria

- **Mean weighted score ≥ 4.2/5** across 100 prompts
- **ZERO strict-input fabrications** across all 100

## Comparison

Run identical eval against v1 archived adapter to prove v2 beat v1. Eval report includes side-by-side delta.

## Auto vs hand grading

- **Auto-grade dimensions** (deterministic · no human needed):
  - Strict-input fidelity (uses `agent/tools/strict_input_check.py`)
  - Brand voice baseline (slop-phrase + broker-vocab counts)
- **Hand-grade dimensions** (require human reviewer · Donovan + dev):
  - Curb appeal
  - Deliverable structure
  - Ready-to-ship polish
- **Brand voice** uses auto-baseline + hand adjustment

## Usage

```bash
# Hand-graded (interactive, ~2h for 100 prompts)
python eval/score.py \
    --suite eval/prompts/ship_eval_100.jsonl \
    --adapter /home/smash/atlas-bookmaker_v2/merged/atlas-bookmaker-v2 \
    --report eval/v2_ship_eval_2026_05_09.jsonl

# Auto-only (deterministic dims · ~10 min · for CI sanity)
python eval/score.py \
    --suite eval/prompts/ship_eval_100.jsonl \
    --adapter /home/smash/atlas-bookmaker_v2/merged/atlas-bookmaker-v2 \
    --report eval/v2_auto_only.jsonl \
    --auto-only
```

## What this eval does NOT do

1. Does NOT score numerical correctness — Bookmaker never computes, so this dim is intentionally absent
2. Does NOT compare against external benchmarks (BFCL · MMLU · etc.) — those are base-model eval, already validated 12/0 in `docs/GRANITE_BEE.md`
3. Does NOT pass on voice alone — fitness-for-purpose > voice fidelity (firm doctrine)
