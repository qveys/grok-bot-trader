#!/usr/bin/env bash
# Démarre l'envoyeur de battements du veilleur (nohup + pidfile). Sans risque si relancé.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/state"
PID_FILE="$DIR/state/battement.pid"
if [[ -f "$PID_FILE" ]]; then
  old="$(tr -d '[:space:]' < "$PID_FILE" || true)"
  if [[ -n "${old:-}" ]] && kill -0 "$old" 2>/dev/null; then
    echo "battement déjà en marche (pid=$old)"; exit 0
  fi
  rm -f "$PID_FILE"
fi
nohup python3 "$DIR/battement.py" >>"$DIR/state/battement.out" 2>&1 </dev/null &
echo $! >"$PID_FILE"
sleep 0.3
if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "battement démarré (pid=$(cat "$PID_FILE"))"
else
  echo "échec de démarrage du battement — voir $DIR/state/battement.out" >&2; rm -f "$PID_FILE"; exit 1
fi
