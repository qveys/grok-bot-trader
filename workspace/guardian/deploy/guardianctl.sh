#!/usr/bin/env bash
# Contrôleur du gardien sans systemd : start | stop | status | logs | run
# Installation attendue : /workspace/guardian (code, .env, secrets/, data/)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
DATA_DIR="${GUARDIAN_DATA_DIR:-$ROOT/data}"
PY="$ROOT/.venv/bin/python"
PIDFILE="$DATA_DIR/supervisor.pid"
LOGFILE="$DATA_DIR/guardian.out"

load_env() {
  [ -f "$ENV_FILE" ] || { echo "Fichier $ENV_FILE manquant (voir deploy/grok-bot.env.example)"; exit 1; }
  set -a; # shellcheck disable=SC1090
  source "$ENV_FILE"; set +a
}

supervise() {
  # Relance après crash ; s'arrête sur les codes volontaires :
  # 0 = arrêt manuel, 42 = halt/mort/victoire, 43 = déjà mort
  # (codes distincts de 1/2 pour ne pas confondre avec un crash Python)
  while true; do
    "$PY" -m guardian && rc=0 || rc=$?
    echo "$(date -u +%FT%TZ) guardian exited rc=$rc" >> "$LOGFILE"
    case "$rc" in 0|42|43) break ;; esac
    sleep 30
  done
  rm -f "$PIDFILE"
}

is_running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

case "${1:-}" in
  run)      # premier plan, pour le debug et le dry_run interactif
    load_env; cd "$ROOT"; exec "$PY" -m guardian ;;
  start)
    is_running && { echo "Déjà lancé (pid $(cat "$PIDFILE"))"; exit 0; }
    load_env; mkdir -p "$DATA_DIR"; cd "$ROOT"
    nohup bash -c "$(declare -f supervise); PY='$PY' LOGFILE='$LOGFILE' PIDFILE='$PIDFILE' supervise" \
      >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Gardien lancé (superviseur pid $(cat "$PIDFILE")) — logs : $0 logs" ;;
  stop)
    is_running || { echo "Pas lancé"; exit 0; }
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    pkill -TERM -f "python -m guardian" 2>/dev/null || true
    rm -f "$PIDFILE"
    echo "Arrêté (SIGTERM : l'état est sauvegardé proprement)" ;;
  status)
    if is_running; then echo "En cours (pid $(cat "$PIDFILE"))"; else echo "Arrêté"; fi
    [ -f "$DATA_DIR/journal.log" ] && { echo "Dernière entrée du journal :"; tail -1 "$DATA_DIR/journal.log"; } ;;
  logs)
    exec tail -f "$LOGFILE" "$DATA_DIR/journal.log" ;;
  *)
    echo "Usage : $0 {start|stop|status|logs|run}"; exit 1 ;;
esac
