#!/usr/bin/env bash
# Arrête : refresh 5 min, prix 30 s, serveur web local, publication Cloudflare 15 min, envoi direct (D1/KV).
# (Le site en ligne reste en place, figé sur la dernière publication.)
cd "$(dirname "$0")"
for f in refresh_loop.pid prices_loop.pid server.pid deploy_loop.pid push_live_loop.pid; do
  if [ -f "$f" ]; then pid=$(cat "$f"); kill "$pid" 2>/dev/null && echo "arrêté: $f (pid $pid)"; rm -f "$f"; fi
done
pkill -f "dashboard/refresh_loop.sh|\./refresh_loop.sh" 2>/dev/null
pkill -f "dashboard/prices_loop.sh|\./prices_loop.sh" 2>/dev/null
pkill -f "dashboard/deploy_loop.sh|\./deploy_loop.sh" 2>/dev/null
pkill -f "push_live_loop.sh" 2>/dev/null
true
