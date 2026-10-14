# Écart à la cible — simulations fermées depuis le 8 oct. 2026 (+ briefs Research + test sur le passé)
_PM-Compound, 11 oct. 2026, ~08h00 (heure de Bruxelles). Lecture seule : aucun ordre, pas d'`ai.sh ask`, aucun secret. Pas de proposition de règle._

Fichiers : `ecart_cible.py` (parties 1–3 + contexte), `ecart_cible.csv`, `briefs_research.csv`, `totaux.json`, `backtest_grille.csv` (504 tests), `backtest_par_cible.csv`, `backtest/` (commandes, JSON de chaque test, `scripts/analyse.py`).

Méthode prix : relevés 30 s côté sortie (bid pour une hausse, ask pour une baisse) ; trous > 90 s comblés par bougies 5 min Coinbase (haut pour une hausse, bas pour une baisse) — colonne « source » = tick ou **bougie**. Trous : 10 oct. 03h08–07h58, 08h25–09h05, 09h15–11h41, 11h58–15h08, 15h18–18h10, et 10→11 oct. 19h01–07h32.

## 1. Les 10 trades (hors rétro)
| D | Paire | Sens | Sortie | Entrée | Visé | Écart visé % | Écart arrêt % | Ouvert (h) | Meilleur mouvement % (prix, heure, source) | % du chemin vers le visé | Plage du jour % | Visé en % de la plage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D-021 | SOL | baisse | arrêt | 98,00 | 96,53 | 1,50 | 1,50 | 15,5 | +1,09 (96,93 ; 09/10 03h20 ; tick) | 73 % | 10,6 (8/10) | 14 % |
| D-024a | SOL | hausse | idée morte | 98,69 | 100,09 | 1,42 | 1,41 | 0,6 | −0,02 (98,67 ; à l'entrée ; tick) | −1 % | 3,2 | 45 % |
| D-026 | SOL | baisse | arrêt | 97,49 | 95,54 | 2,00 | 1,01 | 0,7 | −0,06 (97,55 ; 16h01 ; tick) | −3 % | 3,2 | 63 % |
| D-023 | BTC | hausse | idée morte | 74 120 | 75 232 | 1,50 | 1,00 | 2,7 | +0,31 (74 349 ; 09/10 16h34 ; tick) | 21 % | 2,4 | 62 % |
| D-031a | BTC | hausse | idée morte | 73 981 | 74 843 | 1,17 | 1,16 | 6,9 | +0,23 (74 147 ; 09/10 17h32 ; tick) | 19 % | 2,4 | 48 % |
| D-031b | SOL | baisse | idée morte | 97,93 | 96,32 | 1,64 | 0,96 | 14,9 | +1,14 (96,81 ; 09/10 21h59 ; tick) | 70 % | 3,2 | 52 % |
| D-036a | SOL | baisse | idée morte | 96,96 | 95,10 | 1,92 | 1,92 | 8,0 | −0,04 (97,00 ; 10/10 00h14 ; tick) | −2 % | 2,0 (10/10) | 95 % |
| D-024b | ETH | baisse | idée morte | 2 232,70 | 2 197 | 1,60 | 1,00 | 27,1 | +1,06 (2 209,11 ; 09/10 22h06 ; tick) | 66 % | 2,1 | 77 % |
| D-028a | ETH | baisse | idée morte | 2 225,87 | 2 181 | 2,02 | 1,98 | 25,8 | +0,75 (2 209,11 ; 09/10 22h06 ; tick) | 37 % | 2,1 | 97 % |
| D-042a | SOL | hausse | idée morte | 98,475 | 100,44 | 2,00 | 1,51 | 13,4 | +0,27 (98,74 ; 10/10 21h35 ; **bougie**) | 13 % | 2,0 (10/10) | 99 % |

Rétro, pour comparer (non comptés) :
| D | Paire | Sens | Entrée | Visé | Écart visé % | Écart arrêt % | Ouvert (h) | Meilleur mouvement % | % du chemin | Plage du jour % | Visé en % de la plage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-020 | SOL | baisse | 100,695 | 100,20 | 0,49 | 0,50 | 0,5 | +0,38 (ask 100,31 ; 15h01 ; tick) | 78 % | 10,6 | 5 % |
| D-019 | ETH | baisse | 2 261,905 | 2 250,60 | 0,50 | 0,50 | 1,1 | +0,48 (ask 2 251,16 ; 15h38 ; tick) | 95 % | 7,5 | 7 % |
(Les deux sont notés « visé touché » : rejoués après coup, sur un ordre à prix fixé ; côté ask strict, l'ask le plus bas reste à quelques centimes au-dessus du visé.)

Plage du jour = (haut − bas) / bas, prix mid, journée de Bruxelles, jour d'ouverture du trade :
| | 8 oct. | 9 oct. | 10 oct. | 11 oct. (jusqu'à 07h46) |
|---|---|---|---|---|
| BTC | 3,97 % | 2,41 % | 0,91 % | 0,43 % |
| ETH | 7,54 % | 2,07 % | 1,62 % | 0,58 % |
| SOL | 10,64 % | 3,16 % | 2,02 % | 1,46 % |
(9 oct. cohérent avec Scan : BTC 2,3 / ETH 1,7 / SOL 2,6 ; nos chiffres sont un peu plus larges, avec le pic SOL 99,86 pris dans le trou 13h19–13h59 et la journée complète jusqu'à minuit. 8 oct. : 4,0–10,6 % contre 3,7–9,7 % chez Scan.)

**Résumé (10 trades)** :
- Écart moyen jusqu'au visé **1,68 %** (arrêt moyen 1,35 %) ; meilleur mouvement moyen **+0,47 %**, soit en moyenne **29 %** du chemin.
- Au moins 50 % du chemin : **3/10** (D-021 73 %, D-031b 70 %, D-024b 66 %) ; au moins 75 % : **0/10**. 3 trades n'ont jamais été en gain (D-024a, D-026, D-036a).
- Durée médiane ouverte : **10,7 h**.
- Le visé représente en moyenne **65 %** de toute la plage haut–bas du jour (de 14 % le 8 oct. à 95–99 % le 10 oct.). Les 2 rétro gagnants visaient 0,5 %, soit 5–7 % de la plage du jour.

## 2. Briefs Research (8 et 9 oct.)
- **8 oct. 14h33** : aucune ligne chiffrée (prix seulement, « pas de signal d'achat clair »). La ligne chiffrée par crypto n'est devenue obligatoire que le 8 oct. à 18h45. Rien à mesurer.
- **9 oct. 14h44** (prix relevés à 15h04:59, heure limite 17h00 pour les trois lignes) :

| Paire | Idée | Entrée | Visé | Écart visé % | Arrêt (écart %) | Meilleur mouvement jusqu'à 17h00 | % du chemin | Visé atteint ? | Arrêt touché ? | Visé en % de la plage du 9 oct. |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC | hausse | 74 121 | 75 232 | 1,50 | 73 379 (1,00) | +0,31 % (bid 74 349, 16h34, tick) | 21 % | non | non | 62 % |
| ETH | baisse | 2 230 | 2 197 | 1,48 | 2 263 (1,48) | +0,79 % (ask 2 212,34, 15h36, tick) | 54 % | non | non | 71 % |
| SOL | hausse | 98,61 | 100,09 | 1,50 | 97,13 (1,50) | +0,20 % (bid 98,81, 16h34, tick) | 14 % | non | non | 48 % |

Aucune des 3 lignes n'atteint son visé avant l'heure limite (en 2 h, une cible de 1,5 % pèse 48–71 % de la plage de toute la journée).

## 3. Contexte seulement : taille typique d'un mouvement (8–11 oct.)
Mouvement favorable maximal après une entrée à chaque palier de 5 min (prix mid ; série de 5 min faite de nos relevés, avec les bougies Coinbase dans les trous, soit ~45 % des paliers) :
| Paire | Médiane dans les 6 h — hausse / baisse | Médiane dans les 24 h — hausse / baisse |
|---|---|---|
| BTC | +0,32 % / 0,22 % | +0,80 % / 0,34 % |
| ETH | +0,46 % / 0,33 % | +1,04 % / 0,62 % |
| SOL | +0,52 % / 0,74 % | +1,07 % / 1,55 % |
885 entrées (6 h) et 669 entrées (24 h) par paire, mais elles se chevauchent : il n'y a en réalité que ~3 jours de marché, dont la forte chute du 8 oct. À lire comme un ordre de grandeur, pas comme une statistique.

## 4. Test sur le passé : plus petit écart de visé encore gagnant après frais
**Outil** : `backtest.sh` (Vibe-Trading), bougies 1 h Binance EUR **depuis le cache** (`home/cache/ccxt`, `--end 2026-10-07 --days 365`, du 7 oct. 2025 au 7 oct. 2026, coupure des moitiés le 7 avr. 2026 23h30 UTC). Pas d'appel réseau à Binance (451). Fenêtre 15–17h en jours ouvrés, sans sortie 22h, sécurité 48 h.
- **Grille** : visé {0,75 ; 1 ; 1,25 ; 1,5 ; 2 ; 2,5 ; 3} % × arrêt = visé / {1 prudente ; 1,5 équilibrée ; 2 risquée} × BTC/ETH/SOL.
- **Achats** : `team_rebound`, `team_breakout`, avec frais `revolutx` (immédiat, 0,14 %/côté) et `revolutx-maker --fill touch`.
- **Ventes** : `sell_rebuy` (vente de pièces qu'on a, rachat au visé, rachat de sécurité = arrêt), avec filtre 200 h (`tm200`) et sans filtre (`tm0`). Frais `revolutx` (frais par défaut de l'outil : vente et rachat au visé à 0 %, sécurité à 0,14 %) et `alltaker` (0,14 % partout). `--fill touch` n'existe pas pour `sell_rebuy`.
- Au total 504 tests. « Passe » = règle d'équipe : net > 0, au moins 20 trades, les deux moitiés > 0, pire baisse sur le capital < 8 %, et le test en achat immédiat positif (mon recalcul = verdict de l'outil, 21/21).
- Seuil de réussite nécessaire (taux de gagnants) = (arrêt + frais de l'arrêt) / (visé − frais du visé + arrêt + frais de l'arrêt), sans compter les sorties à 48 h.

Par écart de visé (72 cases chacun : 3 paires × 4 règles × 3 rapports × 2 frais) :
| Visé | Cases nettes > 0 | Nettes > 0 et 2 moitiés > 0 | Passent le test | Net médian | Gagnants médians (immédiat / maker) | Seuil médian (immédiat / maker) |
|---|---|---|---|---|---|---|
| 0,75 % | 5 | 2 (ETH baisse tm200, 9 trades) | 0 | −7,4 % | 30 % / 24 % | 56 % / 46 % |
| 1 % | 8 | 2 (ETH baisse tm200, 8 trades) | 0 | −7,3 % | 37 % / 29 % | 53 % / 45 % |
| 1,25 % | 8 | 2 (ETH baisse tm200, 7 trades) | 0 | −6,1 % | 38 % / 36 % | 51 % / 44 % |
| **1,5 %** | 16 | 4 | **2** | −4,5 % | 43 % / 39 % | 49 % / 43 % |
| 2 % | 19 | 9 | 5 | −2,7 % | 44 % / 44 % | 46 % / 42 % |
| 2,5 % | 29 | 7 | 6 | −1,0 % | 44 % / 44 % | 44 % / 42 % |
| 3 % | 34 | 11 | 8 | −0,5 % | 46 % / 45 % | 44 % / 42 % |

À 1 %/1 % : les 24 cases sont toutes négatives sauf ETH baisse tm200 (8 trades, moitié 2 négative) et BTC cassure maker-touch (+0,13 %, moitié 1 −5,6 %). C'est cohérent avec la note de Predict (perte partout).

Plus petit écart par paire et par sens :
| Paire / sens | Net > 0 dans les 2 moitiés (quel que soit le nombre de trades) | Passe le test d'équipe |
|---|---|---|
| BTC hausse | **aucun** (jusqu'à 3 %) | aucun |
| BTC baisse | **aucun** | aucun |
| ETH hausse | **aucun** | aucun |
| ETH baisse | 0,75 % (tm200, 9 trades, +2,6 % ; trop peu de trades) | **2,5 %** (tm0, prudente 2,5/2,5 ; 46 trades ; +4,7 % ; 52,2 % de gagnants pour un seuil de 51,4 % ; moitiés +1,7 / +3,0) |
| SOL hausse | 1,5 % | **1,5 %** (`team_rebound`, prudente 1,5/1,5 : immédiat 21 trades +2,5 %, 61,9 % de gagnants pour un seuil de 59,3 %, moitiés +0,6/+1,9 ; maker-touch 23 trades +6,2 %, 60,9 % pour 52,2 %, moitiés +2,2/+3,9) |
| SOL baisse | 2,5 % (tm200, 11 trades) | aucun |

**Réponse** : le plus petit écart de visé net positif dans les deux moitiés **et** passant le test d'équipe est **1,5 %**, mais dans **un seul cas** : SOL, idée à la hausse après rebond (`team_rebound`), arrêt 1,5 % (prudente), avec les deux modèles de frais.
- Il ne tient qu'avec ~21–23 trades par an et une marge de 2,6 points au-dessus du taux de gagnants nécessaire (immédiat).
- Les voisins 1,5 % équilibrée et risquée ne passent pas.
- **Sous 1,5 %, rien ne passe** : 0/216 cases à 0,75–1,25 %. Les seuls positifs sur les deux moitiés sont des ventes ETH avec 7 à 9 trades.
- Pour BTC (les deux sens) et ETH hausse, aucun écart jusqu'à 3 % n'est positif dans les deux moitiés.
- Limites : prix Binance 1 h jusqu'au 7 oct. 2026, si arrêt et visé sont touchés dans la même bougie on compte l'arrêt, les règles de l'outil approximent les décisions manuelles, et 504 cases testées font qu'une poignée de positifs peut venir de la chance.

## 5. Limites générales
- 10 trades, 3 jours, presque tous des « idée morte » : l'échantillon est très petit.
- Les bougies sont des prix d'échange (pas bid/ask) : le meilleur mouvement de D-042a vient d'une bougie.
- Les plages des 10 et 11 oct. reposent beaucoup sur les bougies (gros trous dans les relevés).
