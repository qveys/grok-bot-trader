#!/usr/bin/env bash
# Écrit site/data/prices.json toutes les 30 s depuis les ticks du collecteur (aucun réseau, aucune IA).
# Arrêt : ./stop.sh  (ou kill $(cat prices_loop.pid))
cd "$(dirname "$0")"
echo $$ > prices_loop.pid
while true; do
  timeout 20 python3 prices.py >> logs/prices.log 2>&1 || echo "$(date '+%F %T') prices.py échoué" >> logs/prices.log
  if [ -f logs/prices.log ] && [ "$(wc -l < logs/prices.log)" -gt 500 ]; then tail -n 200 logs/prices.log > logs/prices.log.tmp && mv logs/prices.log.tmp logs/prices.log; fi
  sleep 30
done
