# Live Revolut — prêt en permanence

Quand l’équipe choisit **live** (max 1 / jour, gain espéré ≥ 3× coûts) :

1. Écrire la décision dans `knowledge/decision_log.md` (oui live + pourquoi).
2. Préparer `order.json` : `pair`, `side`, `type: limit`, `price`, `amount_eur`.
3. Valider : `python3 guardian/scripts/validate_order.py --order order.json`
4. **Armer un seul live** : `touch /workspace/predict-market-bot/LIVE_ONCE`  
   (MODE reste `paper` sauf besoin ; LIVE_ONCE se consomme après un ordre OK.)
5. Envoyer : `python3 guardian/scripts/live_place.py --order order.json`
6. Vérifier soldes : `revx account balances --json`
7. Journal après vente dans `knowledge/trading_journal.md` ; Compound fait le bilan.

Sécurité :
- Pas de market order ; limit + post-only seulement.
- Si `STOP` ou `HALTED` → aucun ordre.
- Dry-run : `python3 guardian/scripts/live_place.py --order order.json --dry-run`
- Après le live : LIVE_ONCE disparaît ; rester en simulation jusqu’au prochain armement.

## Garde-fou mécanique (pas seulement Risk)

Fichier `state/live_day.json` : compte les lives du jour (Europe/Brussels).
`live_place.py` **refuse** un 2e ordre live le même jour, même si quelqu’un retouche `LIVE_ONCE`.
Après un live réussi, le compteur passe à 1 et `LIVE_ONCE` est effacé.


## Plafonds (2026-10-07, Compound propose / Risk valide)
- Simu: max ~25€/trade
- Live mini: 8€ (aligné ~5% cash ~165€); bloqué si >5%
- MetaMask: pause

## Stops (toutes positions)

`guardian/scripts/watch_stops.py` (ou `start_stop_watch.sh`) surveille **toutes** les positions ouvertes (guardian `state.json`, `state/positions.json` crypto, fills live, ordres ouverts revx si dispo) jusqu’à flat :

- Démarré **automatiquement** (détaché) après chaque ouverture paper (`paper_fill`) et chaque ordre live réussi (`live_place`) ; intervalle 30 s ; prix = tick du collecteur (≤ 2 min) sinon Revolut, sinon scan.
- **Paper/sim** → clôture auto via `paper_fill` + `state/auto_stop_wake.json` ; continue tant qu’il reste des positions.
- **Live** → sortie automatique (section ci-dessous). Si elle échoue, ou pour une ligne live qui ne vient pas de `live_orders.jsonl` : wake urgent `mode=live` « Stop touché en LIVE — vente à faire ».

## Règle 8 oct (Orchestrator + Risk)
Pas de live tant que l’alerte « prix d’arrêt touché en LIVE » ne réveille pas réellement PM-Risk et Quentin (sonnette/webhook testée). Un fichier de réveil seul ne suffit pas. Risk refuse tout live d’ici là.

## Sortie automatique sur stop — 8 oct

Décision Quentin (8 oct) : la sortie live sur stop est **automatique**, comme en simulation (pas de réveil pour décider).
`guardian/config.json` → `allow_live_auto_sell: true` (+ note) et bloc `live_exit` (marges, attente, essais, avoirs de Quentin, pas de prix/quantité).

Chemin : `watch_stops.py` (prix ≤ stop d’une position live de `state/live_orders.jsonl`) → `python3 guardian/scripts/live_place.py --exit` (spec JSON sur stdin : `position_id`, `pair`, `side`, `stop`, `trigger_price`, `cost_eur`, `avg_price`).

1. **Verrou** `state/live_exits.json` : une seule sortie par position (statuts `in_progress` / `done` / `partial` / `failed` / `no_fill` / `closed_by_target` / `error`). Jamais de doublon, jamais de nouvel essai automatique après un échec.
2. **Relecture Revolut** (`~/.local/bin/revx`) : ordre d’entrée (`order get` → quantité réellement remplie ; reste non rempli annulé), ordres ouverts de la paire, solde réel.
3. **Annule d’abord l’ordre objectif du bot** lié à la position (ligne `live_orders.jsonl` avec `target_for` / `linked_position_id` = position, ou `purpose: target`). Les autres ordres ouverts (ceux de Quentin) ne sont jamais touchés. Si l’objectif a déjà été rempli, la quantité est déduite (`closed_by_target`).
4. **Quantité** = `min(qty position, solde disponible, solde total − avoirs de Quentin)`. Avoirs de Quentin = max(config : 0,0309 ETH, 0,342 SOL, 0,0000066 BTC ; `state/live_equity.json` `hors_bot`). Les pièces de Quentin ne sont jamais vendues ; quantité arrondie vers le bas au pas Revolut.
5. **Ordre** : limite exécutable tout de suite (pas post-only, GTC) au meilleur acheteur −0,3 %. Pas rempli après ~60 s → annulation, nouveau prix acheteur −0,5 %, 3 essais max. Encore invendu → statut `failed`/`partial` + **alerte urgente** (réveil `urgent: true`, événement `stop_hit_live_exit_failed`).
6. **Idée à la baisse live** (vente puis rachat) : symétrique — rachat automatique au-dessus du stop, limite au meilleur vendeur +0,3 % (puis +0,5 %), limité par l’EUR disponible.
7. **Après la sortie** : ligne `kind: auto_exit` dans `state/live_orders.jsonl` (`amount_eur` = coût fermé, `quote_eur`, `realized_pnl_eur`), événement `state/auto_stop_events.jsonl`, réveil `state/auto_stop_wake.json` pour Risk (bilan + journal) avec `urgent: false`. Pas d’alerte urgente quand tout s’est bien passé.
8. La sortie **ne consomme pas `LIVE_ONCE`** et **n’écrit pas `live_day.json`** (c’est la fermeture du trade déjà compté). Elle reste autorisée si `STOP` / `HALTED` existe (elle réduit le risque) ; seules les nouvelles entrées sont bloquées.

Entrées live inchangées : `LIVE_ONCE` ou `MODE=live`, max 1/jour, espérance ≥ 3× coûts, limite post-only.

## Horaires live — 8 oct

Validé Quentin (`references/regles-litterature.md` « Horaires »). Config : `guardian/config.json` → `live_window`.
- **Entrée live** seulement **15:00–17:00** (Bruxelles), sauf **15 min après une annonce** : 14:30, 15:30 (+ heures du jour
  dans `state/annonces_du_jour.json`, ex. Fed 20:00). Donc 15:00–15:30 et 15:45–17:00. Sinon `live_place.py` refuse (rc 12).
- **Séance en plus** : seulement avec le feu vert de Quentin → `state/LIVE_EXTRA_SESSION.json`
  `{"date":"<aujourd'hui>","start":"HH:MM","end":"HH:MM"}`. Jamais d'entrée après 22:00.
- **Fermeture 22h RETIRÉE** (décision Quentin 8 oct) : `force_close_enabled: false`. Code conservé ; `true` pour réactiver.
- **Simulation à toute heure.**
- **Battements** (sonnette Grok Bot → réveil PM-Risk ; pas de notif ici) :
  - `state/watch_stops_heartbeat.json` chaque tour du surveillant ;
  - `state/revolut_heartbeat.json` toutes les ~5 min tant qu'une position est ouverte (lecture seule Revolut :
    ticker / balances ; `ok` + `consecutive_failures`).
