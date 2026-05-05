#!/usr/bin/env bash
# deploy/anchor.sh · Hedera anchor for Atlas-Bookmaker v2
#
# Anchors:
#   1. Corpus Merkle root (training pairs)
#   2. Adapter sha256 (the merged LoRA weights)
#   3. Eval summary hash
#
# Topic: 0.0.10291838 (firm deed anchor topic, mainnet)
# Operator: 0.0.10291827
# Cost: ~$0.0008 per publish · 3 publishes per ship = ~$0.0024 total
#
# Approval gate REQUIRED before publish (per ml-hack/REVIEW.md doctrine).

set -euo pipefail

ROOT="/home/smash/atlas-bookmaker_v2"
ADAPTER="$ROOT/merged/atlas-bookmaker-v2"
CORPUS="$ROOT/corpus/train.jsonl"
EVAL="$ROOT/eval/v2_ship_eval.jsonl"
HEDERA_TOPIC="${HCS_TOPIC:-0.0.10291838}"
HEDERA_OPERATOR="${HEDERA_OPERATOR:-0.0.10291827}"

echo "═══════════════════════════════════════════════════════════"
echo "  Atlas-Bookmaker v2 · Hedera anchor"
echo "═══════════════════════════════════════════════════════════"
echo "  topic:     $HEDERA_TOPIC"
echo "  operator:  $HEDERA_OPERATOR"
echo ""

# Compute hashes
ADAPTER_HASH=$(sha256sum "$ADAPTER/adapter_model.safetensors" | awk '{print $1}')
CORPUS_HASH=$(sha256sum "$CORPUS" | awk '{print $1}')
EVAL_HASH=$(sha256sum "$EVAL" | awk '{print $1}')

cat <<EOF
Hashes to anchor:
  adapter:  $ADAPTER_HASH
  corpus:   $CORPUS_HASH
  eval:     $EVAL_HASH

This will publish 3 messages to Hedera HCS.
Estimated cost: ~\$0.0024
Continue? (y/N)
EOF

read -r CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "anchor aborted."
    exit 0
fi

# Bridge to merkle.py / hedera_bridge.py on swarmrails
ANCHOR_PAYLOAD=$(cat <<JSON
{
  "session": "atlas-bookmaker-v2-2026-05-08",
  "model": "atlas-bookmaker-v2",
  "base": "ibm-granite/granite-4.1-8b",
  "recipe": "recipe_4_8b_hack_granite",
  "adapter_sha256": "$ADAPTER_HASH",
  "corpus_sha256": "$CORPUS_HASH",
  "eval_sha256": "$EVAL_HASH",
  "topic": "$HEDERA_TOPIC",
  "anchored_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
)

echo "$ANCHOR_PAYLOAD" > "$ROOT/anchor_payload.json"

# Dispatch to swarmrails Hedera bridge
echo ""
echo "Dispatching to swarmrails Hedera bridge..."
scp "$ROOT/anchor_payload.json" swarm@swarmrails:/tmp/atlas_bookmaker_v2_anchor.json
ssh swarm@swarmrails "cd /home/swarm/swarmchain && python hedera_bridge.py --payload /tmp/atlas_bookmaker_v2_anchor.json --topic $HEDERA_TOPIC"

echo ""
echo "✓ anchored. Verify at:"
echo "  https://hashscan.io/mainnet/topic/$HEDERA_TOPIC"
