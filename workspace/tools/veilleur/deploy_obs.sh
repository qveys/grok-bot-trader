#!/usr/bin/env bash
# Déploie le PROTOTYPE pm-sonnette-cf (observation : aucune sonnerie) et active l'envoi d'état depuis la box.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$DIR"
source <(grep -E '^VEILLEUR_SECRET=' secrets.env)
"$DIR/wr_obs.sh" d1 execute pm-veilleur --remote --file schema.sql >/dev/null
out="$("$DIR/wr_obs.sh" deploy 2>&1)" || { echo "$out" | tail -20; exit 1; }
url="$(echo "$out" | grep -oE 'https://pm-sonnette-cf\.[a-z0-9-]+\.workers\.dev' | head -1)"
printf '%s' "$VEILLEUR_SECRET" | "$DIR/wr_obs.sh" secret put BATTEMENT_SECRET >/dev/null
[[ -n "$url" ]] || { echo "URL introuvable"; echo "$out" | tail -10; exit 1; }
grep -q '^VEILLEUR_OBS_URL=' secrets.env && sed -i "s#^VEILLEUR_OBS_URL=.*#VEILLEUR_OBS_URL=$url#" secrets.env || echo "VEILLEUR_OBS_URL=$url" >> secrets.env
chmod 600 secrets.env; echo "Prototype déployé : $url (observation, logs seulement)"
