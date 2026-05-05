# Atlas-Bookmaker

> **The AI Marketing Coordinator the firm wishes she was.**
> $60K/yr creative hire · packages a Hack's deal-highlights into shipable creative · NEVER computes.

Atlas-Bookmaker is the marketing & creative production AI for Swarm & Bee LLC, the Florida-licensed AI-native CRE brokerage. She takes a Hack's curated deal-highlights and produces ship-ready creative — OM PDF booklets, landing pages, e-blast teasers, CoStar / LoopNet listings, social cards, brokerage fliers, investor packets, map captions, comp callouts, photo briefs.

**She is not a broker.** She does not compute. Cap rates · DSCR · NOI · vacancy · comps come pre-locked from the Hack on the input page. Her job is curb appeal · brand alignment · polish. The polish team and the dial team never trade roles.

```
   ┌───────────┐    deal-highlights JSON   ┌──────────────┐    creative output    ┌─────────┐
   │   HACK    │ ────────────────────────► │  BOOKMAKER   │ ───────────────────► │ MARKET  │
   │ licensed  │   numbers locked           │ creative AI  │   OM · landing ·     │ buyers  │
   │ broker    │   by the underwriter       │ Granite-Bee  │   e-blast · social   │ sellers │
   └───────────┘                            └──────────────┘                       └─────────┘
                                                  │
                                          ┌───────┴──────────────┐
                                          │  Granite-4.1-8B      │  the writer
                                          │  Granite-Vision-4B   │  the eyes (PDFs · photos)
                                          │  Granite-Docling     │  PDF parser
                                          │  Granite-Speech-2B   │  voice-to-text
                                          │  Granite-Guardian-8B │  brand-drift gate
                                          │  BeeAI Framework     │  orchestration
                                          └──────────────────────┘
```

Built by **Swarm & Bee LLC** (D-U-N-S 138652395) for the Atlas Hack-fleet. Apache 2.0.

## What She Ships

10 deliverable types from one deal-highlights JSON input:

| # | Deliverable | What it is |
|---|---|---|
| 1 | **OM PDF booklet** | Multi-page institutional offering memorandum — the proposal Harvey ships to sellers |
| 2 | **Landing page** | HTML5 + inline CSS · headline · stat strip · receipt bar · CTA |
| 3 | **E-blast teaser** | Subject line · preview text · 4-paragraph body · sign-off (HTML email) |
| 4 | **CoStar / LoopNet listing** | 350-char description · feature bullets · key terms · structured JSON |
| 5 | **Social card** | LinkedIn deal post · Twitter/X teaser · Instagram caption |
| 6 | **1-page brokerage flier** | Branded PDF · key stats · contact card |
| 7 | **Investor packet TOC** | Cover · executive summary · property overview · market · financial · contact |
| 8 | **Map caption** | Location storytelling · submarket positioning |
| 9 | **Comp callout** | "Trades like X" framing · visual annotation copy |
| 10 | **Photography brief** | Shot list for the building · brand-aligned creative direction |

## The Strict-Input Rule

```
INPUT  · deal_highlights JSON (numbers locked by the Hack)
       · brand_pack
       · deliverable type
       · template choice

OUTPUT · creative copy + structural markup ready for layout engine
       · NEVER computes cap rate · DSCR · NOI · vacancy · comps
       · uses [TBD: <field>] when a value is missing from input
       · Granite-Guardian gate enforces no brand-drift before ship
```

**Three layers of defense against fabrication:**
1. **Corpus** — every training pair audited; numbers in output must appear in input
2. **Cook** — Granite-4.1-8B respects the strict-input rule natively (validated 12/0)
3. **Inference** — deterministic regex/numeric gate runs BEFORE Granite-Guardian sees the output

## Foundation: Granite-Bee Stack (Apache 2.0)

