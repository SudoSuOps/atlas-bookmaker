#!/usr/bin/env python3
"""
agent/main.py · BeeAI orchestrator for Atlas-Bookmaker v2.

Composes all 5 Granite-Bee models behind one ReAct agent:
  - Granite-Speech-4.1-2B  → voice-to-text (input layer)
  - Granite-Docling-258M   → PDF parser (input layer)
  - Granite-Vision-4.1-4B  → photo + chart extraction (input layer)
  - Granite-4.1-8B (cooked) → the writer (compose tool)
  - Granite-Guardian-4.1-8B → brand-drift gate (output layer)

Inference-time guard sequence (THE ROLE LOCK at runtime):
  1. Inputs (voice/PDF/photo + brief) → Speech/Docling/Vision normalize to deal_highlights JSON
  2. compose_tool generates creative copy (Granite-4.1-8B cooked adapter)
  3. strict_input_check runs FIRST (deterministic) — fabrication → regenerate (3 retries)
  4. brand_gate runs SECOND (Guardian model) — drift → regenerate (2 retries)
  5. Output ships only after BOTH pass

Usage:
    python -m agent.main                          # interactive REPL
    python -m agent.main "ship an OM for ..."     # headless one-shot
    python -m agent.main --serve                  # FastAPI server on :7860
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# BeeAI Framework imports — Apache 2.0 · IBM-built
try:
    from beeai_framework.adapters.openai import OpenAIChatModel
    from beeai_framework.agents.react import ReActAgent
    from beeai_framework.memory import UnconstrainedMemory
    from beeai_framework.tools import Tool
except ImportError:
    print("ERROR: beeai-framework not installed. Run: uv sync", file=sys.stderr)
    sys.exit(1)

# Local tool implementations · 6 total
from agent.tools.brand_gate import BrandGateTool
from agent.tools.compose import ComposeTool
from agent.tools.image_extract import ImageExtractTool
from agent.tools.pdf_parse import PdfParseTool
from agent.tools.speech_in import SpeechInTool
from agent.tools.strict_input_check import StrictInputCheckTool


# ─── Configuration ───────────────────────────────────────────────────────────
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_v2.yaml"
VLLM_BASE_URL = os.environ.get("VLLM_URL", "http://smash:8089/v1")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "atlas-bookmaker-v2")


def load_system_prompt() -> str:
    import yaml
    return yaml.safe_load(SYSTEM_PROMPT_PATH.read_text())["system_prompt"]


def build_agent() -> ReActAgent:
    """Build the Bookmaker agent with all 6 tools wired."""

    # LLM · Granite-4.1-8B served by vLLM in OpenAI-compat mode on smash:8089
    llm = OpenAIChatModel(
        model=VLLM_MODEL,
        base_url=VLLM_BASE_URL,
        api_key="EMPTY",  # vLLM doesn't auth
    )

    # Tools — ORDER MATTERS · strict_input_check runs first, brand_gate second
    tools: list[Tool] = [
        SpeechInTool(),           # voice → text
        PdfParseTool(),           # PDF → markdown
        ImageExtractTool(),       # photo → JSON
        ComposeTool(),            # deal_highlights → creative copy
        StrictInputCheckTool(),   # deterministic fabrication gate (FIRST)
        BrandGateTool(),          # Granite-Guardian brand-drift gate (SECOND)
    ]

    agent = ReActAgent(
        llm=llm,
        tools=tools,
        memory=UnconstrainedMemory(),
        meta={"system_prompt": load_system_prompt()},
    )
    return agent


async def run_one_shot(prompt: str):
    """Headless single-shot mode."""
    agent = build_agent()
    result = await agent.run(prompt)
    print(result.text if hasattr(result, "text") else result)


async def run_repl():
    """Interactive REPL mode · the dial-floor desk."""
    agent = build_agent()
    print("═" * 60)
    print("  Atlas-Bookmaker v2 · the AI Marketing Coordinator")
    print("  type 'exit' or Ctrl-D to quit")
    print("═" * 60)
    while True:
        try:
            user_input = input("\nbookmaker > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye fren.")
            break
        if user_input.lower() in {"exit", "quit", "bye"}:
            print("bye fren.")
            break
        if not user_input:
            continue
        result = await agent.run(user_input)
        print(result.text if hasattr(result, "text") else result)


def serve():
    """FastAPI server mode · /v1/atlas/bookmaker endpoint."""
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(title="Atlas-Bookmaker v2", version="0.2.0")
    agent = build_agent()

    @app.post("/v1/atlas/bookmaker")
    async def bookmaker(payload: dict):
        prompt = payload.get("prompt", "")
        if not prompt:
            return {"error": "missing 'prompt' field"}
        result = await agent.run(prompt)
        return {"output": result.text if hasattr(result, "text") else str(result)}

    @app.get("/v1/atlas/bookmaker/health")
    async def health():
        return {"status": "ok", "model": VLLM_MODEL}

    uvicorn.run(app, host="0.0.0.0", port=7860)


def cli():
    """Entry point · `atlas-bookmaker` CLI."""
    ap = argparse.ArgumentParser(description="Atlas-Bookmaker · the AI Marketing Coordinator")
    ap.add_argument("prompt", nargs="?", default=None, help="One-shot prompt (omit for REPL)")
    ap.add_argument("--serve", action="store_true", help="Run FastAPI server on :7860")
    args = ap.parse_args()

    if args.serve:
        serve()
    elif args.prompt:
        asyncio.run(run_one_shot(args.prompt))
    else:
        asyncio.run(run_repl())


if __name__ == "__main__":
    cli()
