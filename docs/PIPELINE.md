# Pipeline · how the cook works

End-to-end · corpus build → tribunal → cook → eval → ship.

## High-level flow

```
                ┌────────── Phase 1 (corpus build · ~10h) ──────────┐
                │                                                   │
   sources A+B+C+D ──► merge+dedup ──► strict-input audit ──► hivecells
                                                                    │
                                                                    ▼
                ┌────────── Phase 2 (tribunal · ~12h) ──────────────┐
                │                                                   │
        gemma3:12b + qwen2.5:32b on swarmrails ──► royal-jelly tier
                                                                    │
                                                                    ▼
                ┌────────── Phase 3 (cook · ~1.5h) ────────────────┐
                │                                                   │
        Granite-4.1-8B QLoRA on smash 5090 ──► merged adapter
                                                                    │
                                                                    ▼
                ┌────────── Phase 4 (vision cook · ~3-4h · parallel)┐
                │                                                   │
        Granite-Vision-4.1-4B QLoRA ──► CRE doc adapter
                                                                    │
                                                                    ▼
                ┌────────── Phase 5 (orchestration · ~4h) ─────────┐
                │                                                   │
        BeeAI agent · 6 tools wired ──► strict-input + brand gate
                                                                    │
                                                                    ▼
                ┌────────── Phase 6 (eval · ~2h hand-graded) ──────┐
                │                                                   │
        100-prompt suite · 5-dim rubric · ≥4.2/5 mean · 0 fab
                                                                    │
                                                                    ▼
                ┌────────── Phase 7 (ship · ~3h) ──────────────────┐
                │                                                   │
        Hedera anchor ──► vLLM serve ──► /v1/atlas/bookmaker live
```

## Phase 1 · Corpus build (10 h)

See [`corpus/README.md`](../corpus/README.md). Four sources · 12,000 pairs target · 7 hard gates.

### Source mining recipes (the actual scripts)

**Source A — `01_extract_marketing.py`**
```python
# Existing creative copy on NAS · highest signal · direct pull
swarmmarket_honey.jsonl + swarmmarket_v2.jsonl
filter:
  - len(assistant) >= 500
  - no underwriting/analytical content (drop role drift)
  - rewrite system prompt to v2 Bookmaker
  - tag deliverable type per content shape
target: ~3,000 keepers
```

**Source B — `02_flip_cre_to_strict_input.py` (LOAD-BEARING)**
```python
# The role-flip · the most fragile script · hand-validate before scaling
cre_honey_stamped.jsonl
filter task_type IN {"underwriting", "comp_analysis", "valuation", "rent_roll", "lease_analysis"}
for each pair:
  1. extract numerical answers from assistant content via regex
  2. repackage as deal_highlights JSON (the new user input)
  3. call teacher LLM (Granite-4.1-8B at smash:8089) to write Bookmaker creative output
  4. emit new pair with strict-input rule baked into system prompt
hand-validate first 50 pairs · if <80% clean drop target to 1,500
target: ~3,500 pairs
```

**Source C — `03_bookmaker_grinder.py`**
```python
# Synth generator · 10 deliverable templates × 400 pairs each
modes:
  TEMPLATE-FILL  # given template + deal_highlights, fill slots
  BRAND-VOICE    # given generic creative, rewrite in firm voice
  REWRITE        # given public OM/REIT page, restyle
teachers:
  default: Granite-4.1-8B (vLLM smash:8089)         # 80% · sovereign
  diversity: Claude Opus 4.x (anthropic API)        # 20% · break Granite-loop
  fallback: Atlas-70B (when ships Wed PM)
target: ~4,000 pairs · stratified across 10 deliverables
```

**Source D — `04_reit_listing_extract.py`**
```python
# Public REIT IR + listing patterns
sources:
  - SEC EDGAR 10-K + 8-K attachments (Realty Income · Spirit · NNN REIT · Agree)
  - public IR pages (PDF mirrors)
  - CoStar/LoopNet listing PATTERNS only (synthetic Granite rewrites · NEVER verbatim)
pipeline:
  1. fetch PDFs
  2. Granite-Docling → markdown
  3. Granite-Vision-4.1-4B (KVP) → deal_highlights
  4. pair the deal_highlights with the surrounding creative copy
  5. tag deliverable · emit JSONL
target: ~1,500 pairs
```

