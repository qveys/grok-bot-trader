#!/usr/bin/env bash
# Publie UNE fois le site construit (site/) + la protection (functions/) sur Cloudflare Pages.
# Copie dans cloudflare/public/ (jamais rien d'autre que site/), vérifie qu'aucun secret n'y traîne, puis déploie.
# Identifiants lus dans l'environnement (CLOUDFLARE_API_TOKEN) ; rien n'est affiché ni écrit.
set -euo pipefail
cd "$(dirname "$0")"
PROJECT="${CF_PAGES_PROJECT:-pm-pipeline-tableau}"
INTERVAL_MIN="${DEPLOY_INTERVAL_MIN:-15}"
SITE=../site
[ -n "${CLOUDFLARE_API_TOKEN:-}" ] || { echo "CLOUDFLARE_API_TOKEN absent" >&2; exit 2; }
[ -f "$SITE/index.html" ] && [ -f "$SITE/data/summary.json" ] || { echo "site/ incomplet" >&2; exit 3; }

# 1) copie propre (liste blanche de types de fichiers ; pas de .tmp, pas de fichiers cachés)
rm -rf public.new && mkdir -p public.new
( cd "$SITE" && find . -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.json' -o -name '*.png' -o -name '*.svg' -o -name '*.ico' \) \
    ! -name '.*' ! -path '*/.*' -print0 ) | while IFS= read -r -d '' f; do
  mkdir -p "public.new/$(dirname "$f")"; cp -p "$SITE/$f" "public.new/$f"
done
cp robots.txt public.new/robots.txt
python3 - "$INTERVAL_MIN" > public.new/data/deploy.json <<'PY'
import json, sys, datetime
print(json.dumps({"deployed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "interval_min": int(sys.argv[1]), "host": "cloudflare-pages"}))
PY

# 2) garde-fou : aucun secret dans ce qui part en ligne
if ! python3 check_secrets.py public.new functions; then
  echo "$(date '+%F %T') ABANDON : contenu sensible détecté dans la copie à publier" >&2; rm -rf public.new; exit 4
fi
rm -rf public && mv public.new public

# 3) déploiement (branche main = production)
/workspace/tools/wrangler/wrangler.sh pages deploy public --project-name "$PROJECT" --branch main --commit-dirty=true \
  --commit-message "auto $(date '+%F %H:%M')" 2>&1 | grep -vE '^\s*$|Proxy environment variables' | tail -4
