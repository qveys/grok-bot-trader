# Journal des trades (après vente seulement)

**Une entrée seulement s’il y a eu achat puis vente.**  
Les idées refusées et les « pas encore acheté » → `decision_log.md`.

## Modèle

### YYYY-MM-DD | PAIRE | essai ou live | lien décision (ex. D-001)
- Achat : prix / montant €
- Vente : prix / montant €
- Coût réel aller-retour : € (et %)
- Résultat : gain ou perte = € (et %)
- Pourquoi vente :
- Leçon (1 ligne) :
- Motif / type de trade :

---

## Entrées

### 2026-10-07 | ETH-EUR | essai | test stop (pas d’id D-xxx à l’achat — fill test du 6 oct)
- Achat : 2500 € / 10 € (0,004 ETH)
- Vente : ~2293 € / ~9,17 € (stop 2300 € touché ~15h17)
- Coût réel aller-retour : inclus dans le PnL simulé (frais non isolés)
- Résultat : perte ≈ **−0,83 €** (−8,3 %)
- Pourquoi vente : stop de protection touché (chute avant Fed)
- Leçon (1 ligne) : un achat test à 2500 € sans décision écrite claire + marché qui baisse fort = perte attendue ; ne pas racheter juste après le stop
- Motif / type de trade : essai stop ETH (achat long + stop −8 %)


### 2026-10-08 | ETH-EUR | essai | D-019
- Vente : 2 261,905 € / 0,0055 ETH (≈ 12,44 €) — idée à la baisse, étiquette **rétro** (exception réglage, accord Quentin)
- Achat : 2 250,60 € à 15h39 (rachat des 0,0055 ETH)
- Coût réel aller-retour : ordres qui attendent dans le carnet, frais quasi nuls
- Résultat : gain ≈ **+0,05 €** (≈ +0,4 %), compté en euros, pièces inchangées
- Pourquoi vente : idée à la baisse ; la cible de rachat (2 250,60 €) a été touchée avant le prix d'arrêt (ETH monté à 2 271,3 €, à 2 € de l'arrêt)
- Leçon (1 ligne) : gain réel mais de justesse (arrêt presque touché) et calculé après coup, donc il ne prouve pas encore que l'idée marche
- Motif / type de trade : idée à la baisse (rétro), simulation

### 2026-10-08 | SOL-EUR | essai | D-020
- Vente : 100,695 € / 0,124 SOL (≈ 12,49 €) — idée à la baisse, étiquette **rétro** (exception réglage, accord Quentin)
- Achat : 100,20 € à 15h02 (rachat des 0,124 SOL)
- Coût réel aller-retour : ordres qui attendent dans le carnet, frais quasi nuls
- Résultat : gain ≈ **+0,05 €** (≈ +0,4 %), compté en euros, pièces inchangées
- Pourquoi vente : idée à la baisse ; la cible de rachat (100,20 €) a été touchée avant le prix d'arrêt (101,20 €)
- Leçon (1 ligne) : D-019 et D-020 ouvertes en même temps partagent le plafond de 25 € ; un essai rétro compte à part dans le bilan pour ne pas gonfler les vrais résultats
- Motif / type de trade : idée à la baisse (rétro), simulation

### 2026-10-09 | SOL-EUR | essai | D-021
- Vente : 98,00 € / 0,15 SOL (≈ 14,70 €) — idée à la baisse, simulation (nuit du 8 oct.)
- Achat (rachat) : 98,77 € / 0,15 SOL à 14h26 — fermeture à la main (Risk)
- Coût réel aller-retour : frais ≈ 0,015 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,13 €** (−0,89 %)
- Pourquoi vente : idée à la baisse ouverte la veille ; cible 96,53 € jamais touchée (creux ~96,93 €), prix contre nous près de l’arrêt 99,47 € (haut ~99,31 €) ; Predict a déclaré l’idée morte à 14h02 ; Risk a fermé pour libérer le plafond simu (heure limite 10h = rappel seulement)
- Leçon (1 ligne) : une idée de nuit sans cible touchée avant l’heure rappel, avec le prix déjà contre nous, vaut mieux être coupée tôt plutôt que de garder le plafond bloqué
- Motif / type de trade : idée à la baisse, simulation

