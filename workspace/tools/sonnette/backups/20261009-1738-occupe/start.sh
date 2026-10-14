#!/usr/bin/env bash
# Start the sonnette watcher (nohup + pidfile). Safe to re-run.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
mkdir -p state
PID_FILE="$DIR/state/sonnette.pid"
LOG_FILE="$DIR/state/sonnette.out"

# secrets.env is read by sonnette.py itself (re-read every cycle; never echoed).
# The file is the source of truth: drop any SONNETTE_* inherited from this shell
# (stale exports would otherwise override the file). Set SONNETTE_USE_ENV=1 to keep them.
if [[ "${SONNETTE_USE_ENV:-0}" != "1" ]]; then
  for v in $(compgen -e | grep '^SONNETTE_' || true); do unset "$v"; done
fi

if [[ -f "$PID_FILE" ]]; then
  old="$(tr -d '[:space:]' < "$PID_FILE" || true)"
  if [[ -n "${old:-}" ]] && kill -0 "$old" 2>/dev/null; then
    echo "sonnette déjà en marche (pid=$old)"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

nohup python3 "$DIR/sonnette.py" >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
sleep 0.4
if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "sonnette démarrée (pid=$(cat "$PID_FILE")) — log=$LOG_FILE"
  echo "  Astuce: ./status.sh   puis   ./stop.sh"
else
  echo "échec de démarrage — voir $LOG_FILE" >&2
  rm -f "$PID_FILE"
  exit 1
fi
