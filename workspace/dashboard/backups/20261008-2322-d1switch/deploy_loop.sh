#!/usr/bin/env bash
# Publie site/ sur Cloudflare Pages toutes les 15 min, SEULEMENT si site/data a changé depuis la dernière publication.
# Arrêt : ./stop.sh  (ou kill $(cat deploy_loop.pid))
cd "$(dirname "$0")"
mkdir -p logs
echo $$ > deploy_loop.pid
INTERVAL_MIN="${DEPLOY_INTERVAL_MIN:-15}"
export DEPLOY_INTERVAL_MIN="$INTERVAL_MIN"
datahash() { (cd site && find data -type f -name '*.json' -print0 | sort -z | xargs -0 sha256sum; sha256sum *.html *.js *.css 2>/dev/null) | sha256sum | cut -d' ' -f1; }
while true; do
  h=$(datahash)
  last=$(cat logs/deploy.lasthash 2>/dev/null || true)
  if [ "$h" != "$last" ]; then
    if timeout 300 ./cloudflare/deploy.sh >> logs/deploy.log 2>&1; then
      echo "$h" > logs/deploy.lasthash; echo "$(date '+%F %T') publié (hash ${h:0:12})" >> logs/deploy.log
    else
      echo "$(date '+%F %T') publication échouée (on réessaie au prochain tour)" >> logs/deploy.log
    fi
  else
    echo "$(date '+%F %T') rien de nouveau, pas de publication" >> logs/deploy.log
  fi
  if [ "$(wc -l < logs/deploy.log)" -gt 1000 ]; then tail -n 400 logs/deploy.log > logs/deploy.log.tmp && mv logs/deploy.log.tmp logs/deploy.log; fi
  sleep $((INTERVAL_MIN * 60))
done
