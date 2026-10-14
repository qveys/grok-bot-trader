# Sorties par type — simulations fermées depuis le 8 oct. 2026
_PM-Compound, 11 oct. 2026, 07h45 (heure de Bruxelles). Lecture seule, aucun ordre. Script : `sorties_par_type.py` ; données : `sorties_par_type.csv`, `result.json`, `totaux.json`._

Sources : `guardian/state.json` (positions fermées) + `state/trades_log.jsonl` (résultats après frais) + `knowledge/trading_journal.md`. Frais : 0,05 % par côté (`FEE_REVOLUT`, guardian/scripts/paper_fill.py). D-021 compté au résultat corrigé à l'arrêt (−0,24 €, correction Risk 10/10 18h25).

## 1. Par type de sortie (hors rétro)
| Type | Trades | Résultat total après frais |
|---|---|---|
| (1) Prix d'arrêt touché | 2 (D-021, D-026) | **−0,35 €** |
| (2) Prix visé touché | 0 | 0,00 € |
| (3) Fermé « idée morte » | 8 | **−0,95 €** |
| **Total** | 10 | **−1,30 €** |

À part, rejouées « rétro » (non comptées) : D-019 ETH baisse +0,05 €, D-020 SOL baisse +0,05 € — toutes les deux au prix visé, total +0,10 €.

Détail arrêt : D-021 SOL baisse 14,70 € −0,24 € (09/10 14h26, arrêt 99,47 dépassé pendant un trou de relevés) ; D-026 SOL baisse 10,00 € −0,11 € (09/10 16h22).

## 2. Idée morte : et si on avait laissé courir ?
Méthode : à partir de l'heure réelle de fermeture, 1er niveau touché (arrêt ou visé) côté sortie (bid pour revendre un achat, ask pour racheter une vente) sur nos relevés 30 s ; trous > 90 s comblés par bougies 5 min Coinbase (haut/bas ; arrêt d'abord si les deux dans la même bougie ; Kraken pas nécessaire). Remplissage au prix du niveau, frais 0,05 % par côté. Avant fermeture : aucun des 8 n'avait touché son arrêt ou son visé (vérifié).

| D | Paire | Sens | Taille | Réel | Fermé le | Si laissé ouvert | Niveau / quand | Délai |
|---|---|---|---|---|---|---|---|---|
| D-024a | SOL | hausse | 15,00 € | −0,20 € | 09/10 15h43 | **−0,23 €** | arrêt 97,30 — 09/10 21h32 (relevé bid) | +5 h 49 |
| D-036a | SOL | baisse | 13,40 € | −0,18 € | 10/10 08h04 | **−0,27 €** | arrêt 98,82 — 10/10 16h35–16h40 (bougie 5 min, haut 98,82 pile) | +8 h 30 |
| D-023 | BTC | hausse | 24,98 € | −0,08 € | 09/10 17h09 | −0,01 € (marque) | pas encore tranché (visé 75 232 / arrêt 73 379) — bid 74 124,68 | — |
| D-031a | BTC | hausse | 15,00 € | −0,09 € | 10/10 00h06 | +0,01 € (marque) | pas encore tranché (74 843 / 73 120) — bid 74 124,68 | — |
| D-031b | SOL | baisse | 10,00 € | −0,04 € | 10/10 08h04 | +0,01 € (marque) | pas encore tranché (96,32 / 98,87 ; haut vu 98,86, à 1 centime de l'arrêt le 10/10 ~16h45) — ask 97,76 | — |
| D-024b | ETH | baisse | 10,00 € | −0,04 € | 10/10 18h14 | −0,03 € (marque) | pas encore tranché (2 197 / 2 255) — ask 2 236,66 | — |
| D-028a | ETH | baisse | 15,00 € | −0,11 € | 10/10 18h14 | −0,09 € (marque) | pas encore tranché (2 181 / 2 270) — ask 2 236,66 | — |
| D-042a | SOL | hausse | 25,00 € | −0,21 € | 11/10 07h37 | −0,21 € (marque) | pas encore tranché (100,44 / 96,99) — bid 97,75 (fermé il y a 5 min) | — |

Marques = dernier relevé 11/10 07h42.

## 3. Bilan idée morte
- **Tranchés (2)** : réel **−0,38 €** contre **−0,50 €** si laissés ouverts → la fermeture tôt a **épargné 0,12 €**. Les 2 auraient fini à l'arrêt, 0 au prix visé.
- **Pas encore tranchés (6)** : réel −0,57 € ; valeur actuelle s'ils étaient encore ouverts −0,31 € (+0,26 € de mieux pour l'instant, mais non réalisé et tous encore entre arrêt et visé).
- **Total des 8 avec marques** : réel −0,95 € contre −0,81 € → avec les marques actuelles, fermer tôt **coûte 0,14 €** pour l'instant.
- En clair : sur ce qui est vraiment tranché, fermer « idée morte » a **fait gagner** de l'argent (0,12 €, 2 sur 2 auraient touché l'arrêt). En comptant les 6 encore ouverts au prix d'aujourd'hui, ça a **coûté** 0,14 €. Les deux lectures changent avec le prix — rien n'est décidé.
- **Échantillon minuscule** : 8 trades idée morte, dont 2 tranchés ; écarts de quelques centimes, dans une seule fenêtre de 3 jours. Aucune conclusion solide.

## 4. Limites
- Relevés 30 s avec beaucoup de trous le 10 oct. (03h08–07h58, 08h25–09h05, 09h15–11h41, 11h58–15h08, 15h18–18h10) et la nuit 10→11 oct. (19h01–07h32) : comblés par bougies 5 min Coinbase. Les bougies sont des prix d'échange (pas bid/ask) : D-036a touche son arrêt à 98,82 pile (haut de bougie 98,82, aussi en bougie 1 min ~16h39) — cas limite.
- Remplissage au prix exact du niveau (pas de glissement).
- D-023 n'avait pas de frais d'entrée enregistrés (avant le 9 oct. 15h) : réel et contrefactuel calculés pareil.
- D-024a : un reste de 0,0018 SOL soldé 3 min plus tard est inclus dans le réel (−0,0019 €) ; contrefactuel sur 0,15199 SOL.
