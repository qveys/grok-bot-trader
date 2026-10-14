#!/usr/bin/env bash
# Déploie le Worker pm-veilleur, pose le secret BATTEMENT_SECRET et note l'URL dans secrets.env.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$DIR"
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN manquant}"
source <(grep -E '^VEILLEUR_SECRET=' secrets.env)
"$DIR/wr.sh" d1 execute pm-veilleur --remote --file schema.sql >/dev/null
out="$("$DIR/wr.sh" deploy 2>&1)" || { echo "$out" | tail -20; exit 1; }
url="$(echo "$out" | grep -oE 'https://pm-veilleur\.[a-z0-9-]+\.workers\.dev' | head -1)"
printf '%s' "$VEILLEUR_SECRET" | "$DIR/wr.sh" secret put BATTEMENT_SECRET >/dev/null
if [[ -n "$url" ]]; then
  sed -i "s#^VEILLEUR_URL=.*#VEILLEUR_URL=$url#" secrets.env; chmod 600 secrets.env
  echo "Worker déployé : $url"
else
  echo "Déployé, mais URL workers.dev introuvable dans la sortie :"; echo "$out" | tail -15
fi
