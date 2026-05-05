# DOCTRINE

> Six rules. Override every default review habit. If something here contradicts a generic best practice, follow this.

## 1. The Bookmaker NEVER computes

Cap rates · DSCR · NOI · vacancy · comps come pre-locked from the Hack on the input page. If a value is missing, the Bookmaker writes `[TBD: <field>]` — never fabricates. **Three layers enforce this:** the corpus audit (`06_strict_input_audit.py`), the Granite-4.1-8B base (validated 12/0 to respect strict-input rule natively), and the inference-time `strict_input_check` tool.

If you find yourself wanting to add a math computation to the Bookmaker, **STOP**. That's the Hack's job. The Bookmaker writes copy and chooses layout. Numbers come from the Hack.

## 2. We don't ship slop

Fitness-for-purpose > voice fidelity. A Bookmaker that "sounds right" but generates Hack-analytical output is still slop because it's the wrong role. v1 (Qwen 2.5 14B QLoRA · loss 0.30-0.42 deploy band · cooked 2026-05-05) was archived for exactly this reason — voice was right, role was wrong.

**Misaligned cooks get archived as learning artifacts. They do not deploy.** v1 lives at `/home/smash/atlas-bookmaker_v1_archive/` as a deeded learning artifact.

## 3. The polish team and the dial team never trade roles

Harvey dials. The Bookmaker packages. Harvey ships. **We never take Harvey off the dials.**

| | Hack (licensed) | Bookmaker (creative) |
|---|---|---|
| Salary | $562K/yr from Harvey's Math | $60K/yr |
| Owns | the deal · numbers · negotiation · sit · close | the LOOK · brand · layout · creative production |
| Computes? | YES | **NEVER** |

If the Bookmaker starts running comps, she's drifted into Hack territory. Pull her back.

## 4. Brand language uses broker vocab on customer surfaces

Customer-facing copy uses **broker vocabulary**, never AI/ML lab vocabulary. Internal logs / commits can use whichever is faster.

| Broker word | Replaces (lab vocab) |
|---|---|
| Hack | fine-tune · specialized model · adapter |
| Cook | training run · SFT job |
| Bookmaker / Atlas / The Closer | model · agent · LLM |
| Jelly · Honey · Pollen · Propolis | curated dataset tier |
| MAGIC | sales process · OKRs |
| Pass / Proceed | rejected / approved · negative/positive |
| Defendable / receipt / deed | explainability · audit log |

The vocabulary IS the moat. **"Granite-Bee runs the Hive."** Not "the AI agent."

## 5. Validate the validator

We prove the foundation BEFORE the cook. Granite-4.1-8B was validated 12/0 (architecture · LoRA targets · tool calling · strict-input discipline · code generation · brand voice baseline · multilingual · speed bench · VRAM headroom) on 2026-05-05 BEFORE we cooked any QLoRA on it.

If the foundation isn't proven, no cook lands. See [`docs/GRANITE_BEE.md`](docs/GRANITE_BEE.md) for the validation receipt.

## 6. Every output carries a Defendable receipt

Atlas-Bookmaker outputs anchor to Hedera HCS topic `0.0.10291838` (operator `0.0.10291827`) at the corpus level (Merkle root of training pairs) and the model level (sha256 of merged adapter). Customer-facing creative includes a receipt bar:

```
Defendable verified · receipt 0x... · hashscan.io/topic/0.0.10291838/<seq>
```

The receipt is part of the firm voice, not a wrapper. **The pair is the receipt.**

---

## Always-P0 (block merge regardless of review depth)

Inherited from `ml-hack/REVIEW.md` upstream doctrine, applied to atlas-bookmaker:

- **Strict-input rule violation** — any output that fabricates a number not in the input
- **Approval gate bypassed** — cook dispatch · Hedera anchor · email blast bypassed
- **Honey ledger write skipped** — model output without provenance row
- **Hedera anchor missing or misrouted** — wrong HCS topic
- **Recipe deviation without justification** — Recipe #4 changes need cook-log entry
- **Brand-language regression** — re-introducing "as-a-service" / treating Bookmaker as generic agent
- **Role drift** — Bookmaker computing or analyzing instead of writing copy

---

*Default bias: rigor. Hold the line on P0. The polish team and the dial team never trade roles.*

— Donovan Mackey, founder · 2026-05-05
