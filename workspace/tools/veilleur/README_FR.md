# Veilleur de l'ordinateur (Cloudflare)
- `worker/` : Worker `pm-veilleur` (POST /battement, GET /etat, POST /test-verif, POST /test-telegram ; cron */5). D1 `pm-veilleur`.
- `battement.py` + `start_battement.sh` / `stop_battement.sh` : envoie un battement toutes les 60 s (lancé aussi par `tools/sonnette/start.sh`). Log : `state/battement.log`.
- `secrets.env` (600) : VEILLEUR_SECRET, VEILLEUR_URL (rempli par deploy.sh), VEILLEUR_OBS_URL (prototype).
- `./deploy.sh` : déploie + pose le secret + écrit l'URL. Puis `./set_telegram.sh` (lit $TELEGRAM_BOT_TOKEN).
- `sonnette-cf/` + `./deploy_obs.sh` : PROTOTYPE observation (aucune sonnerie). Voir PLAN_DEPLACEMENT.md.
