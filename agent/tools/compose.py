#!/usr/bin/env python3
"""
agent/tools/compose.py · the writer tool.

Calls Granite-4.1-8B (the cooked Bookmaker LoRA adapter) via vLLM at smash:8089.
Generates creative copy from deal_highlights + deliverable + brand_pack.

This is the only tool that PRODUCES output. The other tools shape inputs
(speech, pdf, image) or gate outputs (strict_input_check, brand_gate).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

VLLM_URL = os.environ.get("VLLM_URL", "http://smash:8089/v1")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "atlas-bookmaker-v2")


def compose(
    deal_highlights: dict[str, Any],
    deliverable: str,
    brand_pack: str = "swarm_and_bee",
    template_id: str | None = None,
    max_tokens: int = 1500,
    temperature: float = 0.7,
) -> str:
    """Synchronous compose call to Granite-4.1-8B via vLLM."""
    from agent.prompts import load_system_prompt
    system_prompt = load_system_prompt()

    user_msg = (
        f"Brief: ship a {deliverable} for the deal below. Brand pack: {brand_pack}."
        f"{' Template: ' + template_id if template_id else ''}\n\n"
        f"deal_highlights = {deal_highlights}\n\n"
        f"Strict-input rule applies. Use ONLY the values given. "
        f"For any missing value, write [TBD: <field>]."
    )

    payload = {
        "model": VLLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.9,
    }
    r = httpx.post(f"{VLLM_URL}/chat/completions", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


class ComposeTool:
    name = "compose"
    description = (
        "Generate creative copy (one of 10 deliverables) from a deal_highlights "
        "JSON and brand_pack. Returns the markup ready for layout. "
        "Calls the cooked Granite-4.1-8B Bookmaker adapter."
    )

    def run(
        self,
        deal_highlights: dict[str, Any],
        deliverable: str,
        brand_pack: str = "swarm_and_bee",
        template_id: str | None = None,
    ) -> str:
        return compose(deal_highlights, deliverable, brand_pack, template_id)
