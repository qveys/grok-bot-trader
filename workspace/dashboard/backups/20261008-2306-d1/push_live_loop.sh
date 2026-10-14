#!/usr/bin/env bash
# Mode « quasi direct » : toutes les 10 s, pousse dans Cloudflare D1 les fichiers de données qui ont changé
# (en pratique : prix ≈ toutes les 30 s, le reste toutes les 5 min). Arrêt : ./stop.sh
cd "$(dirname "$0")/.."
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:8791}"
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-45be0d9d9ab486a652b81f7732f8f0d7}"
echo $$ > push_live_loop.pid
while true; do
  timeout 120 python3 cloudflare/d1/push_live.py >> logs/push_live.log 2>&1
  if [ -f logs/push_live.log ] && [ "$(wc -l < logs/push_live.log)" -gt 2000 ]; then tail -n 500 logs/push_live.log > logs/push_live.log.tmp && mv logs/push_live.log.tmp logs/push_live.log; fi
  sleep 10
done
