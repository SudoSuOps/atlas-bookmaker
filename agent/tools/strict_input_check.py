#!/usr/bin/env python3
"""
agent/tools/strict_input_check.py · the firm-doctrine inference-time gate.

Deterministic numeric/regex audit. Runs BEFORE Granite-Guardian. If the writer
fabricates ANY number not in the deal_highlights input, this tool fails and
the agent regenerates.

This is a LAYER-3 defense (corpus audit → cook discipline → inference gate).
The agent will retry up to 3 times. After 3 failures, the agent must emit
[TBD: <field>] placeholders.

NO MODEL CALLS — pure regex/comparison. Fast (microseconds).
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

# Reuse the patterns from corpus/scripts/06_strict_input_audit.py
# (one source of truth for what counts as a "number")
NUMERIC_PATTERNS = [
    re.compile(r"\$[\d,]+(?:\.\d+)?[MKB]?"),
    re.compile(r"\d+(?:\.\d+)?%"),
    re.compile(r"\b(?:19|20)\d{2}\b"),
    re.compile(r"\b\d{1,3}(?:,\d{3})*\s*SF\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*acres?\b", re.IGNORECASE),
    re.compile(r"\bDSCR[:\s]+\d+(?:\.\d+)?x?\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}-?\s*yr\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s+years?\s+remaining\b", re.IGNORECASE),
    re.compile(r"\bNOI[:\s]+\$[\d,]+(?:\.\d+)?[MKB]?\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}(?:\.\d+)?%\s+(?:bumps?|escalation)\b", re.IGNORECASE),
]

ALWAYS_ALLOWED = {
    "0.0.10291838",  # Hedera deed anchor topic
    "0.0.10291827",  # Hedera operator
    "$0.0008",       # publish cost
    "$0.0052",       # cost-to-mint per deed
    "1031",          # exchange code
    "2026",          # current year
}


def extract_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for pat in NUMERIC_PATTERNS:
        for m in pat.findall(text):
            out.add(re.sub(r"\s+", " ", m.strip().upper()))
    return out


def normalize(tok: str) -> str:
    return re.sub(r"\s+", "", tok.upper().replace(",", ""))


# ─── BeeAI Tool wrapper ──────────────────────────────────────────────────────


class StrictInputCheckInput(BaseModel):
    deal_highlights: dict[str, Any] = Field(
        description="The structured deal data the Hack provided · numbers locked"
    )
    generated_text: str = Field(
        description="The Bookmaker's draft creative output · about to ship"
    )


class StrictInputCheckOutput(BaseModel):
    pass_check: bool = Field(description="True = no fabrications · safe to ship")
    fabricated_tokens: list[str] = Field(default_factory=list)
    advice: str = Field(default="")


def run_strict_input_check(deal_highlights: dict[str, Any], generated_text: str) -> StrictInputCheckOutput:
    """Pure-Python check · no model call."""
    user_text = "\n".join(str(v) for v in deal_highlights.values() if v is not None)
    user_tokens = {normalize(t) for t in extract_tokens(user_text)} | {normalize(t) for t in ALWAYS_ALLOWED}
    asst_tokens = extract_tokens(generated_text)

    fabricated: list[str] = []
    for t in asst_tokens:
        if normalize(t) in user_tokens:
            continue
        # Allow if appears near "[TBD" marker
        idx = generated_text.upper().find(t.upper())
        if idx >= 0:
            ctx = generated_text[max(0, idx - 30):idx + 30].upper()
            if "TBD" in ctx:
                continue
        fabricated.append(t)

    if fabricated:
        return StrictInputCheckOutput(
            pass_check=False,
            fabricated_tokens=fabricated,
            advice=(
                f"You fabricated these numbers: {fabricated}. "
                f"Use ONLY the values in deal_highlights. If a value is missing, "
                f"write [TBD: <field>]. Regenerate with the correct values or [TBD] placeholders."
            ),
        )
    return StrictInputCheckOutput(pass_check=True)


# ─── BeeAI Tool subclass (signature TBD · matches beeai-framework Tool API) ──


class StrictInputCheckTool:
    """BeeAI Tool wrapper. The actual subclass signature depends on beeai-framework version.

    NOTE: Verify the BeeAI Tool[Input, Output, Options] API on the installed package
    before final wire-up. The Plan agent flagged: `python -c "from beeai_framework.tools import Tool; help(Tool)"`.

    For v0.2.0, this stub returns the validated function. The tool surface in BeeAI
    will be wired in BV2-7.
    """

    name = "strict_input_check"
    description = (
        "Run a deterministic audit: every number in the generated text must "
        "appear in deal_highlights. If anything was fabricated, reject and ask "
        "the writer to regenerate with [TBD: <field>] for missing values. "
        "Always run BEFORE brand_gate."
    )

    def run(self, deal_highlights: dict[str, Any], generated_text: str) -> dict[str, Any]:
        result = run_strict_input_check(deal_highlights, generated_text)
        return result.model_dump()


if __name__ == "__main__":
    # Self-test
    sample_input = {
        "asset_class": "Dollar General STNL",
        "market": "Tampa FL",
        "price": "$2.4M",
        "cap_rate": "6.85%",
        "tenant_credit": "BBB / IG",
    }
    bad_output = "$2.4M Dollar General STNL · Tampa FL · 6.85% cap · 8,710 SF building."  # 8,710 SF fabricated
    good_output = "$2.4M Dollar General STNL · Tampa FL · 6.85% cap · [TBD: SF] building."

    print("Test 1 · fabricated SF (should fail):")
    print(run_strict_input_check(sample_input, bad_output).model_dump_json(indent=2))
    print("\nTest 2 · TBD placeholder (should pass):")
    print(run_strict_input_check(sample_input, good_output).model_dump_json(indent=2))
