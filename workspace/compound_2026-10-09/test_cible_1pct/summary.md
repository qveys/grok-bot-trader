# Test « cible 1 % / arrêt 1 % » contre les réglages actuels de Predict — PM-Compound, 9 oct. 2026 (~21h05)

Simulation seulement. Aucun ordre, pas d'IA (`ai.sh` non utilisé), aucun secret écrit.

## Réponse courte
**Non : 1 %/1 % ne bat pas les réglages actuels après les vrais frais, sur aucune moitié de l'année, et ne passe la règle d'équipe dans aucun cas (0 sur 42).**
- Achat immédiat 0,14 %/côté (0,28 % aller-retour) : 1/1 est négatif dans tous les tests des signaux de l'équipe (outil : 12/12 négatifs, de −0,2 % à −20 %), et dans les deux moitiés presque partout.
- Duel direct (102 cases avec frais immédiats : paire × règle × 2 moteurs × 3 vérifs) : 1/1 fait mieux que 1,5/1,5 dans 31 cas seulement, que 2/1 dans 33, que 2,25/1,5 dans 20.
- Seule exception : en témoin neutre « baisse chaque jour à 15h », 1/1 perd un peu moins que 1,5/1,5 (−55 à −59 % contre −59 à −61 %) — mais tout perd énormément là-bas.
- Avant 2 jours de nos relevés 30 s : 1/1 aurait touché la cible 4 fois et l'arrêt 3 fois (21 entrées distinctes) ; le 9 oct. seul : 0 cible, 3 arrêts. Beaucoup trop court pour conclure.

