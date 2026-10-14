#!/usr/bin/env bash
# Wrangler local (Node 22 local) via le proxy HTTPS de la box. Les identifiants viennent de l'environnement
# (CLOUDFLARE_API_TOKEN) — jamais écrits dans un fichier.
export PATH="/workspace/tools/node22/bin:$PATH"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:8791}"
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:8791}"
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-45be0d9d9ab486a652b81f7732f8f0d7}"
export WRANGLER_SEND_METRICS=false
export WRANGLER_CACHE_DIR="${WRANGLER_CACHE_DIR:-/workspace/dashboard/cloudflare/.wrangler-cache}"
export WRANGLER_LOG_PATH="${WRANGLER_LOG_PATH:-/workspace/dashboard/logs/wrangler}"
exec /workspace/tools/wrangler/node_modules/.bin/wrangler "$@"