### 2026-10-09 | SOL-EUR | essai | D-024a
- Achat : 98,69 € / 15,00 € (0,15199 SOL) à ~15h08 — idée à la hausse, simulation
- Vente : 97,49 € / ≈ 14,82 € (0,15199 SOL) à 15h43
- Coût réel aller-retour : frais ≈ 0,015 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,20 €** (−1,32 %)
- Pourquoi vente : idée morte (Risk) — ni le prix visé 100,09 € ni l’arrêt 97,30 € n’ont été touchés (creux ticks ~97,49 €) ; SOL a cassé sous 97,90 € et Predict a basculé en idée à la baisse (D-025/D-026), plafond simu plein → fermeture pour libérer de la place
- Leçon (1 ligne) : à surveiller — couper une idée à la hausse « morte » avant l’arrêt fixe une petite perte et libère le plafond, mais ce n’est qu’un essai (pas une règle)
- Motif / type de trade : idée à la hausse, simulation

### 2026-10-09 | SOL-EUR | essai | D-026
- Vente : 97,49 € / 10,00 € (0,10257 SOL) à 15h43 — idée à la baisse, simulation (risquée)
- Achat (rachat) : 98,51 € / ≈ 10,10 € à 16h22 — arrêt touché
- Coût réel aller-retour : frais ≈ 0,01 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,11 €** (−1,15 %)
- Pourquoi vente : arrêt 98,47 € touché (ticks mid 98,51 € à 16h21:59) ; cible de rachat 95,54 € jamais atteinte (creux pendant l’ouverture ~97,54 €) ; fermeture auto stop_hit / safety
- Leçon (1 ligne) : à surveiller — sur cet essai SOL a monté vers l’arrêt avant d’atteindre la cible ; 2e perte baisse SOL du jour (après D-021), pas encore assez d’essais pour une règle
- Motif / type de trade : idée à la baisse, simulation

### 2026-10-09 | BTC-EUR | essai | D-023
- Achat : 74 120 € / 24,98 € (0,000337 BTC) à 14h30 — idée à la hausse, simulation
- Vente : 73 927,97 € / ≈ 24,91 € à 17h09
- Coût réel aller-retour : frais ≈ 0,012 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,08 €** (−0,32 %)
- Pourquoi vente : idée morte (Predict après rappel 17h00) — prix un peu contre nous (≈ 74 082 € puis sortie 73 928 €) ; ni le prix visé 75 232 € ni l’arrêt 73 379 € n’ont été touchés (haut ticks ~74 349 €, creux ~73 663 €) ; Risk a fermé pour libérer ~25 € sous le plafond simu
- Leçon (1 ligne) : à surveiller — après l’heure rappel, une idée à la hausse encore loin de la cible et déjà un peu contre peut être coupée tôt pour libérer le plafond (2e essai hausse simu du jour après D-024a, pas une règle)
- Motif / type de trade : idée à la hausse, simulation

### 2026-10-10 | BTC-EUR | essai | D-031a
- Achat : 73 981,11 € / 15,00 € (0,000203 BTC) à 17h11 — idée à la hausse, simulation
- Vente : 73 586,39 € / ≈ 14,92 € à 00h06 — fermeture idée morte (Risk après rappel 22h)
- Coût réel aller-retour : frais ≈ 0,015 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,09 €** (−0,63 %)
- Pourquoi vente : idée morte — rappel 22h00 passé, prix contre nous (~73 475 € à 22h, sortie 73 586 €) ; ni le prix visé 74 843 € ni l’arrêt 73 120 € n’ont été touchés (haut ticks ~74 148 €, creux ~73 444 €) ; Predict a déclaré l’idée morte à ~00h04, Risk a fermé pour libérer ~15 €
- Leçon (1 ligne) : à surveiller — 3e perte « idée à la hausse » simu d’affilée (après D-024a et D-023) : après le rappel, loin de la cible et déjà contre, couper libère le plafond ; rien ne change (~3 essais hausse fermés)
- Motif / type de trade : idée à la hausse, simulation