## Point clé : la règle « gain visé ≥ 3 × frais »
- 3 × 0,28 % = 0,84 %. Une cible de 1 % passe ce contrôle **de justesse (marge 0,16 %)**.
- Mais une cible touchée rapporte **+0,72 %** net, un arrêt touché coûte **−1,28 %** net. Il faut gagner **64 %** des fois juste pour ne rien perdre.
- Taux de réussite mesurés avec 1/1 : 27–62 % (signaux de l'équipe), 42–52 % (témoin). Même le meilleur cas sérieux (SOL baisse après +3 % en 24 h, 47 trades, 61,7 % gagnants) reste sous 64 % et finit à −1,9 %. Cohérent avec le calcul.
- Pour comparer (même calcul, frais 0,28 %) : 1,5/1,5 → 59 % requis ; 1,5/1 → 51 % ; 2,25/1,5 → 47,5 % ; 2/1 → 43 % ; 2,25/1 → 40 %.
- Avec cible en ordre à prix fixé à 0 % (entrée et arrêt à 0,14 %) : 1/1 demande encore 60 %.

## Données utilisées
- **Bougies 1 h Binance, paires en EUR (BTC-EUR, ETH-EUR, SOL-EUR)**, du 7 oct. 2025 00h00 au 7 oct. 2026 23h00 UTC (366 jours, 8 784 bougies évaluées), **retrouvées dans le cache de l'outil** (`/workspace/tools/vibe-trading/home/cache/ccxt/`, écrites hier par les 144 tests). Aucun trou, aucun doublon. Copies : `data/*.csv`.
- Aucun changement de l'outil nécessaire : le cache est indexé par dates, donc `--end 2026-10-07 --days 365` le réutilise sans réseau (Binance renvoie 451 ce soir). Comportement par défaut inchangé.
- Heures vérifiées : bougies en UTC (écart moyen 0,03 % avec nos relevés 30 s à la bonne heure, 0,6–0,7 % avec 1 h de décalage).
- Relevés 30 s : `state/price_ticks/2026-10-08.jsonl` et `2026-10-09.jsonl` (jusqu'à 20h59). Un trou de ~40 min le 9 oct. vers 13h19–14h00 (avant les décisions scorées).

## Ce qui a été testé
- Grille : cible {1 ; 1,5 ; 2 ; 2,25} % × arrêt {1 ; 1,5} %. Frais : `revolutx-maker` (0 %), achat immédiat `revolutx` (0,09 % + 0,05 % = 0,14 %/côté), et `--fill touch`. Sans sortie 22h (`--exit-hour -1`), sécurité 48 h (`--max-bars 48`).
- Hausse : `team_rebound`, `team_breakout` (outil, 15–17h jours ouvrés). Baisse : `sell_rebuy` (vente de pièces qu'on a, rachat au prix visé = cible, rachat de sécurité = arrêt, 48 h max ; avec et sans filtre 200 h).
- Recalcul indépendant (`scripts/own_sim.py`) : mêmes signaux hausse + règles miroir baisse (rebond miroir, cassure miroir, hausse 3 %/24 h), et **témoin neutre : entrée chaque jour à 15h Bruxelles** dans chaque sens (aussi en jours ouvrés seulement), sortie seulement au prix visé, à l'arrêt, à 48 h ou en fin de données.
- Prudent partout : si une bougie touche les deux prix, on compte l'arrêt d'abord.
- 240 tests outil (`tool_json/`, dossiers dans `home/runs/`), 3 × 720 calculs indépendants (`own_sim/`). `vt_verdict.py --all` relancé.

## Niveaux de risque (PM-Risk : cible/arrêt ≥ 1 prudente, ≥ 1,5 équilibrée, ≥ 2 risquée)
| réglage | rapport | niveau(x) |
|---|---|---|
| 1/1 | 1,0 | prudente |
| 1,5/1,5 | 1,0 | prudente |
| 2/1,5 | 1,33 | prudente |
| 1/1,5 | 0,67 | aucun (interdit) |
| 1,5/1 | 1,5 | prudente + équilibrée |
| 2,25/1,5 | 1,5 | prudente + équilibrée |
| 2/1 | 2,0 | prudente + équilibrée + risquée |
| 2,25/1 | 2,25 | prudente + équilibrée + risquée |

Duels dans chaque niveau (102 cases, achat immédiat) :
- **Prudente** : 1,5/1,5 bat 1/1 dans 71 cas sur 102.
- **Équilibrée** : 2,25/1,5 bat 1,5/1 dans 83 cas sur 102 (c'est aussi le réglage le plus souvent positif : 16/102).
- **Risquée** : 2,25/1 bat 2/1 dans 93 cas sur 102.
Mais aucun réglage n'est solide : même le meilleur reste négatif dans la grande majorité des cases.

## Tableau principal — achat immédiat 0,14 %/côté
Format : net % après frais (trades, moitié 1 / moitié 2). Coupure des moitiés : 7 avr. 2026 23h30 UTC.
Pire baisse sur notre capital (outil × 5 %) : sous 1,4 % pour tous les signaux d'équipe ; ≤ 4 % pour le témoin quotidien → jamais le critère bloquant.

| règle                     | paire   | 1/1                      | 1.5/1.5                  | 1.5/1                    | 2/1                      | 2.25/1.5                 | 2.25/1                   |
|:--------------------------|:--------|:-------------------------|:-------------------------|:-------------------------|:-------------------------|:-------------------------|:-------------------------|
| outil team_rebound        | BTC     | -7.3 (11, -5.0/-2.4)     | -1.1 (11, -0.7/-0.5)     | -5.9 (11, -3.6/-2.4)     | -7.3 (11, -5.0/-2.4)     | -6.1 (11, -4.4/-1.9)     | -6.9 (11, -4.6/-2.4)     |
| outil team_rebound        | ETH     | -4.9 (17, -1.6/-3.4)     | +0.4 (17, +5.0/-4.4)     | -1.0 (17, +1.4/-2.4)     | -1.3 (17, +0.1/-1.4)     | -1.1 (17, +1.8/-2.9)     | +0.2 (17, +1.1/-0.9)     |
| outil team_rebound        | SOL     | -9.5 (21, -6.2/-3.5)     | +2.5 (21, +0.6/+1.9)     | -5.8 (21, -4.8/-1.1)     | -2.0 (21, -3.3/+1.4)     | +3.7 (21, -2.4/+6.3)     | -0.1 (21, -2.6/+2.6)     |
| outil team_breakout       | BTC     | -9.5 (34, -7.5/-2.2)     | -13.2 (34, -9.4/-4.3)    | -9.1 (34, -7.0/-2.3)     | -6.4 (34, -7.5/+1.2)     | -8.7 (34, -8.4/-0.3)     | -5.7 (34, -6.6/+1.0)     |
| outil team_breakout       | ETH     | -6.8 (30, -3.2/-3.7)     | -6.2 (30, -6.2/-0.1)     | -4.5 (30, -2.3/-2.3)     | -1.2 (30, -2.3/+1.1)     | -0.8 (30, -5.5/+5.0)     | +0.8 (30, -1.1/+1.9)     |
| outil team_breakout       | SOL     | -9.9 (36, -3.2/-6.9)     | -4.4 (36, -3.3/-1.1)     | -6.8 (36, -4.7/-2.2)     | -0.9 (36, -2.3/+1.5)     | +0.6 (36, -1.9/+2.6)     | -0.7 (36, -4.3/+3.8)     |
| outil sell_rebuy_ma0      | BTC     | -15.9 (34, -8.6/-8.1)    | -11.6 (29, -7.0/-4.9)    | -15.6 (31, -6.4/-9.8)    | -13.3 (30, -5.2/-8.6)    | -6.0 (28, -0.2/-5.9)     | -11.8 (30, -4.0/-8.1)    |
| outil sell_rebuy_ma0      | ETH     | -20.1 (60, -8.4/-12.8)   | -13.5 (54, -3.2/-10.6)   | -18.2 (57, -5.5/-13.4)   | -18.2 (56, -7.8/-11.3)   | -12.6 (52, -7.8/-5.3)    | -15.1 (56, -5.4/-10.3)   |
| outil sell_rebuy_ma0      | SOL     | -15.4 (68, -5.7/-10.2)   | -18.9 (61, -4.3/-15.2)   | -18.3 (63, -7.9/-11.2)   | -19.6 (62, -9.7/-10.9)   | -16.3 (59, -3.8/-13.0)   | -15.6 (62, -7.1/-9.1)    |
| outil sell_rebuy_ma200    | BTC     | -1.1 (4, -1.1/+0.0)      | -1.1 (4, -1.1/+0.0)      | -0.1 (4, -0.1/+0.0)      | +0.9 (4, +0.9/+0.0)      | +0.5 (4, +0.5/+0.0)      | +1.5 (4, +1.5/+0.0)      |
| outil sell_rebuy_ma200    | ETH     | -0.2 (8, +0.4/-0.5)      | +5.8 (7, +4.5/+1.2)      | +1.1 (7, +2.4/-1.3)      | -2.9 (7, -1.6/-1.3)      | +2.7 (7, +0.7/+2.0)      | -2.4 (7, -1.1/-1.3)      |
| outil sell_rebuy_ma200    | SOL     | -1.3 (12, +0.5/-1.8)     | -1.4 (11, -0.9/-0.5)     | -1.5 (11, +1.1/-2.5)     | -1.9 (11, +0.6/-2.5)     | -0.6 (11, -0.9/+0.2)     | -0.9 (11, +1.6/-2.5)     |
| own daily15h long         | BTC     | -68.6 (332, -48.2/-39.5) | -50.9 (285, -37.9/-20.8) | -62.9 (313, -43.8/-34.0) | -64.6 (295, -45.6/-35.0) | -48.3 (250, -43.2/-9.0)  | -63.7 (286, -44.8/-34.2) |
| own daily15h long         | ETH     | -75.7 (348, -58.3/-41.7) | -59.8 (314, -44.0/-28.3) | -70.8 (334, -57.9/-30.8) | -66.4 (323, -57.8/-20.3) | -54.3 (287, -40.0/-23.9) | -66.2 (315, -57.3/-20.8) |
| own daily15h long         | SOL     | -78.9 (358, -60.4/-46.6) | -69.4 (340, -53.5/-34.2) | -77.0 (351, -61.0/-41.1) | -70.8 (339, -57.1/-31.9) | -66.2 (311, -52.2/-29.1) | -74.4 (331, -58.0/-39.1) |
| own daily15h short        | BTC     | -55.1 (332, -31.6/-34.3) | -58.8 (285, -32.8/-38.7) | -55.4 (313, -27.1/-38.8) | -52.4 (298, -23.5/-37.8) | -37.3 (253, -8.4/-31.5)  | -48.0 (287, -17.1/-37.3) |
| own daily15h short        | ETH     | -59.1 (348, -32.8/-39.2) | -60.8 (314, -35.6/-39.1) | -67.2 (340, -43.7/-41.6) | -61.0 (326, -38.4/-36.7) | -48.0 (294, -21.5/-33.8) | -54.3 (323, -28.8/-35.9) |
| own daily15h short        | SOL     | -56.4 (358, -33.5/-34.5) | -59.4 (340, -30.6/-41.5) | -60.6 (352, -33.1/-41.1) | -59.2 (340, -36.1/-36.2) | -60.2 (317, -39.6/-34.1) | -53.7 (335, -33.0/-30.9) |
| own mirror_rebound short  | BTC     | -4.1 (8, -4.3/+0.2)      | -4.1 (8, -2.8/-1.3)      | -4.6 (8, -3.8/-0.8)      | -3.6 (8, -3.3/-0.3)      | -1.9 (8, -1.3/-0.6)      | -3.1 (8, -3.1/-0.1)      |
| own mirror_rebound short  | ETH     | -9.9 (16, -7.0/-3.0)     | -7.0 (16, -3.2/-4.0)     | -9.8 (16, -7.5/-2.6)     | -8.0 (16, -6.1/-2.1)     | -1.9 (16, +1.4/-3.3)     | -7.1 (16, -5.3/-1.8)     |
| own mirror_rebound short  | SOL     | -0.9 (18, -1.3/+0.3)     | -7.5 (18, -3.2/-4.5)     | -2.9 (18, -0.3/-2.6)     | -4.7 (18, -0.2/-4.5)     | -8.8 (18, -2.4/-6.6)     | -3.3 (18, +1.1/-4.3)     |
| own mirror_breakout short | BTC     | -23.4 (61, -13.5/-11.5)  | -19.4 (60, -10.5/-9.9)   | -22.8 (61, -14.3/-9.9)   | -21.2 (61, -12.6/-9.9)   | -9.9 (59, +1.4/-11.1)    | -19.2 (61, -10.5/-9.7)   |
| own mirror_breakout short | ETH     | -22.6 (53, -15.2/-8.7)   | -13.4 (53, -7.8/-6.0)    | -22.1 (53, -15.5/-7.8)   | -15.1 (53, -12.5/-3.0)   | -5.5 (52, -3.7/-1.8)     | -14.4 (53, -10.9/-3.9)   |
| own mirror_breakout short | SOL     | -16.2 (39, -11.8/-5.0)   | -15.0 (38, -10.1/-5.4)   | -16.2 (39, -12.2/-4.5)   | -20.3 (39, -14.4/-6.9)   | -18.0 (38, -10.0/-8.9)   | -21.2 (39, -13.3/-9.2)   |
| own rise3_noma short      | BTC     | -11.2 (25, -4.5/-7.0)    | -7.9 (25, -2.0/-6.0)     | -11.2 (25, -1.5/-9.8)    | -10.4 (25, -1.5/-9.1)    | -4.6 (25, +3.4/-7.8)     | -9.0 (25, -0.2/-8.8)     |
| own rise3_noma short      | ETH     | -11.4 (44, -3.3/-8.4)    | -5.7 (44, +1.3/-6.9)     | -12.6 (44, -4.2/-8.8)    | -10.3 (44, -2.2/-8.3)    | -3.1 (44, +0.7/-3.8)     | -7.4 (44, +0.1/-7.5)     |
| own rise3_noma short      | SOL     | -1.9 (47, +0.8/-2.7)     | -7.8 (47, +2.0/-9.7)     | -9.3 (47, -3.0/-6.5)     | -11.0 (47, -3.0/-8.3)    | -7.5 (47, +3.0/-10.2)    | -7.3 (47, -0.4/-6.9)     |

## Verdict équipe pour 1/1 (achat immédiat)
Critères : gain > 0 après frais, ~20 trades ou plus, les deux moitiés gagnantes, pire baisse < 8 % du capital, gagnant en achat immédiat.
**0 cas sur 42 passent** (tableau D de `tables.md`). Le seul critère toujours tenu est la pire baisse (< 4 % du capital).
Cas où 1/1 est positif : seulement `rise3_ma200` baisse ETH (+0,35 %, 6 trades) et SOL (+0,53 %, 9 trades) — trop peu de trades, une moitié perdante.
Avec 0 % de frais (`revolutx-maker`, tout rempli) : 1/1 est encore négatif sur 5 des 6 tests des signaux hausse de l'outil.

Les « oui » trouvés par l'outil dans cette grille ne sont **pas pour 1/1** : SOL `team_rebound` 1,5/1,5 (+2,5 % immédiat, 21 trades) et 2/1,5 (+5,5 %), SOL `team_breakout` 2/1,5 (+0,2 %). Fragiles : mon recalcul indépendant donne une moitié 1 perdante pour SOL rebond (−0,5 %) et −6,8 % pour SOL cassure 2/1,5. Seulement 21–36 trades. À ne pas transformer en règle sans plus de vérifications.

## Revérification (étape 4) — même conclusion à chaque fois
| vérification | 1/1 : cases gagnantes | 1,5/1,5 | 1,5/1 | 2/1 | 2,25/1,5 |
|---|---|---|---|---|---|
| recalcul indépendant (arrêt d'abord), immédiat | 2/30 | 2/30 | 0/30 | 2/30 | 4/30 |
| recalcul, cible doit passer 0,10 % au-delà | 0/30 | 1/30 | 0/30 | 2/30 | 4/30 |
| recalcul, cible d'abord (optimiste) | 4/30 | 2/30 | 0/30 | 3/30 | 4/30 |
| outil, achat immédiat | 0/12 | 3/12 | 1/12 | 1/12 | 4/12 |
| outil, 0 % + `--fill touch` (hausse) | 1/6 | 3/6 | 1/6 | 3/6 | 3/6 |
| outil, 0 % tout rempli (hausse) | 1/6 | 5/6 | 5/6 | 5/6 | 4/6 |
Autre coupure : en 4 trimestres, 1/1 n'a en moyenne que 0,3–0,7 trimestre gagnant sur 4. Deux moteurs différents (outil avec blocage 48 h après un signal ; mon calcul avec nouvelle entrée dès la sortie) donnent le même classement : 1/1 parmi les pires.

## Nos relevés 30 s (8–9 oct.) — décisions réelles de Predict
Méthode : entrée à l'heure de la décision si le prix est à moins de 0,15 % du prix de départ prévu, sinon au premier passage par ce prix. Ensuite : premier prix touché (prix du milieu ; même résultat avec achat/vente réels bid/ask). Décisions annulées (D-027, D-032) exclues. Doublons rétro D-019/D-020 = D-016/D-017.
- 33 variantes, 29 entrées (D-025a, D-025c, D-028c, D-033b : prix de départ jamais atteint) ; 21 entrées distinctes.

| | cible d'abord | arrêt d'abord | rien encore (20h59) |
|---|---|---|---|
| réglage réel (29 variantes) | 3 (D-015/16/17, à ±0,5 %) | 4 (D-024c, D-026b, D-026c, D-029c) | 22 |
| 1/1 (29 variantes) | 4 (D-015/16/17 + D-021) | 7 (+ D-024a, D-026a, D-029a) | 18 |
| 1/1 (21 entrées distinctes) | 4 | 3 | 14 |
| 9 oct. seul, 1/1 (25 variantes) | 0 | 7 | 18 |

- Là où 1/1 change le résultat : D-021 (SOL baisse de nuit) cible 97,02 € touchée à 02h26 → mieux ; D-024a, D-026a, D-029a → arrêt touché au lieu de « rien » → pire. 1 mieux, 3 pires.
- Le 9 oct., tous les arrêts à 1 % déjà présents ont été touchés de la même façon ; 1/1 ajoute seulement des arrêts.
- Résultat net en frais immédiats sur les 21 entrées distinctes avec 1/1 : 4 × 0,72 % − 3 × 1,28 % ≈ −0,96 % cumulé.
- **2 jours, c'est beaucoup trop court pour conclure** (7 trades fermés à 1/1). C'est seulement une illustration.

## Prudence / limites
- Bougies 1 h : on ne sait pas l'ordre des prix dans l'heure ; « arrêt d'abord » est prudent ; « cible d'abord » montré en vérif (ne change pas la conclusion).
- Les signaux d'équipe sont des copies approchées : les vraies décisions de Predict viennent de sonnettes et de lecture du marché. Le témoin quotidien 15h dit seulement ce que donne la sortie elle-même, sans avantage d'entrée.
- L'outil (hausse) garde un signal 48 h : pas de nouvelle entrée pendant 48 h après un signal → moins de trades que mon calcul. Même conclusion des deux côtés.
- Baisse en `sell_rebuy` = résultat en pièces comparé à garder ; pas d'emprunt.
- L'année a été très baissière (BTC −30 %, ETH −42 %, SOL −48 %) : les tests de hausse sont désavantagés, ceux de baisse avantagés.
- Prix Binance EUR ; Revolut X peut différer un peu.

## Fichiers
`tables.md` (tous les tableaux), `table_main_immediat.md`, `tool_results.csv`, `head_to_head_cells.csv`, `own_sim/grid_{main,touch,tpfirst}.csv`, `ticks_replay_entry.csv` (méthode principale), `ticks_replay_decision.csv` (méthode feuille de score), `scripts/` (commandes et calculs), `data/` (bougies du cache).
