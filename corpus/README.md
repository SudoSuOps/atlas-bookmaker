# corpus/

Build pipeline for Atlas-Bookmaker v2 training corpus. **Mirrors the aviation cook pattern verbatim** (proven on 8,662 pairs with full Hedera receipts).

## Target

12,000 pairs · stratified across 10 deliverables · ≥7,500 royal-jelly post-tribunal.

| Source | Volume | Description | Script |
|---|---|---|---|
| **A · Marketing honey extract** | ~3,000 | Direct creative copy from `swarmmarket_honey.jsonl` + `swarmmarket_v2.jsonl` · system-prompt rewrite to Bookmaker v2 | `01_extract_marketing.py` |
| **B · CRE honey strict-input flip** | ~3,500 | Extract numbers from `cre_honey_stamped.jsonl` IC memos · repackage as `deal_highlights` JSON · cook creative output | `02_flip_cre_to_strict_input.py` (LOAD-BEARING) |
| **C · Synthetic Granite + Claude** | ~4,000 | 10 deliverable templates × 400 pairs each · Granite-4.1-8B teacher (80%) + Claude diversity (20%) | `03_bookmaker_grinder.py` |
| **D · Public REIT/listing** | ~1,500 | Realty Income · Spirit · NNN REIT · Agree decks (SEC EDGAR public) + synthetic CoStar/LoopNet patterns | `04_reit_listing_extract.py` |

## Pipeline

```
                     A · marketing extract                 B · CRE flip
                     C · synth grinder                     D · REIT decks
                              │                                    │
                              ▼                                    ▼
                ┌───────── 05_merge_dedup.py ──────────────────────┐
                │  fingerprint = sha256(messages) · drop dupes      │
                └────────────────────┬─────────────────────────────┘
                                     │
                                     ▼
                     ┌─── 06_strict_input_audit.py ────┐
                     │  FIRM-DOCTRINE GATE             │
                     │  every number in output must    │
                     │  appear in input · or [TBD]     │
                     │  REJECT pairs that fabricate    │
                     └────────────────────┬────────────┘
                                          │
                                          ▼
                     ┌─── 07_think_tag_scan.py ────────┐
                     │  KILL SWITCH                     │
                     │  >1% <think> contamination →     │
                     │  rebuild from sources            │
                     └────────────────────┬────────────┘
                                          │
                                          ▼
                     ┌─── 08_emit_hivecells.py ────────┐
                     │  emit canonical hivecells       │
                     │  matches aviation schema +      │
                     │  deliverable field              │
                     └────────────────────┬────────────┘
                                          │
                                          ▼
              /tmp/swarm-nfs/atlas-bookmaker/v2/hivecells/
                bookmaker_hivecells_v2.jsonl
                     │
                     ▼
              SCP to swarmrails ─► tribunal (gemma3:12b + qwen2.5:32b)
                     │
                     ▼
              royal-jelly · honey · propolis · receipts
                     │
                     ▼
              merged train.jsonl ─► smash 5090 ─► QLoRA cook
```

## Hard gates (every gate must pass)

1. ≥11,000 pairs after dedup (10% headroom over 10K target)
2. Dedup rate <1%
3. Strict-input audit: **0 fabrications** (REJECT pairs · do not "fix")
4. Think-tag scan: **0 occurrences** (>1% kills batch)
5. Stratification: each of 10 deliverables ≥800 pairs
6. Eval holdout: 500 pairs · fingerprint-checked · **0 leaks vs train**
7. Schema check: every row has `messages`, `deliverable`, `fingerprint`, `lineage`

## Schemas

- [`schemas/deal_highlights.schema.json`](schemas/deal_highlights.schema.json) — Bookmaker INPUT shape (Hack-curated)
- [`schemas/pair.schema.json`](schemas/pair.schema.json) — training pair shape

## Source paths (NAS · read-only)

```bash
NAS=/tmp/swarm-nfs/swarm-and-bee-datasets

# Source A
$NAS/marketing/swarmmarket_honey.jsonl       # 10,027 pairs
$NAS/marketing/swarmmarket_v2.jsonl          #  5,447 pairs

# Source B
$NAS/cre/cre_honey_stamped.jsonl             # 810,097 pairs (mine ~3,500)

# Source D (downloaded fresh)
# - REIT IR pages · Realty Income · Spirit · NNN REIT · Agree (SEC EDGAR + IR PDF mirror)
# - CoStar/LoopNet listing patterns (synthetic only · no verbatim)
```

## Output paths (NAS · canonical layout · mirrors aviation)

```
/tmp/swarm-nfs/atlas-bookmaker/v2/
├── raw/
│   ├── source_a_marketing.jsonl
│   ├── source_b_flipped.jsonl
│   ├── source_c_synthetic.jsonl
│   └── source_d_reit.jsonl
├── hivecells/
│   └── bookmaker_hivecells_v2.jsonl     ← Phase 1 deliverable
├── live_cook/                            ← teacher LLM outputs
├── judged/                               ← post-tribunal
├── royal_jelly/                          ← top tier (≥0.85)
├── honey/                                ← (≥0.70)
├── propolis/                             ← (≥0.50)
├── receipts/                             ← Hedera anchors
├── stamped/                              ← post-cook deeded versions
└── CANONICAL.md                          ← provenance chain
```

## Risk mitigations (from Plan agent risk register)

| Risk | Mitigation |
|---|---|
| Source B role-flip JSON malformed | Hand-validate 50 transformed pairs · drop target to 1,500 if <80% clean |
| Strict-input audit kills >40% pairs | Rerun source-C with stricter teacher prompt forcing `[TBD]` |
| Tribunal returns <7,500 royal-jelly | Relax to ≥6,000 + top 2,000 honey (aviation precedent: 7,980 was enough) |
| Anthropic API budget shortfall | Fallback to Atlas-70B once it ships Wed PM |
| CoStar/LoopNet copyright | Source D restricted to public REIT decks + synthetic-pattern Granite rewrites |
