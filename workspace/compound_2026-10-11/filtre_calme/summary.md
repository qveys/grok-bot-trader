# Filtre « plage 24 h > X % » — test sur le passé
_PM-Compound, 11 oct. 2026, 08h30 (heure de Bruxelles). Lecture seule sur les marchés : aucun ordre, pas d'`ai.sh ask`, aucun secret. Pas de proposition de règle._

## Réglages
- **Données** : bougies 1 h Binance EUR depuis le cache, du 7 oct. 2025 au 7 oct. 2026. Coupure des moitiés le 7 avr. 2026 23h30 UTC.
- **Entrées** : 15–17h en jours ouvrés, sans sortie 22h, sécurité 48 h.
- **Visé** : 1,5 / 2 / 2,5 / 3 %. **Arrêt** = visé ÷ 1 (prudente), ÷ 1,5 (équilibrée) ou ÷ 2 (risquée).
- **Achats** : `team_rebound` et `team_breakout`, avec frais `revolutx` (immédiat) et `revolutx-maker --fill touch`.
- **Ventes** : `sell_rebuy` avec et sans filtre 200 h, avec les frais par défaut de l'outil et en « tout au marché » (`--maker-fee 0.0014`).
- **Paires** : BTC, ETH, SOL.
- **Volume** : 288 réglages × 8 valeurs de X = 2 304 tests. Les 288 à X = 0 sont repris de la grille du matin, avec les mêmes paramètres ; la sortie est vérifiée identique.
- **Filtre ajouté à l'outil** : `--min-range24 X` dans `vt_tools.py` (achats, aussi pour `--fill touch`) et dans `vt_sellrebuy.py` (ventes). Le défaut 0 ne change rien.
  - Sauvegardes : `checks/*_before_range24.py.bak`. Section ajoutée dans README_FR.md.
  - Les 4 suites de tests existantes passent (55 vérifs, `../tests_range24.log`).
  - Vérif indépendante (`scripts/check_filtre.py`) : chaque achat filtré a bien une plage > X %, et aucun achat nouveau n'apparaît.
- `vt_verdict.py --all` relancé après coup (3 828 tests relus, sans erreur ; `vt_verdict_all.log`).
- **Unités** : net = % après frais du test (achats : % du capital de l'outil ; ventes : % de pièces par rapport à « garder »). Une « somme » additionne les % des réglages : c'est un indicateur, pas un montant. 1 réglage = 1 an, donc trades par réglage = trades par an.

**Important** : `team_rebound` exige déjà une baisse ≥ 3 % en 24 h et `sell_rebuy` une hausse ≥ 3 % en 24 h. Leur plage dépasse donc toujours 3 %, et **le filtre ne change rien pour eux tant que X ≤ 3**. Pour la cassure (`team_breakout`), il ne change rien jusqu'à X = 1,5.

## Par valeur de X (288 réglages chacun)
| X | Net somme | Net médiane | Médiane achats / ventes | Réglages > 0 | Trades/an (moy. par réglage) | Passent le test d'équipe | Moitié 1 (somme) | Moitié 2 (somme) |
|---|---|---|---|---|---|---|---|---|
| 0 (sans filtre) | −817,7 | −2,15 | −2,92 / −1,46 | 98 | 26,6 | 21 | −343,5 | −468,5 |
| 1 | −817,7 | −2,15 | identique | 98 | 26,6 | 21 | identique | identique |
| 1,5 | −817,7 | −2,15 | identique | 98 | 26,6 | 21 | identique | identique |
| 2 | −806,0 | −2,15 | −2,65 / −1,46 | 100 | 26,4 | 21 | −323,5 | −478,3 |
| 2,5 | −990,5 | −2,46 | −3,65 / −1,46 | 93 | 25,8 | 21 | −277,5 | −720,8 |
| 3 | −1 046,8 | −2,60 | −4,03 / −1,46 | 91 | 24,7 | 21 | −230,3 | −825,5 |
| 4 | −958,7 | −2,44 | −1,95 / −2,66 | 81 | 21,6 | 5 | −415,3 | −558,4 |
| **5** | **−712,1** | **−1,04** | +1,35 / −4,12 | 114 | 17,3 | 4 | −132,9 | −591,5 |

- **Ce qui garde le plus au total : X = 5 %** (−712 contre −818 sans filtre, soit +106 points de somme), avec 35 % de trades en moins (17,3 contre 26,6 par an).
  - Le gain vient de la **moitié 1 seulement** (−133 contre −344). La **moitié 2 est pire** (−592 contre −469).
- X = 2 fait à peine mieux que sans filtre (+12) : seule la cassure change.
- X = 2,5 à 4 font moins bien que sans filtre.
- Réglages qui passent le test d'équipe : 21 de X = 0 à 3 (les mêmes qu'à X = 0), puis 5 à X = 4 et 4 à X = 5. **Le filtre fait baisser le nombre de réglages qui passent**, surtout parce que beaucoup tombent sous 20 trades par an.