### 2026-10-10 | SOL-EUR | essai | D-036a
- Vente : 96,96 € / 13,40 € (0,1382 SOL) à ~00h06 — idée à la baisse, simulation (prudente)
- Achat (rachat) : 98,19 € / ≈ 13,57 € à 08h05 — fermeture idée morte (Risk)
- Coût réel aller-retour : frais ≈ 0,014 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,18 €** (−1,37 %)
- Pourquoi vente : idée morte — après la cassure SOL au-dessus de 98,03 € (D-040), prix contre nous (~98,19 € vs entrée 96,96 €, +1,27 %) ; ni le prix visé 95,10 € ni l’arrêt 98,82 € n’ont été touchés (creux ticks ~96,89 €, haut ~98,37 €) ; Predict a déclaré l’idée morte ~08h05, Risk a fermé pour libérer ~13 € (rappel 10h00 = rappel seulement)
- Leçon (1 ligne) : à surveiller — 4e perte « idée à la baisse » simu d’affilée (D-021, D-026, D-031b, D-036a) : vente juste après une baisse déjà faite, puis rebond contre nous ; rien ne change (loin de ~20 essais)
- Motif / type de trade : idée à la baisse, simulation

### 2026-10-10 | SOL-EUR | essai | D-031b
- Vente : 97,93 € / 10,00 € (≈ 0,1021 SOL) à 17h11 — idée à la baisse, simulation (équilibrée)
- Achat (rachat) : 98,19 € / ≈ 10,03 € à 08h05 — fermeture idée morte (Risk)
- Coût réel aller-retour : frais ≈ 0,01 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,04 €** (−0,37 %)
- Mode : simulation (essai)
- Prix visé : 96,32 € · prix d'arrêt : 98,87 € · ni l'un ni l'autre touchés (creux ticks ~96,80 €, haut ~98,37 €)
- Pourquoi vente : idée morte — rappel 22h00 passé ; SOL a cassé au-dessus de 98,03 € (~08h) avec le prix contre nous (sortie 98,19 € > entrée 97,93 €, vers l'arrêt 98,87 €) ; Predict a déclaré l'idée morte (D-040), Risk a fermé pour libérer ~10 €
- Leçon (1 ligne) : à surveiller — 3e perte « idée à la baisse » simu d'affilée (D-021, D-026, D-031b ; D-036a fermée au même instant → 4) : après le rappel, loin de la cible et déjà contre, couper avant l'arrêt limite la casse ; rien ne change (loin de ~20 essais)
- Motif / type de trade : idée à la baisse, simulation

### 2026-10-10 | ETH-EUR | essai | D-024b
- Vente : 2 232,70 € / 10,00 € (0,004479 ETH) à 15h08 (9 oct.) — idée à la baisse, simulation (équilibrée)
- Achat (rachat) : 2 240,07 € / ≈ 10,03 € à 18h14 (10 oct.) — fermeture idée morte (Risk)
- Coût réel aller-retour : frais ≈ 0,01 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,04 €** (−0,43 %)
- Mode : simulation (essai)
- Prix visé : 2 197 € · prix d'arrêt : 2 255 € · ni l'un ni l'autre touchés (creux ticks ~2 208,95 €, haut ~2 240,58 €)
- Pourquoi vente : idée morte — rappels passés ; ETH a remonté au-dessus de l'entrée (sortie 2 240,07 € > 2 232,70 €, +0,33 %) sans toucher le visé ni l'arrêt ; Predict (D-042) a déclaré l'idée morte ~18h12, Risk a fermé pour libérer ~10 € (D-028a fermée au même instant)
- Leçon (1 ligne) : à surveiller — 5e perte « idée à la baisse » simu d'affilée (D-021, D-026, D-031b, D-036a, D-024b) : après les rappels, loin de la cible et déjà contre, couper avant l'arrêt limite la casse ; rien ne change (loin de ~20 essais)
- Motif / type de trade : idée à la baisse, simulation

### 2026-10-10 | ETH-EUR | essai | D-028a
- Vente : 2 225,87 € / 15,00 € (0,006739 ETH) à 16h24 (9 oct.) — idée à la baisse, simulation (prudente)
- Achat (rachat) : 2 240,07 € / ≈ 15,10 € à 18h14 (10 oct.) — fermeture idée morte (Risk)
- Coût réel aller-retour : frais ≈ 0,015 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,11 €** (−0,74 %)
- Prix visé : 2 181 € · prix d'arrêt : 2 270 € · ni l'un ni l'autre touchés (creux ticks ~2 208,95 €, haut ~2 240,58 €)
- Pourquoi vente : idée morte — rappel 14h00 (prolongé après 22h00 du 9) passé ; ETH remonté contre nous (sortie 2 240,07 € > entrée 2 225,87 €, +0,64 %) ; Predict a déclaré l'idée morte (D-042), Risk a fermé avec D-024b pour libérer ~15 €
- Leçon (1 ligne) : à surveiller — rappel dépassé, prix remonté, cible et arrêt non touchés ; 5e/6e perte « idée à la baisse » simu d'affilée (D-021, D-026, D-031b, D-036a, D-028a ; D-024b au même instant) ; rien ne change (loin de ~20 essais)
- Motif / type de trade : idée à la baisse, simulation

### 2026-10-11 | SOL-EUR | essai | D-042a
- Achat : 98,475 € / 25,00 € (0,25387 SOL) à 18h14 (10 oct.) — idée à la hausse, simulation (prudente)
- Vente : 97,75 € / ≈ 24,82 € à 07h37 (11 oct.) — fermeture idée morte (Risk)
- Coût réel aller-retour : frais ≈ 0,025 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,21 €** (−0,84 %)
- Mode : simulation (essai)
- Prix visé : 100,44 € · prix d'arrêt : 96,99 € · ni l'un ni l'autre touchés (haut ticks ~98,585 €, creux ~97,75 €)
- Pourquoi vente : idée morte — rappel 22h00 passé ; SOL sous l'entrée (97,75 € vs 98,475 €, −0,74 %) après cassure zone 98,17 € ; cible et arrêt non touchés ; Predict (D-043) a déclaré l'idée morte ~07h35, Risk a fermé pour libérer ~25 €
- Leçon (1 ligne) : à surveiller — 4e perte « idée à la hausse » simu d'affilée (D-024a, D-023, D-031a, D-042a) : après le rappel, loin de la cible et déjà contre, couper avant l'arrêt limite la casse ; rien ne change (loin de ~20 essais)
- Motif / type de trade : idée à la hausse, simulation

### 2026-10-12 | ETH-EUR | essai | D-043a
- Achat : 2 237,49 € / 25,00 € (0,011173 ETH) à 07h37 (11 oct.) — idée à la hausse, simulation (prudente)
- Vente : 2 283,30 € / ≈ 25,51 € à 07h30 (12 oct.) — cible touchée
- Coût réel aller-retour : frais ≈ 0,025 € (inclus dans le PnL)
- Résultat : gain ≈ **+0,49 €** (+1,95 %)
- Mode : simulation (essai)
- Prix visé : 2 283,30 € · prix d'arrêt : 2 193,75 € · cible touchée (trou nuit comblé Coinbase 60 s : haut ~2 293,41 €, bougie 04h18 haut 2 284,64 €) ; ticks locaux 11 oct. max ~2 271,57 € (sous la cible)
- Pourquoi vente : cible 2 283,30 € touchée (fermeture auto target_hit / rattrapage trou) ; arrêt 2 193,75 € jamais touché (creux ticks ~2 230,50 €)
- Leçon (1 ligne) : 1er gain « idée à la hausse » simu depuis plusieurs essais — la cible +2 % a été touchée pendant la nuit (trou comblé) ; rien ne change (encore peu d’essais hausse)
- Motif / type de trade : idée à la hausse, simulation

### 2026-10-12 | SOL-EUR | essai | D-047c
- Vente : 100,44 € / 10,00 € (0,09956 SOL) à 07h35 — idée à la baisse, simulation (risquée)
- Rachat : 98,39 € / ≈ 9,80 € à 14h42 — cible touchée
- Coût réel aller-retour : frais ≈ 0,01 € (inclus dans le PnL)
- Résultat : gain ≈ **+0,19 €** (+1,94 %)
- Mode : simulation (essai)
- Prix visé : 98,39 € · prix d'arrêt : 101,40 € · cible touchée (trou 11h39–14h42 comblé Coinbase 60 s : bas ~98,35 €, bougie 14h41 bas 98,35 €) ; ticks locaux 12 oct. min ~98,57 € (au-dessus de la cible) ; arrêt jamais touché (haut ticks ~100,85 €)
- Pourquoi vente : cible 98,39 € touchée (fermeture auto target_hit / rattrapage trou) ; arrêt 101,40 € jamais touché
- Leçon (1 ligne) : 1er gain « idée à la baisse » simu après 6 pertes d’affilée (hors rétro) — la cible −2 % a été touchée via rattrapage ; rien ne change (loin de ~20 essais)
- Motif / type de trade : idée à la baisse, simulation

### 2026-10-12 | ETH-EUR | essai | D-047a
- Achat : 2 278,90 € / 15,00 € (0,006582 ETH) à 07h35 — idée à la hausse, simulation (prudente)
- Vente : 2 265,64 € / ≈ 14,91 € à 14h47 — fermeture idée morte (Risk)
- Coût réel aller-retour : frais ≈ 0,015 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,10 €** (−0,68 %)
- Mode : simulation (essai)
- Prix visé : 2 325,60 € · prix d'arrêt : 2 234,40 € · ni l'un ni l'autre touchés (haut ticks ~2 299,85 € à 09h14, soit +0,92 %, moins de la moitié du chemin ; creux ~2 261,97 € à 14h42 ; trou de relevés 11h39–14h42, haut/bas du jour des bougies identiques)
- Pourquoi vente : idée morte — rappel 14h00 passé avec ETH sous l'entrée (2 265 € vs 2 278,90 €) ; Predict (D-049) l'a déclarée morte, Risk a fermé pour libérer la place
- Leçon (1 ligne) : ETH est monté vers 2 300 € le matin puis est retombé au plus bas du jour ; couper au rappel a limité la perte à 0,10 € ; rien ne change (7 essais hausse simu, loin de ~20)
- Motif / type de trade : idée à la hausse, simulation

### 2026-10-12 | ETH-EUR | essai | D-049a
- Achat : 2 265,00 € / 25,00 € (0,011038 ETH) à 14h47 — idée à la hausse, simulation (prudente)
- Vente : 2 249,30 € / ≈ 24,83 € à 20h48 — fermeture idée morte (Risk)
- Coût réel aller-retour : frais ≈ 0,025 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,20 €** (−0,79 %)
- Mode : simulation (essai)
- Prix visé : 2 310,30 € · prix d'arrêt : 2 219,70 € · ni l'un ni l'autre touchés (haut ticks ~2 272,49 € ; creux ~2 248,83 € ; trou 19h17–20h43 : bas 2 241,80 € > arrêt)
- Pourquoi vente : idée morte — rappel 20h00 passé avec ETH sous l'entrée (2 251,5 € vs 2 265 €, −0,6 %) ; Predict (D-051) l'a déclarée morte, Risk a fermé
- Leçon (1 ligne) : même pari ETH hausse que D-047a fermé juste avant (fermé puis racheté) — deux pertes de frais pour un seul sens ; rien ne change (8 essais hausse simu, loin de ~20)
- Motif / type de trade : idée à la hausse, simulation

### 2026-10-12 | ETH-EUR | essai | D-049a
- Achat : 2 265,00 € / 25,00 € (0,011038 ETH) à 14h47 — idée à la hausse, simulation (prudente), ouverte juste après la fermeture de D-047a
- Vente : 2 249,30 € / ≈ 24,83 € à 20h48 — fermeture idée morte (Risk)
- Coût réel aller-retour : frais ≈ 0,025 € (inclus dans le PnL)
- Résultat : perte ≈ **−0,20 €** (−0,79 %, frais compris)
- Mode : simulation (essai)
- Prix visé : 2 310,30 € · prix d'arrêt : 2 219,70 € · ni l'un ni l'autre touchés (meilleur prix ~2 275,00 € vers 15h45–16h, soit +0,44 %, moins d'un quart du chemin ; creux ~2 241,80 € dans le trou 19h17–20h43 comblé Coinbase 60 s)
- Pourquoi vente : idée morte — rappel 20h00 passé avec ETH sous l'entrée (2 251,5 € vs 2 265 €) ; Predict (D-051) l'a déclarée morte, Risk a fermé à 20h48 (48 min après le rappel, à cause du trou de relevés 19h17–20h43)
- Leçon (1 ligne) : 1er cas « fermé puis racheté » (D-047a −0,10 € puis D-049a −0,20 €, même pari ETH à la hausse, frais payés deux fois) : le même pari a coûté −0,30 € au total ; observation seulement, rien ne change (8 essais hausse simu, 1er cas sur ~20)
- Motif / type de trade : idée à la hausse, simulation, « fermé puis racheté »

