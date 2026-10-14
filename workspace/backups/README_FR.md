# Vibe-Trading : rejouer une idée sur les prix du passé

## Ce que c'est
- Un outil qui rejoue une règle d'achat et de vente sur les prix d'avant, pour voir ce qu'elle aurait donné.
- Il lit seulement des prix publics (Binance par défaut, ou OKX). Aucun compte, aucun portefeuille, aucune clé.
- Il ne passe JAMAIS d'ordre. Pas d'argent réel. Pas besoin d'IA ni de clé d'IA.
- Achat simple seulement : pas d'emprunt, pas de vente à découvert.
- Frais comptés par défaut comme chez Revolut X : 0,09 % à l'achat et 0,09 % à la vente, plus 0,05 % d'écart de prix à chaque fois (environ 0,28 % pour un aller-retour).
  `--costs revolutx-maker` = 0 % de frais (cas le plus favorable). `--costs flat01` = 0,1 %.
- Attention : un bon résultat sur le passé ne garantit rien pour demain. Ce n'est pas un conseil.
- Les heures sont celles de Bruxelles pour la fenêtre 15h-17h. Dans les tableaux de détail, les heures sont en UTC (Bruxelles moins 1 ou 2 heures).
- Tout passe par un seul fichier : `/workspace/tools/vibe-trading/backtest.sh`. Ajouter `--json` donne un résultat lisible par un bot.

## Les commandes, et pour quel bot

### 1. `run` : tester une idée → PM-Predict
Rejoue une règle et donne : gain ou perte en %, nombre d'achats, part des achats gagnants, pire baisse, frais payés, et la comparaison avec « acheter au début et garder ».
Il dit aussi si la règle de l'équipe est respectée : le gain visé fait au moins 3 fois les frais, la pire baisse reste sous 8 %.
```
backtest.sh run --pair BTC-EUR --tf 1D --days 365 --strategy sma_cross --fast 20 --slow 50 --json
```
Règles simples : `sma_cross`, `ema_cross` (deux moyennes qui se croisent), `rsi_revert` (acheter après une forte baisse), `buy_hold` (acheter et garder).

### 2. Les règles « comme l'équipe » : rejouer un type de trade → PM-Compound
Au lieu d'attendre environ 20 vrais essais, on rejoue le même type de trade sur un an de prix.
Par défaut : bougies d'une heure, achat seulement entre 15h et 17h (heure de Bruxelles), du lundi au vendredi,
vente si le prix baisse de 1,5 % (stop) ou monte de 1,5 % (objectif), sinon vente à 22h le même jour.
- `team_rebound` : le prix a baissé d'au moins 3 % en 24 heures, puis une bougie remonte (plus haut que la précédente) → achat.
- `team_breakout` : le prix passe au-dessus du plus haut des 8 dernières heures et au-dessus de sa moyenne de 50 heures → achat.
```
backtest.sh run --pair ETH-EUR --strategy team_rebound --sl 8 --tp 3 --json
backtest.sh run --pair BTC-EUR --strategy team_breakout --session 15-17 --tz Europe/Brussels --weekdays --sl 1.5 --tp 1.5
```
Ce sont des approximations : la vraie décision de l'équipe est faite à la main (lecture du marché, confirmation sur une bougie fermée). L'outil ne la copie pas parfaitement.
Réglages : `--sl` stop en %, `--tp` objectif en %, `--exit-hour` heure de sortie forcée, `--drop-pct`, `--drop-hours`, `--lookback`, `--trend`.

### 3. `robust` : vérifier qu'une idée n'est pas de la chance → PM-Predict et PM-Compound
Rejoue la règle avec beaucoup de réglages différents, sur des morceaux de période différents, et en mélangeant l'ordre des trades.
Il dit : si le résultat aurait pu venir du hasard, et si « le meilleur réglage choisi sur le passé » tient encore sur la période d'après.
Si la « probabilité de sur-ajustement » (PBO) dépasse 0,5, le bon résultat vient sans doute de la chance.
```
backtest.sh robust --pair BTC-EUR --strategy team_rebound --json
```
Lent : quelques minutes.

### 4. `risk` : la pire chute du passé face à la limite de 8 % → PM-Risk
Donne : la plus grosse chute depuis un sommet (et sa date), la chute actuelle, combien de temps le prix est resté plus de 8 % sous son sommet,
la pire journée, et la chance que le prix tombe de 8 % en 2 jours.
```
backtest.sh risk --pair BTC-EUR --days 1095 --limit 8 --hold-days 2 --json
```

### 5. `sentiment` : l'humeur du marché → PM-Scan / Research
Indice « peur et avidité » des cryptos (0 = grande peur, 100 = grande avidité), aujourd'hui et sur 30 jours. Il vaut pour toutes les cryptos, pas pour une seule.
```
backtest.sh sentiment --history 30 --json
```

### 6. `corr` : est-ce que BTC, ETH et SOL bougent ensemble ? → PM-Scan / Research et PM-Risk
Si elles bougent ensemble, acheter les trois revient presque à acheter trois fois la même chose.
```
backtest.sh corr --pairs BTC-EUR,ETH-EUR,SOL-EUR --tf 1D --days 365 --json
```

### 7. `journal` : relire les trades de test de l'équipe → PM-Compound
Lit une COPIE de `predict-market-bot/state/trades_log.jsonl` (l'original n'est jamais modifié) et cherche des mauvaises habitudes.
Il faut beaucoup de trades pour que ce soit utile.
```
backtest.sh journal --json
```

### 8. `report` : une page PDF d'un test → pour un humain
```
backtest.sh report /workspace/tools/vibe-trading/home/runs/<dossier du test>
```

## Où sont les résultats
Chaque test garde ses détails dans `/workspace/tools/vibe-trading/home/runs/`. Aide complète : `backtest.sh --help` ou `backtest.sh <commande> --help`.

## IA (compte ChatGPT de Quentin) — ajouté le 8 oct.
- Question libre : `/workspace/tools/vibe-trading/ai.sh ask "ta question"`
- Équipe d'analystes : `/workspace/tools/vibe-trading/ai.sh swarm ...`
- RÈGLE (Quentin, 8 oct.) : l'IA ne s'utilise QUE s'il y a une vraie preuve de besoin (une question précise que les autres commandes gratuites ne peuvent pas trancher). Jamais par routine, jamais en boucle, jamais « pour voir ». Note la raison dans ton journal à chaque usage.
- Ça consomme le quota ChatGPT de Quentin.
- Analyse seulement : aucun ordre, aucun compte branché. La décision reste à l'équipe et aux règles.
