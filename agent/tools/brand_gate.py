#!/usr/bin/env python3
"""
agent/tools/brand_gate.py · Granite-Guardian-4.1-8B brand-drift gate.

Runs SECOND (after strict_input_check). Uses BYOC (Bring Your Own Criteria)
prompt-shaped binary classification. If brand drifts (e.g. "as-a-Service",
"agent", "Marcus & Millichap"), regenerate · 2 retries · then refuse.

Reference: https://huggingface.co/ibm-granite/granite-guardian-4.1-8b
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

VLLM_URL = os.environ.get("VLLM_URL", "http://smash:8089/v1")
GUARDIAN_MODEL = os.environ.get("GUARDIAN_MODEL", "granite-guardian-4.1-8b")

JUDGE_PREFIX = (
    "<no-think>As a judge agent, assess whether the provided text meets the "
    "given judging criteria. Output empty <think>\\n</think> tags followed by "
    "your score in <score></score> tags."
)

# Brand-drift criteria · firm-locked · matches DOCTRINE.md + system_v2.yaml
BRAND_DRIFT_CRITERIA = (
    "The assistant text references competing brokerages, mentions specific firm "
    "names other than 'Swarm & Bee' or 'Atlas', uses tech-vendor language like "
    "'as-a-Service', 'platform', 'tool', 'agent', 'fine-tune', 'SaaS' instead of "
    "'Atlas-as-a-Closer', 'Hack', 'Bookmaker', 'cook', 'MAGIC', 'Defendable', "
    "'Pass/Proceed' framing. Also flag any 'as an AI' or 'I'm sorry' style "
    "AI-self-reference, or any reference to 'Marcus & Millichap', 'M&M', or "
    "'Caballerz Network LLC' (firm legal entity · never customer-facing)."
)


def guard_block(criteria: str) -> str:
    return (
        f"<guardian>{JUDGE_PREFIX}\n\n"
        f"### Criteria: {criteria}\n\n"
        f"### Scoring Schema: If the last assistant's text DRIFTS from the criteria "
        f"(violates the brand rules), return 'yes'; otherwise 'no'."
    )


def check_brand_drift(
    user_msg: str,
    draft_output: str,
    criteria: str = BRAND_DRIFT_CRITERIA,
) -> dict[str, Any]:
    """Returns {'drift': bool, 'score': str, 'raw': str}."""
    chat = [
        {"role": "user",      "content": user_msg},
        {"role": "assistant", "content": draft_output},
        {"role": "user",      "content": guard_block(criteria)},
    ]
    payload = {
        "model": GUARDIAN_MODEL,
        "messages": chat,
        "max_tokens": 2048,
        "temperature": 0,
    }
    r = httpx.post(f"{VLLM_URL}/chat/completions", json=payload, timeout=60)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    m = re.findall(r"<score>\s*(.*?)\s*</score>", text, re.DOTALL)
    score = (m[0].strip().lower() if m else "")
    return {
        "drift": score == "yes",
        "score": score,
        "raw": text,
    }


class BrandGateTool:
    name = "brand_gate"
    description = (
        "Run Granite-Guardian-4.1-8B brand-drift check on the latest draft. "
        "Returns {'drift': bool, 'score': str}. If drift=True, regenerate with "
        "tighter brand voice. Always run AFTER strict_input_check."
    )

    def run(self, user_msg: str, draft: str, criteria: str | None = None) -> dict[str, Any]:
        return check_brand_drift(user_msg, draft, criteria or BRAND_DRIFT_CRITERIA)
