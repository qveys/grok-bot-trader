#!/usr/bin/env bash
# Start stop-loss watcher for ALL opens (paper auto-close; live = urgent wake).
# Foreground via exec so exit 10 wakes the caller.
# Usage: run in background from PM-Risk, e.g. Shell block_until_ms=0.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p state
exec python3 guardian/scripts/watch_stops.py --interval 15
