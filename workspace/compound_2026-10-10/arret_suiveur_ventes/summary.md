# Arrêt suiveur sur les ventes, sans sortie à l'heure — PM-Compound, 10 oct. 2026
SIMULATION seulement. Aucun ordre, pas d'IA. Prix 1 h Binance (cache), 2025-10-07 → 2026-10-07, ETH/SOL/BTC-EUR. Coupure des moitiés : 2026-04-07.
570 essais (`run_all.py`) + 39 essais voisins (`recheck/neighbors.py`). Tous les tableaux : `tables.md` ; chiffres bruts : `results.csv`, `raw/`.

## Réponse simple
**Non.** Sur les ventes (`sell_rebuy`, idée à la baisse), avec les frais réels, un stop suiveur ne garde **pas** plus d'argent que le stop fixe **dans les deux moitiés**.
- Avec les frais Revolut X (K : vente et rachat au prix visé à 0 %, rachat de sécurité au marché à 0,14 %), la meilleure version suiveur (suiveur 1,5 % qui démarre à +0,5 %, avec prix visé) fait plus sur l'année : **+33,2 contre +25,1** (somme des 3 paires, % de pièces). Mais tout l'écart vient de la 1re moitié. En 2e moitié : **−6,66 contre −6,60**, donc pareil.
- Par paire : **BTC** : le fixe est mieux dans les deux moitiés, pour les 13 versions suiveur. **ETH** : le suiveur est mieux en 1re moitié et moins bien en 2e, pour toutes les versions. **SOL** : c'est la seule paire où le suiveur est mieux dans les deux moitiés (9 versions sur 13).
- Si chaque ordre est au marché à 0,14 % (K2) : tout perd, et le fixe perd le moins (−0,66 contre −1,4 au mieux). Le suiveur fait plus de ventes (196–267 au lieu de 129), donc il paie plus de frais.
- Verdict de l'équipe (`vt_verdict.py --all`) sur les ventes avec frais réels (K, K2) : **seul BTC avec le stop fixe passe** (« oui »). Aucune version suiveur ne passe.

## 1. Outil
- Avant ce test, on ne pouvait pas couper la sortie de 22h des trades `team_*` (`--exit-hour` obligatoire). `sell_rebuy` n'a déjà pas de sortie à l'heure (sauf `--max-hours`).
- Options ajoutées (sans ces options, rien ne change) :
  - `--no-time-exit` : un trade se ferme seulement au stop, au prix visé ou en fin de données ; au plus un achat par jour.
  - `--trail-start PCT` : le suiveur démarre seulement après un gain, puis le stop ne repasse jamais sous le prix d'achat.
  - `sell_rebuy --dip 0` : pas de prix visé.
- Contrôles :
  - 6 essais d'avant refaits : sorties identiques, octet par octet (`regression/`).
  - Anciens tests : 10 + 15 + 13 vérifs OK. Nouveau test `checks/test_notime.py` : 17 vérifs OK.
  - Moteur = copie indépendante dans les 90 essais `--fill touch`, `--no-time-exit` compris.
- Diff : `code/changes.diff`. Doc : README_FR.md.

## 2. Ventes (`sell_rebuy`), frais réels Revolut X (K) — % de pièces vs garder
| version | ETH | SOL | BTC | somme | H1 | H2 | ventes | gagnantes | pire baisse capital (×5 %) | pire vente | mieux que le fixe dans les 2 moitiés |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a fixe + prix visé (actuel) | +0,08 | +10,05 | +14,98 | **+25,11** | +33,31 | **−6,60** | 129 | 38,8 % | 0,74 % | −1,62 % | — |
| b fixe, sans prix visé ⚠ | +50,05 | +60,76 | +33,71 | +144,5 | +144,5 | 0 | 12 | 25 % | 2,59 % | −1,62 % | (sans valeur, voir ⚠) |
| c suiveur 1,5 + prix visé | +4,75 | +17,14 | +2,61 | +24,50 | +35,76 | −9,48 | 200 | 41,0 % | 0,60 % | −1,62 % | SOL |
| d suiveur 1,5, sans prix visé | +3,75 | +16,80 | +6,84 | +27,39 | +43,15 | −13,32 | 196 | 40,8 % | 0,65 % | −1,62 % | SOL |
| d suiveur 1,0, sans prix visé | +10,25 | +0,12 | +1,16 | +11,53 | +21,61 | −9,42 | 263 | 40,3 % | 0,58 % | −1,13 % | — |
| d suiveur 2,0, sans prix visé | −1,80 | +8,29 | +6,45 | +12,94 | +31,37 | −16,13 | 158 | 39,9 % | 0,78 % | −1,62 % | — |
| e à zéro puis suiveur 1,0 + prix visé | +5,88 | +19,16 | −0,97 | +24,07 | +32,59 | −7,30 | 227 | 42,7 % | 0,49 % | −1,62 % | SOL |
| **e à zéro puis suiveur 1,5 + prix visé** | +2,36 | +25,57 | +5,25 | **+33,18** | +41,27 | **−6,66** | 217 | 34,6 % | 0,55 % | −1,62 % | SOL |
| e à zéro puis suiveur 1,5, sans prix visé | −0,29 | +20,55 | +9,54 | +29,80 | +41,99 | −10,49 | 214 | 34,1 % | 0,71 % | −1,62 % | SOL |
| e à zéro puis suiveur 2,0 + prix visé | −2,65 | +16,69 | +6,08 | +20,12 | +31,62 | −9,86 | 211 | 25,1 % | 0,70 % | −1,62 % | SOL |

