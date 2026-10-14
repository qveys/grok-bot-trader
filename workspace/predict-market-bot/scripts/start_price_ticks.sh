#!/usr/bin/env bash
# Start the 30s mid-price tick collector with auto-restart if the process dies.
# Note: if the internet is down, the process keeps running but writes nothing —
# restarting it does not help until the network is fixed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TICKS_DIR="$ROOT/state/price_ticks"
PID_FILE="$TICKS_DIR/collector.pid"
SUPERVISE_PID="$TICKS_DIR/supervisor.pid"
LOG_FILE="$TICKS_DIR/collector.log"
PY="$ROOT/scripts/collect_price_ticks.py"

export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:8791}"
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:8791}"
export ALL_PROXY="${ALL_PROXY:-http://127.0.0.1:8791}"

mkdir -p "$TICKS_DIR"
cd "$ROOT"

# Already supervised?
if [[ -f "$SUPERVISE_PID" ]]; then
  sp="$(tr -d '[:space:]' < "$SUPERVISE_PID" || true)"
  if [[ -n "${sp:-}" ]] && kill -0 "$sp" 2>/dev/null; then
    echo "price_ticks supervisor already running (pid=$sp)"
    exit 0
  fi
  rm -f "$SUPERVISE_PID"
fi

# Or bare collector still alive without supervisor
if [[ -f "$PID_FILE" ]]; then
  old_pid="$(tr -d '[:space:]' < "$PID_FILE" || true)"
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "price_ticks collector already running (pid=$old_pid) — leave it; network outage does not need a restart"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

(
  echo $$ >"$SUPERVISE_PID"
  trap 'rm -f "$SUPERVISE_PID"' EXIT
  while true; do
    echo "[supervisor] starting collector @ $(date -Iseconds)" >>"$LOG_FILE"
    python3 "$PY" >>"$LOG_FILE" 2>&1 || true
    code=$?
    echo "[supervisor] collector exited code=$code @ $(date -Iseconds); restart in 5s" >>"$LOG_FILE"
    sleep 5
  done
) >/dev/null 2>&1 &
disown
sleep 0.5
echo "started price_ticks supervisor pid=$(tr -d '[:space:]' < "$SUPERVISE_PID") log=$LOG_FILE"
