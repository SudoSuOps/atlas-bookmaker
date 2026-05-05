#!/usr/bin/env bash
# deploy/vllm_serve.sh · serve Atlas-Bookmaker v2 via vLLM on smash:8089
#
# Loads:
#   - Granite-4.1-8B base (full bf16 · fits 5090 with room)
#   - Atlas-Bookmaker v2 LoRA adapter (or merged weights)
#
# Uses vLLM's --enable-lora flag for adapter hot-swap (BeeAI agent can switch
# between Bookmaker / future Hack adapters without reloading the base).

set -euo pipefail

GRANITE_BASE="${GRANITE_LLM:-/home/smash/granite/granite-4.1-8b}"
ADAPTER_PATH="${VLLM_ADAPTER_PATH:-/home/smash/atlas-bookmaker_v2/checkpoints/final}"
PORT="${VLLM_PORT:-8089}"
ADAPTER_NAME="${VLLM_ADAPTER_NAME:-atlas-bookmaker-v2}"

echo "═══════════════════════════════════════════════════════════"
echo "  Atlas-Bookmaker v2 · vLLM serve"
echo "═══════════════════════════════════════════════════════════"
echo "  base:    $GRANITE_BASE"
echo "  adapter: $ADAPTER_PATH"
echo "  name:    $ADAPTER_NAME"
echo "  port:    $PORT"
echo ""

# Verify adapter exists
if [[ ! -f "$ADAPTER_PATH/adapter_config.json" ]]; then
    echo "ERROR: adapter not found at $ADAPTER_PATH"
    echo "Did the cook complete? Check /home/smash/atlas-bookmaker_v2/checkpoints/"
    exit 1
fi

# Activate venv (smash standard)
source /home/smash/hack-cook-venv/bin/activate

# Serve via vLLM with LoRA adapter
exec vllm serve "$GRANITE_BASE" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --enable-lora \
    --lora-modules "$ADAPTER_NAME=$ADAPTER_PATH" \
    --max-loras 4 \
    --max-lora-rank 32 \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.85 \
    --dtype bfloat16 \
    --served-model-name "$ADAPTER_NAME" \
    --tensor-parallel-size 1 \
    --trust-remote-code
