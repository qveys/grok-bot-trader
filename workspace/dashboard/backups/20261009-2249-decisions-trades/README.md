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
- `config.json` : `SHOW_REAL` (soldes réels ; l'adresse du portefeuille n'est jamais publiée), proxy, chemins.
- `cache/` : dernières valeurs connues (prix, soldes, Fear & Greed, RSS) en cas de panne réseau.
- `refresh_loop.sh` : build complet toutes les 5 min.
- `prices.py` + `prices_loop.sh` : prix en direct toutes les 30 s → `site/data/prices.json` (lit seulement les ticks du collecteur, aucun réseau). Les pages relisent prices.json toutes les 30 s ; « ancien » si dernier tick > 2 min.
  Fraîcheur dans l'en-tête, sous « TABLEAU DE BORD » (`#fresh`, recalculée toutes les 5 s) : « ● à jour il y a 30 s » = âge de l'envoi direct (sinon le plus récent entre prix et page). Point vert < 2 min, orange 2–10 min (ou prix anciens), rouge > 10 min. Détail prix / page / direct au survol (infobulle) et au toucher. La bande de prix ne montre que BTC, ETH, SOL (retour à la ligne, jamais coupée).
- `start.sh` / `stop.sh` : démarrent / arrêtent les 4 boucles (build, prix, envoi direct, publication) + le serveur local (127.0.0.1:8080).
- `screenshot.py` : captures headless (Chrome système via Playwright dans `.venv-shot`) + contrôle du débordement mobile.

## Utilisation
```bash
cd /workspace/dashboard
./start.sh          # lance les 4 boucles + http.server 127.0.0.1:8080 (boîte seulement, sans mot de passe)
./stop.sh           # arrête tout (ou: kill $(cat refresh_loop.pid) $(cat prices_loop.pid) $(cat server.pid))
python3 build.py    # régénérer à la main
SHOW_REAL=false python3 build.py   # version sans soldes réels
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
Décision Quentin (9 oct. 2026) : `SHOW_REAL=true`, y compris en ligne — les soldes réels restent sur le site, **toujours
derrière le mot de passe** (Basic Auth Cloudflare). L'adresse du portefeuille MetaMask n'est **jamais** publiée :
`build.py` retire `live_equity.metamask.adresse` et masque toute adresse `0x` + 40 caractères dans les JSON construits
(donc aussi dans le paquet D1) ; `cloudflare/check_secrets.py` refuse la publication et l'envoi direct s'il en trouve une.
Le serveur local (`http.server`, sans mot de passe) n'écoute que sur 127.0.0.1:8080 (la boîte), plus sur 0.0.0.0.
Les journaux des bots et le carnet des décisions sont aussi des infos personnelles : jamais sans mot de passe.

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
  `summary.sonnette.zones` (+ `zones_updated`, `enabled`) → même paquet `/api/live`. Écart et état : écrits par la sonnette (lot 2 ci-dessous), plus calculés dans le navigateur.
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
| Contrôle avec Revolut X (gain équipe, gain Revolut, écart, heure) | guardian/state.json → rapprochement_revolut ; absent → « pas évalué » | PM-Risk |
| Plafonds | guardian/config.json | PM-Risk |
| Résultat de chaque trade, cycles (regroupés par cycle_id seulement ; objectif, sécurité, gains) | state/trades_log.jsonl | outils PM-Risk |
| Écart et état des zones (même valeur sur toutes les pages) | tools/sonnette/state/status.json → zones_distance (ecart_pct, etat) | outil sonnette |
| Chiffres globaux (gain réalisé, taux de réussite, trades terminés…) | state/performance.json | PM-Compound (scripts/performance.py) |
| « Test du passé réussi » / « Autorisé en réel » | verdict_equipe.test_du_passe_reussi / verdict_equipe.autorise_en_reel dans le fichier du test ; absent → gris « non évalué par l'équipe » | PM-Compound / PM-Risk |
| Capital réel, pièces hors bot (€), soldes Revolut X (disponible / réservé / staké / €), MetaMask (ETH, €), total réel | state/live_equity.json (soldes_revolut_x, metamask, total_reel_eur) | outil sonnette (live_equity.py) |
| Compteurs des sonnettes (du jour ; vrais réveils / essais / dernier vrai) | tools/sonnette/state/status.json (today.*, totals.<bot>.{vrais,essais,dernier_vrai}, recalculés de rings.jsonl à chaque sonnerie) | outil sonnette |
| Achats réels du jour | state/live_day.json | PM-Risk |
| Ordres réels (historique) | Revolut X order history / transactions (lecture seule) + state/live_orders.jsonl | — / PM-Risk |

Le site ne lit plus aucun solde (ni `revx account balances`, ni MetaMask) : retirés de la liste blanche revx de build.py.

`cloudflare/verify.py` vérifie l'égalité exacte (build, envoi direct et page) pour le portefeuille, le rapprochement, les trades,
les cycles, performance.json, les verdicts des tests, la sonnette et live_equity.json, et que les fonctions de calcul ont disparu.

## Règles communes (9 oct. 2026, 14h05)

La page À propos > Règles suit la structure de `references/regles-litterature.md` (PM-Orchestrator) : un groupe par titre `##`,
dans l'ordre du fichier ; les 3 parties du haut (« Règles pour les deux », « Simulation », « Réel (live) ») sont les groupes
principaux (ouverts). Les étiquettes **(Simulation)** / **(Réel)** / **(Les deux)** deviennent des pastilles, seulement là où le
fichier les écrit. Plus aucun rangement par le site. « mises à jour le … » = « version du … » du titre du fichier.
Rapprochement du portefeuille : remplacé au lot 2 par le contrôle écrit par PM-Risk (`rapprochement_revolut`), plus de somme.

