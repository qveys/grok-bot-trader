# Plan : déplacer la sonnette et le surveillant des arrêts de Risk vers Cloudflare

État au 10 oct 2026, 18h55. Ce plan n'éteint rien et ne modifie aucun fichier des bots.

## 0. Pourquoi
La box se fige parfois pendant des heures (03:08–07:58, 11:58–15:08, 15:18–18:10). Pendant ce temps, tout s'arrête :
le collecteur de prix (`scripts/collect_price_ticks.py`), la sonnette (`tools/sonnette/sonnette.py`) et
`guardian/scripts/watch_stops.py`. Personne ne voit un arrêt touché, une zone ou une heure limite.
Cloudflare tourne en dehors de la box : il peut voir le prix, retenir ce qui s'est passé et prévenir.

## 1. Ce qui existe déjà (relu dans le code)
| Rôle | Où | Source de prix | Ce qu'il fait |
|---|---|---|---|
| Collecteur | `predict-market-bot/scripts/collect_price_ticks.py` | Coinbase, toutes les 30 s | écrit `state/price_ticks/AAAA-MM-JJ.jsonl` |
| Sonnette | `tools/sonnette/sonnette.py` (≈ 270 Ko) | lit les fichiers du collecteur | sonne Predict (zones, mouvement > 0,5 %, sans décision 4 h, heure limite), Risk (stop_hit / stop_near / perte du jour / drawdown — **positions réelles seulement**, + santé : surveillant ou Revolut à l'arrêt), Compound (trade fermé). Plafonds par jour, anti-doublons, mode « occupé ». |
| Surveillant des arrêts | `guardian/scripts/watch_stops.py` (≈ 2 600 lignes), lancé par `paper_fill.py` / `live_place.py` / `start_stop_watch.sh` | ticks → `revx market ticker` → scan | ferme **lui-même** les simulations (stop / objectif) dans `guardian/state.json`, réveille Risk pour le réel, rappel d'heure limite, **rattrapage des trous** : si le dernier prix a > 120 s, il lit les bougies Coinbase 1 min/5 min du trou et ferme au **niveau du stop** à la première bougie qui l'a traversé (`gap_catch_up` / `gap_crossing`, stop prioritaire si stop et objectif dans la même bougie). |

Conséquence clé : **après un gel, Risk ferme déjà les simulations au bon prix** (rattrapage). Ce qui manque pendant le gel :
(a) quelqu'un qui le *sait* et le dit tout de suite (surtout pour le **réel**, où une vente manquée coûte de l'argent),
(b) les sonneries Predict (zones, mouvement, heure limite).

## 2. Ce qui peut tourner dans un Worker (cron chaque minute)
- **Prix** : Revolut X public, sans clé (vérifié depuis la box le 10 oct) :
  `GET https://revx.revolut.com/api/1.0/public/tickers?symbols=BTC/EUR,ETH/EUR,SOL/EUR&region=EEA` (1 requête pour les 3 paires) et
  `GET /api/1.0/public/candles/{BTC-EUR}?interval=1&since=<ms>` (bougies 1 min : bas/haut → on attrape les mèches entre deux contrôles ;
  limite 1 requête/s → 1,1 s d'attente entre paires, ce n'est pas du temps CPU). Secours : Coinbase public
  (`/products/{pair}/ticker` et `/candles`, la **même source que le rattrapage de Risk** → à garder en double pour comparer).
- **Contrôles purs** (aucun fichier) : stop / objectif (long : bas ≤ stop ; baisse : haut ≥ stop — même règle que `gap_crossing`),
  zones (`sous` : bas ≤ prix ; `au-dessus` : haut ≥ prix ; une fois par zone et par jour), heure limite (une fois par position + heure limite),
  stop proche (1 %), mouvement > 0,5 % depuis la dernière décision (si la box pousse le prix de référence).
