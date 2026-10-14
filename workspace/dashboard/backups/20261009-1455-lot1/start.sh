#!/usr/bin/env bash
# Démarre : build complet toutes les 5 min + prix toutes les 30 s + serveur web local (0.0.0.0:8080)
# + publication Cloudflare Pages toutes les 15 min si les données ont changé (si CLOUDFLARE_API_TOKEN est dans l'env)
# + mode « quasi direct » : envoi du paquet de données vers Cloudflare (Cloudflare D1) dès qu'il change.
cd "$(dirname "$0")"
mkdir -p logs
running() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }
if running refresh_loop.pid; then echo "refresh 5 min déjà en marche (pid $(cat refresh_loop.pid))";
else nohup ./refresh_loop.sh > /dev/null 2>&1 & echo "refresh 5 min démarré (pid $!)"; fi
if running prices_loop.pid; then echo "prix 30 s déjà en marche (pid $(cat prices_loop.pid))";
else nohup ./prices_loop.sh > /dev/null 2>&1 & echo "prix 30 s démarré (pid $!)"; fi
if running server.pid; then echo "serveur déjà en marche (pid $(cat server.pid))";
else nohup python3 -m http.server 8080 --bind 0.0.0.0 --directory "$PWD/site" > logs/server.log 2>&1 & echo $! > server.pid; echo "serveur démarré (pid $!) → http://localhost:8080/"; fi
if running deploy_loop.pid; then echo "publication 15 min déjà en marche (pid $(cat deploy_loop.pid))";
elif [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then echo "publication Cloudflare NON démarrée : CLOUDFLARE_API_TOKEN absent de l'environnement";
else nohup ./deploy_loop.sh > /dev/null 2>&1 & echo "publication 15 min démarrée (pid $!) → https://pm-pipeline-tableau.pages.dev/"; fi
if running push_live_loop.pid; then echo "envoi direct déjà en marche (pid $(cat push_live_loop.pid))";
elif [ -z "${CLOUDFLARE_API_TOKEN:-}" ] || [ ! -f cloudflare/d1/live.json ]; then echo "envoi direct NON démarré : jeton absent ou cloudflare/d1/live.json manquant (lancer cloudflare/d1/setup.py)";
else nohup ./cloudflare/push_live_loop.sh > /dev/null 2>&1 & echo "envoi direct démarré (pid $!) → /api/live"; fi
