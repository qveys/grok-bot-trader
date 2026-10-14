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

- **Paper/sim** → clôture auto via `paper_fill`, exit **10** + `state/auto_stop_wake.json`.
- **Live** → **pas** de vente marché silencieuse. Wake urgent `state/auto_stop_wake.json` avec `mode=live` et message « Stop touché en LIVE — vente à faire » ; Risk arme `LIVE_ONCE` puis `live_place` limit sell. Pas de close auto live tant que le playbook / `live_place` n’a pas de chemin stop-close documenté (armement + expectancy + max 1/jour restent obligatoires).

## Règle 8 oct (Orchestrator + Risk)
Pas de live tant que l’alerte « prix d’arrêt touché en LIVE » ne réveille pas réellement PM-Risk et Quentin (sonnette/webhook testée). Un fichier de réveil seul ne suffit pas. Risk refuse tout live d’ici là.
