#!/usr/bin/env bash
# Lancement du gardien sans systemd (machine cloud du Grok Bot).
# Usage : run.sh start | stop | status | logs
# Variables : GUARDIAN_HOME (défaut /opt/grok-guardian), GUARDIAN_ENV (défaut /etc/grok-bot/env)
set -euo pipefail
GUARDIAN_HOME="${GUARDIAN_HOME:-/opt/grok-guardian}"
GUARDIAN_ENV="${GUARDIAN_ENV:-/etc/grok-bot/env}"
PIDFILE="${GUARDIAN_HOME}/guardian.pid"
LOG="${GUARDIAN_HOME}/guardian.out"
PY="${GUARDIAN_HOME}/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

start() {
  if status >/dev/null 2>&1; then echo "déjà démarré (pid $(cat "$PIDFILE"))"; exit 0; fi
  [ -r "$GUARDIAN_ENV" ] || { echo "fichier env introuvable : $GUARDIAN_ENV"; exit 1; }
  # Boucle de supervision : relance après crash, jamais après halt/mort/victoire (codes 1 et 2)
  nohup bash -c "
    set -a; . '$GUARDIAN_ENV'; set +a
    cd '$GUARDIAN_HOME'
    while true; do
      '$PY' -m guardian; code=\$?
      if [ \$code -eq 1 ] || [ \$code -eq 2 ]; then echo \"arrêt définitif (code \$code)\"; exit \$code; fi
      echo \"crash (code \$code), relance dans 30 s\"; sleep 30
    done" >>"$LOG" 2>&1 &
  echo $! >"$PIDFILE"
  echo "démarré (pid $!) — logs : $LOG"
}
stop()   { [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null && rm -f "$PIDFILE" && echo "arrêté" || echo "pas démarré"; }
status() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null && echo "actif (pid $(cat "$PIDFILE"))" || { echo "inactif"; return 1; }; }
logs()   { tail -n "${2:-50}" -f "$LOG"; }
case "${1:-}" in start) start;; stop) stop;; status) status;; logs) logs "$@";; *) echo "usage: $0 start|stop|status|logs"; exit 2;; esac
