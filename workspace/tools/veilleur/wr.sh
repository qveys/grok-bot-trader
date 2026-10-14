#!/usr/bin/env bash
# Wrangler pour le veilleur (cache/logs gardés ici, pas dans /workspace/dashboard).
export WRANGLER_CACHE_DIR=/workspace/tools/veilleur/.wrangler-cache
export WRANGLER_LOG_PATH=/workspace/tools/veilleur/logs/wrangler
cd /workspace/tools/veilleur/worker
exec /workspace/tools/wrangler/wrangler.sh "$@"
