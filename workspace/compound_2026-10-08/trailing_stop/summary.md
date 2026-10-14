# Stop suiveur vs stop fixe — PM-Compound, 8 oct. 2026 (décision Quentin 22h03)

Simulation seulement (prix publics Binance, 1 h). Aucun ordre, aucune IA payante.
Période : 07/10/2025 00h → 07/10/2026 23h UTC (1 an). Moitié 1 = avant le 07/04/2026 12h UTC, moitié 2 = après (classement par heure d'achat / de vente).
Mêmes signaux d'entrée dans les deux cas. Rebond / cassure : achats 15h–17h Bruxelles, lun–ven, stop −1,5 %, objectif +1,5 %, sortie 22h.
Stop suiveur testé : stop = max(achat −1,5 %, plus haut depuis l'achat −1,5 %), ne redescend jamais (heures finies seulement).
`sell_rebuy` (idée à la baisse) : miroir — l'achat de sécurité descend avec le plus bas depuis la vente.

Coûts : **M** = `revolutx-maker`, tout rempli, 0 % (cas le plus favorable). **T** = `revolutx-maker --fill touch` (achat à prix fixé rempli seulement si le prix passe dessous ; stop et 22h = ordre au marché 0,09 % + 0,05 %). **K** = `--costs revolutx` (achat immédiat au marché, 0,09 % + 0,05 % à chaque ordre).
Baisse sur notre capital = pire baisse de l'outil × 5 % (mises de 5 %).

## Tableau principal (stop fixe vs suiveur à la même distance 1,5 %)
| pair | strat | stop | net M | net T | net K | trades | win% | H1 (M) | H2 (M) | worst drop capital 5% (M) | biggest loss/trade % | avg loss % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ETH | rebound | fixed | +5.58 | +0.97 | +0.92 | 19 | 58 | +7.63 | -1.90 | 0.17 | -1.50 | -1.19 |
| ETH | rebound | trail1.5 | +2.72 | -0.18 | -1.92 | 19 | 47 | +5.92 | -3.02 | 0.17 | -1.50 | -1.06 |
| ETH | breakout | fixed | -6.43 | -9.34 | -15.13 | 40 | 40 | -6.01 | -0.45 | 0.37 | -1.50 | -1.15 |
| ETH | breakout | trail1.5 | -6.05 | -7.25 | -15.52 | 40 | 35 | -4.88 | -1.22 | 0.32 | -1.50 | -0.98 |
| ETH | sell_rebuy | fixed | +4.08 | +4.08 | +0.08 | 43 | 35 | +2.27 | +1.78 | 0.57 | -1.48 | -1.48 |
| ETH | sell_rebuy | trail1.5 | +14.24 | +14.24 | +4.75 | 72 | 47 | +13.50 | +0.66 | 0.34 | -1.48 | -0.89 |
| SOL | rebound | fixed | +8.23 | +6.39 | -0.63 | 23 | 65 | +2.91 | +5.17 | 0.15 | -1.50 | -1.39 |
| SOL | rebound | trail1.5 | -0.92 | +4.05 | -9.26 | 23 | 44 | -2.24 | +1.35 | 0.18 | -1.50 | -1.05 |
| SOL | breakout | fixed | +3.56 | +3.09 | -6.13 | 41 | 56 | +2.10 | +1.43 | 0.40 | -1.50 | -1.39 |
| SOL | breakout | trail1.5 | +0.05 | -0.69 | -9.74 | 41 | 44 | -0.88 | +0.93 | 0.38 | -1.50 | -1.04 |
| SOL | sell_rebuy | fixed | +16.23 | +16.23 | +10.05 | 63 | 38 | +24.87 | -6.92 | 0.62 | -1.48 | -1.48 |
| SOL | sell_rebuy | trail1.5 | +30.47 | +30.47 | +17.14 | 95 | 46 | +35.38 | -3.62 | 0.42 | -1.48 | -0.88 |
| BTC | rebound | fixed | +0.99 | -2.91 | -1.63 | 11 | 46 | +1.41 | -0.41 | 0.11 | -1.50 | -1.07 |
| BTC | rebound | trail1.5 | -0.57 | -4.54 | -3.35 | 11 | 36 | +0.36 | -0.93 | 0.12 | -1.50 | -0.93 |
| BTC | breakout | fixed | +1.14 | -2.94 | -8.95 | 42 | 50 | -5.18 | +6.67 | 0.37 | -1.50 | -1.10 |
| BTC | breakout | trail1.5 | +2.93 | -1.28 | -7.89 | 42 | 45 | -3.61 | +6.78 | 0.28 | -1.50 | -0.84 |
| BTC | sell_rebuy | fixed | +16.93 | +16.93 | +14.98 | 23 | 48 | +15.04 | +1.64 | 0.43 | -1.48 | -1.48 |
| BTC | sell_rebuy | trail1.5 | +6.71 | +6.71 | +2.61 | 33 | 42 | +8.02 | -1.22 | 0.30 | -1.48 | -0.71 |

H1/H2, baisse capital = cas M. « biggest loss » = pire trade (% de la mise) ; en capital 5 % : ≈ 0,075 % (M), 0,08 % (T), 0,09 % (K). Pour `sell_rebuy` le gain est en pièces gagnées vs garder.

## Verdict
- **Rebond / cassure (vrais « mêmes trades », 6 cas)** : le **stop fixe garde plus d'argent**. Somme des gains nets : M fixe +13,1 vs suiveur −1,8 ; T −4,7 vs −9,9 ; K −31,6 vs −47,7. Le suiveur ne gagne que sur la cassure ETH et BTC (en K : seulement BTC cassure).
  Raison : avec l'objectif +1,5 %, le stop suiveur 1,5 % ne monte au mieux qu'au prix d'achat → il coupe des trades qui allaient toucher l'objectif (taux de réussite ETH rebond 58 → 47 %, SOL rebond 65 → 44 %).
- **Le suiveur limite mieux les pertes** : perte moyenne par trade perdant ≈ −1,3 % → −0,9/−1,0 % ; pire baisse plus petite dans 6 cas sur 9 (M et T). **Pire perte d'un trade inchangée** (−1,5 % ; −1,64 % T ; −1,73 % K) : au début du trade, les deux stops sont au même endroit.
- **Idée à la baisse (`sell_rebuy`)** : mélangé. ETH et SOL mieux avec le suiveur (K : ETH +4,75 vs +0,08 ; SOL +17,1 vs +10,1), BTC nettement moins bien (+2,6 vs +15,0). Somme K quasi égale (24,5 vs 25,1). ⚠ Ce ne sont PAS les mêmes trades : le suiveur ferme les cycles plus tôt, donc plus de ventes (ETH 43 → 72, SOL 63 → 95, BTC 23 → 33).
- **Moitiés d'année** : moitié 2 (avr.–oct. 2026), le fixe gagne 7 cas sur 9 (M). Inversions : ETH cassure (suiveur en H1, fixe en H2 ; M et K), ETH `sell_rebuy` (suiveur H1, fixe H2 ; M, T, K).
- **Distance** : 0,75 % (plus serré) = pire partout pour rebond/cassure (trop de sorties). 2,25 % = presque identique au fixe (il ne peut presque jamais monter avant l'objectif +1,5 %).

## Piste à vérifier (pas une conclusion)
Sans objectif +1,5 % (`--tp 0`, sortie au stop ou à 22h), rebond/cassure deviennent bien meilleurs — **mais c'est surtout l'objectif retiré, pas le suiveur** : stop fixe sans objectif M +52,8 / T +28,2 / K −1,3 vs suiveur sans objectif M +54,2 / T +34,9 / K +0,9 (somme 6 cas ; stop fixe avec objectif : +13,1 / −4,7 / −31,6). Entre fixe et suiveur sans objectif : 3–4 cas sur 6, mélangé. Gain concentré sur la cassure ETH/BTC en moitié 2. Peu de trades (11–42) → à passer par `robust` avant toute décision.
Test en plus, cassure avec filtre 200 h (`--trend 200`, comme l'équipe) : fixe et suiveur perdent tous les deux avec l'objectif +1,5 % (suiveur mieux sur BTC, moins bien sur ETH) ; sans objectif, positif en M sur les 3 paires. Fichier `results_breakout_trend200.csv`.

## Limites
- Peu de trades : rebond BTC 11, rebond ETH 19, SOL 23 ; cassure ~40. Pas de règle des 20 trades pour BTC/ETH rebond. Une année seulement, ETH et SOL ont baissé de plus de 40 %.
- Données : 1 h Binance (pas Revolut X), complètes (aucun trou signalé, BTC présent). Dans une heure on ne sait pas si le haut vient avant le bas : le plus haut de l'heure ne compte qu'à partir de l'heure suivante (prudent). Stop rempli au niveau du stop (ou à l'ouverture si le prix a sauté dessous) : en vrai il peut glisser plus.
- `sell_rebuy` T = M (identique : `--fill touch` ne change presque rien ici et le rachat de sécurité est à 0 % en M/T). Le cas réaliste pour `sell_rebuy` est K.
- Le rebond de l'outil n'a pas le filtre 200 h de l'équipe.

## Code ajouté (comportement par défaut inchangé : 5 sorties anciennes identiques octet par octet, anciens tests OK)
- Option `--trail PCT` (0 = arrêt) : `vt_tools.py` (option, contrôles, config `spot_trailing_stop`), `vt_runner.py` (moteur), `vt_fill.py` (modèles `--fill touch` / `--fill-rate`), `vt_sellrebuy.py` (miroir idée à la baisse).
- Test : `checks/test_trail.py` (13 vérifs OK). Copies avant modif : `checks/*_before_trail.py.bak`. Doc : README_FR.md (section 2b).
- Contrôle croisé : sur les 48 essais rebond/cassure `--fill touch`, la copie indépendante (`vt_fill.py`) retrouve le résultat du moteur (même nombre de trades, écart < 0,5 € sur 10 000), stop suiveur compris.

## Fichiers
`results.csv` (144 essais), `results_breakout_trend200.csv` (36), `tables.md` (tous les tableaux), `raw/` (JSON + trades de chaque essai + commande), `regression/` (avant/après le code), `run_all.py`, `summarize.py`.
