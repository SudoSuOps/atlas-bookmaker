# Recipe #4 · QLoRA r=32 alpha=16 · Granite-4.1-8B (LOCKED)

> **Hack-fleet primary tier.** Atlas-Bookmaker v2 is the first cook on this recipe.
> Validated 2026-05-05 · transfers cleanly from prior Qwen 2.5 14B v1 cook (loss 0.30-0.42 deploy band).

## Locked configuration

| Setting | Value | Source / rationale |
|---|---|---|
| **Base model** | `ibm-granite/granite-4.1-8b` | Validated 12/0 on smash · arch `GraniteForCausalLM` · 128K ctx · 8.38B params · BFCL 68 tool-calling · respects strict-input rule natively |
| **Quantization** | 4-bit nf4 + double-quant | Standard QLoRA · BitsAndBytes |
| **Compute dtype** | bf16 | sm_120 Blackwell native |
| **LoRA rank** | r=32 | Same as v1 · sweet spot for 8B |
| **LoRA alpha** | 16 | scaling = alpha / r = 0.5 |
| **LoRA dropout** | 0.05 | regularization · prevents overfit on 12K-pair corpus |
| **Bias** | "none" | LoRA-only |
| **Task type** | "CAUSAL_LM" | |
| **target_modules** | `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` | All 7 validated present in Granite-4.1-8B (Test 3 of validation suite) |
| **Optimizer** | `paged_adamw_8bit` | memory-efficient · proven on v1 |
| **Learning rate** | 1e-5 | conservative · cosine schedule |
| **LR scheduler** | cosine | proven on Atlas-27B / Curator-27B / v1 Bookmaker |
| **Warmup steps** | 50 | |
| **Weight decay** | 0.0 | LoRA doesn't need it |
| **Max grad norm** | 1.0 | clip-norm |
| **Batch size (per device)** | 1 | with grad_accum = 8 → effective batch 8 |
| **Gradient accumulation** | 8 | |
| **Max sequence length** | 4096 | OM booklets fill context · longer than v1's 2048 |
| **Epochs** | 1 | proven on v1 · loss lands deploy band in 1 epoch |
| **Save steps** | 200 | |
| **Save total limit** | 4 | keep last 4 checkpoints |
| **Evaluation steps** | 500 | 500-pair holdout · loss-only metric (rubric eval is post-cook) |
| **Logging** | trackio · `disable_tqdm=True` · `logging_strategy="steps"` · `logging_first_step=True` | grep-able plain text |
| **bf16 mixed precision** | True | |
| **Gradient checkpointing** | True · `use_reentrant=False` | |
| **Attention impl** | `eager` (default) · sdpa works too | tested in v1 validation |
| **Trackio project** | `bookmaker-fleet` | shared with Hack-fleet (future Hacks live here too) |
| **Run name** | `atlas-bookmaker-v2-2026-05-08` (or date of cook) | descriptive |

## Cook venue

**smash @ 192.168.0.164** (RTX 5090 · 32GB · sm_120)

| | v1 (Qwen 2.5 14B) | v2 (Granite-4.1-8B) |
|---|---|---|
| Total params | 14B | 8.38B |
| 4-bit weights | ~10 GB | ~5 GB |
| LoRA trainable | 137.6M (1.66%) | ~85M (1.01%) — needs verification at first cook |
| VRAM peak (training) | 21 GB | ~14-16 GB (estimate · 60% of v1) |
| Step time | 5.5 s | ~3-4 s (estimate · Granite is 2× speed at inference, training ratio TBD) |
| Cook time (12K pairs · 1 epoch · eff batch 8 = ~1500 steps) | 2h 21m actual | **~1.5h estimate** |

## Cook artifacts on smash

```
/home/smash/atlas-bookmaker_v2/
├── base/                    → symlink → /home/smash/granite/granite-4.1-8b/
├── corpus/
│   ├── train.jsonl          ← royal-jelly + honey union · fingerprint-deduped vs eval
│   └── eval.jsonl           ← 500 pairs · stratified across 10 deliverables
├── checkpoints/
│   ├── checkpoint-200/
│   ├── checkpoint-400/
│   ├── ...
│   └── final/               ← terminal LoRA adapter (~150 MB)
├── merged/
│   └── atlas-bookmaker-v2/  ← post-merge weights for vLLM serve (~16 GB)
├── logs/
│   ├── train.log
│   └── auditor-*.log        ← cook auditor 3h cron output
└── scripts/
    ├── train_bookmaker_v2.py
    ├── smoke.py             ← 30-prompt eval (5 per top-6 deliverables)
    └── cook_auditor.sh      ← same pattern as Atlas-70B cook auditor
```

## Cook gates (every gate must pass before next phase)

1. **Train loss in 0.30–0.42 deploy band** at end of epoch 1 (proven on v1 · same band expected)
2. **Eval loss tracks within 0.05 of train** (no overfit hint)
3. **Smoke eval passes** (30 prompts · 5 per top-6 deliverables · ≥27/30 with 0 fabricated numbers)
4. **Strict-input regression** (re-run `06_strict_input_audit.py` over smoke outputs · 0 fabrications)
5. **Cook auditor confirms zero kill-switch trips** (think-tag contamination <1% throughout cook)

## Recipe deviation policy

Per `ml-hack/AGENTS.md`: deviation from a locked recipe requires **written justification in the cook log**. Examples of approved deviations from this recipe:

- **LR halve to 1e-4** if loss diverges (>0.6 train at step 1000) — record in `logs/train.log` with reason
- **r=64 alpha=32** if r=32 underfits (loss plateau >0.45) — needs a separate ablation cook log

## Comparison to other recipes in the firm cookbook

| Recipe | Model class | Cook venue | Use case |
|---|---|---|---|
| Recipe #1 — FSDP-QLoRA bf16 | 70B (Llama 3.3) | swarmrails 2× PRO 6000 | Atlas-tier Senior MD · in-flight cook (2026-05-03 → 2026-05-07) |
| Recipe #2 — LoRA r=64 alpha=32 | 27B specialist | swarmrails 1× PRO 6000 | SwarmAtlas-27B · CreditSniper-27B · SwarmCurator-27B |
| Recipe #3 — QLoRA r=32 alpha=16 | 9B Hack-fleet next-tier | smash 5090 / swarmrails | SwarmCurator-9B (deployed) |
| **Recipe #4 — QLoRA r=32 alpha=16 · Granite-4.1-8B** | **8B Hack-fleet primary** | **smash 5090** | **Atlas-Bookmaker v2 · all Hacks (Hack-DG · Hack-Auto · Hack-QSR · Hack-Dialer · Hack-Closer)** |

**Recipe #4 is the new firm default** for Bookmaker + Hack-fleet specialists. Apache 2.0 base + same recipe cleanly across N adapters · operationally unfragmented.

## References

- v1 cook receipt: `/home/smash/atlas-bookmaker_v1_archive/checkpoints/final/`
- Validation receipt: `~/.claude/projects/-home-swarm-Desktop/memory/granite_bee_validation_2026_05_05.md`
- Stack doctrine: `~/.claude/projects/-home-swarm-Desktop/memory/granite_bee_stack_doctrine.md`
- Role doctrine: `~/.claude/projects/-home-swarm-Desktop/memory/bookmaker_role_doctrine.md`
- Aviation cook precedent (template): `/tmp/swarm-nfs/swarm-and-bee-datasets/aviation/`