- **Sonneries** : POST JSON vers les URL des routines (même format que `post_json` / `ring()` de la sonnette : `bot`, `kind`, `message_fr`, …).
  URL et en-têtes copiés de `tools/sonnette/secrets.env` en **secrets Worker** (`SONNETTE_RISK_URL`, `SONNETTE_RISK_AUTH`, `…PREDICT…`, `…COMPOUND…`)
  par un script qui lit le fichier et passe chaque valeur sur l'entrée standard de `wrangler secret put` (jamais affichées).
- **Anti-doublons et plafonds** dans D1 (table d'événements à clé unique, compteurs par jour Bruxelles).
- **Telegram** (secrets déjà prévus pour le veilleur) : un message court quand un arrêt est touché **pendant que la box est figée**,
  avec le prix d'arrêt exact et l'heure : « Arrêt touché sur SOL à 96,99 € à 14h12. L'ordinateur est figé : la simulation sera fermée à ce prix à la reprise. »
  Pour le **réel** : « … Vente réelle non faite : à vendre à la main dans Revolut si besoin. »

## 3. Comment le Worker connaît l'état (poussé par la box quand il change)
La box est la seule à savoir quelles positions sont ouvertes. Elle pousse un résumé **compact et en lecture seule** :
- `POST /etat-bots` (même secret que `/battement`), envoyé par l'envoyeur de battements **quand le résumé change** (hash) ou toutes les 10 min.
- Contenu : positions ouvertes (`id, pair, side, idea_type, stop, target, deadline, decision_id, mode`), zones actives
  (`id, paire, sens, prix, bot, expire`), et plus tard : prix de référence de la dernière D-xxx, compteurs de sonneries du jour.
- Prototype : `pousse_etat.py` lit `guardian/state.json` + `state/zones_reveil.json`. **À faire avant la bascule** : utiliser la même fusion
  que `watch_stops.py` (`normalize_position`, positions réelles venant de `live_orders.jsonl` / `positions.json` / ordres revx), sinon le Worker ne verrait pas tout le réel.
- Pendant un gel, le Worker garde le **dernier état reçu** : c'est exactement ce dont il a besoin (les positions ne changent pas quand tout est figé).
- Délai : une position ouverte est vue par le Worker ≤ 60 s après son écriture.

## 4. Ce qui reste sur la box
- L'**écriture des résultats** (fermer la simulation dans `guardian/state.json`, `trades_log.jsonl`, bilans) : c'est `watch_stops.py` / les scripts de PM-Risk.
  Le Worker **n'écrit jamais** dans ces fichiers.
- Les **ordres réels** (`live_place.py`, clé Revolut privée) : restent sur la box, la clé n'est pas mise dans Cloudflare.
- Les sonneries qui lisent des fichiers riches (sans décision 4 h dans `decision_log.md`, perte du jour / drawdown via `live_equity.json`,
  santé Revolut, Compound « trade fermé ») : elles restent dans la sonnette ; elles n'ont pas de sens pendant un gel.
- Attention : les routines Risk/Predict travaillent elles aussi sur la box. **Une sonnerie pendant un gel ne sera traitée qu'à la reprise.**
  D'où le double canal : sonnerie à Risk (pour qu'il agisse dès la reprise, avec `prix_stop` et `heure` dans le message) **+ Telegram à Quentin** tout de suite.
- À la reprise, rien de spécial à faire : le rattrapage de `watch_stops.py` ferme au niveau du stop, ce qui correspond au prix annoncé par le Worker.
  Petit risque : Revolut X et Coinbase peuvent différer de quelques centimes autour du stop → le Worker vérifie aussi Coinbase et note les deux.

## 5. Règle de partage pour éviter les doublons
- **Box en vie** (battement < 3 min dans le veilleur) : la sonnette de la box reste maître ; le Worker observe seulement.
- **Box figée** (pas de battement depuis > 3 min) : le Worker prend le relais pour les stops, objectifs, zones et heures limites ;
  chaque sonnerie porte `source: "cloudflare"` et une clé d'événement identique à celle de la sonnette (`stop|<position>`, `zone|<id>|<jour>`, `heure_limite|<position>|<deadline>`).