| Model | Role | Cooked? |
|---|---|---|
| `ibm-granite/granite-4.1-8b` | The writer · 128K ctx · BFCL 68 · 66 tok/s on 5090 | **YES** — QLoRA on creative-production corpus |
| `ibm-granite/granite-vision-4.1-4b` | The eyes · 94.4% KVP zero-shot · CRE doc extraction | **YES** — QLoRA on CRE doc-extraction pairs |
| `ibm-granite/granite-docling-258M` | PDF parser · 209k downloads · firm-trusted from aviation cook | as-is |
| `ibm-granite/granite-speech-4.1-2b-nar` | Voice-to-text · ASR · multilingual auto-detect | as-is |
| `ibm-granite/granite-guardian-4.1-8b` | Brand-drift gate · BYOC criteria | as-is |
| [BeeAI Framework](https://github.com/i-am-bee/beeai-framework) | ReAct + tools · Apache 2.0 · IBM-built | wired |

Validated 2026-05-05 on smash (RTX 5090): **12/0 pass · recipe transfers cleanly · 2× speed of Qwen 2.5 14B**. See [`docs/GRANITE_BEE.md`](docs/GRANITE_BEE.md) for the full validation receipt.

## Quick Start

```bash
git clone git@github.com:SudoSuOps/atlas-bookmaker.git
cd atlas-bookmaker
uv sync                              # install pinned deps
cp .env.example .env                 # edit with HF_TOKEN, HEDERA_OPERATOR, etc.

# Build the corpus (Phase 1 · pulls from cre_honey + REIT decks + synth + grinder)
python corpus/scripts/01_extract_marketing.py
python corpus/scripts/02_flip_cre_to_strict_input.py     # the load-bearing transform
python corpus/scripts/03_bookmaker_grinder.py            # 10 deliverable templates
python corpus/scripts/04_reit_listing_extract.py
python corpus/scripts/05_merge_dedup.py
python corpus/scripts/06_strict_input_audit.py           # firm-doctrine gate
python corpus/scripts/07_think_tag_scan.py
python corpus/scripts/08_emit_hivecells.py

# Tribunal grade on swarmrails (gemma3:12b + qwen2.5:32b · 9B+9B different-family judges)
ssh swarmrails ./run_tribunal.sh bookmaker_hivecells_v2.jsonl

# Cook on smash 5090 (~1.5h)
ssh smash@192.168.0.164 './train/train_bookmaker_v2.py'

# Eval (curb-appeal rubric · NEVER scores numerical fidelity)
python eval/score.py --suite eval/prompts/ship_eval_100.jsonl

# Ship — Hedera anchor + endpoint
./deploy/anchor.sh atlas-bookmaker-v2
./deploy/vllm_serve.sh
```

## Workflow · How Harvey Uses Her

```
Harvey on the dial floor                              Atlas-Bookmaker
─────────────────────────                             ──────────────
1. Closes a 7-Eleven listing in Charlotte             
   $3.1M · 6.50% cap · BBB · 10-yr NNN
                                                      
2. Dictates deal-highlights into ml-hack:    ──────►  Granite-Speech 2B → transcript
   "Got the 7-Eleven, $3.1M, BBB credit..."
                                                      
3. Drops the lease + rent roll PDFs:         ──────►  Granite-Docling → structured JSON
                                                      Granite-Vision → key terms
                                                      
4. "Pull a comp set + ship me an OM, blast,
    landing page, and CoStar listing"        ──────►  Bookmaker generates 4 deliverables
                                                      from one deal-highlights JSON
                                                      
5. Reviews · approves · ships to             ◄──────  Strict-input gate runs first
   his 1031 buyers list                              Guardian gate runs second
                                                      Hedera receipt anchored
                                                      
6. Stays on the dials.                                The polish team did the polish.
```

> **"We never take Harvey off the dials. The Bookmaker is marketing — creative design, the team's polish, curb appeal."** — Donovan Mackey, founder

## Pricing · The $60K/yr Creative Hire

Per [`atlas_on_demand_menu`](https://swarmandbee.ai), the firm offers Atlas-Bookmaker outputs as a service line:

| Deliverable | Per-piece price | Per-deal package |
|---|---|---|
| OM PDF booklet | $1,500 | included in $5K full-deal package |
| Landing page | $500 | included |
| E-blast | $2,000 (with The Book targeting) | included |
| CoStar / LoopNet listing | $200 | included |
| Brokerage flier | $300 | included |

Internal cost · ~$0.0052/deed to mint via Granite-Bee on sovereign compute. **Margin is the moat. Volume is the kicker.**

## Documentation

- [`docs/ROLE.md`](docs/ROLE.md) — full role doctrine · Bookmaker vs Hack · "we don't ship slop"
- [`docs/HARVEY_MATH.md`](docs/HARVEY_MATH.md) — the funnel that justifies the build
- [`docs/GRANITE_BEE.md`](docs/GRANITE_BEE.md) — foundation validation receipts
- [`docs/PIPELINE.md`](docs/PIPELINE.md) — corpus build → cook → eval → ship
- [`recipes/recipe_4_8b_hack_granite.md`](recipes/recipe_4_8b_hack_granite.md) — the locked QLoRA recipe
- [`ROADMAP.md`](ROADMAP.md) — phased ship plan (cooking by Saturday, anchor + endpoint Sunday)
- [`DOCTRINE.md`](DOCTRINE.md) — what doesn't ship, ever

## License

Apache 2.0 — matches the Granite-Bee stack and BeeAI framework. See [LICENSE](LICENSE).

## Brand Glossary

- **Bookmaker** — the firm's AI Marketing Coordinator (this repo)
- **Hack** — junior CRE broker · each Hack-fleet specialist is a Granite-4.1-8B QLoRA on one vertical
- **Harvey** — the prototype dialer (300 dials/day) · the Hack-fleet's pure-dialer ancestor
- **The Book** — relationship + counterparty + deal graph · firm-owned moat
- **MAGIC** — Meetings · Appraisals · Grind · Ink · Close (the 5-letter lifecycle)
- **The Lane** — STNL net-lease at $1M-$5M (where AI dominates)
- **Atlas-as-a-Closer** — vendor service line · REITs/operators rent the Hack-fleet
- **Royal Jelly** — top tier of training-pair grade (Class A under Defendable v0.1.0)
- **Validate the Validator** — proving the foundation BEFORE the cook (firm doctrine)
- **We Don't Ship Slop** — fitness-for-purpose > voice fidelity (firm doctrine)