« À zéro puis suiveur » = le suiveur démarre quand la vente est à +0,5 % de gain, puis le prix de rachat ne repasse jamais au-dessus du prix de vente.
⚠ b (stop fixe sans prix visé) n'est pas une vraie stratégie : 4–5 ventes sont stoppées en octobre 2025. Ensuite, une vente reste ouverte presque toute l'année pendant la chute (ETH et SOL −40 % et plus), puis elle est rachetée en fin de données. C'est un pari sur la baisse du marché. 0 trade en 2e moitié.

**Les ventes selon les frais** (somme des 3 paires ; H1 / H2) :
| version | revolutx-maker (M) | touch (T) | K réel | K2 tout à 0,14 % | Guardian 0,05 % (G) |
|---|---|---|---|---|---|
| a fixe + prix visé | +37,2 | +37,2 | +25,1 (+33,3 / −6,6) | −0,7 (+12,7 / −12,3) | +23,1 (+31,3 / −6,7) |
| c suiveur 1,5 + prix visé | +51,4 | +51,4 | +24,5 (+35,8 / −9,5) | −9,3 (+7,6 / −16,0) | +28,2 (+38,3 / −8,5) |
| d suiveur 1,5, sans prix visé | +59,3 | +59,3 | +27,4 (+43,2 / −13,3) | −1,4 (+19,2 / −19,0) | +36,2 (+50,3 / −11,7) |
| e à zéro puis suiveur 1,5 + prix visé | +64,2 | +64,2 | +33,2 (+41,3 / −6,7) | −4,1 (+9,9 / −13,1) | +37,9 (+44,9 / −5,7) |
| e à zéro puis suiveur 1,5, sans prix visé | +65,1 | +65,1 | +29,8 (+42,0 / −10,5) | −1,7 (+15,2 / −16,0) | +39,5 (+50,1 / −8,9) |

- T = M pour `sell_rebuy`, comme le 8 oct. : `--fill touch` ne change rien ici.
- « Guardian 0,05 % » n'est pas un profil de l'outil : j'ai utilisé `--fee-pct 0.05`, soit 0,05 % sur chaque vente et chaque rachat. Pour `team_*` : `--fee 0.0005 --slippage 0`.
- En G, H2 : le fixe fait −6,70 ; e 1,5 + prix visé fait −5,67, à peine mieux. Toutes les autres versions suiveur sont moins bien.

## 3. Achats `team_rebound` / `team_breakout`, sans sortie 22h, achat immédiat 0,14 % (K) — somme des 3 paires
| version | rebond somme (H1 / H2) | cassure somme (H1 / H2) |
|---|---|---|
| a fixe + prix visé, avec 22h (avant) | −1,3 (+0,9 / −2,1) | −30,2 (−21,1 / −9,7) |
| a fixe + prix visé, sans 22h | −2,3 (+0,9 / −3,0) | −35,9 (−23,9 / −13,1) |
| b fixe, sans prix visé | −9,2 (−46,5 / +44,2) | +23,1 (−64,9 / +112,2) ⚠ peu de trades gagnants (2–5 %) |
| c suiveur 2,0 + prix visé | +0,3 (+1,3 / −0,8) | −32,0 (−24,5 / −8,1) |
| d suiveur 1,0, sans prix visé | −26,2 (−16,2 / −10,6) | +6,0 (+4,9 / +1,2) |
| d suiveur 1,5, sans prix visé | +6,3 (+8,3 / −1,8) | −1,7 (−5,7 / +4,4) |
| e à zéro puis suiveur 1,5, sans prix visé | −7,8 (−1,4 / −6,5) | +11,3 (−0,3 / +12,0) |
| e à zéro puis suiveur 2,0, sans prix visé | −9,4 (−1,0 / −8,5) | +9,0 (+6,8 / +2,9) |

