#!/usr/bin/env bash
# Grok Bot : envoyer la décision. Usage : decide.sh /chemin/decision.json
set -euo pipefail
: "${GUARDIAN_URL:=http://127.0.0.1:8750}"
[ -n "${GUARDIAN_TOKEN:-}" ] || { echo "GUARDIAN_TOKEN manquant" >&2; exit 2; }
[ -r "${1:-}" ] || { echo "usage: decide.sh decision.json" >&2; exit 2; }
python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$1" || { echo "JSON invalide" >&2; exit 1; }
curl -s -w "\nHTTP %{http_code}\n" -X POST -H "Authorization: Bearer $GUARDIAN_TOKEN" \
     -H "Content-Type: application/json" --data @"$1" "$GUARDIAN_URL/decision"
