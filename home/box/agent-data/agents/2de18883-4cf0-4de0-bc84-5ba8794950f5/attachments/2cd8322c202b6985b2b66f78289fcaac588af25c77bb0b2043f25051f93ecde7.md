# Installer le bot de trading sur ton serveur (guide simple)

Avant tout : sur la boîte, arrête tout ou mets le trading en pause. **Deux machines ne doivent jamais trader en même temps.** Refais ensuite une archive fraîche si tu veux les données les plus récentes.

## 1. Copier les fichiers
Depuis ton ordinateur, récupère le dossier `/workspace/export/` de la boîte, puis :
```
scp migration-20261013.tar.gz secrets.tar.gz.gpg SHA256SUMS moi@serveur:~
ssh moi@serveur
sha256sum -c SHA256SUMS          # tout doit dire OK
sudo mkdir -p /workspace && sudo chown $USER /workspace
tar xzf migration-20261013.tar.gz -C /   # crée /workspace/... et home/box/...
```
Garde les mêmes chemins (`/workspace/...`). Les scripts les utilisent. Les fichiers `home/box/...` sont surtout là pour référence. Copie `home/box/.config/.wrangler` dans ton `~/.config/` si tu veux.

## 2. Installer les logiciels
```
sudo apt install python3 python3-venv python3-pip gnupg curl
# Node 22 (via nodejs.org ou nvm)
cd /workspace/guardian && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd /workspace/tools/wrangler && npm install
cd /workspace/tools/vibe-trading && python3 -m venv .venv && .venv/bin/pip install -r /workspace/export/inventory/pip-freeze-vibe-trading-venv.txt
npm install -g @revolut/revolut-x-cli      # commande revx
pip install -r /workspace/export/inventory/pip-freeze-system.txt   # si un script réclame un module
```

## 3. Remettre les secrets
Le mot de passe est dans `PASSPHRASE.txt`. Transmets-le à part, jamais avec l'archive.
```
gpg -d secrets.tar.gz.gpg > s.tar.gz     # colle le mot de passe
tar xzf s.tar.gz -C / && rm s.tar.gz
mkdir -p ~/.config && mv /home/box/.config/revolut-x ~/.config/   # si ton utilisateur n'est pas « box »
chmod 600 /workspace/*/secrets.env /workspace/**/.env ~/.config/revolut-x/*
```
Pense aussi à mettre à jour `private_key_path` dans ~/.config/revolut-x/config.json si le chemin change.
Important : ajoute l'adresse IP du serveur dans les clés API Revolut X (liste blanche d'IP) si tu l'utilises.
Supprime la ligne proxy `127.0.0.1:8791` (propre à la boîte) : `export HTTPS_PROXY= HTTP_PROXY= ALL_PROXY=` avant de lancer les scripts, ou retire-la de `start_price_ticks.sh` et `~/.local/bin/revx`.

## 4. Démarrer, dans cet ordre
1. Gardien : `cd /workspace/guardian && GUARDIAN_HOME=/workspace/guardian GUARDIAN_ENV=/workspace/guardian/.env deploy/run.sh start` (ou le service systemd `deploy/grok-bot.service`)
2. Collecteur de prix : `/workspace/predict-market-bot/scripts/start_price_ticks.sh`
3. Surveillance des stops (seulement s'il y a une position ouverte) : `nohup /workspace/predict-market-bot/guardian/scripts/start_stop_watch.sh &`
4. Sonnette (lance aussi le battement du veilleur) : `/workspace/tools/sonnette/start.sh`
5. Tableau de bord : `set -a; . /workspace/tools/veilleur/secrets.env; set +a; /workspace/dashboard/start.sh` (le fichier doit contenir CLOUDFLARE_API_TOKEN)

Pour tout relancer après un redémarrage du serveur, mets ces commandes dans un `@reboot` de `crontab -e`.

## 5. Vérifier
- `ps aux | grep -E 'guardian|sonnette|battement|collect_price|watch_stops|loop'` : chaque programme doit être là.
- `curl -s 127.0.0.1:8750/…` (le gardien répond) ; `/workspace/tools/sonnette/status.sh`
- `tail /workspace/predict-market-bot/state/price_ticks/collector.log` : de nouveaux prix toutes les 30 s.
- Le site https://pm-pipeline-tableau.pages.dev se met à jour (les données Cloudflare restent sur ton compte, rien à déplacer).
- Le veilleur Cloudflare ne doit plus signaler « boîte muette ».

## 6. Les bots eux-mêmes
Les bots sont des agents IA de l'app Grok Bot. Ils ne tournent pas sur le disque. Sur ton serveur, il faut les remplacer par un planificateur (cron) qui appelle une IA (API d'un LLM) avec leurs instructions (`home/box/agent-data/agents/*/profile.json`, champ « description »). Ce que fait chacun :
- **PM-Orchestrator** : coordonne la chaîne Scan → Research → Predict → Risk → Compound (ETH-EUR, SOL-EUR), en mode simulation tant que tu n'as pas dit « passe en live ».
- **PM-Scan** : lance `scripts/scan_crypto.py`, classe les paires et transmet à Research. Ne passe aucun ordre.
- **PM-Research** : résume l'actualité et l'ambiance du marché pour les paires signalées.
- **PM-Predict** : juge s'il y a un avantage à acheter ou à vendre (seuils dans config.json). Sinon : « pas de trade ».
- **PM-Risk** : valide chaque trade (`validate_order.py`) puis simule l'ordre (`paper_fill.py`). Respecte STOP/HALTED.
- **PM-Compound** : fait le bilan après un trade (failure_log.md, performance.py) et alerte si les pertes dépassent les limites.
- **PM-Dev** : maintient le tableau de bord (/workspace/dashboard). Pas de trading.
- **Ca$her** : bot « organisme » qui suit /workspace/bot/INSTRUCTIONS.md. Toutes les 30 min : `wake.sh`, puis il décide et envoie avec `decide.sh` au gardien. Sa routine est actuellement **désactivée**.
- **Grok Bot** : assistant principal qui répartit les demandes entre les bots.
Leurs routines (heures et textes) sont listées dans INVENTAIRE.md. Les textes exacts sont à recopier depuis l'app.
Les compétences des bots (méthodes) sont dans `home/box/agent-data/workflows/*/SKILL.md`.