## Champs PM-Risk du 9 oct. 2026 (14h22)

- guardian/state.json lu sous verrou partagé non bloquant (guardian/state.json.lock, ~3 s d'essais) ; sinon dernière copie (« verrouillé »).
  Chaque version lue est gardée dans cache/guardian_snapshots/ pour que verify.py compare chaque copie du site à SA version.
- Carte portefeuille : equity, total_pnl, exposure (simulation : plafond paper_max_exposure_pct), drawdown_pct, summary_updated_at ;
  positions : last_mid_eur, mark_eur, unrealized_pnl_eur/_pct, mark_ts.
- config.json : max_live_per_day (badge « Achats réels : n / max »), paper_max_exposure_pct, max_exposure_pct (réel).
- live_orders.jsonl (sorties) : realized_pnl_eur (net), realized_pnl_gross_eur, fees_eur tels quels.
- Verdicts des tests : formes (a) chaîne « oui/non » + par/date/raison et (b) objet {ok, valeur, par, date, raison, pourquoi} ;
  raison au survol ; gris seulement sans verdict ; *_grid : « pas de verdict (grille d'essais) ».

## Lot 1 de l'audit (9 oct. 2026, 14h55–15h10)

Sauvegarde avant modif : `backups/20261009-1455-lot1/` (build.py, README.md, src/app.js, src/style.css, cloudflare/verify.py,
cloudflare/check_secrets.py, start.sh).

- **Identifiants** : `check_secrets.py` refuse tout UUID (identifiant de bot ou de groupe) dans `team_rules` ; ailleurs dans les
  JSON, seulement un avertissement, sauf sous les clés de numéro d'enregistrement `id`, `order_id`, `client_order_id`,
  `venue_order_id` (numéros d'ordre Revolut X, id de trades), autorisées. `verify.py` vérifie aussi le HTML des règles en ligne.
- **Sorties réelles** (`state/live_orders.jsonl`, live_place.py) : `load_live_log()` lit les deux formes (ordre d'achat
  `cmd/stdout/order` et sortie `kind=auto_exit` avec `attempts[]`). `bot_orders` porte tels quels `kind`, `status` (+ libellé),
  `quote_eur`, `realized_pnl_eur`, `realized_pnl_gross_eur`, `fees_eur`. Les ordres remplis Revolut X sont reliés aux essais
  de sortie (`attempts[].order_id` / `client_order_id`) : tag « bot », pas de doublon (la ligne de la sortie les remplace).
  Montant d'une sortie = « Vente : X € reçus » (`quote_eur`). La décision d'une sortie = celle de son achat (`exit_for`, même
  formule que live_place). `stderr` n'est plus publié : « Ordre refusé par Revolut X (code N) ».
- **Performance › Argent réel** : résultats réels = `performance.json` → `totaux.live` (PM-Compound) tels quels ; absent → « pas évalué ».
- **Nuit sans décision** : heures = `night_sans_decision_detail.debut/fin` de la sonnette (plus de 22h/9h en dur) ; drapeau non
  écrit (null) → note neutre « Nuit pas évaluée ». Durée d'affichage inchangée (c'est la sonnette qui garde le drapeau).
- **Règles** : tableaux markdown → vrais tableaux (une carte par ligne sur petit écran) ; « version du … » accepte mois en
  toutes lettres, « 1er », « à 14h49 », « 14 h 49 », majuscules (`rule_version()`). `team_rules` note `source_sha256`,
  `source_mtime`, `built_at` : `verify.py` compare chaque copie strictement si elle a lu la version actuelle du fichier, et
  tolère un fichier modifié depuis moins de 10 min (build toutes les 5 min). Titres comptés comme build.py (`##` et plus) ;
  mois inconnu → pas de plantage.
- **Robustesse / ménage** : plafonds en % via `pct100()` (champ absent → « — », plus de build cassé). Retirés : `price_eur`,
  `fr_num`, `METAMASK_ADDRESS`/`ARBITRUM_RPC` (défauts de build.py), paramètres inutilisés de `load_real*`, `mmss` (app.js).
- **CSS** : plus de `body{overflow-x:hidden}` (cachait un vrai dépassement : pastilles des Décisions écrites, corrigé) ;
  onglets sur plusieurs lignes ; tableaux en cartes jusqu'à 1000 px, plus aucun défilement horizontal (ni page ni bloc) ;
  règles CSS en double fusionnées. Captures : `screenshots/lot1/`.
- **MetaMask / serveur local** : voir « Vie privée » ci-dessus (adresse jamais publiée, serveur local sur 127.0.0.1).
- **`verify.py --local`** : vérifications sans réseau ni fichiers des bots modifiés (fixtures en dossier temporaire, site/ servi
  par un petit serveur temporaire, Chrome sans proxy, données injectées) : identifiants, adresse 0x, sorties réelles (parseur +
  page), totaux.live, bandeau de nuit (vrai / null / faux), règles (build + page), aucun défilement à 375/768/1000/1440 px.
  `verify.py` (complet) lance d'abord ces vérifications locales puis celles en ligne.

## Lot 2 de l'audit (9 oct. 2026, 15h50–16h40) — chiffres écrits par PM-Risk / la sonnette

Sauvegarde avant modif : `backups/20261009-1550-lot2/` (build.py, README.md, src/app.js, src/style.css, cloudflare/verify.py,
cloudflare/check_secrets.py).

- **Contrôle avec Revolut X** (ex-rapprochement, Accueil › Vue d'ensemble) : `guardian/state.json → rapprochement_revolut`
  (gain_equipe_eur, gain_revolut_eur, ecart_eur, controle_at, mode, note) recopié tel quel dans `paper.rapprochement.raw`.
  Nombre → montant ; texte → recopié (« sans objet » + « (simulation) » quand PM-Risk écrit mode=simulation) ; champ ou bloc
  absent → « pas évalué ». Supprimés : la somme départ + gains (build.py `_sum`, `reconciliation`) et son affichage (app.js).
- **Cycles** : `load_cycles()` remplace `load_sell_first()`. Les lignes simulées de `state/trades_log.jsonl` sont regroupées
  UNIQUEMENT par `cycle_id` (une ligne en fait partie si son `cycle_id` vaut K, ou si son `id` vaut K — la ligne d'ouverture
  que les autres désignent, ex. D-019/D-020 « retro »). Ligne sans `cycle_id` que personne ne désigne = trade seul, jamais
  rattachée (supprimés : `open_buys`, mots-clés « rachat », appariement par `linked_position_id`). Vaut pour la hausse aussi :
  D-024a = 1 achat + 2 ventes (avant, la 2e vente écrasait la 1re). Ouvert/fermé = statut de la position du gardien (même id) ;
  ligne seule sans statut ni raison de clôture → « ❔ Inconnu ». Rachat prévu (objectif/sécurité) seulement pour un cycle
  à la baisse ouvert. `trades.json` : `cycles` (list, used_ids) remplace `sell_first`. Gains, objectifs, frais tels qu'écrits.
- **Zones** : écart = `ecart_pct` de la sonnette (`status.json → zones_distance`, zone la plus proche de chaque côté), affiché
  sans arrondi, identique sur Accueil › Sonnette et Analyses › Prévisions ; autres zones → « pas évalué ». État (dans la zone /
  au-dessus / en dessous) = champ `etat` de la sonnette s'il est écrit (paire, côté, ou {id de zone: état}) ; sinon « pas
  évalué ». Plus aucun calcul d'écart ni de « 🔔 atteinte » dans le navigateur.
- **Valeurs inventées retirées** : objectifs go/no-go (`|| 0.08`, `|| 0`), seuil (`0.5`) / intervalle (`30`) / compteur du
  réveil mouvement, multiple d'espérance (`3` dans build.py) → « pas évalué » ou « — » si le fichier ne l'écrit pas.
- **verify.py** : nouvelles vérifications locales `contrôle Revolut = Risk` (build = fichier ; absent / sans objet / chiffré
  en fixtures), `cycles: cycle_id seul` (fixtures : 2 lignes sans cycle_id restent seules, 3 lignes d'un cycle ensemble,
  chiffres tels quels), `cycles: page`, `zones: écart = sonnette` (même lecture que build.py comparée au fichier ; même valeur
  sur les 2 pages ; état injecté), `pas de valeur inventée`. En ligne : « contrôle Revolut = Risk », « cycles = cycle_id »,
  et la liste « aucun recalcul (code) » couvre les calculs retirés. Captures : `screenshots/lot2/`.

## Carte « Réveil mouvement » + règle stricte cycle_id (9 oct. 2026, 17h25–17h45)

Sauvegarde avant modif : `backups/20261009-1724-carte-mouvement/` (build.py, README.md, src/app.js, src/style.css, cloudflare/verify.py).

- **Carte Réveil mouvement** : une seule sur le site, dans Accueil › Vue d'ensemble › Cycles automatiques, à côté de
  « Collecteur de prix », avec le MÊME composant que les autres cycles (`cycleCard` / `cycleTiming` / `ledHtml` /
  `tickCountdowns`, via `mvCycle()` + `allCycles()`) : afficheur mm:ss jusqu'à `predict_mouvement.prochain_reveil_possible`
  (sonnette), « PRÊT » dans l'afficheur quand l'heure est passée, légende « prochain réveil possible (à HHhMM) », barre
  « délai écoulé » sur `intervalle_min_min`, pastille (En pause / Bientôt / Prêt / Attend une décision / Désactivé),
  mouvement par paire depuis la décision de référence tel qu'écrit (vert = monte, rouge = baisse), « N réveils
  aujourd'hui », pied « Dernier passage » = `dernier_reveil`. Ancienne carte pleine largeur supprimée (`mvBlock`, `mvText`,
  `tickMv`) : sa case sombre était vide car la couleur des chiffres (`--c`) n'était pas définie. Onglet Sonnette : un lien
  d'une ligne, sans chiffre. Note sous les cycles raccourcie (le détail « ≈ » / « – – » est dans l'info-bulle).
- **Cycles** : PM-Risk écrit maintenant `cycle_id` sur toutes les lignes (D-019/D-020, achat + stop du 6 oct.). Le repli
  « id = cycle_id d'une autre ligne » n'est plus utilisé par aucune ligne : retiré, règle stricte (cycle_id seul).
- **verify.py** : `carte mouvement: une seule` (10 pages × 375/768/1000/1440 px : exactement 1 carte, dans la grille, même
  largeur que ses voisines, composant commun, afficheur allumé, mouvements = sonnette, « prêt » en données injectées) ; en
  ligne : même contrôle sur la page publiée. Fixtures cycles : ligne sans cycle_id désignée par un autre cycle_id → reste seule.

### Ajouts à la même mise en ligne (9 oct. 2026, 17h35–17h50)
- **Notes de source en français simple** (audit #18) : plus aucun nom de fichier visible ; le détail technique est au plus dans une infobulle (`title`). Page Trades : « Simulation : chiffres de PM-Risk · Réel : historique Revolut X. »
- **Achats/ventes Revolut X hors bots** : un achat BTC-EUR non relié à un ordre de bot = « 🪙 Arrondi Revolut (petite monnaie, hors bots) » (arrondis automatiques du compte principal) ; tout autre fill non relié (autre paire ou vente) = « Hors bots (app Revolut) ». Plus de ❔. Prix affiché seulement s'il est écrit dans l'historique Revolut X (`price` / `rate` / `exchange_rate` / `average_fill_price`), sinon « — » (aucune division).
- **Zones** : `zones_distance.paires.*.{dessous,dessus}.etat` (dedans / au-dessus / en dessous) affiché tel quel à côté de l'écart (Accueil › Sonnette et Analyses › Prévisions) ; côté sans `etat` → « pas évalué ». Plus de traduction des mots de la sonnette.
- **Bandeau nuit** : « « Nuit sans décision » — la nuit dernière (8 oct.), 22h–09h » à partir de `night_sans_decision_detail.date` + `fenetre` tels qu'écrits (repli : `nuit` et heures `debut`–`fin`) ; reste affiché tant que la sonnette garde le drapeau (toute la journée).
- verify.py : nouveaux contrôles « notes simples + manuels » ; « zones » compare aussi l'état par côté avec status.json ; « bandeau nuit » teste date + fenêtre et le repli debut/fin ; contrôle en ligne de la carte mis à jour (`allCycles(s).map(cycleCard)`).
- **Numéros de décision en double** : build.py (`mark_decision_duplicates`) repère les D-xxx écrits plusieurs fois dans `knowledge/decision_log.md`, sans rien renuméroter ; chaque carte a une clé unique (`D-025#1`, `D-025#2`) donc les deux sont montrées ; liste dans `summary.json` + `research.json` → `decision_duplicates`. Écran : « ⚠️ Numéro en double (D-025) : Predict doit le corriger » sur chaque carte et en haut d'Analyses › Décisions écrites, petite note orange sur Accueil. Disparaît seul quand Predict renumérote. verify.py : « décisions: numéros uniques » = KO tant qu'il y a un doublon (pour le voir) mais ne bloque PAS la publication (deploy.sh / check_secrets ne le lisent pas) ; « décisions: rendu doublons » teste l'affichage.
- **Predict occupé** : `status.json → predict_occupe` (actif, minutes, jusqua_fr, file) repris tel quel ; carte Sonnette : « ⏳ Predict réfléchit : les autres alertes attendent sa décision (5 min max) » (+ « jusqu'à HHhMM » et nombre d'alertes en attente s'ils sont écrits) seulement si `actif` est vrai, rien sinon. verify.py : « sonnette: Predict occupé ». Contrôle en ligne du compte à rebours mouvement mis à jour pour la carte unique `#cycle-mouvement`.