### 2026-10-13 | ETH-EUR | essai | D-051c
- Vente : 2 251,50 € / 5,00 € (0,002221 ETH) le 12 oct. à 20h48 — idée à la baisse, simulation (risquée)
- Rachat : 2 206,40 € / ≈ 4,90 € — cible touchée dans la bougie de 01h00 le 13 oct., fermeture enregistrée à 07h24 (rattrapage du trou de relevés)
- Coût réel aller-retour : frais ≈ 0,005 € (inclus dans le PnL)
- Résultat : gain ≈ **+0,10 €** (+1,90 %)
- Mode : simulation (essai)
- Prix visé : 2 206,40 € · prix d'arrêt : 2 274,00 € · cible touchée (trou 20h58–07h23 comblé Coinbase 60 s : bas 2 157,33 €, haut 2 267,33 € < arrêt) ; bougie 01h00 bas 2 206,11 € ; arrêt et cible pas dans la même bougie ; ETH est remonté à ~2 266 € à 07h24, tout près de l'arrêt
- Pourquoi vente : cible 2 206,40 € touchée la nuit (fermeture auto target_hit via rattrapage) ; arrêt 2 274,00 € jamais touché
- Leçon (1 ligne) : la baisse prévue par Predict est arrivée dans la nuit et la cible −2 % a été prise avant la remontée ; rien ne change (11 essais baisse simu avec D-051a fermé en même temps, loin de ~20) ; à noter : 10 h 25 sans relevé de prix (20h58–07h23)
- Motif / type de trade : idée à la baisse, simulation

