#!/usr/bin/env bash
# Branche Telegram sur le veilleur : lit $TELEGRAM_BOT_TOKEN, trouve le chat privé du dernier message
# envoyé au bot, pose TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID comme secrets du Worker, envoie un test.
# Le jeton n'est jamais affiché (ni passé en argument de commande).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$DIR"
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then echo "ERREUR : TELEGRAM_BOT_TOKEN absent de l'environnement." >&2; exit 1; fi
source <(grep -E '^VEILLEUR_(URL|SECRET)=' secrets.env)
if [[ -z "${VEILLEUR_URL:-}" ]]; then echo "ERREUR : Worker pas encore déployé (lancez d'abord ./deploy.sh)." >&2; exit 1; fi
tg() { printf 'url = "https://api.telegram.org/bot%s/%s"\n' "$TELEGRAM_BOT_TOKEN" "$1" | curl -s -m 20 -K -; }
me="$(tg getMe)"
if [[ "$(jq -r '.ok' <<<"$me")" != "true" ]]; then echo "ERREUR : jeton refusé par Telegram (getMe)." >&2; exit 1; fi
bot="$(jq -r '.result.username' <<<"$me")"
upd="$(tg getUpdates)"
chat="$(jq -r '[.result[]? | (.message // .edited_message) | select(.chat.type=="private") | .chat.id] | last // empty' <<<"$upd")"
if [[ -z "$chat" ]]; then
  echo "ERREUR : aucun message privé trouvé pour @$bot." >&2
  echo "→ Ouvrez Telegram, écrivez « bonjour » à @$bot (bouton Démarrer), puis relancez ce script." >&2
  exit 2
fi
printf '%s' "$TELEGRAM_BOT_TOKEN" | "$DIR/wr.sh" secret put TELEGRAM_BOT_TOKEN >/dev/null
printf '%s' "$chat" | "$DIR/wr.sh" secret put TELEGRAM_CHAT_ID >/dev/null
echo "Secrets Telegram posés sur pm-veilleur (bot @$bot, chat ${chat})."
sleep 3
res="$(printf 'header = "Authorization: Bearer %s"\n' "$VEILLEUR_SECRET" | curl -s -m 30 -K - -X POST "$VEILLEUR_URL/test-telegram")"
if [[ "$(jq -r '.ok' <<<"$res" 2>/dev/null)" == "true" ]]; then echo "Message de test envoyé par le Worker."
else echo "ERREUR : le Worker n'a pas pu envoyer le test ($res)." >&2; exit 3; fi
