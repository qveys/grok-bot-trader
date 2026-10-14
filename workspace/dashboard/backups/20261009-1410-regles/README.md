# Équipe trading — Tableau de bord

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
  Fraîcheur dans l'en-tête, sous « TABLEAU DE BORD » (`#fresh`, recalculée toutes les 5 s) : « ● à jour il y a 30 s » = âge de l'envoi direct (sinon le plus récent entre prix et page). Point vert < 2 min, orange 2–10 min (ou prix anciens), rouge > 10 min. Détail prix / page / direct au survol (infobulle) et au toucher. La bande de prix ne montre que BTC, ETH, SOL (retour à la ligne, jamais coupée).
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
  et `data/deploy.json` (heure de publication → l'en-tête affiche « Publié il y a … » si l'envoi direct est absent),
  lance `cloudflare/check_secrets.py` (refuse si jeton, mot de passe, clé privée, .env, config revx…), puis
  `wrangler pages deploy public --branch main` (wrangler local : `/workspace/tools/wrangler/wrangler.sh`, Node 22 local
  dans `/workspace/tools/node22`, via le proxy).
- Mot de passe : `python3 cloudflare/set_secret.py` (re)pose `DASHBOARD_PASSWORD` depuis l'environnement (prod + preview).
- Vérification : `python3 cloudflare/verify.py` (401 sans / mauvais identifiants, 200 avec ; titre « Équipe trading », fraîcheur sur 1 ligne dans l'en-tête, bande de prix complète sans défilement horizontal à 1440 et 375 px) ;
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
le plus récent connu du navigateur (prices.json ou /api/live) < 2 min → « En marche » ; sinon, si le build a vu le
pid vivant et des ticks frais → « En marche (dernière mise à jour) » ; sinon « Arrêté ? » avec l'âge du dernier prix.

**Mode quasi direct (source unique).** La box pousse UN paquet (contenu de `site/data/{prices,summary,trades,performance,research,news}.json`
= prix du collecteur 30 s + données des bots) vers Cloudflare, seulement s'il a changé. La fonction `functions/api/live.js`
(`GET /api/live?f=…`, derrière le même mot de passe) le sert ; le navigateur l'interroge toutes les 30 s et ne relit les fichiers
publiés que si `/api/live` répond `available:false` (réessai toutes les 5 min). Aucune autre source de prix.
- Envoi : `cloudflare/push_live_loop.sh` (vérifie toutes les 10 s, lancé par `start.sh`, arrêté par `stop.sh`), script
  `cloudflare/d1/push_live.py` (refuse d'envoyer si `check_secrets.py` trouve quelque chose ; plafond d'écritures/jour).
  Log : `logs/push_live.log`. Config (aucun secret) : `cloudflare/d1/live.json`.
- **D1 (actif depuis le 8 oct. 2026, 23h22)** : base `pm-pipeline-live`, binding `LIVE_DB` (production + aperçus), table
  `live_files` (`cloudflare/d1/schema.sql`), une ligne par fichier, envoi à chaque changement (prix toutes les 30 s ;
  ~4 000 écritures/jour, limite gratuite 100 000, plafond de sécurité 90 000). Mise en place : `python3 cloudflare/d1/setup.py`
  (jeton avec **Account › D1 › Edit**), puis `cloudflare/deploy.sh`. `verify.py` exige `store=d1` et un envoi de moins de 90 s.
- **KV abandonné** : l'ancien chemin Workers KV (envoi toutes les 2 min) est retiré du code et le binding `LIVE` est détaché du projet.
  Le namespace KV `pm-pipeline-live` existe encore (non supprimé, inutilisé). Ancien script : `backups/20261008-2322-d1switch/`.
- **Publication** : `cloudflare/deploy.sh` prend un verrou (`logs/deploy.lock`, `flock`) : la boucle 15 min et les publications
  à la main ne tournent jamais en même temps.

## Passages des routines (8 oct., soir)

Accueil › onglet **Journal des cycles** › section « Passages des routines ». Source unique (lecture seule) :
`state/routine_runs.jsonl`, écrit par `/workspace/tools/routine_log/log.py` (une ligne `demarre` / `fini` / `arret` par étape).
`build.py` (`load_routine_runs`) garde les 7 derniers jours (300 lignes max) dans `summary.json` → `routine_runs`, donc aussi
dans le paquet direct `/api/live`. Le navigateur apparie chaque `demarre` au `fini`/`arret` suivant du même bot + routine :
✅ Fini, ⛔ Arrêt, ⏳ En cours (< 30 min sans fin), ❓ Pas fini (> 30 min sans fin). Filtre par bot. Test sans toucher au vrai
fichier : `ROUTINE_RUNS_FILE=/chemin/exemple.jsonl python3 build.py` dans une copie du dossier. `cloudflare/verify.py` vérifie la
section (code, build, envoi direct).

## Zones de prix de PM-Predict + 3 sonnettes (8 oct., 21h40)

- **Analyses › Prévisions** (`research.html#predict`, ex-« Avis Predict ») : section « Zones de prix du jour », une ligne par zone
  (paire en couleur de la monnaie, 📈 à la hausse / 📉 à la baisse, prix de la zone, fin, statut active/expirée/coupée, prix actuel + écart).
  Source unique : `state/zones_reveil.json` (lecture seule, refait par Predict chaque jour vers 14h55) → `load_sonnette()` →
  `summary.sonnette.zones` (+ `zones_updated`, `enabled`) → même paquet `/api/live`. Statut et écart recalculés dans le navigateur à chaque prix.
  L'onglet Accueil › Sonnette ne montre plus que le nombre de zones + un lien (pas de doublon).
- Sonnette : 3 sonnettes (Predict, Risk, Compound) — `compound_mode` et `today.compound` ajoutés depuis `status.json`.
- Carte PM-Predict : horaire « 14h55 zones de prix du jour · avis sur demande ».
- `cloudflare/verify.py` vérifie aussi les zones (code, build, envoi direct). Sauvegarde avant modif : `backups/20261008-*-zones/`.

## Nettoyage Décisions écrites + Prix Research + Règles communes (8 oct., 21h50)

- **Décisions écrites** (Analyses) : `parse_decision_log()` ignore les blocs `### … Test du passé …` / bilan Compound / vibe-trading
  sans id `D-xxx` (ce sont des bilans de tests, pas des décisions). Ils restent lisibles dans le carnet ; les tests eux-mêmes sont
  dans Performance › Tests du passé (source vibe-trading, inchangée). `app.js` refiltre : seules les cartes `D-\d+` s'affichent.
- **Dernier point PM-Research** : `last_research.prix` est un objet par paire → `prixHtml()` (« BTC 73 588 € −1,0 % · ETH … »,
  couleur de la monnaie). `esc()` passe par `plain()` : un objet ou une liste ne s'affiche plus jamais « [object Object] ».
- **Règles communes** (À propos `#regles`) : source unique `references/regles-litterature.md` (PM-Orchestrator, lecture seule) →
  `load_team_rules()` → `summary.team_rules` (même paquet `/api/live`). 2 règles officielles en haut, puis groupes repliés
  Simulation / Live / Horaires / Surveillance et sonnettes / Équipe et carnets. Date = heure de modification du fichier.
  Plus aucune copie en dur des règles (les cartes « Simulation ou réel » ont été retirées). Les id de groupes ne sont pas affichés.
- `cloudflare/verify.py` : vérifie la date des règles (build + envoi direct = mtime du fichier) et rend les pages en ligne
  (Playwright, `.venv-shot/bin/python cloudflare/verify.py`) : échec si « [object Object] » ou une décision « Test du passé » sans id.
- Sauvegarde avant modif : `backups/20261008-2148-decisions/`.

## Règle : le site AFFICHE, il ne calcule pas (9 oct. 2026)

Chaque chiffre métier vient tel quel du fichier de son propriétaire. build.py copie, app.js met en forme (arrondi, « il y a X s »,
couleur d'un verdict déjà écrit). Seules exceptions : les prix du marché (collecteur de Scan) et les compteurs de lignes.

| Chiffre affiché | Fichier lu | Propriétaire |
|---|---|---|
| Valeur, liquidités, sommet, baisse, résultat du jour, positions (sens, quantité, prix, stop, objectif, valeur) | guardian/state.json | PM-Risk |
| Rapprochement : départ + Σ realized_pnl_eur fermés + Σ unrealized_pnl_eur ouverts − Σ fee_eur ouverts ; si ≠ equity_eur → « écart X € » | guardian/state.json | PM-Risk |
| Plafonds | guardian/config.json | PM-Risk |
| Résultat de chaque trade, cycles « vendre d'abord » (objectif, sécurité, gains) | state/trades_log.jsonl | outils PM-Risk |
| Chiffres globaux (gain réalisé, taux de réussite, trades terminés…) | state/performance.json | PM-Compound (scripts/performance.py) |
| « Test du passé réussi » / « Autorisé en réel » | verdict_equipe.test_du_passe_reussi / verdict_equipe.autorise_en_reel dans le fichier du test ; absent → gris « non évalué par l'équipe » | PM-Compound / PM-Risk |
| Capital réel, pièces hors bot (€), soldes Revolut X (disponible / réservé / staké / €), MetaMask (ETH, €), total réel | state/live_equity.json (soldes_revolut_x, metamask, total_reel_eur) | outil sonnette (live_equity.py) |
| Compteurs des sonnettes (du jour ; vrais réveils / essais / dernier vrai) | tools/sonnette/state/status.json (today.*, totals.<bot>.{vrais,essais,dernier_vrai}, recalculés de rings.jsonl à chaque sonnerie) | outil sonnette |
| Achats réels du jour | state/live_day.json | PM-Risk |
| Ordres réels (historique) | Revolut X order history / transactions (lecture seule) + state/live_orders.jsonl | — / PM-Risk |

Le site ne lit plus aucun solde (ni `revx account balances`, ni MetaMask) : retirés de la liste blanche revx de build.py.

`cloudflare/verify.py` vérifie l'égalité exacte (build, envoi direct et page) pour le portefeuille, le rapprochement, les trades,
les cycles, performance.json, les verdicts des tests, la sonnette et live_equity.json, et que les fonctions de calcul ont disparu.