### 2026-10-13 | SOL-EUR | essai | D-051a
- Vente : 96,53 € / 20,00 € (0,20719 SOL) à 20h48 (12 oct.) — idée à la baisse, simulation (prudente)
- Rachat : 95,08 € / ≈ 19,70 € à 07h24 (13 oct.) — cible touchée
- Coût réel aller-retour : frais ≈ 0,02 € (inclus dans le PnL)
- Résultat : gain ≈ **+0,28 €** (+1,40 %)
- Mode : simulation (essai)
- Prix visé : 95,08 € · prix d'arrêt : 97,97 € · cible touchée (trou 20h58–07h24 comblé Coinbase 60 s : haut ~97,45 € < arrêt, bas ~91,09 € ; bougie 23h45 haut 96,29 / bas 95,08 ; stop et objectif pas dans la même bougie)
- Pourquoi vente : cible 95,08 € touchée (fermeture auto target_hit / rattrapage trou) ; arrêt 97,97 € jamais touché
- Ouverture : attente 30 min SOL **non respectée** (ouverte 20h48 alors que SOL déjà −1 % sous haut 2 h) — **ne pas compter** dans les 10 essais de la règle d’attente SOL ; noter à part « attente non respectée »
- Leçon (1 ligne) : 2e gain « idée à la baisse » simu à la cible après D-047c (suite aux 6 pertes) — la cible −1,5 % a tenu malgré l’entrée trop tôt ; rien ne change (~10 essais baisse hors rétro, loin de ~20)
- Motif / type de trade : idée à la baisse, simulation, attente non respectée (hors compteur règle 30 min)
