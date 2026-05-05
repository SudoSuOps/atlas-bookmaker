#!/usr/bin/env bash
# cook_auditor.sh · Bookmaker v2 cook auditor · 3h cron pattern
# Same shape as Atlas-70B auditor / v1 Bookmaker auditor.
#
# What it does:
#   1. Pulls latest training log loss + step
#   2. Scans latest checkpoint for contamination markers (<think> leakage)
#   3. Computes JellyScore (loss trend + contamination rate)
#   4. KILL SWITCH: contamination >1% → kills the cook process
#   5. Posts status line to Discord webhook (#cook-auditor)
#
# Cron: 0 */3 * * * /home/smash/atlas-bookmaker_v2/scripts/cook_auditor.sh

set -uo pipefail

SESSION="atlas-bookmaker-v2-2026-05-08"
ROOT="/home/smash/atlas-bookmaker_v2"
LOG_DIR="$ROOT/logs"
CKPT_DIR="$ROOT/checkpoints"
TRAIN_LOG="$LOG_DIR/train.log"
AUDITOR_LOG="$LOG_DIR/auditor-$(date +%Y%m%d-%H%M).log"
DISCORD_URL_FILE="$HOME/.discord_cook_auditor_webhook"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$AUDITOR_LOG"; }

post_discord() {
    local msg="$1"
    if [[ -f "$DISCORD_URL_FILE" ]]; then
        local url
        url=$(cat "$DISCORD_URL_FILE")
        curl -s -X POST -H "Content-Type: application/json" \
            -d "{\"content\": \"$msg\"}" "$url" >/dev/null 2>&1 || true
    fi
}

log "=== Atlas-Bookmaker v2 cook auditor · session=$SESSION ==="

# ─── 1. Cook process check ───────────────────────────────────────────────────
COOK_PID=$(pgrep -f "train_bookmaker_v2.py" | head -1 || true)
if [[ -z "$COOK_PID" ]]; then
    if [[ -f "$CKPT_DIR/final/adapter_model.safetensors" ]]; then
        log "  cook complete · final adapter saved"
        post_discord "✓ **Atlas-Bookmaker v2** cook complete · session=$SESSION · adapter saved"
    else
        log "  cook process NOT RUNNING · check $TRAIN_LOG"
        post_discord "🚨 **Atlas-Bookmaker v2** cook process not running · session=$SESSION"
    fi
    exit 0
fi
log "  cook PID:        $COOK_PID"
COOK_VRAM=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader \
    | awk -F', ' -v pid="$COOK_PID" '$1==pid {print $2}')
log "  cook VRAM:       $COOK_VRAM"

# ─── 2. Latest loss + step ───────────────────────────────────────────────────
LATEST_STEP=$(grep -oE "step[: ]+[0-9]+" "$TRAIN_LOG" 2>/dev/null | tail -1 | grep -oE "[0-9]+")
LATEST_LOSS=$(grep -oE "'loss':\s*[0-9.]+" "$TRAIN_LOG" 2>/dev/null | tail -1 | grep -oE "[0-9.]+")
log "  step:            ${LATEST_STEP:-?}"
log "  loss:            ${LATEST_LOSS:-?}"

# ─── 3. Contamination scan (latest checkpoint) ──────────────────────────────
LATEST_CKPT=$(ls -dt "$CKPT_DIR"/checkpoint-* 2>/dev/null | head -1)
CONTAM_NOTE="n/a (no eval samples cached)"
if [[ -n "${LATEST_CKPT:-}" ]]; then
    log "  latest ckpt:     $LATEST_CKPT"
    # If on-checkpoint generation samples exist · scan them.
    SAMPLE_FILE="$LATEST_CKPT/eval_samples.jsonl"
    if [[ -f "$SAMPLE_FILE" ]]; then
        TOTAL=$(wc -l < "$SAMPLE_FILE")
        CONTAM=$(grep -cE '<think>|</think>|<reasoning>' "$SAMPLE_FILE" 2>/dev/null || echo 0)
        if [[ $TOTAL -gt 0 ]]; then
            RATE_PCT=$(awk -v c="$CONTAM" -v t="$TOTAL" 'BEGIN{printf "%.3f", (c/t)*100}')
            CONTAM_NOTE="$CONTAM/$TOTAL ($RATE_PCT%)"
            # Kill switch · >1% contamination
            if (( $(awk -v r="$RATE_PCT" 'BEGIN{print (r > 1.0)}') )); then
                log "  🚨 KILL SWITCH: contamination $RATE_PCT% > 1%"
                kill -9 "$COOK_PID" || true
                post_discord "🚨 **Atlas-Bookmaker v2** KILLED · contamination $RATE_PCT% · session=$SESSION"
                exit 0
            fi
        fi
    fi
fi
log "  contamination:   $CONTAM_NOTE"

# ─── 4. JellyScore ────────────────────────────────────────────────────────────
JELLY="n/a"
if [[ -n "${LATEST_LOSS:-}" ]]; then
    JELLY=$(python3 -c "l=$LATEST_LOSS; print(f'{max(0, 1 - l/10):.3f}')")
fi
log "  JellyScore:      $JELLY"

# ─── 5. Discord ping ─────────────────────────────────────────────────────────
post_discord "**Atlas-Bookmaker v2** auditor · step ${LATEST_STEP:-?} · loss ${LATEST_LOSS:-?} · jelly $JELLY · vram $COOK_VRAM · contam $CONTAM_NOTE"
log "  ✓ auditor cycle done · log: $AUDITOR_LOG"
