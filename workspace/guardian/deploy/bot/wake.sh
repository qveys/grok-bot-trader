#!/usr/bin/env bash
# Grok Bot : récupérer le réveil en attente. Sortie : le contexte (code 200) ou "NO_WAKE" (204).
set -euo pipefail
: "${GUARDIAN_URL:=http://127.0.0.1:8750}"
[ -n "${GUARDIAN_TOKEN:-}" ] || { echo "GUARDIAN_TOKEN manquant" >&2; exit 2; }
code=$(curl -s -o /tmp/wake.txt -w "%{http_code}" -H "Authorization: Bearer $GUARDIAN_TOKEN" "$GUARDIAN_URL/wake")
case "$code" in
  200) cat /tmp/wake.txt ;;
  204) echo "NO_WAKE" ;;
  *)   echo "ERREUR HTTP $code" >&2; exit 1 ;;
esac
