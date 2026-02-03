#!/bin/bash
# OpenClaw Memory - Installation Script

set -e

WORKSPACE="${HOME}/.openclaw/workspace"
REPO_DIR="${WORKSPACE}/openclaw-memory"

echo "🧠 OpenClaw Memory - Installation"
echo "=================================="
echo

# Check OpenClaw is installed
if ! command -v openclaw &> /dev/null; then
    echo "❌ OpenClaw not found. Install from: https://github.com/openclaw/openclaw"
    exit 1
fi

echo "✅ OpenClaw detected"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

echo "✅ Python 3 detected"

# Create memory directory if needed
mkdir -p "${WORKSPACE}/memory"
echo "✅ Memory directory ready"

# Make scripts executable
chmod +x "${REPO_DIR}/scripts/"*.{py,sh} 2>/dev/null || true
echo "✅ Scripts executable"

# Test consolidation script
echo
echo "🧪 Testing consolidation script..."
python3 "${REPO_DIR}/scripts/memory-consolidate.py" --dry-run
echo

# Offer to install cron jobs
echo "📅 Cron Job Installation"
echo "========================"
echo
echo "Would you like to install automatic memory consolidation?"
echo "  - Runs every 6 hours"
echo "  - Extracts events from daily notes"
echo "  - Updates MEMORY.md automatically"
echo
read -p "Install memory consolidation cron? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    openclaw cron add \
      --name memory_consolidation \
      --schedule "0 */6 * * *" \
      --target isolated \
      --payload '{"kind":"agentTurn","message":"Run memory consolidation: python3 '"${REPO_DIR}"'/scripts/memory-consolidate.py --auto","deliver":false}'
    echo "✅ Memory consolidation cron installed"
fi

echo
echo "Would you like to install context monitoring?"
echo "  - Runs every 15 minutes"
echo "  - Alerts when context window fills"
echo "  - Prevents data loss"
echo
read -p "Install context monitor cron? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    openclaw cron add \
      --name context_monitor \
      --schedule "*/15 * * * *" \
      --target main \
      --payload '{"kind":"systemEvent","text":"Run context monitor: '"${REPO_DIR}"'/scripts/context-monitor.sh"}'
    echo "✅ Context monitor cron installed"
fi

echo
echo "✨ Installation complete!"
echo
echo "Test it:"
echo "  python3 ${REPO_DIR}/scripts/memory-consolidate.py --dry-run"
echo
echo "Check cron jobs:"
echo "  openclaw cron list"
echo
echo "Documentation:"
echo "  ${REPO_DIR}/README.md"
echo
