# ROADMAP — Atlas-Bookmaker v2 · Class-A Ship

> **Target ship: Sunday 2026-05-10**
> Source-of-truth plan: synthesized from the architect agent run on 2026-05-05.
> Foundation: Granite-Bee validated 12/0 on smash. Recipe transfers from v1 (Qwen 2.5 14B QLoRA · loss 0.30-0.42).

## Critical-path Gantt

| Day | Phase | Wall hours | Hard dependencies |
|---|---|---|---|
| **Tue night (2026-05-05)** | Phase 0 — Provenance & v1 quarantine | 0.5 h | none |
| **Wed AM** | Phase 1A · 1B (sources A+B) | 4 h | Phase 0 |
| **Wed PM** | Phase 1C · 1D (sources C+D) + Phase 4 vision corpus kickoff | 4 h | Phase 0 |
| **Wed late** | Phase 1.5–1.7 audits — strict-input · think-tag · dedup | 1 h | Phase 1A-D |
| **Wed → Thu** | Phase 2 tribunal on swarmrails | ~12 h overnight | Phase 1 done |
| **Thu PM** | Phase 2 tier emit + 7,500-royal-jelly gate | 1 h | Phase 2 |
| **Thu PM → Fri AM** | Phase 3 — Granite-4.1-8B QLoRA cook on smash | 1.5 h cook + ~3 h smoke | Phase 2 royal-jelly tier |
| **Fri** | Phase 4 — Granite-Vision-4.1-4B QLoRA + tribunal | 4 h | Phase 4 corpus |
| **Sat AM** | Phase 5 — BeeAI orchestrator wiring | 4 h | Phase 3 |
| **Sat PM** | Phase 6 — eval rubric run | 2 h | Phase 5 |
| **Sun AM** | Phase 7 — ship (Hedera anchor + endpoint deploy) | 3 h | Phase 6 pass |

## Phases

### Phase 0 — Provenance & v1 quarantine (30 min)
- Move v1 corpora to `/tmp/swarm-nfs/atlas-bookmaker/v1_archive/` with README marking DO NOT TRAIN
- Create `/tmp/swarm-nfs/atlas-bookmaker/v2/{raw,hivecells,live_cook,judged,royal_jelly,propolis,honey,stamped,receipts}/` mirroring aviation cook layout
- Drop `v2/CANONICAL.md` stub matching `aviation/CANONICAL.md` shape

**Gate:** v1 not auto-resolvable by any cook script · v2 directory tree matches aviation pattern.

### Phase 1 — Corpus build pipeline (10 h wall · mostly automated)

**Target:** 12,000 pairs stratified across 10 deliverables · ≥7,500 royal-jelly post-tribunal.

| Source | Volume | Shape | Owner |
|---|---|---|---|
| **A — Marketing honey extract** (`swarmmarket_honey.jsonl` · `swarmmarket_v2.jsonl`) | ~3,000 | Direct creative copy · system-prompt rewrite to Bookmaker v2 | `01_extract_marketing.py` |
| **B — CRE honey strict-input flip** (`cre_honey_stamped.jsonl`) | ~3,500 | Extract numbers → repackage as `deal_highlights` JSON; assistant references but never computes | `02_flip_cre_to_strict_input.py` |
| **C — Synthetic Granite + Claude diversity** | ~4,000 | 10 deliverable templates × 400 each · stratified · 80% Granite-4.1-8B · 20% Claude Opus diversity | `03_bookmaker_grinder.py` |
| **D — Public REIT/listing corpus** | ~1,500 | Realty Income · Spirit · NNN REIT · Agree decks + synthetic CoStar/LoopNet patterns | `04_reit_listing_extract.py` |

**QC scripts (every pair must pass):**
- `05_merge_dedup.py` · concatenate · run `hive.validate` over union
- `06_strict_input_audit.py` · **firm-doctrine gate** · every number in output must appear in input
- `07_think_tag_scan.py` · kill if `<think>` in assistant content (>1% contamination kills batch)
- `08_emit_hivecells.py` · final hivecells JSONL → `bookmaker_hivecells_v2.jsonl`

