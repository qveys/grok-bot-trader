# Meilleur gain possible — 6 pertes « idée à la baisse » (simulation) d'affilée
_PM-Compound · 10 oct. 2026, 18h25 (heure de Bruxelles) · simulation seulement, aucun ordre_

## Quelles ventes
Ventes « idée à la baisse » fermées (guardian/state.json + trades_log + trading_journal), par heure de fermeture : D-019 (+0,05 €) et D-020 (+0,05 €), toutes deux rétro et gagnantes, puis **6 pertes d'affilée** :
**D-021, D-026, D-031b, D-036a, D-024b, D-028a**. D-024b en fait partie (fermée à 18h14, à la même seconde que D-028a). Aucune autre vente à la baisse n'est fermée.

## Méthode
- Prix : relevés 30 s `state/price_ticks/*.jsonl` (Coinbase). Côté rachat = **ask** (sinon mid) ; le mid est donné à côté.
- Frais = ceux du guardian (`guardian/scripts/paper_fill.py`, `FEE_REVOLUT = 0,05 %` par côté) : gain net = (prix de vente − prix de rachat) × quantité − frais de vente − 0,05 % × montant du rachat. J'ai vérifié : la formule redonne exactement le résultat enregistré.
- Seuil « à zéro » (gain net = 0) = prix de vente × 0,9995/1,0005 (≈ −0,10 %).
- +0,5 % / +1 % favorable = ask ≤ prix de vente × 0,995 / 0,99 (mouvement brut du prix).
- Trous dans les relevés (> 90 s sans prix) détectés pour chaque trade. Comblés avec des **bougies 5 min Coinbase** (bas = rachat), plus Kraken 5 min pour 2 créneaux sans bougie Coinbase. Attention : le bas d'une bougie est un prix de transaction, pas un ask. Plus aucun moment sans prix → aucun chiffre « incomplet ».

## Tableau (heures de Bruxelles)
| Vente | Paire | € | Vente (prix · heure) | Rachat (prix · heure) ; ask/mid au tick | Résultat | Cible / Arrêt | Meilleur ask (mid) · heure · après | Gain max net | % du chemin vers la cible | +0,5 % | +1 % | En gain net après |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D-021 | SOL | 14,70 | 98,00 · 08/10 22h58 | 98,77 · 09/10 14h26 ; 98,74 / 98,73 | **−0,13 €** (−0,89 %) | 96,53 / 99,47 | 96,93 (96,925) · 09/10 03h20 · 4h21 | **+0,15 € (+0,99 %)** | 73 % | oui, après 3h03 | oui, après 3h27 | 0h04 |
| D-026 | SOL | 10,00 | 97,49 · 09/10 15h43 | 98,51 · 09/10 16h22 (arrêt) ; 98,52 / 98,51 | **−0,11 €** (−1,15 %) | 95,54 / 98,47 | 97,55 (97,54) · 16h01 · 0h18 | −0,02 € (−0,16 %) | −3 % (jamais sous la vente) | non | non | jamais |
| D-031b | SOL | 10,00 | 97,93 · 09/10 17h11 | 98,19 · 10/10 08h04 ; 98,15 / 98,14 | **−0,04 €** (−0,37 %) | 96,32 / 98,87 | 96,81 (96,80) · 09/10 21h59 · 4h48 | **+0,10 € (+1,04 %)** | 70 % | oui, après 4h18 | oui, après 4h36 | 0h02 |
| D-036a | SOL | 13,40 | 96,96 · 10/10 00h06 | 98,19 · 10/10 08h04 ; 98,15 / 98,14 | **−0,18 €** (−1,37 %) | 95,10 / 98,82 | 97,00 (96,99) · 00h14 · 0h07 | −0,02 € (−0,14 %) | −2 % (jamais sous la vente) | non | non | jamais |
| D-024b | ETH | 10,00 | 2 232,70 · 09/10 15h08 | 2 240,07 · 10/10 18h14 ; 2 240,31 / 2 240,07 | **−0,04 €** (−0,43 %) | 2 197 / 2 255 | 2 209,11 (2 208,945) · 09/10 22h06 · 6h57 | **+0,10 € (+0,96 %)** | 66 % | oui, après 0h26 | oui, après 6h38 | 0h05 |
| D-028a | ETH | 15,00 | 2 225,87 · 09/10 16h24 | 2 240,07 · 10/10 18h14 ; 2 240,31 / 2 240,07 | **−0,11 €** (−0,74 %) | 2 181 / 2 270 | 2 209,11 (2 208,945) · 09/10 22h06 · 5h41 | **+0,10 € (+0,65 %)** | 37 % | oui, après 4h10 | non | 0h02 |

Gain max au mid (pour comparer) : D-021 +0,147 € · D-026 −0,015 € · D-031b +0,105 € · D-036a −0,018 € · D-024b +0,097 € · D-028a +0,099 €.

## Trous dans les relevés et ce que montrent les bougies
| Vente | Trous dans les relevés pendant l'ouverture | Bas / haut dans les trous (5 min) | Change le meilleur prix ? |
|---|---|---|---|
| D-021 | 09/10 13h19–13h59 (40 min) | 97,86 / **99,86 à 13h45** | non. Mais le haut **dépasse l'arrêt 99,47** : l'arrêt aurait été touché pendant le trou, alors que le watcher ne voyait aucun prix |
| D-026 | aucun | — | — |
| D-031b, D-036a | 10/10 03h08–07h58 (4h50) | 97,62 / 98,52 | non (cible et arrêt non touchés) |
| D-024b, D-028a | 10/10 03h08–07h58, 08h25–09h05, 09h15–11h41, 11h58–15h08, 15h18–18h10 (13h56 au total) | 2 221,37 / 2 246,66 (16h40) | non (cible et arrêt non touchés) |
Créneaux comblés par Kraken (aucune bougie Coinbase) : SOL 10/10 07h20, ETH 10/10 05h10. Statut : **complet** pour les 6.

## Résumé
- **4 sur 6 ont été en gain net (après frais) à un moment** : D-021, D-031b, D-024b, D-028a. Chaque fois, le gain net est arrivé 2 à 5 min après la vente. Les 4 ont fait +0,5 % ; 3 ont fait +1 % (pas D-028a). Leur meilleur moment était à 66–73 % du chemin vers la cible (37 % pour D-028a). Aucune n'a touché sa cible.
- **2 sur 6 ne sont jamais passées au-dessus des frais** : D-026 et D-036a. Le prix n'est jamais descendu nettement sous la vente et il est vite reparti contre nous.
- **Meilleur gain moyen : +0,56 %** sur les 6 (+0,91 % sur les 4 qui ont été en gain). En €, le meilleur moment de chaque trade fait +0,41 € au total, contre un résultat réel de **−0,62 €**.
- **« Laisser filer les gains » : oui, pour 4 sur 6.** Elles ont été en gain de plus que les frais (+0,65 % à +1,04 % net), puis fermées en perte (−0,04 € à −0,13 €), parce que le prix est reparti contre nous avant la cible et que la fermeture est venue plus tard (idée morte ou heure de rappel). Les 2 autres étaient perdantes dès le début.
- Les chiffres de meilleur gain viennent tous des relevés 30 s. Les bougies 5 min des trous ne donnent jamais mieux.

Fichiers : `meilleur_gain_ventes.csv` (séparateur « ; »), `analyse.py`, `candles_cache_5m/`, `kraken_*_5m.json`.
