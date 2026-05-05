#!/usr/bin/env python3
"""
agent/tools/image_extract.py · property photos + charts → structured JSON.

Calls Granite-Vision-4.1-4B (cooked CRE-extraction adapter from Phase 4).

Task tags supported (per IBM model card):
  <chart2csv>  <chart2code>  <chart2summary>
  <tables_json>  <tables_html>  <tables_otsl>
  KVP via JSON-schema prompts
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

GRANITE_VISION = os.environ.get("GRANITE_VISION", "/home/smash/granite/granite-vision-4.1-4b")
VISION_ADAPTER = os.environ.get("VISION_ADAPTER", "/home/smash/atlas-bookmaker_v2/checkpoints/vision_final")

_MODEL = None
_PROCESSOR = None


def _ensure_loaded():
    global _MODEL, _PROCESSOR
    if _MODEL is None:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        _PROCESSOR = AutoProcessor.from_pretrained(GRANITE_VISION, trust_remote_code=True)
        _PROCESSOR.tokenizer.padding_side = "left"
        _MODEL = AutoModelForImageTextToText.from_pretrained(
            GRANITE_VISION,
            trust_remote_code=True,
            dtype=torch.bfloat16,
            device_map="cuda:0",
        ).eval()
        # TODO · attach Phase-4 vision adapter via PEFT
    return _MODEL, _PROCESSOR


def extract(image_path: str | Path, schema: dict[str, Any] | str) -> dict[str, Any]:
    """Extract structured data from an image · returns dict matching schema."""
    import torch
    from PIL import Image

    model, processor = _ensure_loaded()
    img = Image.open(str(image_path)).convert("RGB")

    if isinstance(schema, dict):
        prompt = (
            f"Extract structured data from this image.\n"
            f"Return a JSON object matching this schema:\n\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            f"Return null for fields you cannot find. Return ONLY valid JSON."
        )
    else:
        prompt = schema  # task-tag mode

    conv = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
    text = processor.apply_chat_template(conv, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[img], return_tensors="pt", padding=True, do_pad=True).to("cuda:0")

    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=4096, use_cache=True)
    raw = processor.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    try:
        return {"data": json.loads(raw), "raw": raw}
    except json.JSONDecodeError:
        return {"data": None, "raw": raw, "error": "json parse failed"}


class ImageExtractTool:
    name = "image_extract"
    description = (
        "Extract structured data from an image (property photo, chart, table) "
        "using Granite-Vision-4.1-4B. Pass a JSON schema (dict) for KVP extraction "
        "or a task tag string like '<chart2csv>'. Returns dict with 'data' + 'raw'."
    )

    def run(self, image_path: str, schema: dict[str, Any] | str) -> dict[str, Any]:
        return extract(image_path, schema)