**Gates:**
1. ≥11,000 pairs after dedup
2. Dedup rate <1%
3. Strict-input audit: 0 fabrications
4. Think-tag scan: 0 occurrences
5. Stratification: each deliverable ≥800 pairs
6. Eval holdout: 500 pairs · 0 leaks
7. Schema check: all rows valid

### Phase 2 — Tribunal grading (~12 h overnight)
- SCP hivecells to swarmrails: `scp ... swarmrails:/data2/atlas-bookmaker/v2/`
- Dual-judge tribunal: `gemma3:12b` (GPU0) + `qwen2.5:32b` (GPU1) · weighted 50/50
- Custom rubric (override defaults · this is critical):
  - 25% strict-input fidelity
  - 20% brand voice fitness
  - 20% deliverable structure
  - 15% curb appeal
  - 10% format completeness
  - 10% no brand drift / slop
- Tier emit: ≥0.85 royal-jelly · ≥0.70 honey · ≥0.50 propolis · <0.50 receipts only

**Gate:** royal-jelly ≥7,500 · if under, relax to ≥6,000 + 2,000 honey (firm precedent: aviation 7,980 was enough).

### Phase 3 — Granite-4.1-8B QLoRA cook (1.5 h cook + 3 h smoke)

**Recipe (locked · transfers from v1 with base swap):**
- Base: `/home/smash/granite/granite-4.1-8b/` (validated 12/0)
- LoRA: r=32 · alpha=16 · dropout=0.05
- Quant: 4-bit nf4 · bf16 compute · double-quant
- Targets: q_proj · k_proj · v_proj · o_proj · gate_proj · up_proj · down_proj (validated present)
- Optimizer: paged_adamw_8bit · lr=1e-5 · cosine · warmup 50 steps
- Batch: per_device=1 · grad_accum 8 (eff. 8)
- Seq len: 4096 (creative pairs run long)
- Epochs: 1 (proven on v1 · loss lands 0.30-0.42 deploy band)
- Save: every 200 steps · keep last 3
- Eval: 500-pair holdout · every 500 steps

**Cook venue:** smash @ 192.168.0.164 · manual SCP+bash workflow · NOT ml-hack agent loop.

**Gates:**
1. Train loss in 0.30-0.42 deploy band
2. Eval loss tracks within 0.05 of train (no overfit)
3. Smoke: 30 prompts · 5 per top-6 deliverables · ≥27/30 pass with 0 fabricated numbers
4. Strict-input regression: re-run `06_strict_input_audit.py` over smoke outputs · 0 fabrications

### Phase 4 — Granite-Vision-4.1-4B QLoRA (parallel · can slip to Mon)

**Corpus:** 3,000-5,000 vision pairs across 4 doc types:
- Rent rolls (~1,000) · T-12 statements (~1,000) · STNL leases (~700) · ALTA surveys (~600) · property photos (~700)

**Sources:** Public SEC 10-K rent roll exhibits · EDGAR lease filings · public ALTA samples · public broker MLS feeds.

**Cook venue:** smash 5090 AFTER Phase 3 cook completes (Friday onward) · 4B base fits comfortably · LoRA recipe identical to Phase 3.

**Gate:** smoke 30 docs across 4 types · field-level F1 ≥0.90 on rent-roll/T-12 numerical extraction.

**Critical-path note:** Vision is NOT on the writer's critical path. Ship writer Sun, Vision Mon if needed.

### Phase 5 — BeeAI orchestrator wiring (4 h)

One agent fronting all 5 Granite models · `agent/main.py` · BeeAI `ReActAgent`.

