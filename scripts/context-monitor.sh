#!/bin/bash
# Context Monitor - Auto-flush when thresholds hit
# Run this periodically via cron

SESSION_KEY="${1:-agent:main:main}"
WORKSPACE="/home/mars/.openclaw/workspace"
DAILY_LOG="$WORKSPACE/memory/$(date +%Y-%m-%d).md"

# Get session status
STATUS=$(openclaw sessions status --session "$SESSION_KEY" --json 2>/dev/null)

if [ $? -ne 0 ]; then
  echo "Failed to get session status"
  exit 1
fi

# Parse context percentage (this is hacky, would need actual JSON parsing)
# For now, just trigger flush manually via session_send

CONTEXT_PCT=$(echo "$STATUS" | grep -oP 'Context: \K[0-9]+' || echo "0")

# Thresholds
ACTIVE_FLUSH=70
EMERGENCY_FLUSH=85

if [ "$CONTEXT_PCT" -ge "$EMERGENCY_FLUSH" ]; then
  echo "[$(date)] EMERGENCY FLUSH at ${CONTEXT_PCT}%" >> "$WORKSPACE/memory/context-monitor.log"
  
  # Send flush command to session
  openclaw sessions send --session "$SESSION_KEY" \
    "EMERGENCY CONTEXT FLUSH (${CONTEXT_PCT}%): Write complete session state to daily notes NOW. Include: decisions made, current work, open threads, next actions."
  
elif [ "$CONTEXT_PCT" -ge "$ACTIVE_FLUSH" ]; then
  echo "[$(date)] Active flush at ${CONTEXT_PCT}%" >> "$WORKSPACE/memory/context-monitor.log"
  
  # Gentle reminder
  openclaw sessions send --session "$SESSION_KEY" \
    "Context at ${CONTEXT_PCT}% - time to flush key points to daily notes."
fi

echo "Context: ${CONTEXT_PCT}%"