- À la reprise, la box envoie ses clés déjà sonnées dans `/etat-bots`, et le Worker pousse ses événements (lecture via `GET /obs`) pour que la sonnette ne re-sonne pas la même chose.
  (Ce dernier point demande un petit ajout dans la sonnette **plus tard**, avec accord : lire la liste des événements Cloudflare avant de sonner.)

## 6. Limites du plan gratuit (Workers Free + D1 Free)
| Limite | Gratuit | Usage prévu |
|---|---|---|
| Requêtes Worker | 100 000 / jour | ≈ 1 440 battements + 1 440 états + 1 440 + 288 crons ≈ 4 700 |
| CPU par appel | 10 ms | lecture de ≤ 360 bougies × 3 + JSON : quelques ms ; contrôles purs |
| Sous-requêtes par appel | 50 | 1 ticker + 3 bougies (+ Coinbase en secours) + sonneries ≤ 10 |
| Crons | 5 par compte | 2 (veilleur */5, sonnette-cf chaque minute) |
| D1 lectures / écritures | 5 M / 100 k par jour | ≈ 10 k lectures, ≈ 5 k écritures |
| D1 stockage | 5 Go | quelques Ko (événements purgés après 14 jours) |
| KV (non utilisé) | 1 000 écritures / jour | trop juste pour 1 battement/min → D1 choisi |
Le cron Cloudflare n'est pas garanti à la seconde (souvent quelques secondes de retard) : les bougies 1 min couvrent cet écart.

## 7. Étapes
1. **Fait (prototype, observation)** : Worker `pm-sonnette-cf` dans `tools/veilleur/sonnette-cf/` (cron chaque minute, Revolut X → bougies 1 min,
   stop / objectif / zones / heure limite, journal D1 `obs_evenements`, `GET /obs`, `POST /controle`). **Aucune sonnerie, aucun Telegram.**
   Testé en local (wrangler dev) : prix Revolut X lus, 3 zones détectées, stop simulé détecté avec prix et minute exacts, pas de doublon.
   Non déployé : la clé Cloudflare n'a pas le droit « Workers Scripts : Edit » (voir rapport). Déploiement : `./deploy_obs.sh` (active aussi l'envoi d'état de la box).
2. **Période en parallèle : 7 jours minimum, dont au moins 1 gel réel.** Chaque jour, comparer `GET /obs` avec `tools/sonnette/state/rings.jsonl`
   et `predict-market-bot/state/auto_stop_events.jsonl` / `price_gaps.jsonl` : même événement, même minute (± 1 min), même prix.
   Critère : 0 stop manqué, 0 fausse alerte de stop, écart de prix Revolut/Coinbase noté.
3. **Mode relais** (avec accord de Quentin) : activer les sonneries Cloudflare **seulement quand la box est figée** (règle §5) + Telegram stop.
   Secrets de sonnerie posés par script. Encore 7 jours en parallèle.
4. **Bascule éventuelle** (décision de Quentin, pas avant) : la sonnette de la box pourrait laisser les zones/stops à Cloudflare
   (option de config dans la sonnette, à ajouter par son propriétaire). Le surveillant des arrêts **reste** sur la box (il écrit les résultats).
5. Retour arrière à tout moment : supprimer le cron du Worker (`triggers.crons = []` puis déploiement) ; la box n'a jamais cessé de fonctionner.

## 8. Risques connus
- Revolut X peut bloquer les IP Cloudflare (pas encore testé depuis Cloudflare) → secours Coinbase.
- L'état poussé est en retard de ≤ 60 s ; une position ouverte juste avant un gel peut manquer → l'envoyeur pousse aussi immédiatement après changement (hash).
- Les positions réelles ne sont pas toutes dans `guardian/state.json` → réutiliser la fusion de `watch_stops.py` avant le mode relais.
- Heure de Bruxelles : le jour est calculé avec le fuseau Europe/Brussels (passage à l’heure d’hiver géré).
