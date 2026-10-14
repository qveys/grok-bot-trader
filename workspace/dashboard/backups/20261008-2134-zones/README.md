# PM Pipeline — Tableau de bord

Site statique (HTML + JS + CSS, Chart.js copié en local) qui montre l'équipe de bots
`/workspace/predict-market-bot` : portefeuille simulé et réel, cycles, journal, trades,
décisions, performance, analyses, actualités. **Aucun appel IA. Aucune commande d'ordre.**
Mise en page inspirée de tbot.augustwheel.com (structure et ambiance seulement : code et textes sont propres à ce projet).

## Fichiers
- `build.py` : relit les sources (lecture seule) et écrit `site/` (copie de `src/` + `site/data/*.json`).
- `src/` : pages (`index, trades, performance, research, news, about`.html), `app.js`, `style.css` (mobile d'abord).
- `site/` : le site prêt à publier (dossier statique). `site/data/*.json` = données.
- `data/news.json` : actualités fusionnées, à lire par les bots (PM-Research).
- `config.json` : `SHOW_REAL` (soldes réels + adresse du portefeuille), proxy, chemins.
- `cache/` : dernières valeurs connues (prix, soldes, Fear & Greed, RSS) en cas de panne réseau.
- `refresh_loop.sh` : build complet toutes les 5 min.
- `prices.py` + `prices_loop.sh` : prix en direct toutes les 30 s → `site/data/prices.json` (lit seulement les ticks du collecteur, aucun réseau). Les pages relisent prices.json toutes les 30 s ; « ancien » si dernier tick > 2 min.
- `start.sh` / `stop.sh` : démarrent / arrêtent les 2 boucles + le serveur local.
- `screenshot.py` : captures headless (Chrome système via Playwright dans `.venv-shot`) + contrôle du débordement mobile.

## Utilisation
```bash
cd /workspace/dashboard
./start.sh          # lance refresh_loop.sh (build toutes les 5 min) + http.server 0.0.0.0:8080
./stop.sh           # arrête tout (ou: kill $(cat refresh_loop.pid) $(cat prices_loop.pid) $(cat server.pid))
python3 build.py    # régénérer à la main
SHOW_REAL=false python3 build.py   # version sans soldes réels (pour publier)
.venv-shot/bin/python screenshot.py   # captures dans screenshots/
```
Pas de crontab sur la boîte → boucle `nohup`. Elle ne redémarre pas toute seule après un redémarrage de la boîte : relancer `./start.sh`.

## Sources lues (lecture seule)
- `guardian/state.json`, `guardian/config.json`, `config.json`, `MODE`, fichiers `STOP`/`HALTED`/`LIVE_ONCE` (présence seulement)
- `state/trades_log.jsonl`, `state/live_orders.jsonl` (si présent), `state/live_day.json`, `state/scan_history.jsonl`,
  `state/last_scan*.json`, `state/last_predict.json`, `state/predictions_log.jsonl`, `state/last_research.json`,
  `state/research_briefs/*`, `state/alerts_last.json`, `state/buy_wake.json`, `state/auto_stop_events.jsonl`, `state/price_ticks/*`
- `knowledge/trading_journal.md`, `decision_log.md`, `failure_log.md`, `predict_scorecard.md`, `bot_journals/*.md`
- revx en LECTURE SEULE (liste blanche `REVX_ALLOWED` dans build.py) : `account balances`, `market tickers/candles`,
  `order history --start-date 2026-10-06`, `order open`, `transaction list --start-date 2026-10-06` (+ `order fills/get`, `trade private` autorisés).
  `place`, `cancel`, `replace` sont refusés par le code.
- Argent réel : trades = ordres Revolut X remplis depuis PROJECT_START (2026-10-06), achats/ventes appariés FIFO par crypto ;
  avoirs de départ = solde actuel − mouvements depuis le début ; tag « bot » si l'ordre figure dans `state/live_orders.jsonl`.
- RPC public Arbitrum `eth_getBalance` (MetaMask), `vibe-trading/backtest.sh sentiment --json` (cache 30 min),
  `vibe-trading/home/runs/*/artifacts/metrics.csv`, `vibe-trading/checks/*.json`
- RSS CoinDesk, CoinTelegraph, Decrypt (via proxy 127.0.0.1:8791)

## Vie privée
`SHOW_REAL=true` en local. Avant toute publication : `SHOW_REAL=false` **et** protéger le site par mot de passe
(les journaux des bots et le carnet des décisions sont aussi des infos personnelles).

## Version en ligne (Cloudflare Pages)

- URL : https://pm-pipeline-tableau.pages.dev/ — identifiant `quentin`, mot de passe = secret Cloudflare `DASHBOARD_PASSWORD`
  (production ET aperçus `<hash>.pm-pipeline-tableau.pages.dev`). Sans secret configuré, le site répond 503 (échec fermé).
- Protection : `cloudflare/functions/_middleware.js` (HTTP Basic Auth sur toutes les URL, y compris `/data/*.json`,
  comparaison à temps constant, 401 + `WWW-Authenticate`, en-tête `X-Robots-Tag: noindex`). Seule exception : `/robots.txt`
  (`Disallow: /`, aucune donnée).
- Publication : `deploy_loop.sh` (lancé par `start.sh`, arrêté par `stop.sh`) toutes les 15 min (`DEPLOY_INTERVAL_MIN`),
  seulement si le hash de `site/data/*.json` + html/js/css a changé. Une publication à la main : `./cloudflare/deploy.sh`.
- `cloudflare/deploy.sh` copie uniquement `site/` (html/js/css/json/png/svg) dans `cloudflare/public/`, ajoute `robots.txt`
  et `data/deploy.json` (heure de publication → les pages affichent « version en ligne, publiée toutes les ~15 min »),
  lance `cloudflare/check_secrets.py` (refuse si jeton, mot de passe, clé privée, .env, config revx…), puis
  `wrangler pages deploy public --branch main` (wrangler local : `/workspace/tools/wrangler/wrangler.sh`, Node 22 local
  dans `/workspace/tools/node22`, via le proxy).
- Mot de passe : `python3 cloudflare/set_secret.py` (re)pose `DASHBOARD_PASSWORD` depuis l'environnement (prod + preview).
- Vérification : `python3 cloudflare/verify.py` (401 sans / mauvais identifiants, 200 avec) ;
  captures : `.venv-shot/bin/python shot_hosted.py` → `screenshots/hosted-*.png`.
- Journal : `logs/deploy.log`. Les identifiants ne sont jamais écrits dans un fichier : ils viennent de l'environnement.

## Ajouts du 8 oct. (après-midi)

| Bloc (page) | Source (lecture seule) | Écrit par |
|---|---|---|
| Vendre d'abord — cycles (Trades > onglet, Performance) | `state/trades_log.jsonl` : ligne `side=sell` d'ouverture (marquée `kind/strategy/decision_id` = sell_first / sell_rebuy / D-018, ou `role=open`, ou vente sans position simulée ouverte) + ligne `side=buy` de rachat liée (`cycle_id`, `linked_position_id`, `parent_id`, `sell_id`… = id de la vente, ou marquée `rebuy`/`rachat`) | paper_fill / watch_stops (à venir) |
| Vendre d'abord — décisions | `knowledge/decision_log.md` (D-018 ou texte « vendre haut / racheter plus bas ») | PM-Predict |
| Pièces disponibles à vendre (Accueil, Performance) | `revx account balances --json` (available / staked / reserved) + MetaMask `eth_getBalance` | — |
| Capital réel du bot (Accueil, Performance) | `state/live_equity.json` | tools/sonnette/live_equity.py |
| Sonnette (Accueil) | `tools/sonnette/state/status.json` + `rings.jsonl` (champs choisis ; `secrets.env` jamais lu ; URL masquées) + `state/zones_reveil.json` | tools/sonnette |
| Tests du passé « vendre d'abord » (Performance) | `tools/vibe-trading/home/runs/*/summary.json` (sell_rebuy et sell_rebuy_robust) + `rapport_fr.md` (« En clair ») ; doublons cachés | vt_sellrebuy.py |
| Autres rapports (Performance) | `tools/vibe-trading/reports/**/*.json|md` si le dossier apparaît | — |

## Nettoyage + mode « quasi direct » (8 oct., fin d'après-midi)

**Une seule place par information.** Accueil en onglets (`#apercu`, `#reel`, `#cycles`, `#sonnette`), Performance en onglets
(`#simulation`, `#reel`, `#monnaies`, `#tests`), Analyses en onglets (`#marche`, `#predict`, `#decisions`, `#score`, `#archives`, `#journaux`).
L'onglet choisi est gardé dans l'adresse (#…). Trades : une ligne par achat ou vente, colonnes **Sens** (Achat/Vente) et **Type**
(Sim/Réel + « à la hausse » / « à la baisse »), filtres Tous/Simulation/Réel et Toutes/Achats/Ventes/À la hausse/À la baisse ;
les deux lignes d'un même trade portent le même numéro (`#2 1/2`, `#2 2/2` ; idée à la baisse : `B1 1/2` vente puis `B1 2/2` rachat).
Vocabulaire : « idée à la hausse » / « idée à la baisse » (D-018). L'ancienne expression est remplacée même dans les textes des
bots/outils (`build.py`, `write_json`).

**Collecteur de prix « Arrêté » à tort — cause :** le statut venait du build (pid vu + seuil de 180 s sur `last_ok`) et était
recalculé côté navigateur à partir de l'heure du dernier tick figée dans `summary.json` ; sur la version en ligne (publiée toutes
les ~15 min) et entre deux builds (5 min), ce tick avait toujours plus de 2-3 min → « Arrêté ». Correction : statut = âge du prix
le plus récent connu du navigateur (prices.json ou /api/live) < 2 min (4 min en KV) → « En marche » ; sinon, si le build a vu le
pid vivant et des ticks frais → « En marche (dernière mise à jour) » ; sinon « Arrêté ? » avec l'âge du dernier prix.

**Mode quasi direct (source unique).** La box pousse UN paquet (contenu de `site/data/{prices,summary,trades,performance,research,news}.json`
= prix du collecteur 30 s + données des bots) vers Cloudflare, seulement s'il a changé. La fonction `functions/api/live.js`
(`GET /api/live?f=…`, derrière le même mot de passe) le sert ; le navigateur l'interroge toutes les 30 s et ne relit les fichiers
publiés que si `/api/live` répond `available:false` (réessai toutes les 5 min). Aucune autre source de prix.
- Envoi : `cloudflare/push_live_loop.sh` (vérifie toutes les 10 s, lancé par `start.sh`, arrêté par `stop.sh`), script
  `cloudflare/d1/push_live.py` (refuse d'envoyer si `check_secrets.py` trouve quelque chose ; plafond d'écritures/jour).
  Log : `logs/push_live.log`. Config (aucun secret) : `cloudflare/d1/live.json`.
- **D1 (prévu)** : binding `LIVE_DB`, table `live_files` (`cloudflare/d1/schema.sql`), une ligne par fichier, envoi à chaque
  changement (≈ 30 s ; ~4 000 écritures/jour, limite gratuite 100 000). Activation : jeton avec **Account › D1 › Edit**, puis
  `python3 cloudflare/d1/setup.py` (crée `pm-pipeline-live`, la table, relie LIVE_DB en production + aperçus, écrit live.json
  provider=d1), puis `cloudflare/deploy.sh` (le binding s'applique au déploiement suivant). Rien d'autre à changer.
- **KV (provisoire, actif)** : le jeton actuel n'a PAS D1 (API D1 → 401) mais a Workers KV. Namespace `pm-pipeline-live`,
  binding `LIVE` (production + aperçus) créés par `cloudflare/d1/setup_kv.py`. KV gratuit = 1 000 écritures/jour, donc envoi
  d'un seul blob au plus toutes les 2 min (≤ 720/jour, plafond de sécurité 950). Prix en ligne : âge typique 30 s – 3 min.
  Dès que D1 est configuré, la fonction préfère D1 et le script passe à l'envoi toutes les ~30 s.

## Passages des routines (8 oct., soir)

Accueil › onglet **Journal des cycles** › section « Passages des routines ». Source unique (lecture seule) :
`state/routine_runs.jsonl`, écrit par `/workspace/tools/routine_log/log.py` (une ligne `demarre` / `fini` / `arret` par étape).
`build.py` (`load_routine_runs`) garde les 7 derniers jours (300 lignes max) dans `summary.json` → `routine_runs`, donc aussi
dans le paquet direct `/api/live`. Le navigateur apparie chaque `demarre` au `fini`/`arret` suivant du même bot + routine :
✅ Fini, ⛔ Arrêt, ⏳ En cours (< 30 min sans fin), ❓ Pas fini (> 30 min sans fin). Filtre par bot. Test sans toucher au vrai
fichier : `ROUTINE_RUNS_FILE=/chemin/exemple.jsonl python3 build.py` dans une copie du dossier. `cloudflare/verify.py` vérifie la
section (code, build, envoi direct).
