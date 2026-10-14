#!/usr/bin/env bash
# Wrangler pour le prototype pm-sonnette-cf (observation).
export WRANGLER_CACHE_DIR=/workspace/tools/veilleur/.wrangler-cache
export WRANGLER_LOG_PATH=/workspace/tools/veilleur/logs/wrangler
cd /workspace/tools/veilleur/sonnette-cf
exec /workspace/tools/wrangler/wrangler.sh "$@"
