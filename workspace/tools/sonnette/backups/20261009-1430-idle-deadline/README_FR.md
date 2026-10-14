# Sonnette — surveillant de prix gratuit (sans IA)

Regarde les prix toutes les 30 s et **réveille une routine Grok Bot** (PM-Predict, PM-Risk ou PM-Compound)
par un webhook (HTTP POST JSON) quand une zone de prix est touchée ou qu'un trade se ferme.
Python standard uniquement, aucun coût, aucune IA. Ne passe **jamais** d'ordre.

## Fichiers

| Fichier | Rôle |
|---------|------|
| `sonnette.py` | Le programme (boucle, tests, statut, envoi test). |
| `departs.py` | « Alertes de départ » (observation seulement) : détection hausse / baisse / accumulation + résultats. |
| `live_equity.py` | Calcul du capital réel (lecture seule revx) → `state/live_equity.json` de l'équipe. |
| `start.sh` / `stop.sh` / `status.sh` | Démarrer (nohup + pidfile), arrêter, voir l'état. `start.sh` ignore les `SONNETTE_*` du shell : seul `secrets.env` compte (sauf `SONNETTE_USE_ENV=1`). |
| `config.json` | Réglages (fenêtre Predict, maximums, seuils Risk). |
| `secrets.env.example` | Modèle pour les URL/clés des webhooks (à copier en `secrets.env`, chmod 600). |
| `state/` | Mémoire de la sonnette : `status.json`, `state.json` (compteurs du jour), `rings.jsonl` (toutes les sonneries), `sonnette.log`, `sonnette.out`, `PRIX_PERIMES.flag`, `ALERTE_RISK_URGENTE.json`, `alertes_urgentes.jsonl`, `compound_rung.json`, `sante.json`, `departs.jsonl`, `departs_resultats.jsonl`, `departs_etat.json`. |

Côté équipe (lecture seule, sauf le fichier des zones) :
- prix : `/workspace/predict-market-bot/state/price_ticks/AAAA-MM-JJ.jsonl` (collecteur 30 s)
- zones : `/workspace/predict-market-bot/state/zones_reveil.json` (écrit par Predict/Risk)
- mode d'emploi pour les bots : `/workspace/predict-market-bot/references/sonnette.md`
- positions réelles : `guardian/state.json`, `state/positions.json`, `state/live_orders.jsonl`,
  plus `revx order open` **en lecture seule** (au plus toutes les 5 min).

## Commandes

```bash
cd /workspace/tools/sonnette
./start.sh                        # démarre en arrière-plan
./status.sh                       # état : marche/arrêt, âge du dernier prix, sonneries, compteurs, dry/réel
./stop.sh                         # arrête
python3 sonnette.py --simulate    # auto-tests (faux prix dans /tmp, ne touche à rien de réel)
python3 sonnette.py --test risk   # envoie UNE sonnerie d'essai à Risk (test=true)
python3 sonnette.py --test predict
python3 sonnette.py --test compound
python3 sonnette.py --once        # un seul tour
python3 sonnette.py --departs     # bilan des alertes de départ (combien, et combien ont marché)
```

## Règles

**Predict** (zones `"bot": "predict"`) : fenêtre et jours réglables dans `config.json`
(actuellement 00:00–24:00, 7 jours sur 7 ; `predict.days`, 0 = lundi), `max_per_day` sonneries max par jour au total (actuellement 6),
chaque zone 1 fois par jour.

**Risk** — seulement si une position **en argent réel** est ouverte (les positions simulées ne sonnent jamais) :
- `stop_hit` : prix ≤ prix d'arrêt → tout de suite, à toute heure ; rappel au plus toutes les 10 min ; 6 max/jour/position.
- `stop_near` : prix à moins de 1 % au-dessus du prix d'arrêt → 1 fois/position/jour.
- `daily_loss` ≥ 12 % → 1 fois/jour ; encore 1 fois à 15 %. `drawdown` ≥ 6 % → 1 fois/jour ; encore à 8 %.
  Calculés sur le **capital réel** (`state/live_equity.json`, voir plus bas), et seulement si un achat réel
  est ouvert **ou** a été fait aujourd'hui (Bruxelles). Si le capital est périmé → pas de sonnerie.
  Si on saute directement au-delà des deux seuils, une seule sonnerie (au seuil le plus haut).
- `stale_price` : dernier prix > 10 min → 1 fois, puis au plus toutes les 30 min.
- `manual_zone` : zone `"bot": "risk"` touchée → 1 fois/zone/jour.
- En cas de `stop_hit` : fichier `state/ALERTE_RISK_URGENTE.json` (`actif: true`), repasse à `false` quand le prix remonte.