### Hard gates (every gate must pass)

1. ≥11,000 pairs after dedup
2. Dedup rate <1%
3. **Strict-input audit: 0 fabrications** (`06_strict_input_audit.py`)
4. **Think-tag scan: 0 occurrences · >1% kills batch** (`07_think_tag_scan.py`)
5. Stratification: each deliverable ≥800 pairs
6. Eval holdout: 500 pairs · 0 leaks
7. Schema check: every row valid

## Phase 2 · Tribunal (12 h)

```bash
# SCP hivecells to swarmrails
scp /tmp/swarm-nfs/atlas-bookmaker/v2/hivecells/bookmaker_hivecells_v2.jsonl \
    swarm@swarmrails:/data2/atlas-bookmaker/v2/

# Run dual-judge tribunal · existing infra
ssh swarm@swarmrails ./run_tribunal.sh \
    --input /data2/atlas-bookmaker/v2/bookmaker_hivecells_v2.jsonl \
    --judge-a gemma3:12b \
    --judge-b qwen2.5:32b \
    --rubric atlas-bookmaker-v2 \
    --output /data2/atlas-bookmaker/v2/judged.jsonl
```

Custom rubric (override defaults):
- 25% strict-input fidelity
- 20% brand voice fitness
- 20% deliverable structure
- 15% curb appeal
- 10% format completeness
- 10% no brand drift

Tier emit: ≥0.85 royal-jelly · ≥0.70 honey · ≥0.50 propolis · <0.50 receipts only.

**Gate:** royal-jelly ≥7,500 · if under, relax to ≥6,000 + 2,000 honey.

## Phase 3 · Cook (1.5 h)

See [`recipes/recipe_4_8b_hack_granite.md`](../recipes/recipe_4_8b_hack_granite.md) for the full locked recipe. Cook on smash 5090 with the v1 SCP+bash pattern (NOT ml-hack agent loop):

```bash
scp /tmp/swarm-nfs/atlas-bookmaker/v2/royal_jelly_combined.jsonl \
    smash:/home/smash/atlas-bookmaker_v2/corpus/train.jsonl

ssh smash@192.168.0.164 'source /home/smash/hack-cook-venv/bin/activate &&
    cd /home/smash/atlas-bookmaker_v2 &&
    python scripts/train_bookmaker_v2.py'
```

Gates: train loss in 0.30-0.42 deploy band · eval loss tracks within 0.05 · smoke ≥27/30 · 0 fabrications in smoke.

## Phase 5 · Orchestration

The 6 BeeAI tools wired in [`agent/main.py`](../agent/main.py):

```
voice memo ──► SpeechInTool      ─┐
PDF lease  ──► PdfParseTool       ├──► deal_highlights JSON
photo      ──► ImageExtractTool  ─┘            │
                                               ▼
                                      ComposeTool (cooked Granite-4.1-8B)
                                               │
                                               ▼
                                  StrictInputCheckTool (deterministic)
                                               │ pass
                                               ▼
                                       BrandGateTool (Granite-Guardian)
                                               │ pass
                                               ▼
                                          shipable creative
```

Inference-time guards (in order):
1. **`strict_input_check`** runs FIRST · deterministic regex/numeric audit · fabrication → regenerate (3 retries → `[TBD]` placeholder)
2. **`brand_gate`** runs SECOND · Granite-Guardian BYOC criteria · drift → regenerate (2 retries → refuse)

## Phase 7 · Ship

```bash
# 1. Hedera anchor
./deploy/anchor.sh atlas-bookmaker-v2

# 2. vLLM serve on smash:8089
ssh smash 'systemctl --user start atlas-bookmaker-vllm'

# 3. Cloudflare proxy update
# api.swarmandbee.ai/v1/atlas/bookmaker → smash:8089
gh workflow run deploy-bookmaker-route.yml
```

## What this pipeline does NOT do

1. Does NOT wire ml-hack agent loop · ml-hack stays separate
2. Does NOT introduce a new tribunal · reuses gemma3:12b + qwen2.5:32b
3. Does NOT delete v1 · archive only
4. Does NOT cook Granite-Speech or Granite-Docling · those ship as base
5. Does NOT run customer beta this window