## Meilleur X par paire et par sens
| Paire / sens | Meilleur X | Net somme (X = 0 →) | Moitiés au meilleur X (X = 0) | Trades/an par réglage (X = 0) | Passent (X = 0) |
|---|---|---|---|---|---|
| BTC hausse | 5 | +37,5 (−271,2) | +40,0 / −2,8 (−234,4 / −37,2) : mieux dans les deux | **6,8** (23,8) | 0 (0) |
| ETH hausse | 5 | +129,9 (−86,2) | +136,7 / −6,8 (−87,6 / +6,3) : moitié 2 pire | 15,2 (26,2) | 0 (0) |
| SOL hausse | 2,5 | +45,9 (+40,1) | −44,5 / +89,9 (−44,5 / +83,8) : quasi identique | 29,6 (30,0) | 17 (17) |
| BTC baisse | 0 (sans filtre) | −161,4 | — | 15,8 | 0 |
| ETH baisse | 0 (sans filtre) | −104,2 | — | 29,2 | 4 |
| SOL baisse | 0 (sans filtre) | −234,7 | — | 34,3 | 0 |

- **Ventes (idée à la baisse)** : le filtre ne fait que perdre (X = 4 et 5 pires sur les trois paires).
- **Achats** : X = 5 améliore BTC et ETH surtout par la cassure (`team_breakout` : somme +168,7 à X = 5 contre −263,3 sans filtre). Mais il reste alors 7 à 15 trades par an et par réglage.

Réglages qui passent à X = 4 et X = 5 (pour mémoire) :
- **X = 4** : ETH vente sans filtre 200 h, frais par défaut, 3/1,5 et 3/1 (44–47 trades) — tous les deux **moins bons** qu'à X = 0 (+7,4 contre +10,7 ; +2,0 contre +5,2). SOL rebond maker-touch 1,5/1, 2/1 et 2,5/1,5 (21 trades) — presque pareil qu'à X = 0.
- **X = 5** : SOL cassure 1,5/1 maker (23 trades, +6,2 contre +1,4 à X = 0), 2/1,5 maker (+7,7 contre +5,1), 2/2 immédiat (+1,5 contre −0,9), 3/2 maker (+8,4 contre +9,8). Les 4 ont une moitié 2 faible (+0,3 à +1,4).

## Chance ou vraie amélioration ?
- **Les deux moitiés** : dans les réglages où le filtre change quelque chose, il améliore les deux moitiés dans :
  - 0 cas sur 48, 66 et 72 à X = 2, 2,5 et 3 ;
  - 19 cas sur 264 à X = 4 (et en dégrade 16) ;
  - 78 cas sur 264 à X = 5 (et en dégrade 43).
  Au total, à X = 5, la moitié 2 est pire. **L'amélioration ne tient pas dans les deux moitiés.**
- **Tirages au hasard** (`scripts/hasard.py`, `hasard_tirages.csv`) : pour chaque test d'achat en frais immédiats où le filtre retire des trades, on tire 5 000 fois au hasard le même nombre de trades parmi ceux du test sans filtre.
  - À X = 5 : 3 tests sur 72 font mieux que 95 % des tirages, alors qu'on en attend 3,6 par pure chance. La valeur p médiane est de 0,36.
  - À X = 2 à 4 : 0 test sous 5 %, p médiane de 0,64 à 0,89.
  - **Le filtre ne choisit pas mieux que le hasard.**
- **Beaucoup de tests, peu de trades** : 2 304 tests, et les meilleurs cas à X = 5 tiennent sur 7 à 23 trades par an. Ce qui ressort ressemble à de la chance.

## Contexte : plage 24 h actuelle (24 bougies 1 h Coinbase, du 10 oct. 07h00 au 11 oct. 07h00, divisée par le prix de 07h57)
| Paire | Haut | Bas | Prix | Plage 24 h |
|---|---|---|---|---|
| BTC | 74 234 | 73 762 | 74 106 | **0,64 %** |
| ETH | 2 248,75 | 2 224,64 | 2 234,56 | **1,08 %** |
| SOL | 98,86 | 97,27 | 97,56 | **1,63 %** |
Aujourd'hui, les trois paires seraient sous X = 2 %. Aucun signal de rebond ou de vente (qui demandent ≥ 3 %) n'est possible à cette plage.

## Fichiers
- `summary.md`
- `filtre_grille.csv` (2 304 lignes, avec les écarts par rapport à X = 0)
- `par_X.csv`, `par_paire_sens_X.csv`, `par_regle_X.csv`, `meilleur_X_par_paire_sens.csv`
- `hasard_tirages.csv`, `range24_now.json`
- `scripts/` (make_cmds.sh, run_batch.sh, analyse.py, hasard.py, check_filtre.py, range24_now.py)
- `tool_json/` (sortie de chaque test)
- `vt_verdict_all.log`
