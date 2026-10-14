#!/usr/bin/env bash
# Start stop-loss watcher for ALL opens (paper auto-close; live auto-exit via live_place.py --exit, 8 oct).
# Foreground via exec (exit 10 when a close leaves nothing else to watch).
# paper_fill.py / live_place.py now start it automatically (detached) after an open.
# Usage: run in background from PM-Risk, e.g. Shell block_until_ms=0.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p state
exec python3 guardian/scripts/watch_stops.py --interval "${WATCH_STOPS_INTERVAL:-30}"
