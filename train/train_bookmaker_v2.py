#!/usr/bin/env python3
"""
train_bookmaker_v2.py · cook Atlas-Bookmaker v2 on Granite-4.1-8B.

Recipe #4 (LOCKED · see recipes/recipe_4_8b_hack_granite.md):
  - Base: ibm-granite/granite-4.1-8b · validated 12/0 on smash 2026-05-05
  - QLoRA r=32 alpha=16 dropout=0.05
  - 4-bit nf4 + bf16 compute · double-quant
  - target_modules: q_proj k_proj v_proj o_proj gate_proj up_proj down_proj
  - LR 1e-5 cosine · warmup 50 steps · grad_accum 8 (eff. batch 8)
  - max_length 4096 · 1 epoch
  - Cook venue: smash 5090 · ~1.5h on 12K pairs

Recipe transferred cleanly from v1 (Qwen 2.5 14B QLoRA · loss 0.30-0.42 deploy band).

Usage:
    python train_bookmaker_v2.py                  # full cook
    python train_bookmaker_v2.py --smoke          # 100 pairs, 20 steps
    python train_bookmaker_v2.py --resume <ckpt>  # resume from checkpoint
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from trl import SFTConfig, SFTTrainer

# ─── Locked paths ────────────────────────────────────────────────────────────
BASE = os.environ.get("GRANITE_LLM", "/home/smash/granite/granite-4.1-8b")
CORPUS_DIR = "/home/smash/atlas-bookmaker_v2/corpus"
TRAIN_JSONL = f"{CORPUS_DIR}/train.jsonl"
EVAL_JSONL  = f"{CORPUS_DIR}/eval.jsonl"
OUTPUT_DIR  = "/home/smash/atlas-bookmaker_v2/checkpoints"
LOGS_DIR    = "/home/smash/atlas-bookmaker_v2/logs"
SESSION_ID  = "atlas-bookmaker-v2-2026-05-08"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke",  action="store_true", help="100 pairs · 20 steps · validate gradients")
    ap.add_argument("--resume", default=None,        help="Resume from checkpoint path")
    ap.add_argument("--corpus", default=TRAIN_JSONL)
    ap.add_argument("--eval",   default=EVAL_JSONL)
    ap.add_argument("--output", default=OUTPUT_DIR)
    return ap.parse_args()


def load_jsonl(path: str, limit: int | None = None) -> list[dict]:
    rows = []
    with open(path) as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            rows.append(json.loads(line))
    return rows


def main():
    args = parse_args()
    is_smoke = args.smoke
    Path(args.output).mkdir(parents=True, exist_ok=True)
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

    print(f"[{time.strftime('%H:%M:%S')}] {'SMOKE' if is_smoke else 'FULL'} cook · session={SESSION_ID}")
    print(f"  base:   {BASE}")
    print(f"  corpus: {args.corpus}")
    print(f"  output: {args.output}")

    # ─── Load corpus ─────────────────────────────────────────────────────────
    train_rows = load_jsonl(args.corpus, limit=100 if is_smoke else None)
    eval_rows  = load_jsonl(args.eval, limit=50 if is_smoke else None) if Path(args.eval).exists() else []
    print(f"  train:  {len(train_rows):,} pairs")
    print(f"  eval:   {len(eval_rows):,} pairs")

    # ─── Tokenizer ───────────────────────────────────────────────────────────
    print(f"\n[{time.strftime('%H:%M:%S')}] loading tokenizer …")
    tok = AutoTokenizer.from_pretrained(BASE, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    print(f"  vocab: {tok.vocab_size:,}")
    print(f"  chat_template embedded: {tok.chat_template is not None}")

    def render(example):
        text = tok.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)
        return {"text": text}

    train_ds = Dataset.from_list(train_rows).map(render, remove_columns=list(train_rows[0].keys()))
    eval_ds  = Dataset.from_list(eval_rows).map(render, remove_columns=list(eval_rows[0].keys())) if eval_rows else None

    # ─── 4-bit nf4 base model ────────────────────────────────────────────────
    print(f"\n[{time.strftime('%H:%M:%S')}] loading base in 4-bit nf4 …")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        BASE,
        quantization_config=bnb,
        device_map="cuda:0",
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
        attn_implementation="eager",
    )
    print(f"  loaded in {time.time() - t0:.1f}s · vram alloc {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    model.config.use_cache = False
    model.config.pretraining_tp = 1
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    # ─── LoRA · Recipe #4 ────────────────────────────────────────────────────
    lora_cfg = LoraConfig(
        r=32,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_cfg)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  LoRA trainable: {trainable / 1e6:.1f}M / total {total / 1e9:.2f}B  ({100 * trainable / total:.3f}%)")

    # ─── SFT config ──────────────────────────────────────────────────────────
    sft_cfg = SFTConfig(
        output_dir=args.output,
        num_train_epochs=1,
        max_steps=20 if is_smoke else -1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=1e-5,
        lr_scheduler_type="cosine",
        warmup_steps=5 if is_smoke else 50,
        logging_steps=1 if is_smoke else 10,
        save_steps=100 if is_smoke else 200,
        save_total_limit=4,
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_8bit",
        max_length=4096,
        dataset_text_field="text",
        report_to="none",
        run_name=f"{SESSION_ID}-{'smoke' if is_smoke else 'full'}",
        seed=42,
        eval_strategy="steps" if eval_ds else "no",
        eval_steps=500 if eval_ds and not is_smoke else None,
        per_device_eval_batch_size=1,
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        args=sft_cfg,
        processing_class=tok,
    )

    # ─── Train ───────────────────────────────────────────────────────────────
    print(f"\n[{time.strftime('%H:%M:%S')}] starting training · {'smoke' if is_smoke else 'full'} run …")
    t0 = time.time()
    trainer.train(resume_from_checkpoint=args.resume)
    elapsed = time.time() - t0
    print(f"\n[{time.strftime('%H:%M:%S')}] training done in {elapsed/60:.1f}min ({elapsed/3600:.2f}h)")
    print(f"  vram peak: {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")

    # ─── Save final adapter ──────────────────────────────────────────────────
    final = Path(args.output) / ("smoke" if is_smoke else "final")
    trainer.save_model(str(final))
    tok.save_pretrained(str(final))
    print(f"  ✓ adapter saved: {final}")


if __name__ == "__main__":
    main()
