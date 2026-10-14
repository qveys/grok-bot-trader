#!/usr/bin/env bash
# Relance build.py toutes les 5 minutes (aucune IA). Arrêt : ./stop.sh  (ou kill $(cat refresh_loop.pid))
cd "$(dirname "$0")"
echo $$ > refresh_loop.pid
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:8791}" HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:8791}"
while true; do
  echo "=== $(date '+%F %T %Z')" >> logs/refresh.log
  timeout 240 python3 build.py >> logs/refresh.log 2>&1 || echo "build échoué (code $?)" >> logs/refresh.log
  # garder le log petit
  if [ "$(wc -l < logs/refresh.log)" -gt 2000 ]; then tail -n 1000 logs/refresh.log > logs/refresh.log.tmp && mv logs/refresh.log.tmp logs/refresh.log; fi
  sleep 300
done
