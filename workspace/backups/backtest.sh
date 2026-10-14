#!/usr/bin/env bash
# Non-LLM spot backtest via Vibe-Trading engine. Commands: run (default), robust, risk, corr, sentiment, journal. See: backtest.sh --help
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:8791}" HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:8791}"
export VIBE_TRADING_HOME="$DIR/home"
exec "$DIR/.venv/bin/python" "$DIR/vt_tools.py" "$@"