- Avec le prix visé +1,5 %, le suiveur ne change presque rien et reste négatif.
- e 1,5 + prix visé = e 2,0 + prix visé : avant +1,5 %, le seuil suiveur reste sous le prix d'achat, donc c'est juste « stop remis au prix d'achat après +0,5 % ».
- Sans prix visé, le suiveur bat le fixe sans prix visé dans les 2 moitiés pour le rebond SOL et BTC. Pour la cassure, jamais : la 2e moitié du fixe sans prix visé est énorme, mais elle tient à quelques longs trades.
- Verdict équipe « oui » en K : 3 cas seulement, sur peu de trades.
  - Cassure ETH, suiveur 1,0 sans prix visé : +6,95 (H1 +3,43 / H2 +3,41, 40 trades).
  - Cassure ETH, à zéro puis suiveur 1,0 sans prix visé : +5,06 (+0,35 / +4,70).
  - Rebond SOL, suiveur 1,5 sans prix visé : +3,81 (+0,74 / +3,05, 23 trades).

## 4. Double vérification du meilleur cas (ventes, e à zéro puis suiveur 1,5 + prix visé)
- **Recalcul indépendant** (`recheck/indep_sr_trail.py`, boucle écrite à partir des règles, n'utilise pas l'outil) : 54 essais sur 54 identiques à l'outil (pièces finales, nombre de ventes). Essais refaits : 6 versions × 3 frais × 3 paires.
- **Par trimestre** (somme des 3 paires, K) :

| | T1 oct–janv | T2 janv–avr | T3 avr–juil | T4 juil–oct |
|---|---|---|---|---|
| a fixe + prix visé | +22,8 | +9,9 | **−0,2** | −6,6 |
| e 1,5 + prix visé | +26,6 | +12,9 | −2,0 | **−4,7** |
| d suiveur 1,5, sans prix visé | +23,9 | +17,5 | −8,2 | −5,2 |

  Le fixe gagne le T3 (contre toutes les versions, aussi en K2 et G). T4 : peu de ventes (ETH 1, SOL 6, BTC 0).
- **Réglages voisins** (K) :
  - Démarrage du suiveur à +0,3 % au lieu de +0,5 % : la somme tombe à **+1,4** (suiveur 1,5), +9,1 (1,25), −8,1 (1,75). Réglage fragile.
  - H2 : aucune des 12 versions voisines ne bat nettement le fixe (−6,60). La meilleure fait −4,56 (1,25 / démarrage 0,3), mais elle est mauvaise en H1.
  - BTC : le fixe reste devant dans les 12.

## 5. Ce qui tient, ce qui ne tient pas
- Ce qui tient : en 1re moitié (marché en forte baisse), le suiveur garde plus de pièces sur ETH et SOL. Sur SOL, il fait mieux dans les deux moitiés. Avec « à zéro puis suiveur », il y a plus de ventes gagnantes (suiveur 1,0 : 42,7 % contre 38,8 %), et la pire vente reste −1,62 % (−1,13 % avec le suiveur 1,0).
- Ce qui ne tient pas : en 2e moitié, rien ne bat le fixe nettement. BTC est toujours moins bien. Le résultat change beaucoup avec le réglage (démarrage 0,3 contre 0,5). Si le rachat de sécurité coûte plus cher (K2), le suiveur perd plus.

## Limites
- Un an seulement. ETH et SOL ont perdu plus de 40 % : les ventes ont profité de la baisse. Peu de ventes en 2e moitié (ETH 11–15, SOL 16–22, BTC 5–6).
- Prix Binance, pas Revolut X. Dans une heure, on ne sait pas si le haut vient avant le bas : le plus bas (ou le plus haut) d'une heure ne compte qu'à partir de l'heure suivante, ce qui est prudent. Le rachat de sécurité se fait au niveau visé, ou à l'ouverture si le prix a sauté au-dessus. En vrai, il peut glisser davantage.
- Le stop « à zéro » est au prix d'achat brut : les frais (0,14 % en K) ne sont pas couverts.
- `team_*` sans sortie à l'heure : un trade peut durer des semaines. La « fin des données » ferme le dernier trade au dernier prix.
- `vt_verdict.py --all` a réécrit les verdicts de tous les dossiers `home/runs` (1248 fichiers ; la date ne change que si le verdict change).
