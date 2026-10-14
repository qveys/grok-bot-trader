#!/usr/bin/env bash
# Fonctions IA de Vibe-Trading via le compte ChatGPT de Quentin (connexion par code d'appareil).
# Usage : ai.sh ask "question"      -> question libre
#         ai.sh swarm <preset> ...  -> équipe d'analystes (vibe-trading swarm)
# Aucun courtier, aucun portefeuille : analyse uniquement, jamais d'ordre.
set -euo pipefail
cd /workspace/tools/vibe-trading
source .venv/bin/activate
export VIBE_TRADING_HOME=/workspace/tools/vibe-trading/home
export HTTPS_PROXY=http://127.0.0.1:8791 HTTP_PROXY=http://127.0.0.1:8791 NO_PROXY=localhost,127.0.0.1
export LANGCHAIN_PROVIDER=openai-codex LANGCHAIN_MODEL_NAME=openai-codex/gpt-6-sol
cmd="${1:-}"; shift || true
case "$cmd" in
  ask)   vibe-trading run -p "$*" ;;
  swarm) vibe-trading swarm "$@" ;;
  *) echo "Usage: ai.sh ask \"question\" | ai.sh swarm <args>"; exit 1 ;;
esac