**Compound** — cloche « trade fermé » (réveille PM-Compound **une seule fois** par trade fermé,
simulation ou live) :
- Sources (lecture seule) : `guardian/state.json` (positions `status=closed`),
  `state/trades_log.jsonl` (lignes avec `close_reason`), `state/live_orders.jsonl`
  (`kind=auto_exit`, ex. sortie auto de `live_place.py --exit`).
- Payload : `decision_id`, `paire`, `sens` (`Achat` = idée à la hausse, `Vente` = idée à la baisse),
  `mode` (`simulation` / `live`), `gain_perte_eur`, `raison_fermeture` (`cible` / `arrêt` / `manuel`).
- Déduplication dans `state/compound_rung.json` (survit aux redémarrages). Au **premier** démarrage,
  tous les trades déjà fermés (ex. D-019, D-020) sont marqués « déjà sonnés » : rien d'ancien ne sonne.
- **5 sonneries max par jour** (jour Europe/Bruxelles). Au-delà : log `reporté au bilan 20h32`, pas d'envoi.


**Santé (sonnette Risk uniquement, jamais Quentin directement)** — validé par Quentin, demandé par PM-Risk.
Le surveillant de Risk (`watch_stops.py`, script de l'équipe, lu seulement) écrit, quand une position est ouverte :
`state/watch_stops_heartbeat.json` (`ts, pid, open_live, open_paper`, ~30 s) et
`state/revolut_heartbeat.json` (`ts, ok, error, consecutive_failures`, ~5 min).
« Position ouverte » = `open_live`/`open_paper` > 0 dans le heartbeat **ou** position ouverte (simulée ou réelle)
dans `guardian/state.json` / `state/live_orders.jsonl`.
- `watcher_down` : position ouverte **et** (heartbeat > 3 min **ou** pid du surveillant absent **ou** fichier heartbeat absent > 3 min).
  Payload : `position_ids`, `cycle_ids`, `open_live`, `open_paper`, `heartbeat_age_s`, `heartbeat_pid`, `pid_vivant`.
- `revolut_down` : position ouverte **et** (`ok=false` avec `consecutive_failures` ≥ 2 **ou** test Revolut > 12 min).
  Payload : `error` (200 caractères max), `consecutive_failures`, `heartbeat_age_s`, + ids/compteurs.
- Anti-répétition : 1 sonnerie max par type toutes les 30 min ; quand tout redevient normal → log `rétabli`
  et le compteur repart à zéro (mémoire : `state/sante.json`, survit aux redémarrages).
- **Fichier heartbeat absent** (correctif demandé par PM-Risk, 08/10/2026) :
  - aucune position ouverte → rien (pas de sonnerie), une ligne INFO dans le log ;
  - position ouverte (`guardian/state.json` ou `state/live_orders.jsonl`) **et** `watch_stops_heartbeat.json` absent
    depuis plus de 3 min (`health.watcher_missing_grace_s`, 180 s) → `watcher_down` pour Risk, comme un heartbeat périmé.
    Le délai de 3 min évite une fausse alerte pendant le démarrage du surveillant ; il est gardé dans `state/sante.json`
    (survit aux redémarrages). Payload : `heartbeat_absent: true`, `absent_depuis_s`, + ids/compteurs.
    Exemple : « Le surveillant ne donne aucun signe de vie (fichier watch_stops_heartbeat.json absent depuis 3 min), 1 trade live ouvert. »
  - même idée pour Revolut : position ouverte, surveillant **vivant** (heartbeat frais) mais `revolut_heartbeat.json`
    absent depuis plus de 12 min (`health.revolut_missing_grace_s`) → `revolut_down`. Si le surveillant est mort,
    seul `watcher_down` sonne (pas de double alerte).
  - Fichier illisible → WARN, pas de sonnerie (inchangé).
- Exemple : « Le surveillant ne donne plus signe de vie depuis 4 min, 1 trade live ouvert. »
- `./status.sh` montre une ligne « Surveillant » et une ligne « Revolut (test) ».
- Aucune logique de fermeture à 22h dans la sonnette.

Prix d'arrêt d'une position réelle : `stop_price_eur`, sinon `stop_pct` appliqué au prix d'achat
(même logique que `watch_stops.py`). Une position réelle sans prix d'arrêt est signalée dans le log et le statut.

**Prix périmés** : si le dernier prix a plus de 3 min → aucune sonnerie sur les prix, ligne de log,
`status.json → "stale": true` et fichier `state/PRIX_PERIMES.flag`.

**Collecteur** : si `collect_price_ticks.py` ne tourne pas, c'est noté dans le statut et le log.
La sonnette **ne le démarre pas** (c'est à l'équipe : `scripts/start_price_ticks.sh`).

## Capital réel (`/workspace/predict-market-bot/state/live_equity.json`)

Calculé au plus toutes les 5 min (module `live_equity.py`), en **lecture seule** :
- `revx account balances` → EUR disponible + réservé (`eur_available`, `eur_reserved`).
- `bot_positions_value` = valeur, au prix du collecteur, du crypto **acheté par le bot** seulement.
- `capital_reel` = EUR dispo + EUR réservé + `bot_positions_value`.

**Crypto perso exclu (`hors_bot`)** : au premier calcul réussi, on prend une photo des soldes BTC/ETH/SOL
(disponible + réservé + staké) = crypto déjà détenu par Quentin. Ensuite, pour une paire où le bot a une position ouverte — achat (idée à la hausse) **ou**
vente d'ouverture (idée à la baisse, via `idea_type` / `cycle_id` dans `live_orders.jsonl`) —
crypto bot = solde − photo. Un rachat de cycle baisse n'ouvre pas un nouvel achat.
Pour une paire **sans** position bot ouverte, tout changement de solde (récompense de staking, achat/vente perso)
est considéré perso : la photo suit le solde (journalisé si ≥ 0,50 €). USDC et autres devises ne sont pas comptés.
Limite : si Quentin achète du crypto perso sur une paire où le bot a une position ouverte, ce sera compté comme bot.

**Référence du jour** (`ref_jour`) : première valeur après minuit (Bruxelles) → la perte du jour repart de 0 chaque jour.
**Plus-haut** (`plus_haut`) : maximum depuis le premier achat réel du bot ; `null` tant qu'il n'y en a pas.
**Dépôts / retraits** : si le cash EUR change de ≥ 0,05 € **sans activité bot** (pas de nouvelle ligne dans
`live_orders.jsonl`, pas de changement de crypto bot), `ref_jour` et `plus_haut` sont décalés du même montant
→ pas compté comme gain/perte. Chaque décalage est noté dans `ajustements[]` et dans le log.
**Panne revx** : on garde les dernières valeurs, `stale: true`, pas de sonnerie perte/baisse, ligne de log.
Idem si une position bot n'a pas de prix frais.

## Message envoyé (JSON)

Predict :
```json
{"bot":"predict","zone_id":"Z-SOL-98","paire":"SOL-EUR","prix":97.85,"seuil":98.0,"sens":"sous",
 "heure":"2026-10-08T15:41:00+02:00","kind":"zone","test":false,"raison":"...","envoi":"reel",
 "message_fr":"SOL est passé sous 98 € (97,85 €) à 15h41. Predict, à toi de juger."}
```

Risk (noms de champs demandés par PM-Risk, + quelques extras) :
```json
{"mode":"live","kind":"stop_hit","pair":"SOL-EUR","price":94.8,"stop":95.0,"position_id":"rx-live-...",
 "ts":"2026-10-11T03:03:00+02:00","test":false,"bot":"risk","rappel":1,"envoi":"reel",
 "message_fr":"URGENT argent réel : SOL est passé sous ton prix d'arrêt 95 € (94,80 €) à 03h03. ..."}
```
Essai (`--test`) : `"test": true`, `"mode": "test"`, `"kind": "stop_hit"`,
`"message_fr": "Essai de la sonnette, rien à faire."` — non compté dans les compteurs.

Compound (trade fermé) :
```json
{"bot":"compound","kind":"trade_ferme","decision_id":"D-021","paire":"ETH-EUR","sens":"Vente",
 "mode":"simulation","gain_perte_eur":0.05,"raison_fermeture":"cible","test":false,"envoi":"dry",
 "message_fr":"Trade fermé D-021: ETH-EUR, Vente, simulation, gain/perte +0,05 €, raison cible."}
```
Essai Compound (`--test compound`) : message contenant « essai », `"test": true`.

## URL et clé des webhooks (secrets)

Uniquement par variables d'environnement ou par le fichier `secrets.env` (chmod 600) :

| Variable | Contenu |
|----------|---------|
| `SONNETTE_PREDICT_URL`, `SONNETTE_RISK_URL`, `SONNETTE_COMPOUND_URL` | URL du webhook de la routine (doit commencer par `https://`). |
| `SONNETTE_PREDICT_AUTH`, `SONNETTE_RISK_AUTH`, `SONNETTE_COMPOUND_AUTH` | **Valeur complète** de l'en-tête `Authorization`, telle que montrée dans le panneau de la routine (`Bearer xxx` ou `xxx`) — envoyée telle quelle. |
| `SONNETTE_PREDICT_KEY`, `SONNETTE_RISK_KEY`, `SONNETTE_COMPOUND_KEY` | Alternative : seulement la clé → envoyée comme `Authorization: Bearer <clé>`. |

Autres façons d'envoyer la clé (si le panneau demande autre chose) :
- `SONNETTE_KEY_HEADER=X-Api-Key` → la clé brute dans l'en-tête `X-Api-Key`.
- `SONNETTE_KEY_HEADER="Authorization: Token <key>"` → modèle libre.
- `SONNETTE_KEY_PREFIX=none` → `Authorization: <clé>` sans `Bearer`.
- `SONNETTE_KEY_MODE=query` (+ `SONNETTE_KEY_PARAM=token`) → `?token=<clé>` dans l'URL.
- `SONNETTE_KEY_MODE=body` (+ `SONNETTE_KEY_PARAM`) → la clé dans le JSON.
- `SONNETTE_KEY_MODE=none` → pas de clé (si l'URL contient déjà le secret).
- Version par bot possible : `SONNETTE_RISK_KEY_HEADER`, `SONNETTE_PREDICT_KEY_MODE`, etc.

Sans URL **et** clé pour un bot → ce bot est en **mode dry** : la sonnerie est écrite dans le log et
`state/rings.jsonl`, mais rien n'est envoyé. `SONNETTE_DRY=1` force le mode dry.
Le fichier `secrets.env` est relu à chaque tour : le passage dry → réel se fait en 30 s, sans redémarrer.
L'URL et la clé ne sont **jamais** affichées ni écrites dans les logs, l'état ou le statut.

## Réseau

Envoi via le proxy HTTPS de la box `http://127.0.0.1:8791`. 4 essais au total (1 + 3 nouveaux essais,
pauses 2 s / 5 s / 10 s). Pas de nouvel essai sur une erreur 4xx (clé refusée → vérifier la clé).
Un envoi raté **ne compte pas** comme livré ; nouvelle tentative après 5 min (Predict) ou 2 min (Risk),
avec un nombre d'essais limité par jour (anti-spam).

## Mettre en service pour de vrai

1. Créer (ou ouvrir) la routine webhook sur PM-Predict et sur PM-Risk, copier l'URL et la valeur `Authorization`.
2. Les mettre dans `secrets.env` (copie de `secrets.env.example`), puis `chmod 600 secrets.env`.
3. `./status.sh` → les deux bots doivent afficher **RÉEL**.
4. `python3 sonnette.py --test risk` puis `--test predict` → la routine doit se réveiller avec « Essai de la sonnette, rien à faire. »

## Alertes de départ (observation seulement)

But : repérer le **début d'un mouvement** (un « départ ») sur BTC, ETH et SOL, et **mesurer** si ces signaux
marchent, **avant** de s'en servir. Pour l'instant la sonnette **ne réveille personne** pour ça
(ni Predict, ni Risk, ni Compound) et ne passe **jamais** d'ordre. Elle note, c'est tout.

**Quand ?** Toutes les 10 min (pas toutes les 30 s). À chaque fois : **un seul lot** de lecture,
`revx market candles` en bougies de 15 min sur les dernières 24 h, une fois par paire (3 appels, lecture seule).
Si une paire échoue, un seul nouvel essai 2 s après ; sinon elle est sautée jusqu'à la prochaine fois.

**Les 3 signaux** (calculés sur les bougies de 15 min **terminées**, fenêtre récente = la dernière heure) :
- **Départ à la hausse** : le prix a monté de **plus de 0,5 %** en 1 h, il est à **3 % ou moins du plus-haut 24 h**,
  le volume de la dernière heure est **plus de 1,2 fois** la moyenne (moyenne = les 20 bougies d'avant, soit 5 h),
  et les bougies vont dans le même sens (au moins **3 sur 4** montent, dont **la dernière** = confirmation 15 min).
- **Départ à la baisse** (pour une « idée à la baisse ») : le miroir — baisse de plus de 0,5 %, à 3 % ou moins
  du **plus-bas 24 h**, volume plus de 1,2 fois la moyenne, au moins 3 bougies sur 4 qui descendent, dont la dernière.
- **Accumulation** : le volume est **au moins 1,5 fois** la moyenne alors que le prix ne bouge presque pas
  (moins de **0,3 %** en 1 h). Quelqu'un achète ou vend beaucoup sans faire bouger le prix.

**Anti-répétition** : au plus **1 alerte par paire et par type toutes les 2 h** (gardé dans le fichier, survit aux redémarrages).

**Où c'est noté ?**
- `state/departs.jsonl` : une ligne par alerte — heure de Bruxelles (`ts`), `paire`, `type` (`hausse` / `baisse` /
  `accumulation`), `prix`, `ratio_volume` (ex. 1,45 = 1,45 fois la moyenne), `variation_pct` (sur 1 h),
  `distance_haut_24h_pct` / `distance_bas_24h_pct` (à combien de % on est du plus-haut / plus-bas 24 h),
  `prix_collecteur` (le prix du collecteur au même moment), `sonnerie: false`.
- `state/departs_resultats.jsonl` : ce qui s'est passé ensuite, **+1 h, +4 h et +24 h** après chaque alerte.
  Une ligne par alerte et par délai : `prix`, `variation_pct`, `reussi` (`true` / `false`).
  Prix pris dans le fichier du collecteur (lecture seule) ; s'il manque, dans les bougies 15 min.
  Si aucun prix n'est trouvé 3 h après l'heure prévue : `statut: "manquant"` (pas compté dans les %).
- `state/departs_etat.json` : les chiffres de la dernière vérification (utile pour voir que tout tourne).

**« Ça a marché »** = le prix a bougé d'**au moins 1 %** dans le sens prévu (hausse : +1 % ; baisse : −1 %).
Pour l'accumulation, on ne connaît pas le sens : ça compte si le prix sort d'au moins 1 % **d'un côté ou de l'autre**.

**Voir le bilan** : `./status.sh` (ligne « Départs », nombre par type et % qui a marché à +4 h) ou
`python3 sonnette.py --departs` (détail à +1 h, +4 h, +24 h).

**Réglages** (`config.json` → `departs`) :

| Réglage | Valeur | Sens |
|---------|--------|------|
| `actif` | `true` | `false` = coupé. |
| `mode` | `"observe"` | Observation seulement. `"ring"` est prévu pour plus tard mais **pas encore branché** (la sonnette le dit dans le log et continue d'observer). |
| `verif_toutes_s` | 600 | Une vérification toutes les 10 min. |
| `intervalle` / `fenetre_min` | `"15m"` / 60 | Bougies de 15 min, mouvement mesuré sur 1 h. |
| `mouvement_min_pct` | 0.5 | Hausse / baisse minimum sur la fenêtre (en %). |
| `proche_extreme_24h_pct` | 3.0 | Distance max au plus-haut (hausse) ou au plus-bas (baisse) 24 h. |
| `volume_ratio_min` | 1.2 | Volume minimum (× la moyenne) pour hausse / baisse. |
| `barres_meme_sens_min` | 3 | Bougies dans le bon sens sur les 4 de la fenêtre (la dernière doit l'être). |
| `accumulation_volume_ratio_min` | 1.5 | Volume minimum pour l'accumulation. |
| `accumulation_mouvement_max_pct` | 0.3 | Mouvement maximum du prix pour l'accumulation. |
| `volume_moyenne_barres` | 20 | Nombre de bougies pour la moyenne du volume (avant la fenêtre). |
| `anti_spam_heures` | 2 | 1 alerte par paire et par type toutes les 2 h. |
| `horizons_h` / `reussite_min_pct` | [1, 4, 24] / 1.0 | Quand on regarde le résultat, et le mouvement qui compte comme réussi. |

Les réglages sont lus au démarrage : après un changement, `./stop.sh` puis `./start.sh`.

## Totaux des sonneries et vue complète de l'argent réel (9 oct. 2026)

- `state/status.json → totals.{predict,risk,compound}` : `vrais`, `essais` (+ détail par résultat livré / dry / échec),
  `dernier_vrai`, `dernier_essai`. Recalculés depuis `state/rings.jsonl` à chaque sonnerie (et à chaque cycle).
  Essai = `payload.test`, `mode=test`, `zone_id=TEST` ou `decision_id` D-ESSAI….
- `live_equity.json` (toutes les ~5 min) ajoute : `soldes_revolut_x.<devise>.{disponible,reserve,stake,total,prix_eur,eur}`,
  `metamask.{adresse,reseau,eth,prix_eur,eur,lu_a,stale}`, `total_revolut_x_eur`, `total_reel_eur` (Revolut X + MetaMask),
  `total_reel_complet` / `total_reel_manque` (devise sans prix, ex. USDC). Lectures seules : `revx account balances` et
  `eth_getBalance` (RPC public Arbitrum). Jamais d'ordre. Aucune sonnerie ne dépend de ces champs.
- Le tableau de bord lit ces champs tels quels (il ne lit plus les soldes lui-même).