**Tools:**
- `tool_speech_in(audio_path) → text` · Granite-Speech-4.1-2B
- `tool_pdf_parse(pdf_path) → markdown_doc` · Granite-Docling-258M
- `tool_image_extract(img_path, schema) → dict` · Granite-Vision-4.1-4B (cooked)
- `tool_compose(deal_highlights, deliverable, brand_pack, template) → markup` · Granite-4.1-8B (cooked)
- `tool_brand_gate(text, deliverable) → {pass, score, drift}` · Granite-Guardian-4.1-8B
- `tool_strict_input_check(deal_highlights, generated_text) → {fabricated: list}` · deterministic regex/numeric (NOT a model call)

**Inference-time guard sequence:**
1. User submits voice/PDF/photo + brief → Speech/Docling/Vision normalize to deal_highlights
2. Compose tool generates creative copy
3. **strict_input_check runs first** (deterministic) · any fabrication → regenerate · 3 retries → `[TBD]` placeholder
4. **brand_gate runs second** (Guardian) · drift → regenerate · 2 retries → refuse
5. Output ships only after both pass

### Phase 6 — Eval rubric run (2 h · hand-graded)

**Eval suite:** 100 prompts · 10 per deliverable type · curated from realistic deal-highlights inputs.

**Rubric (5 dimensions · 1-5 each):**
1. Strict-input fidelity (zero fabrication; 5/5 floor)
2. Curb appeal / sells the trophy
3. Brand voice (broker vocab)
4. Deliverable structure / template fit
5. Ready-to-ship polish

**Pass:** mean ≥4.2/5 across 100 prompts AND zero fabrications across all 100.

**Comparison cohort:** run identical eval against v1 archived adapter to prove v2 beat v1.

### Phase 7 — Ship (3 h)

| Step | Artifact |
|---|---|
| 7.1 | Hedera anchor merged adapter sha256 + corpus fingerprint + eval summary to topic 0.0.10291838 |
| 7.2 | vLLM serve on smash:8089 with `atlas-bookmaker-v2` adapter against Granite-4.1-8B base |
| 7.3 | `/v1/atlas/bookmaker` endpoint on api.swarmandbee.ai proxies to smash:8089 |
| 7.4 | Update `v2/CANONICAL.md` with corpus hash · adapter hash · Hedera receipt · eval summary |
| 7.5 | Update v1 archive README to point at v2 as superseder |

## What this plan does NOT do

1. Does NOT wire ml-hack agent loop · ml-hack stays a separate workstream
2. Does NOT introduce a new tribunal stack · reuses gemma3:12b + qwen2.5:32b on swarmrails
3. Does NOT delete v1 · archive only
4. Does NOT cook a new judge model · Granite-Guardian is inference-time gate
5. Does NOT guarantee Vision ships Sunday · Vision can slip to Mon
6. Does NOT design for v3 · ship one thing: Class-A v2 Bookmaker
7. Does NOT fine-tune Granite-Speech or Granite-Docling · those ship as base
8. Does NOT run customer beta this window · endpoint live Sun · customer rollout is separate decision

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Source B role-flip script malformed JSON | M | H | Hand-validate 50 transformed pairs before scaling · drop to 1,500 if <80% clean |
| Strict-input audit kills >40% of pairs | M | H | Rerun source-C with stricter system prompt forcing `[TBD]` |
| Tribunal returns <7,500 royal-jelly | M | M | Relax to ≥6,000 + top-2,000 honey · aviation precedent supports |
| Granite-8B cook loss diverges (>0.6 at step 1000) | L | H | Stop · halve LR to 1e-4 · restart |
| Smoke eval fails fabrication test | M | H | Inference-time strict_input_check is safety net · slips ship 1d |
| Vision corpus underdelivers | M | L | Ship writer alone Sun · Vision Mon |
| Anthropic API budget shortfall | L | L | Use Atlas-70B fallback when it ships Wed PM |
| smash GPU contention | L | L | Confirmed: hack-bot/signal-swarm CPU-only |
