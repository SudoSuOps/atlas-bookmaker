#!/usr/bin/env python3
"""
deploy/api_route.py · /v1/atlas/bookmaker endpoint scaffold.

This is the PUBLIC FastAPI route exposed at api.swarmandbee.ai/v1/atlas/bookmaker
(via Cloudflare reverse-proxy). Behind the scenes it forwards to:
  - The BeeAI agent (agent/main.py · serve mode) at smash:7860
  - Or directly to vLLM at smash:8089/v1/chat/completions

Deployed via Cloudflare Workers + Tunnel pattern (matches existing
api.swarmandbee.ai and api.router.swarmandbee.com patterns).

Auth: customer API key from swarm-db (sb_live_*) · pricing tier per request.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
app = FastAPI(title="Atlas-Bookmaker API", version="0.2.0")

VLLM_URL = os.environ.get("VLLM_URL", "http://smash:8089/v1")
AGENT_URL = os.environ.get("AGENT_URL", "http://smash:7860")
SWARM_DB_URL = os.environ.get("SWARM_DB_URL", "http://swarmrails:5432")


class BookmakerRequest(BaseModel):
    deal_highlights: dict[str, Any] = Field(..., description="Hack-curated deal data · numbers locked")
    deliverable: str = Field(..., description="One of 10 deliverables: om_pdf · landing_page · eblast · etc.")
    brand_pack: str = Field(default="swarm_and_bee", description="Brand pack ID")
    template_id: str | None = Field(default=None, description="Specific template within deliverable")
    extras: dict[str, Any] = Field(default_factory=dict, description="Hack notes for the Bookmaker")


class BookmakerResponse(BaseModel):
    output: str
    deliverable: str
    deal_id: str | None
    receipts: list[dict[str, Any]] = Field(default_factory=list, description="Hedera anchors for this output")
    audit: dict[str, Any] = Field(default_factory=dict, description="strict_input_check + brand_gate results")


@app.post("/v1/atlas/bookmaker", response_model=BookmakerResponse)
async def bookmaker(
    req: BookmakerRequest,
    authorization: str = Header(...),
):
    """Atlas-Bookmaker · take deal-highlights, ship creative."""

    # 1. Auth · validate API key against swarm-db
    api_key = authorization.replace("Bearer ", "")
    if not api_key.startswith("sb_live_") and not api_key.startswith("sb_test_"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
    # TODO: hit swarm-db /auth/validate · check tier · log usage

    # 2. Validate deliverable type
    valid_deliverables = {
        "om_pdf", "landing_page", "eblast", "costar_listing",
        "social_card", "flier", "investor_toc", "map_caption",
        "comp_callout", "photo_brief",
    }
    if req.deliverable not in valid_deliverables:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"deliverable must be one of {sorted(valid_deliverables)}",
        )

    # 3. Forward to BeeAI agent · the agent runs the strict_input_check + brand_gate
    prompt_payload = {
        "deal_highlights": req.deal_highlights,
        "deliverable": req.deliverable,
        "brand_pack": req.brand_pack,
        "template_id": req.template_id,
        "extras": req.extras,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{AGENT_URL}/v1/atlas/bookmaker", json={"prompt": str(prompt_payload)})
            r.raise_for_status()
            agent_resp = r.json()
    except httpx.HTTPError as e:
        logger.error(f"agent call failed: {e}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="bookmaker agent unreachable")

    return BookmakerResponse(
        output=agent_resp.get("output", ""),
        deliverable=req.deliverable,
        deal_id=req.deal_highlights.get("deal_id"),
        receipts=agent_resp.get("receipts", []),
        audit=agent_resp.get("audit", {}),
    )


@app.get("/v1/atlas/bookmaker/health")
async def health():
    """Health check · validates the agent + vLLM are reachable."""
    health_status: dict[str, Any] = {
        "service": "atlas-bookmaker",
        "version": "0.2.0",
        "components": {},
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            vllm = await client.get(f"{VLLM_URL}/models")
            health_status["components"]["vllm"] = {"status": "ok" if vllm.status_code == 200 else "down"}
    except Exception as e:
        health_status["components"]["vllm"] = {"status": "down", "error": str(e)[:100]}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            agent = await client.get(f"{AGENT_URL}/v1/atlas/bookmaker/health")
            health_status["components"]["agent"] = {"status": "ok" if agent.status_code == 200 else "down"}
    except Exception as e:
        health_status["components"]["agent"] = {"status": "down", "error": str(e)[:100]}

    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7861)
