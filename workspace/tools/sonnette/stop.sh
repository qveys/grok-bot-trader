#!/usr/bin/env bash
# Stop the sonnette watcher.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/state/sonnette.pid"
if [[ ! -f "$PID_FILE" ]]; then
  echo "pas de pidfile — sonnette déjà arrêtée ?"
  exit 0
fi
pid="$(tr -d '[:space:]' < "$PID_FILE" || true)"
if [[ -z "${pid:-}" ]]; then
  rm -f "$PID_FILE"
  echo "pidfile vide — nettoyé"
  exit 0
fi
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.3
  done
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  echo "sonnette arrêtée (pid=$pid)"
else
  echo "processus $pid déjà mort — nettoyage"
fi
rm -f "$PID_FILE"
