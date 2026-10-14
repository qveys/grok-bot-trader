# Carnet des décisions (avant achat)

Une entrée **avant** chaque achat possible — y compris les **non**.
Ça n’est **pas** le journal des trades (qui ne contient que achat→vente).

## Modèle

### YYYY-MM-DD HH:MM | PAIRE | id-décision (ex. D-001)
- Type d’idée : **idée à la hausse** / **idée à la baisse** (plus de « vendre d’abord »)
- Relevé / contexte (1 ligne) :
- Gain espéré (€ et %) :
- Perte max (€ et %) :
- Coût aller-retour estimé (€ et %) :
- Gain ≥ 3× coût ? oui / non *(obligatoire en **live** ; en simulation un petit avantage + stop suffit)*
- Décision : **ACHETER** / **PAS ACHETER** / **VENDRE** (baisse) / **PAS VENDRE**
- Pourquoi (1–2 lignes) :
- Si ouverture → taille € / % capital / stop / (baisse : target + safety) :
- Lien trade plus tard : (vide jusqu’à clôture)

---

## Entrées

### 2026-10-07 11:27 | ETH-EUR | D-002
- Relevé / contexte (1 ligne) : prix ~2337 € (−3,3 % / 24 h), ventes des gros fonds, Fed ce soir ; scan 11h08 raté → on garde 10h34
- Gain espéré (€ et %) : 0 € (0 %) — pas d’avantage clair vs prix
- Perte max (€ et %) : n/a (pas d’achat)
- Coût aller-retour estimé (€ et %) : ~0,2–0,5 % typique (frais + écart)
- Gain ≥ 3× coût ? non
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : pas assez d’écart avec le prix actuel ; attendre les annonces ; simulé test déjà ouvert à 2500 €
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —

### 2026-10-07 11:27 | SOL-EUR | D-003
- Relevé / contexte (1 ligne) : prix ~105,88 € (−1,4 % / 24 h), petite baisse sans info nouvelle
- Gain espéré (€ et %) : 0 € (0 %)
- Perte max (€ et %) : n/a
- Coût aller-retour estimé (€ et %) : ~0,2–0,5 %
- Gain ≥ 3× coût ? non
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : pas d’avantage clair vs prix ; même logique court terme ~48 h
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —

### 2026-10-07 15:17 | BTC-EUR | D-004
- Relevé / contexte (1 ligne) : ~74 592 € (−2,4 % / 24 h), ambiance peur avant Fed ~20h
- Gain espéré (€ et %) : faible / flou — marché d’attente, pas d’avantage clair
- Perte max (€ et %) : si essai ~5 % du capital (~8–14 € selon taille) → stop type −8 %
- Coût aller-retour estimé (€ et %) : ~0,2–0,5 %
- Gain ≥ 3× coût ? non (gain espéré pas assez clair)
- Décision : **PAS ACHETER** (même en simulation)
- Pourquoi (1–2 lignes) : baisse déjà faite + on attend la Fed ; forcer un achat = doute trop grand sans mouvement clair à la hausse
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —

### 2026-10-07 15:17 | ETH-EUR | D-005
- Relevé / contexte (1 ligne) : ~2 293 € (−4,8 %), **sous stop 2300 €** — simulé test déjà fermé en perte
- Gain espéré (€ et %) : 0 (pas d’achat)
- Perte max (€ et %) : n/a
- Coût aller-retour estimé (€ et %) : ~0,2–0,5 %
- Gain ≥ 3× coût ? non
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : ne pas racheter après une baisse forte juste avant la Fed ; leçon du stop à venir via Compound
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —

### 2026-10-07 15:17 | SOL-EUR | D-006
- Relevé / contexte (1 ligne) : ~104 € (−2,6 %), suit le marché
- Gain espéré (€ et %) : 0 / flou
- Perte max (€ et %) : n/a
- Coût aller-retour estimé (€ et %) : ~0,2–0,5 %
- Gain ≥ 3× coût ? non
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : rien de spécial pour SOL ; priorité BTC de toute façon et BTC = non
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —

### 2026-10-07 15:48 | BTC-EUR | D-007
- Relevé / contexte (1 ligne) : mid 74136.54 € (-3.42 %/24h) ; catalyseur = minutes FOMC ~20h (pas décision de taux) ; fenêtre 15h–17h = simu seulement
- **Prévision mesurable** : **UP** / horizon **22h00 CEST** / seuil **±1.5 %** → cible 75248.59 € · inverse 73024.49 €
- Probas modèle : P(seuil sens)=42% · P(inverse)=33% · P(ni l’un ni l’autre)=25%
- Gain espéré si seuil touché (€ et %) : 0.375 € (1.5 % sur taille 25 €)
- Perte max au seuil inverse (€ et %) : 0.375 € (1.5 %) ; stop hard −8 % pos. = 2.00 €
- Coût aller-retour estimé (€ et %) : 0.1 € (0.4 %)
- EV brut : 0.0338 € · EV net (après coût) : -0.0663 € · EV/coût = 0.338× (seuil règle ≥ 3×)
- Gain ≥ 3× coût ? non (Kelly ¼ = 0.0 €)
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : Prévision mesurable avant minutes Fed ~20h : biais rebond (déjà −3.4 %/24h + odds hausse de taux octobre déjà baissées). EV brut 0.0338 € < 3× coût (0.30 €) → pas d’achat ; forecast scoreable.
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —
- Score Compound (22h40) : annulé — aucun seuil touché, 22h00 à 74503,86 € (+0,49 %)

### 2026-10-07 15:48 | ETH-EUR | D-008
- Relevé / contexte (1 ligne) : mid 2286.19 € (-5.32 %/24h) ; catalyseur = minutes FOMC ~20h (pas décision de taux) ; fenêtre 15h–17h = simu seulement
- **Prévision mesurable** : **DOWN** / horizon **22h00 CEST** / seuil **±1.5 %** → cible 2251.90 € · inverse 2320.48 €
- Probas modèle : P(seuil sens)=40% · P(inverse)=28% · P(ni l’un ni l’autre)=32%
- Gain espéré si seuil touché (€ et %) : 0.375 € (1.5 % sur taille 25 €)
- Perte max au seuil inverse (€ et %) : 0.375 € (1.5 %) ; stop hard −8 % pos. = 2.00 €
- Coût aller-retour estimé (€ et %) : 0.1 € (0.4 %)
- EV brut : 0.045 € · EV net (après coût) : -0.055 € · EV/coût = 0.45× (seuil règle ≥ 3×)
- Gain ≥ 3× coût ? non (Kelly ¼ = 0.0 €)
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : Plus faible (−5.3 %/24h), déjà stoppé en simu — pas de rachat. Prévision : touche −1.5 % avant +1.5 % d’ici 22h. Spot long only → PAS ACHETER ; forecast DOWN pour score.
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —
- Score Compound (22h40) : perdu — aucun seuil touché, 22h00 à 2296,09 € (+0,43 %, contre la prévision)

### 2026-10-07 15:48 | SOL-EUR | D-009
- Relevé / contexte (1 ligne) : mid 103.42 € (-3.80 %/24h) ; catalyseur = minutes FOMC ~20h (pas décision de taux) ; fenêtre 15h–17h = simu seulement
- **Prévision mesurable** : **UP** / horizon **22h00 CEST** / seuil **±1.5 %** → cible 104.97 € · inverse 101.87 €
- Probas modèle : P(seuil sens)=38% · P(inverse)=34% · P(ni l’un ni l’autre)=28%
- Gain espéré si seuil touché (€ et %) : 0.375 € (1.5 % sur taille 25 €)
- Perte max au seuil inverse (€ et %) : 0.375 € (1.5 %) ; stop hard −8 % pos. = 2.00 €
- Coût aller-retour estimé (€ et %) : 0.1 € (0.4 %)
- EV brut : 0.015 € · EV net (après coût) : -0.085 € · EV/coût = 0.15× (seuil règle ≥ 3×)
- Gain ≥ 3× coût ? non (Kelly ¼ = 0.0 €)
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : Suit BTC (−3.8 %/24h). Même direction UP, confiance plus basse. EV 0.015 € insuffisant vs 3× coût → PAS ACHETER.
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —
- Score Compound (22h40) : annulé — aucun seuil touché, 22h00 à 103,46 € (+0,04 %)

### 2026-10-07 19:48 | BTC-EUR | D-010
- Relevé / contexte (1 ligne) : session Fed minutes ~20h ; **pas de prix frais** (ticks arrêtés depuis 2026-10-07T17:25:19+02:00, dernier mid ~74162.58 €)
- **Prévision mesurable** : **annulée** — horizon/seuil non fixés sans mid frais
- Gain espéré (€ et %) : 0 (pas d’achat)
- Perte max (€ et %) : n/a
- Coût aller-retour estimé (€ et %) : n/a
- Gain ≥ 3× coût ? non
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : sans prix à jour on ne peut ni calculer un seuil ni un EV fiable ; D-007 (UP ±1,5 % / 22h) reste le seul forecast BTC du soir, à scorer sur ticks quand le réseau revient
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —
- Score Compound : D-010 = annulé (pas mesurable) ; D-007 en attente horizon 22h

### 2026-10-07 19:48 | ETH-EUR | D-011
- Relevé / contexte (1 ligne) : dernier mid ~2288.30 € (sous 2300) ; réseau coupé ; déjà stoppé en simu cet après-midi
- **Prévision mesurable** : **annulée** (pas de mid frais)
- Gain espéré (€ et %) : 0
- Perte max (€ et %) : n/a
- Coût aller-retour estimé (€ et %) : n/a
- Gain ≥ 3× coût ? non
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : pas de rachat impulsif + pas de prix frais ; D-008 (DOWN ±1,5 % / 22h) reste le forecast à scorer
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —
- Score Compound : D-011 = annulé ; D-008 en attente

### 2026-10-07 19:48 | SOL-EUR | D-012
- Relevé / contexte (1 ligne) : dernier mid ~103.68 € ; réseau coupé
- **Prévision mesurable** : **annulée** (pas de mid frais)
- Gain espéré (€ et %) : 0
- Perte max (€ et %) : n/a
- Coût aller-retour estimé (€ et %) : n/a
- Gain ≥ 3× coût ? non
- Décision : **PAS ACHETER**
- Pourquoi (1–2 lignes) : même règle — pas de trade sans prix frais ; D-009 (UP ±1,5 % / 22h) reste le forecast à scorer
- Si ACHETER → taille € / % capital : —
- Lien trade plus tard : —
- Score Compound : D-012 = annulé ; D-009 en attente

### 2026-10-08 13:16 | ETH-EUR + SOL-EUR | D-013 — IDÉE À TESTER « rebond dans la tendance »
- Quand on achète : entre 15h et 17h (Bruxelles), lundi–vendredi, si le prix a baissé d’au moins 3 % en 24 h, puis une bougie d’1 h remonte, **et seulement si le prix est au-dessus de sa moyenne des 200 dernières heures**.
- Comment : ordre à cours limité qui attend dans le carnet (pas d’achat immédiat).
- Quand on revend : −1,5 % (stop) ou +3 % (objectif), sinon à 22h le même jour.
- Test du passé (1 an, Predict, 8 oct ~13h15) : ordres qui attendent (0 frais) → ETH +5,6 % (19 trades), SOL +5,4 % (23 trades), pire baisse ~5,5 %. Avec frais d’achat immédiat → ETH +0,8 %, SOL −4,9 %.
- Garder la crypto sur la même année : ETH −42 %, SOL −48 %.
- Prudence : réglages choisis après avoir vu les résultats → test de solidité + 2 moitiés d’année à faire (Compound 22h32). Un ordre qui attend peut ne pas être rempli quand ça bouge vite.
- Commande exacte : `backtest.sh run --pair ETH-EUR --strategy team_rebound --trend 200 --sl 1.5 --tp 3 --costs revolutx-maker` (idem SOL-EUR)
- Décision : **PAS ACHETER** — idée en attente du test Compound + avis Risk.
- Test du passé Compound (8 oct ~21h30) : **ne passe pas** (ETH et SOL) — voir bloc « Test du passé — Compound 8 oct » en bas. Simulation toujours permise.

### 2026-10-08 13:16 | ETH-EUR | D-014 — IDÉE À TESTER « cassure dans la tendance »
- Quand on achète : entre 15h et 17h, lundi–vendredi, si le prix passe au-dessus du plus haut des 8 dernières heures **et** au-dessus de sa moyenne des 200 heures.
- Comment : ordre à cours limité qui attend.
- Quand on revend : −1,5 % ou +3 %, sinon à 22h.
- Test du passé (1 an) : ordres qui attendent → ETH +4,1 % (34 trades), pire baisse 6,4 %. Avec frais immédiats → −4,4 %. (SOL : +1,6 % seulement → pas proposé.)
- Prudence : mêmes réserves que D-013.
- Commande exacte : `backtest.sh run --pair ETH-EUR --strategy team_breakout --trend 200 --sl 1.5 --tp 3 --costs revolutx-maker`
- Décision : **PAS ACHETER** — idée en attente du test Compound + avis Risk.
- Test du passé Compound (8 oct ~21h30) : **ne passe pas** — voir bloc en bas. Simulation toujours permise.

### 2026-10-08 14:34 | BTC-EUR | D-015
- Relevé / contexte : mid 73559.34 € (-1.55 %/24h) ; **sous sa moyenne 200 h** (75347 €) ; actus : grosses sorties des fonds BTC (les plus fortes depuis des mois), l’État US a déplacé 770 M$ de BTC saisis vers une plateforme, ventes d’emprunts US + pétrole > 100 $ ; Fed : hausse probable d’ici fin d’année
- **Prévision mesurable** : **DOWN** / horizon **17h00 CEST** / seuil **±0.5 %** → cible 73191.54 € · inverse 73927.14 €
- Méthode : seuil calé sur la volatilité des 7 derniers jours (mouvement typique ~0,5–0,7 % d’ici 17h) ; 20 000 simulations avec léger biais baissier (tendance + actus)
- Probas : P(−0.5 % d’abord)=37% · P(+0.5 % d’abord)=18% · P(aucun)=45%
- Achat hypothétique 25 € (stop −0.5 %, objectif +0.5 %) : gain si objectif 0.125 € · perte si stop 0.125 € · coût A/R 0.070 € → EV -0.094 €
- Gain ≥ 3× coût ? non
- Idées D-013/D-014 actives ? non (prix sous la moyenne 200 h)
- Décision : **PAS ACHETER**
- Pourquoi : on prévoit une baisse et on ne peut qu’acheter ; EV négative
- Lien trade plus tard : —
- Score Compound (8 oct ~21h30) : **gagné** — −0,5 % (73191,54) touché à 15h42 (73183,22), arrêt 73927,14 jamais touché (haut 73821,94) ; 17h00 à 73726,81

### 2026-10-08 14:34 | ETH-EUR | D-016
- Relevé / contexte : mid 2261.91 € (-1.77 %/24h) ; **sous sa moyenne 200 h** (2381 €) ; actus : grosses sorties des fonds BTC (les plus fortes depuis des mois), l’État US a déplacé 770 M$ de BTC saisis vers une plateforme, ventes d’emprunts US + pétrole > 100 $ ; Fed : hausse probable d’ici fin d’année
- **Prévision mesurable** : **DOWN** / horizon **17h00 CEST** / seuil **±0.5 %** → cible 2250.60 € · inverse 2273.22 €
- Méthode : seuil calé sur la volatilité des 7 derniers jours (mouvement typique ~0,5–0,7 % d’ici 17h) ; 20 000 simulations avec léger biais baissier (tendance + actus)
- Probas : P(−0.5 % d’abord)=40% · P(+0.5 % d’abord)=22% · P(aucun)=38%
- Achat hypothétique 25 € (stop −0.5 %, objectif +0.5 %) : gain si objectif 0.125 € · perte si stop 0.125 € · coût A/R 0.070 € → EV -0.092 €
- Gain ≥ 3× coût ? non
- Idées D-013/D-014 actives ? non (prix sous la moyenne 200 h)
- Décision : **PAS ACHETER**
- Pourquoi : on prévoit une baisse et on ne peut qu’acheter ; EV négative
- Lien trade plus tard : —
- Score Compound (8 oct ~21h30) : **gagné** — −0,5 % (2250,60) touché à 15h39 sur relevé 30 s (mèche à 2250,00 dès 14h50 sur bougie 1 min), arrêt 2273,22 jamais touché (haut 2271,33) ; 17h00 à 2257,19

### 2026-10-08 14:34 | SOL-EUR | D-017
- Relevé / contexte : mid 100.70 € (-3.43 %/24h) ; **sous sa moyenne 200 h** (106.05 €) ; actus : grosses sorties des fonds BTC (les plus fortes depuis des mois), l’État US a déplacé 770 M$ de BTC saisis vers une plateforme, ventes d’emprunts US + pétrole > 100 $ ; Fed : hausse probable d’ici fin d’année
- **Prévision mesurable** : **DOWN** / horizon **17h00 CEST** / seuil **±0.5 %** → cible 100.20 € · inverse 101.20 €
- Méthode : seuil calé sur la volatilité des 7 derniers jours (mouvement typique ~0,5–0,7 % d’ici 17h) ; 20 000 simulations avec léger biais baissier (tendance + actus)
- Probas : P(−0.5 % d’abord)=48% · P(+0.5 % d’abord)=28% · P(aucun)=24%
- Achat hypothétique 25 € (stop −0.5 %, objectif +0.5 %) : gain si objectif 0.125 € · perte si stop 0.125 € · coût A/R 0.070 € → EV -0.095 €
- Gain ≥ 3× coût ? non
- Idées D-013/D-014 actives ? non (prix sous la moyenne 200 h)
- Décision : **PAS ACHETER**
- Pourquoi : on prévoit une baisse et on ne peut qu’acheter ; EV négative
- Lien trade plus tard : —
- Score Compound (8 oct ~21h30) : **gagné** — −0,5 % (100,20) touché à 15h02 (100,02), arrêt 101,20 jamais touché (haut 100,86) ; 17h00 à 100,29

### 2026-10-08 15:59 | ETH-EUR / SOL-EUR | D-018
- Idée : **idée à la baisse** — Vente de pièces qu’on a déjà, puis Achat (rachat) plus bas (simulation OK ; pas de live avant test du passé)
- Règle claire (3 prix) :
  1. **Prix de vente** : on vend une partie de ce qu’on a déjà (ETH ou SOL) quand le prix monte fort sans vraie raison (ex. +3 % en 24 h alors que les actus ne le justifient pas), et seulement si on est **sous** la moyenne 200 h (tendance qui baisse : les remontées retombent souvent) — tester aussi la version « au-dessus »
  2. **Prix de rachat** : on rachète plus bas, objectif −3 % sous le prix de vente (on garde la différence)
  3. **Prix de rachat forcé** : si le prix continue de monter de +1,5 % après la vente, on rachète quand même pour ne pas perdre nos pièces
- Sortie aussi à 22h si aucun des deux rachats n’est touché
- Taille : max 5 % du capital ; ordres qui attendent dans le livre ; MetaMask inclus pour D-018 : ~0,0387 ETH vendable (Arbitrum), échange via Uniswap (~0,1–0,2 % aller-retour), pas le bouton MetaMask (~1,8 %, refusé)
- Stock vendable (Risk, 15h59) : ~0,0209 ETH (≈47 €) et ~0,241 SOL (≈24 €), hors pièces bloquées → max par vente ≈25 € : ~0,011 ETH ou tout le SOL dispo
- Contexte aujourd’hui : prix déjà en baisse (ETH ~2 249 €, SOL ~100 €) → **PAS VENDRE** (ce serait vendre bas)
- Test demandé à Compound (22h32) : sur ETH-EUR et SOL-EUR, un an de données, ordres qui attendent, frais Revolut X ; gain après frais, mieux que garder sans rien faire, ~20 trades, les deux moitiés de l’année, baisse max sous 8 %
- Décision : **PAS VENDRE** aujourd’hui ; idée en attente du test + du stock vraiment vendable (Risk)
- Test du passé Compound (8 oct ~21h30) : **ne passe pas** (ETH Revolut, SOL Revolut, ETH MetaMask/Uniswap) — voir bloc en bas. Simulation toujours permise (à toute heure).
- Lien trade plus tard : —

### 2026-10-08 17:27 | ETH-EUR | D-019 — SIMULATION RÉTRO (exception paramétrage, accord Quentin)
- Idée : **idée à la baisse** (vendre des pièces qu’on a, puis racheter plus bas)
- Sens : **Vendre en premier**, puis Acheter (rachat)
- Origine : idée à la baisse, tirée de la prévision D-016 écrite à 14h34 avant le mouvement
- Vente simulée : 0.0055 ETH (taille réduite de moitié, total 25 € partagé ; avant : 0.011) à 2261.905 € (≈ 12.44 €) à 14h34
- Rachat (objectif −0,5 %) : 2250.6 € — touché à 15:39 (ticks 30 s) · prix d’arrêt +0,5 % : 2273.22 € (pas touché avant)
- Résultat : +0.0000276 ETH (≈ +0.06 € avant frais) ; Risk compte +0,05 € après frais
- Décision : **VENDRE** (simulation rétro, comptée dans le capital simulé — accord Quentin)
- Pourquoi : prévision de baisse écrite à 14h34, avant le mouvement ; rachat touché avant le prix d’arrêt

### 2026-10-08 17:27 | SOL-EUR | D-020 — SIMULATION RÉTRO (exception paramétrage, accord Quentin)
- Idée : **idée à la baisse** (vendre des pièces qu’on a, puis racheter plus bas)
- Sens : **Vendre en premier**, puis Acheter (rachat)
- Origine : idée à la baisse, tirée de la prévision D-017 écrite à 14h34 avant le mouvement
- Vente simulée : 0.124 SOL (taille réduite de moitié, total 25 € partagé ; avant : 0.241) à 100.695 € (≈ 12.49 €) à 14h34
- Rachat (objectif −0,5 %) : 100.2 € — touché à 15:02 (ticks 30 s) · prix d’arrêt +0,5 % : 101.2 € (pas touché avant)
- Résultat : +0.000613 SOL (≈ +0.06 € avant frais) ; Risk compte +0,05 € après frais
- Décision : **VENDRE** (simulation rétro, comptée dans le capital simulé — accord Quentin)
- Pourquoi : prévision de baisse écrite à 14h34, avant le mouvement ; rachat touché avant le prix d’arrêt
- Note : pas de simulation rétro pour D-015 BTC — on n’a pas de BTC à vendre.

- Risk 17:30 : D-019 et D-020 vérifiés sur les prix 30 s (rachat touché avant l'arrêt ; ETH est monté à 2271,3 €, à 2 € de l'arrêt). Enregistrés à part (étiquette « rétro », state/retro_sims.jsonl), hors capital simulé officiel. Réserve : ouverts en même temps = ~49 € > plafond 5 % (25 €). Avec les règles de demain, une seule des deux passerait (ou deux de ~12 €).


- Réserve Risk (17h27) : D-019 + D-020 ouvertes ensemble ≈ 49 € > 25 € max au total → avec les règles de demain, une seule ou deux de ~12 €. Leçon : les simulations ouvertes en même temps partagent les 25 €.

- **Choix de taille D-019/D-020 (Predict, 17h31, chiffres de 14h34 seulement)** : écarts presque égaux (SOL +20 pts, ETH +18 pts) → **séparer en deux** : ETH 0,0055 (≈12,44 €) et SOL 0,124 (≈12,49 €), total ≈24,9 € ≤ 25 €. Risk doit réduire les tailles enregistrées (étaient ~24,9 € + ~24,3 €).
- Risk 17:31 : D-019 et D-020 réduits à ~12,5 € chacun (demande Predict, plafond 25 € partagé). D-019 +0.0510 €, D-020 +0.0501 €. Gain gardé en euros, mêmes pièces rachetées. Capital simulé 499.27 €.


### 2026-10-08 21:30 | ETH-EUR / SOL-EUR | Test du passé — Compound 8 oct (D-013, D-014, D-018)
Période : 1 an (7 oct 2025 → 7 oct 2026), bougies 1 h Binance EUR. Moitiés : 8 oct 2025 → 7 avr 2026 et 8 avr → 7 oct 2026. Résultats « sur 100 % du capital » comme l'outil ; pire baisse sur **notre** capital = 5 % × pire baisse de l'outil (l'outil met tout le capital dans chaque trade ; nous, max 25 € ≈ 5 % de ~500 €).
Contrôle : les 3 commandes de Grok Bot redonnent exactement ses chiffres (rebond ETH +0,97 % / 19, rebond SOL +6,39 % / 23, cassure ETH −9,34 % / 40, pire baisse −9,45 %).

**D-013 rebond ETH** (stop −1,5 %, objectif +3 %, 15h–17h, sortie 22h) — **ne passe pas**
- Ordres qui attendent, tous remplis : +5,62 % (19) · réaliste `--fill touch` : +3,52 % (19, pire baisse −5,83 % → ≈ −0,29 % de notre capital) · achat immédiat + frais : +0,80 % (19, −6,05 % → ≈ −0,30 %) · 50 % remplis (20 tirages) : milieu +0,11 %, pire −8,77 %.
- Moitiés : 1re +7,38 % (touch) / +5,27 % (immédiat) ; **2e −3,60 % / −4,24 %** → perd sur la 2e moitié.
- Nombre : 19 (< ~20). **Filtre 200 h pas appliqué par l'outil** pour le rebond (option `--trend` ignorée) : recalculé à la main sur la liste des trades, il ne reste que **3 trades en 1 an** (+0,85 %).
- Solidité : PBO 0,85 (> 0,5 → réglage sans doute choisi par chance) → NON.

**D-013 rebond SOL** — **ne passe pas**
- Tous remplis +5,38 % (23) · touch +2,59 % (23, −5,78 % → ≈ −0,29 %) · **achat immédiat −4,89 %** (23, −7,68 % → ≈ −0,38 %) · 50 % remplis : milieu +1,14 %, pire −4,25 %.
- Moitiés : **1re −0,50 % (touch) / −6,40 % (immédiat)** ; 2e +3,11 % / +1,61 %.
- Avec le vrai filtre 200 h : **2 trades en 1 an**. Solidité : PBO 0,42, mais hasard pas exclu (p 0,29) → FRAGILE.

**D-014 cassure ETH** (au-dessus de la moyenne 200 h, appliquée) — **ne passe pas**
- Tous remplis +4,12 % (34) · touch +0,32 % (34, −7,49 % → ≈ −0,37 %) · **achat immédiat −4,38 %** (34, −8,22 % → ≈ −0,41 %) · 50 % remplis : milieu +2,41 %, pire −12,41 %.
- Moitiés : **1re −2,58 % (touch) / −4,00 % (immédiat)** ; 2e +4,70 % / +1,35 %.
- Sans sortie à 22h (stop/objectif ou 7 jours max) : +12,36 % (touch) / +13,40 % (immédiat) sur l'année, mais 1re moitié encore **−1,38 % / −4,87 %** → ne passe pas non plus. Solidité : PBO 0,15, p 0,26 → FRAGILE.

Conditions de Risk : (1) ≥ 20 trades : rebond ETH non (19 ; 3 avec le vrai filtre), rebond SOL oui (23 ; 2 avec le filtre), cassure oui (34). (2) Pire baisse sur notre capital avec 5 % : ≤ 0,41 % partout → oui. (3) Gagnant en achat immédiat : rebond ETH oui (+0,80 %), rebond SOL non, cassure non ; avec `--fill touch` : oui pour les trois. **Bloquant pour les trois : une des deux moitiés de l'année est perdante.**

**D-018 idée à la baisse (vendre haut, racheter −3 %, rachat de sécurité +1,5 %, sans sortie 22h)** — **ne passe pas** (ETH Revolut, SOL Revolut, ETH MetaMask)
- ETH 0,011 (moyenne 200 h) : 43 ventes, 0,011 → 0,011009 ETH (+0,08 % de pièces ≈ **+0,02 €** vs garder). 1re moitié **−0,70 %**, 2e +0,79 %. Gain moyen net 0,03 %/vente < 3× coût moyen 0,27 % → **règle 3× non**. Pire baisse en pièces −12,2 % (sur ~25 € ≈ −0,6 % du capital). Solidité FRAGILE (2/8).
- SOL 0,241 (moyenne 200 h) : 63 ventes, 0,241 → 0,2652 SOL (+10,05 % ≈ **+2,51 €** vs garder). 1re +20,4 %, **2e −8,6 %**. Gain moyen net 0,18 % < 3× coût 0,26 % → **3× non**. Pire baisse −14,7 % en pièces (≈ −0,7 % du capital). FRAGILE (4/8).
- Sans filtre 200 h : ETH −3,3 % de pièces (−0,83 €), NON ; SOL +44,1 % (+11,03 €) mais 2e moitié −7,5 %, pire baisse −31,5 % en pièces, 3× non, FRAGILE (6/8).
- ETH via Uniswap (MetaMask) : −11,7 % de pièces (**−2,96 €** vs garder) : chaque échange paie des frais (pas de rachat à 0 %) → non.
- `--fill touch` : même résultat que tout rempli (ETH et SOL).
- Fenêtre live 15h–17h seulement : 7 ventes ETH / 11 SOL en 1 an → trop peu pour juger.
- Simulation : permise à toute heure (règle de Quentin) ; la version SOL sans filtre est la plus intéressante à simuler, à juger après ~20 essais.

- 2026-10-08 21:32 PM-Risk — Validation live après test 1 an (bilan Compound) : REFUSÉ en live pour rebond ETH, rebond SOL, cassure ETH, vendre haut/racheter bas (ETH, SOL, MetaMask). Raisons : perte sur une moitié d’année et/ou en achat immédiat ; gain < 3× frais pour vendre haut/racheter bas. Tous restent permis en simulation. Limite 25 € au total inchangée.

### Test du passé — 2026-10-08 (Compound)

Rappel : un test réussi n’autorise jamais le live tout seul (il faut encore LIVE_ONCE + avis Risk).

**Filtre « acheter seulement au-dessus de la moyenne 200 h »**
- D-014 (`team_breakout`) : oui, via `--trend 200`.
- D-013 (`team_rebound`) : **filtre impossible** — l’outil n’a pas d’option 200 h pour le rebond (`--trend` ne sert qu’à la cassure ; `--trend-ma` = sell_rebuy seulement). Résultats D-013 = **sans filtre**, avec cette réserve. (La commande notée `--trend 200` sur le rebond ne change rien.)

#### D-013 rebond (SL 1,5 % / TP 3 % / 15–17 / jours ouvrés) — sans filtre 200 h

| Paire | Maker (tout rempli) | Touch | Fill-rate 50 % (médiane 20 seeds) | Frais défaut (taker) | Trades | Moitiés H1/H2 | Baisse max sur notre capital (~5 %/trade) | Robust | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| ETH-EUR | +5,6 % vs hold −42 % | +3,5 % | médiane +0,1 % (pire −8,8 %) | +0,8 % | 19 | H1 +8,9 % / **H2 −3,0 %** | ~0,3 % (sim 499 € / live 165 €) | FRAGILE (maker) ; FRAGILE (défaut) | **ne passe pas** — 2e moitié en perte ; <20 trades |
| SOL-EUR | +5,4 % vs hold −48 % | +2,6 % | médiane +1,1 % (pire −4,3 %) | **−4,9 %** | 23 | H1 +0,7 % / H2 +4,6 % | ~0,3 % | **SOLIDE** (maker) ; **NON** (défaut) | **ne passe pas** — avec frais d’achat immédiat (cas Risk) = perte ; filtre 200 h absent. Simulation OK côté maker/touch |

Risk (a)(b)(c) :
- ETH : (a) non (19) ; (b) oui (~0,3 % < 8 %) ; (c) touch oui (+3,5 %) ; fill-rate médiane ~0 (fragile), pire seed négatif.
- SOL : (a) oui (23) ; (b) oui ; (c) touch oui (+2,6 %), médiane seeds oui (+1,1 %).

Dossiers : `.../20261008_212918_*_ETH-EUR_1H_team_rebound` (maker), `..._212921_*_SOL-EUR_...`, touch/fillrate/default dans `knowledge/nightly_2026-10-08/`.

#### D-014 cassure dans la tendance ETH (`--trend 200`, SL 1,5 / TP 3)

| Maker | Touch | Fill-rate médiane | Défaut | Trades | H1/H2 | DD capital | Robust | Verdict |
|---|---|---|---|---|---|---|---|---|
| +4,1 % | +0,3 % | +2,4 % (pire −12,4 %) | **−4,4 %** | 34 | **H1 −2,7 %** / H2 +7,0 % | ~0,3–0,4 % | FRAGILE (maker) ; NON (défaut) | **ne passe pas** — 1re moitié en perte ; frais immédiats = perte |

Risk : (a) oui (34) ; (b) oui ; (c) touch oui (+0,3 %) mais très faible ; médiane seeds oui, pire seed très négatif.

Dossier maker : `.../20261008_212924_981278_ETH-EUR_1H_team_breakout`.

#### D-018 vendre haut / racheter plus bas (`sell_rebuy`)

Réglages : rise 3 % / 24 h, dip 3 %, stop 1,5 %, trend-ma 200 (sous la moyenne), sauf variante `--trend-ma 0`.

| Variante | Pièces vs garder | € vs garder | Ventes | Win % | 3× frais | H1/H2 (pièces) | Robust | Verdict |
|---|---|---|---|---|---|---|---|---|
| ETH base (0,011) | +0,08 % | +0,02 € | 43 | 35 % | **non** (0,03 % < 0,27 %) | H1 −0,7 % / H2 +0,8 % | FRAGILE (2/8) | **ne passe pas** — gain moyen < 3× frais ; 2e critère moitiés faible ; baisse max pièces −12 % |
| SOL base (0,241) | +10,1 % | +2,51 € | 63 | 38 % | **non** (0,18 % < 0,26 %) | H1 +20 % / **H2 −8,6 %** | FRAGILE (4/8) | **ne passe pas** — 3× frais non ; 2e moitié en perte ; baisse max pièces −15 % |
| ETH session 15–17 | +2,7 % | +0,67 € | **7** | 43 % | oui | H1 −1,8 % / H2 +4,6 % | — | **ne passe pas** — trop peu de ventes (<20) |
| SOL session 15–17 | +5,6 % | +1,40 € | **11** | 46 % | oui | H1 +4,1 % / H2 +1,4 % | — | **ne passe pas** — trop peu de ventes |
| ETH `--trend-ma 0` | **−3,3 %** | −0,83 € | 180 | 34 % | non | H1 +3,6 % / H2 −6,7 % | — | **ne passe pas** — moins de pièces qu’en gardant |
| SOL `--trend-ma 0` | +44 % | +11,0 € | 233 | 38 % | non | H1 +52 % / **H2 −4,9 %** | — | **ne passe pas** — 3× frais non ; 2e moitié en perte ; baisse max −32 % |
| ETH `--costs uniswap` | **−11,7 %** | −2,96 € | 43 | 35 % | non | H1 −8,3 % / H2 −3,7 % | — | **ne passe pas** — perte nette (MetaMask/Uniswap) |

#### C) Rebond / cassure d’origine (défaut outil, frais Revolut X, sans filtre 200 h, SL/TP 1,5)

| Kind × paire | Net % | vs hold | Trades | Win % | MDD strat | Verdict |
|---|---|---|---|---|---|---|
| rebond ETH | +0,9 % | −43 % | 19 | 53 % | −4,0 % | **ne passe pas** — <20 trades ; déjà en pause (test BTC négatif) |
| rebond SOL | −0,6 % | −48 % | 23 | 61 % | −3,4 % | **ne passe pas** — perte après frais |
| cassure ETH | −15,1 % | −43 % | 40 | 38 % | −15,1 % | **ne passe pas** — grosse perte |
| cassure SOL | −6,1 % | −48 % | 41 | 54 % | −10,4 % | **ne passe pas** — perte ; MDD > 8 % sur la courbe stratégie |

#### Échecs de commande
Aucun (tous EXIT:0). JSON bruts : `/workspace/predict-market-bot/knowledge/nightly_2026-10-08/`. Runs : `/workspace/tools/vibe-trading/home/runs/`.


- 2026-10-08 21:39 PM-Risk — Exception levée : rebond/cassure bruts de nouveau permis en simulation (règle Quentin 17h : test 1 an bloque seulement le live). Live toujours refusé pour toutes les sortes. Plafond 25 € et ≥1 simu 15h–17h inchangés.

### 2026-10-08 23:00 | SOL-EUR | D-021 — SIMULATION DE NUIT (demande Orchestrator/Quentin, sans zone)
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 96,53 € (−1,5 %) avant 99,47 € (+1,5 %), d'ici demain 10h00 CEST. Confiance faible (~55 %).
- Décision : SIMULER — vente de 0,15 SOL à 98,00 € (≈ 14,70 €), rachat visé 96,53 €, prix d'arrêt fixe 99,47 €
- Heure limite : 2026-10-09 10:00 (rappel seulement — ne ferme pas le trade, décision Quentin 23h04)
- Pourquoi : SOL est la plus faible du jour (−4,6 %) et remonte de +2 % depuis le creux de 19h (95,99 €) sans nouvelle propre ; nouvelles du soir plutôt à la baisse (sorties des fonds bitcoin, pétrole, humeur 64/100). Gain visé 1,5 % ≫ frais (~0,1–0,2 % aller-retour). Taille 15 € pour garder ~10 € du plafond de 25 € si une zone sonne cette nuit. ETH pas choisi (remonte encore, nouveau plus haut du soir à 22h57) ; BTC au milieu de ses zones, pas d'avance claire.
- Prix au moment de la décision (relevé 22:57) : BTC 72 951 € · ETH 2 208 € · SOL 98,00 €
- 2026-10-08 22:59 PM-Risk — D-021 VALIDÉ en simulation : SOL idée à la baisse, vente 0,15 SOL à 98,00 € (14,70 €), rachat visé 96,53 €, arrêt 99,47 €, heure limite 09/10 10h00. Contrôles : ≤25 €, arrêt présent, total ouvert 14,70/25 €, paire permise, id présent. Gardien lancé. Correction : le capital comptait la vente à découvert en double (capital affiché 528,67 € au lieu de 499,27 €) ; corrigé, sommet remis à 500 €.
- 2026-10-08 23:04 PM-Risk — Heure limite = rappel seulement (décision Quentin) : le gardien ne ferme plus un trade à l'heure limite, en simu comme en live ; il écrit un rappel pour Predict. Seuls le prix d'arrêt et le prix visé ferment. Une heure limite passée ou illisible ne bloque plus un trade. D-021 : 10h00 demain devient un rappel. Gardien redémarré avec la nouvelle règle.


### 2026-10-09 14:02 | BTC-EUR | D-022 — Sonnette Z-BTC-74000
- Zone : Z-BTC-74000 (au-dessus de 74 000 €) touchée à 14h00 — prix sonnette 74 230,24 € ; tick mid 74175.08 € (plus haut du jour ~74 241 € ; min du jour ~72 709 €)
- Actus (news.json ~12h UTC) : « Uptober » difficile ; BTC se stabilise près de 82 500 $ après que Trump écarte une frappe sur l’Iran avant les midterms ; semaine encore en baisse
- Brief Research du jour : **absent** (prochain brief 14h44) ; dernier brief 8 oct : pas de signal d’achat clair
- Simulation ouverte : D-021 SOL idée à la baisse encore ouverte (14,70 € / 25 €) — SOL ~99,16 €, arrêt 99,47 €, cible 96,53 € (creux du jour ~96,93 €, cible non touchée). Rappel heure limite 10h00 déjà passé → **idée D-021 morte** (prix contre nous, près de l’arrêt) : Risk décide
- **Prévision mesurable** : **DOWN** / horizon **17h00 CEST** / seuil **±1 %** vs 74 200 € → cible 73458.0 € · inverse 74942.0 €. Confiance faible (~55 %)
- Idée revue : à la hausse (cassure au-dessus de 74 000 €)
- Idée : à la hausse
- Sens : Achat
- Décision : PAS DE TRADE (ni simulation ni live) — pas d’entrée à 74200 €, pas de prix visé / arrêt d’ordre
- Heure limite : 2026-10-09 17:00
- Pourquoi : la sonnette a sonné alors que BTC était déjà ~230 € au-dessus de 74 000 € et au plus haut du jour (+2 % depuis minuit) — acheter maintenant = courir après. Pas de brief Research du jour. Plafond simu déjà pris à 14,70 € par D-021 (idée morte, près de l’arrêt). Live interdit (aucune sorte ne passe le test du passé ; hors créneau 15h–17h). On attend le brief 14h44 / prévision 14h55.
- Lien trade plus tard : —
- 2026-10-09 14:26 PM-Risk — D-021 FERMÉ à la main (simulation) : rachat 0,15 SOL à 98,77 €, perte −0,13 € (frais compris). Raison : idée déclarée morte par Predict à 14h02 (bonne nouvelle Solana contre nous), heure limite de 10h passée ; fermer libère le plafond pour l'achat BTC prévu. Plafond simu : 0 / 50 € engagés.

### 2026-10-09 14:30 | BTC-EUR | D-023 — SIMULATION (demande Quentin : 50 € libres)
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75 232 € (+1,5 %) avant 73 379 € (−1 %), d'ici aujourd'hui 17h00 CEST. Confiance faible (~55 %).
- Décision : SIMULER — achat de 0,000337 BTC à 74 120 € (≈ 24,98 €), prix visé 75 232 €, prix d'arrêt fixe 73 379 €
- Heure limite : 2026-10-09 17:00 (rappel seulement)
- Avis Research : déjà donné à 14h00 dans le groupe (simu à la hausse possible, confiance faible : hausse due à des rachats forcés, sorties des fonds).
- Pourquoi : BTC a recassé 74 000 € ce midi (Iran plus calme, 1,1 milliard $ de paris à la baisse rachetés) puis recule de 0,35 % sous le haut du jour (74 389 €), tout près de mon prix d'entrée prévu (74 050 €). Gain visé 1,5 % contre une perte de 1 %. ETH et SOL n'ont pas de signal plus net (SOL : idée à la baisse D-021 abandonnée, ETH au milieu de ses zones).
- Prix au moment de la décision (relevé 14:29) : BTC 74 120 € · ETH 2 232 € · SOL 98,75 €
- 2026-10-09 14:30 PM-Risk — D-023 VALIDÉ en simulation : achat 0,000337 BTC à 74 120 € (24,98 €), arrêt 73 379 €, visé 75 232 €, rappel 17h00. Contrôles : ≤25 €, arrêt présent, total 24,98/50 €, paire permise, id présent. Gardien lancé. Défaut repéré : le prix visé n'était pas enregistré pour les achats (hausse) ; correction en cours.
- 2026-10-09 14:34 PM-Risk — Corrigé : le gardien vend désormais un achat (hausse) à son prix visé (le prix d'arrêt reste prioritaire) ; frais d'achat comptés. D-023 a son prix visé 75 232 €. Tests 204/204.

### 2026-10-09 15:08 | SOL-EUR + ETH-EUR | D-024 — 3 PROPOSITIONS (brief Research 15h05)
Prix au moment de la décision (relevé 15:07) : BTC 74 200 € · ETH 2 232,70 € · SOL 98,69 €. Place libre : 25 € sur 50 € (D-023 BTC ouvert, 24,98 €). Réel interdit : aucune sorte de trade n'a passé le test sur un an.

**D-024a — Prudente (passée à Risk)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100,09 € (+1,42 %) avant 97,30 € (−1,41 %), d'ici 17h00 CEST. Confiance faible (~55 %).
- Décision : SIMULER — achat de 0,152 SOL à 98,69 € (≈ 15,00 €), prix visé 100,09 €, prix d'arrêt fixe 97,30 €
- Heure limite : 2026-10-09 17:00 (rappel seulement)

**D-024b — Équilibrée (passée à Risk)**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2 197 € (−1,60 %) avant 2 255 € (+1,00 %), d'ici 17h00 CEST. Confiance faible (~55 %).
- Décision : SIMULER — vente de 0,00448 ETH à 2 232,70 € (≈ 10,00 €), rachat visé 2 197 €, prix d'arrêt fixe 2 255 €
- Heure limite : 2026-10-09 17:00 (rappel seulement)

**D-024c — Risquée (pas passée : plus de place sous les 50 €)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100,70 € (+2,04 %) avant 97,70 € (−1,00 %), d'ici 17h00 CEST.
- Décision : NE PAS SIMULER — aurait été un achat de 10 € de SOL à 98,69 €, visé 100,70 €, arrêt 97,70 €
- Heure limite : 2026-10-09 17:00 (rappel seulement)

- Avis Research : brief de 15h05 (SOL à la hausse, mise à jour du réseau vers 17h ; ETH le plus faible de la semaine, l'argent sort des fonds ; confiance faible partout).
- Pourquoi : je suis les idées de Research pour SOL et ETH. Elles vont en sens inverse, donc elles ne se cumulent pas si tout le marché bouge ensemble. BTC est déjà couvert par D-023. Pour la prudente, le prix d'arrêt est un peu plus serré que celui de Research (97,30 € au lieu de 97,13 €) pour que le gain visé égale au moins la perte possible. La risquée attend qu'une place se libère.
- 2026-10-09 15:08 PM-Risk — D-024 (3 propositions) : a prudente OUI (achat SOL 15 € à 98,69 €, arrêt 97,30 €, visé 100,09 € ; gain = perte, arrêt 1,4 %) ; b équilibrée OUI (vente ETH 10 € à 2 232,70 €, rachat visé 2 197 €, arrêt 2 255 € ; gain 1,6× la perte, arrêt 1 %, raison : sorties des fonds) ; c risquée NON (plus de place sous 50 €). Total engagé 49,98 / 50 €. Lancées en simulation.

### 2026-10-09 15:40 | BTC-EUR (+ ETH/SOL) | D-032 (ancienne D-025 de 15h40, ANNULÉE) — Sonnette Z-BTC-73700 (revue D-023 + 3 propositions, plafond plein)
Prix au moment de la décision (relevé 15:40) : BTC 73,752.67 € · ETH 2,215.51 € · SOL 97.84 €.
Haut/bas du jour : BTC 74,389/72,709 · ETH 2,239/2,201 · SOL 99.31/96.92.
Place libre : ~0,02 € sur 50 € (D-023 BTC 24,98 € + D-024a SOL 15 € + D-024b ETH 10 € = 49,98 €). Réel interdit.
Sonnette : Z-BTC-73700 (sous 73 700 €) à 15h37 — prix 73 696,22 € ; mid actuel 73,752.67 €.
- Avis Research : pas demandé — évident (D-023 encore au-dessus de l'arrêt et plafond déjà plein).
- Pourquoi : BTC a perdu ~0,5 % depuis l'achat D-023 (74 120 €) mais reste au-dessus de l'arrêt 73 379 € (~374 € de marge). L'idée D-023 est **encore vivante** : on laisse courir jusqu'au prix d'arrêt ou au prix visé 75 232 €. Rappel 17h00 pas encore passé. Pas de nouvelle ouverture : plafond plein. Les 3 propositions ci-dessous attendent qu'une place se libère ; Risk n'ouvre rien tant que le total reste à 49,98 €.

**Revue D-023 (ouverte)**
- Idée : à la hausse
- Sens : Achat (déjà ouvert)
- Prévision mesurable : UP / seuil +1,5 % (visé 75 232 €) / −1 % (arrêt 73 379 €) / rappel 17h00
- Décision : GARDER — idée encore vivante (prix 73,752.67 € > arrêt 73 379 €)
- Heure limite : 2026-10-09 17:00 (rappel seulement)

**D-032a — Prudente (en attente de place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL UP / +2 % avant arrêt −2 % / rappel 20h00
- Décision : SIMULER si place libre — achat 25 € de SOL à 97.84 €, visé 99.80 €, arrêt 95.88 €
- Heure limite : 2026-10-09 20:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt 2 %, gain = 1× la perte)

**D-032b — Équilibrée (en attente de place)**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH DOWN / −2,25 % avant arrêt +1,5 % / rappel 20h00
- Décision : SIMULER si place libre — vente 20 € d'ETH à 2215.51 €, rachat visé 2165.7 €, arrêt 2248.7 €
- Heure limite : 2026-10-09 20:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte) — raison : sorties des fonds et ETH le plus faible de la semaine (brief Research)

**D-032c — Risquée (en attente de place ; aucune risquée ouverte)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL UP / +2 % avant arrêt −1 % / rappel 20h00
- Décision : SIMULER si place libre — achat 10 € de SOL à 97.84 €, visé 99.80 €, arrêt 96.86 €
- Heure limite : 2026-10-09 20:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte)

- Décision globale : **pas de nouvelle ouverture maintenant** (plafond 49,98/50 €). Risk : ne valide a/b/c que si une simu ouverte se ferme d'abord (garde d'abord la prudente). D-023 : laisser ouverte.
- Prix d'entrée de secours (si tout reste bloqué) : SOL achat à 97.22 € (zone posée) ; ETH vente renforcement vers 2207.9 € ; BTC ne pas rajouter tant que D-023 est ouverte.



### 2026-10-09 15:36 | SOL-EUR | D-026 — 3 PROPOSITIONS (sonnette Z-SOL-97.9)
Prix au moment de la décision (relevé 15:38) : BTC 73,769.69 € · ETH 2,216.58 € · SOL 97.70 €.
Haut/bas du jour (ticks) : BTC 72 709–74 389 · ETH 2 201–2 239 · SOL 96,93–99,31.
Place libre : 0,02 € sur 50 € (ouverts : D-023 BTC 24,98 € · D-024a SOL 15 € · D-024b ETH 10 € = 49,98 €).
Réel interdit : aucune sorte n'a passé le test sur un an.
Avis Research : non demandé — décision évidente (cassure sous 97,90 € de la zone planifiée, prix 97,70 €).
Brief Research du jour (15h05) : SOL était à la hausse (mise à jour réseau ~17h) ; le prix a cassé le plan zone à la baisse → je suis la cassure, pas le brief.
Note Risk : D-024a (achat SOL à 98,69 €, arrêt 97,30 €) va contre nous (SOL 97,70 €, −1,0 %) ; heure rappel 17h00 pas encore passée → pas « idée morte » encore, mais elle contredit D-025. Pour ouvrir D-026, il faut d'abord libérer de la place (fermer D-024a ou une autre).

**D-026a — Prudente**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 96.23 € (−1.5 %) avant 99.17 € (+1.5 %), d'ici 22h00 CEST. Confiance faible (~55 %).
- Décision : SIMULER — vente de 0.2559 SOL à 97.70 € (≈ 25 €), rachat visé 96.23 €, prix d'arrêt fixe 99.17 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

**D-026b — Équilibrée**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 96.23 € (−1.5 %) avant 98.68 € (+1.0 %), d'ici 22h00 CEST. Confiance faible (~55 %).
- Décision : SIMULER — vente de 0.2047 SOL à 97.70 € (≈ 20 €), rachat visé 96.23 €, prix d'arrêt fixe 98.68 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

**D-026c — Risquée**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 95.75 € (−2.0 %) avant 98.68 € (+1.0 %), d'ici 22h00 CEST. Confiance faible (~55 %).
- Décision : SIMULER — vente de 0.1024 SOL à 97.70 € (≈ 10 €), rachat visé 95.75 €, prix d'arrêt fixe 98.68 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

- Pourquoi : zone Z-SOL-97.9 touchée (plan écrit : idée à la baisse). SOL mid 97.70 € confirme la cassure. Gain/arrêt adaptés aux 3 niveaux Risk. Aucune risquée ouverte actuellement. Place quasi nulle → Risk priorise prudente puis équilibrée puis risquée après avoir libéré de la place.

### 2026-10-09 15:39 | BTC-EUR + SOL-EUR + ETH-EUR | D-025 — Sonnette Z-BTC-73700 (3 propositions, plafond plein)
Prix au moment de la décision (relevé 15:39) : BTC 73,802.71 € · ETH 2,217.97 € · SOL 97.81 €. Haut/bas du jour : BTC 74,389/72,709 · ETH 2,239/2,201 · SOL 99.31/96.92.
Place libre : ~0,02 € sur 50 € (D-023 BTC 24,98 € + D-024a SOL 15 € + D-024b ETH 10 € = 49,98 €). Réel interdit.

**Verdict D-023 (motif de la sonnette) :** idée **encore vivante**. BTC ~73,803 €, encore ~0,5 % au-dessus de l’arrêt 73 379 € ; le rappel 17h00 n’est pas passé. On laisse courir jusqu’à l’arrêt ou au visé 75 232 €. Risk ne ferme pas sur cette sonnette.

**D-025a — Prudente (pas de place maintenant ; prioritaire dès qu’une place se libère)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 99.16 € (+2 %) avant 95.28 € (−2 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : achat de 0.2571 SOL à 97.22 € (≈ 25 €), prix visé 99.16 €, prix d’arrêt fixe 95.28 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

**D-025b — Équilibrée (pas de place maintenant)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2,168 € (−2,25 %) avant 2,251 € (+1,5 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.00902 ETH à 2,217.97 € (≈ 20 €), rachat visé 2,168 €, prix d’arrêt fixe 2,251 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

**D-025c — Risquée (pas de place maintenant ; une seule risquée à la fois)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 74,511 € (+2 %) avant 72,320 € (−1 %), d’ici 22h00 CEST.
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : achat de 0.000137 BTC à 73,050 € (≈ 10 €), prix visé 74,511 €, prix d’arrêt fixe 72,320 € — seulement si D-023 s’est fermée d’abord
- Heure limite : 2026-10-09 22:00 (rappel seulement)

- Avis Research : pas demandé (décision évidente : la zone demandait seulement de revoir D-023 ; le brief 15h05 suffit — BTC fragile mais déjà couvert).
- Pourquoi : BTC a cassé 73 700 € mais reste au-dessus de l’arrêt de D-023 ; on ne tue pas l’idée avant 17h ni avant l’arrêt. Le plafond est plein, donc les 3 nouvelles idées restent en attente. La prudente reprend le plan bas du jour sur SOL ; l’équilibrée prolonge la baisse ETH du brief ; la risquée n’ouvre un rebond BTC que si D-023 est déjà fermée.


### 2026-10-09 15:38 | BTC-EUR + SOL-EUR | D-027 (ancienne D-026 de 15h38, ventes BTC, ANNULÉE) — 3 PROPOSITIONS (sonnette mouvement >0,5 % depuis D-024)
Prix au moment de la décision (relevé 15:38) : BTC 73769.69 € · ETH 2216.58 € · SOL 97.695 €.
Place libre : ≈ 0,02 € sur 50 € (ouverts : D-023 BTC 24,98 € · D-024a SOL 15 € · D-024b ETH 10 € = 49,98 €). Réel interdit.
Mouvement depuis D-024 : BTC −0,67 % · ETH −0,89 % · SOL −1,00 % (les 3 à la baisse).
Note Risk : D-023 et D-024a (achats) vont contre le mouvement ; rappel 17h00 pas encore passé → pas « idée morte » pour l’heure, mais pressées. Pour ouvrir D-027, Risk doit libérer de la place (prudente d’abord).

**D-027a — Prudente (passée à Risk)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : BTC touche 72663.14 € (−1,5 %) avant 74876.24 € (+1,5 %), d’ici 18h00 CEST. Confiance moyenne (~60 %).
- Décision : SIMULER — vente de 0.000339 BTC à 73769.69 € (≈ 25 €), rachat visé 72663.14 €, prix d’arrêt fixe 74876.24 €
- Heure limite : 2026-10-09 18:00 (rappel seulement)
- Avis Research : décidé seul — le mouvement baissier sur les 3 paires depuis D-024 est clair (continuation baisse, pas un rebond).
- Pourquoi : les 3 cryptos baissent ensemble depuis D-024 ; BTC a perdu le niveau 74 000 et reste sous l’entrée D-023. Gain visé = perte possible (1×), arrêt 1,5 % ≤ 2 %.

**D-027b — Équilibrée (passée à Risk)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 96.23 € (−1,5 %) avant 98.672 € (+1,0 %), d’ici 18h00 CEST. Confiance moyenne (~60 %).
- Décision : SIMULER — vente de 0.2047 SOL à 97.695 € (≈ 20 €), rachat visé 96.23 €, prix d’arrêt fixe 98.672 €
- Heure limite : 2026-10-09 18:00 (rappel seulement)
- Avis Research : décidé seul — même raison (baisse claire des 3).
- Pourquoi : SOL a le plus baissé depuis D-024 (−1 %) et D-024a (achat SOL) est déjà sous l’eau ; on suit la continuation vers le bas du jour (~96,93 €). Gain 1,5× la perte, arrêt 1 %.

**D-027c — Risquée (pas de place sous 50 € tant que Risk n’a pas libéré)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : BTC touche 72294.3 € (−2,0 %) avant 74507.39 € (+1,0 %), d’ici 18h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER pour l’instant — aurait été une vente de 0.000136 BTC à 73769.69 € (≈ 10 €), rachat visé 72294.3 €, arrêt 74507.39 € ; 1 seule risquée à la fois (aucune ouverte).
- Heure limite : 2026-10-09 18:00 (rappel seulement)
- Avis Research : décidé seul — baisse claire.
- Pourquoi : même sens que la prudente, mais arrêt plus serré (1 %) et gain 2× ; seulement si Risk libère assez après la prudente et l’équilibrée.

- 2026-10-09 15:43 PM-Predict — Nettoyage des doublons : plusieurs sonnettes sont arrivées en même temps. Ce qui compte : D-025 de 15h37 (rappel 22h00), D-026 avec les ventes de SOL (la risquée est corrigée : vente de 10 € de SOL au prix du moment, rachat visé 95,60 €, arrêt 98,50 €), et D-024a fermée (idée à la hausse sur SOL morte). ANNULÉES : la première D-025, les autres D-025 de 15h36/15h38/15h40, et la D-026 « ventes BTC » de 15h38, arrivée en retard et contraire à D-023.
- 2026-10-09 15:43 PM-Risk — D-024a FERMÉ à la main (idée morte selon Predict, SOL sous l'entrée) : vente 0,15199 SOL à 97,49 €, perte −0,20 €. D-026 risquée OUI : vente 10 € SOL à 97,49 €, rachat visé 95,54 € (−2 %), arrêt 98,47 € (+1 %), rappel 22h00 ; prix ajustés au prix du moment pour garder gain = 2× la perte. D-023 gardé. Engagé 45,16 / 50 €.
- 2026-10-09 15:48 PM-Predict — Numéros uniques, à la demande de Compound : D-025 = la version de 15h37/15h39 avec rappel 22h00 (la seule valable). D-026 = les ventes de SOL avec rappel 22h00 ; la risquée a été lancée à 97,49 €, rachat visé 95,54 €, arrêt 98,47 €. D-027 = l'ancienne « D-026 » de 15h38 (ventes BTC/SOL, rappel 18h00) : ANNULÉE. La version de D-025 avec rappel 20h00 est ANNULÉE aussi.
- 2026-10-09 15:50 PM-Risk — Caisse simu corrigée de −0,18 € (les deux ventes de D-024a avaient crédité le coût au lieu du prix de vente) ; D-024a : perte −0,20 €. Rapprochement Revolut écrit (« sans objet » en simu) ; numéro de cycle sur chaque vente/rachat. Défaut de reste corrigé.


### 2026-10-09 16:23 | BTC-EUR + ETH-EUR + SOL-EUR | D-028 — Sonnette Z-BTC-74166 (3 propositions)
Prix au moment de la décision (relevé 16:23) : BTC 74,206.26 € · ETH 2,225.10 € · SOL 98.38 €. Haut/bas du jour : BTC 74,389/72,709 · ETH 2,239/2,201 · SOL 99.31/96.92.
Place libre : ≈ 5,02 € sur 50 € (ouverts : D-023 BTC 24,98 € · D-024b ETH 10 € · D-026 SOL risquée 10 € = 44,98 €). Réel interdit.

**Verdict zone Z-BTC-74166 :** la **baisse BTC est morte**. BTC est repassé au-dessus de 74 166 € (74,206 €), près du haut du jour (74,389 €). D-023 (idée à la hausse) **encore vivante** (+0,1 %, au-dessus de l’entrée 74 120 €, loin de l’arrêt 73 379 €). Rappel 17h00 pas encore passé → on laisse courir jusqu’à l’arrêt ou au visé 75 232 €.

**Note Risk — D-026 (SOL, idée à la baisse, risquée) :** SOL à 98.38 €, contre nous (−0,96 %), tout près de l’arrêt 98,47 €. Rappel 22h00 pas passé → pas encore « idée morte », mais Risk surveille l’arrêt. **D-024b** (ETH baisse) encore vivante (prix avec nous).

**D-028a — Prudente (pas de place maintenant ; prioritaire dès qu’une place se libère)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2,180.60 € (−2 %) avant 2,269.60 € (+2 %), d’ici 22h00 CEST. Confiance moyenne (~60 %).
- Décision : NE PAS SIMULER maintenant — place ≈ 5 € ; prêt : vente de 0.011235 ETH à 2,225.10 € (≈ 25 €), rachat visé 2,180.60 €, prix d’arrêt fixe 2,269.60 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

**D-028b — Équilibrée (pas de place ; seulement après fermeture de D-026)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100.59 € (+2,25 %) avant 96.90 € (−1,5 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — conflit avec D-026 (vente SOL) et place insuffisante ; prêt : achat de 0.203293 SOL à 98.38 € (≈ 20 €), prix visé 100.59 €, prix d’arrêt fixe 96.90 € — seulement si D-026 est déjà fermée
- Heure limite : 2026-10-09 22:00 (rappel seulement)

**D-028c — Risquée (pas maintenant : une risquée déjà ouverte = D-026)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75,877.80 € (+2 %) avant 73,646.10 € (−1 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — une seule risquée à la fois (D-026 ouverte) ; prêt : achat de 0.00013443 BTC à 74,390.00 € (≈ 10 €) si cassure du haut du jour, prix visé 75,877.80 €, prix d’arrêt fixe 73,646.10 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

- Avis Research : pas demandé (décision évidente : le plan de la zone était de revoir la baisse si BTC remonte ici ; le retour près du haut du jour tue la baisse BTC et confirme D-023).
- Pourquoi : plan écrit de Z-BTC-74166 appliqué. Baisse BTC morte ; D-023 laisse courir. Les 3 propositions attendent de la place (prudente ETH d’abord, puis équilibrée SOL après D-026, puis risquée BTC si plus de risquée ouverte). Prix d’entrée de secours si rien ne passe : BTC 74 050 € (petit recul), idée à la hausse, visé 75 232 €, arrêt 73 379 €.

- 2026-10-09 16:23 PM-Predict — Pendant D-028, D-026 s’est fermée à l’arrêt SOL (stop_hit ~98,51 €, ≈ −0,11 €). Place libre passée à ≈ 15 €. Risquée D-028c débloquée (plus de risquée ouverte) ; prudente 25 € et équilibrée 20 € restent trop grandes sans réduction Risk.
- 2026-10-09 16:25 PM-Risk — D-026 fermé à l'arrêt (98,51 €, −0,11 €). D-028a prudente OUI réduite à 15 € (place libre) : vente ETH à 2 225,87 €, visé 2 181 €, arrêt 2 270 €, rappel 22h00. D-028b NON (pas de place). D-028c risquée NON : BTC déjà engagé par D-023 et plus de place après la prudente. Engagé ~50/50 €.


### 2026-10-09 16:35 | SOL-EUR + ETH-EUR | D-029 — Sonnette Z-SOL-98.60 (3 propositions)
Prix au moment de la décision (relevé 16:32) : BTC 74,287.20 € · ETH 2,230.08 € · SOL 98.63 €.
Haut/bas du jour (ticks) : BTC 74 389–72 709 · ETH 2 239–2 201 · SOL 99,31–96,93.
Place libre : ≈ 0,02 € sur 50 € (ouverts : D-023 BTC 24,98 € · D-024b ETH 10 € · D-028a ETH 15 € = 49,98 €). Réel interdit.
Avis Research : pas demandé — plan de zone clair (revoir D-024a / D-025b après rebond SOL à 98,60 €).

**Verdict zone Z-SOL-98.60 :** SOL est repassé au-dessus de 98,60 € (98,63 €). **D-024a** (achat SOL) est **déjà fermée** (idée morte à 15h43, −0,20 €) — on ne la rouvre pas telle quelle ; on propose une **nouvelle** idée à la hausse sur SOL. **D-025b** (vente ETH) reste le fil à suivre : D-024b et D-028a sont déjà ouvertes sur ETH ; on propose une équilibrée ETH pour quand il y a de la place.

**Ouverts (pas d’idée morte) :**
- D-023 BTC hausse : encore vivante (+0,2 %, loin de l’arrêt 73 379 €). Rappel 17h00 pas encore passé.
- D-024b ETH baisse : encore vivante (prix un peu avec nous). Rappel 17h00 pas encore passé.
- D-028a ETH baisse : un peu contre nous (−0,2 %) ; rappel 22h00 pas passé → on laisse courir.

**D-029a — Prudente (pas de place maintenant ; prioritaire dès qu’une place se libère)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100,60 € (+2 %) avant 96,66 € (−2 %), d’ici 22h00 CEST. Confiance moyenne (~60 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : achat de 0,2535 SOL à 98,63 € (≈ 25 €), prix visé 100,60 €, prix d’arrêt fixe 96,66 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt 2 %, gain ≥ 1× la perte)

**D-029b — Équilibrée (pas de place maintenant)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2 179,90 € (−2,25 %) avant 2 263,53 € (+1,5 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0,00897 ETH à 2 230,08 € (≈ 20 €), rachat visé 2 179,90 €, prix d’arrêt fixe 2 263,53 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte)

**D-029c — Risquée (pas de place maintenant ; aucune risquée ouverte)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100,60 € (+2 %) avant 97,64 € (−1 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : achat de 0,1014 SOL à 98,63 € (≈ 10 €), prix visé 100,60 €, prix d’arrêt fixe 97,64 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte ; 1 seule risquée à la fois)

- Pourquoi : plan écrit de Z-SOL-98.60 appliqué. Rebond SOL → nouvelle hausse SOL (suite de D-024a fermée) ; fil D-025b = vente ETH. Place quasi nulle → Risk garde d’abord la prudente, puis l’équilibrée, puis la risquée dès qu’une simu se ferme. Prix d’entrée de secours : SOL achat à 98,20 € (petit recul), visé 100,60 €, arrêt 96,66 € (zone sous 97,65 € aussi posée).

- 2026-10-09 16h36 PM-Predict — Sonnette Z-ETH-2232 (ETH au-dessus de 2 232 €) : **déjà traité dans D-029**. Pas de nouvelle décision. Zone Z-ETH-2232 désactivée ; nouvelle zone Z-ETH-2235 (au-dessus) posée. Place toujours pleine (~50/50 €).


### 2026-10-09 17:07 | SOL-EUR + ETH-EUR | D-030 — Sonnette mouvement >0,5 % depuis D-029 (3 propositions)
Prix au moment de la décision (relevé 17:07) : BTC 74,082.49 € · ETH 2,223.35 € · SOL 98.055 €.
Haut/bas du jour (ticks) : BTC 74,389–72,709 · ETH 2,239–2,201 · SOL 99.31–96.92.
Place libre : ≈ 0,02 € sur 50 € (ouverts : D-023 BTC 24,98 € · D-024b ETH 10 € · D-028a ETH 15 € = 49,98 €). Réel interdit.
Mouvement depuis D-029 : SOL 98,84 € → 98,07 € (−0,8 %). Les propositions D-029 (valables 30 min) ont expiré à 17h05.
Avis Research : pas demandé — SOL a perdu 0,8 % depuis D-029, la hausse SOL de D-029 est morte ; on suit la baisse.

**Ouverts / rappels :**
- **D-023** BTC hausse : rappel 17h00 **passé**, prix un peu **contre nous** (74 082 € < entrée 74 120 €) → **idée morte**. Risk peut fermer pour libérer ~25 €.
- **D-024b** ETH baisse : rappel 17h00 passé, prix **avec nous** (2 223 € < entrée 2 233 €) → idée encore vivante (laisser jusqu’à arrêt/visé).
- **D-028a** ETH baisse : rappel 22h00 pas passé, prix avec nous → laisser courir.

**D-030a — Prudente (pas de place maintenant ; prioritaire dès qu’une place se libère, surtout si D-023 fermée)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 96.50 € (−1.59 %) avant 99.61 € (+1.59 %), d’ici 22h00 CEST. Confiance moyenne (~60 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.254959 SOL à 98.055 € (≈ 25 €), rachat visé 96.50 €, prix d’arrêt fixe 99.61 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Avis Research : décidé seul — baisse SOL claire (−0,8 % depuis D-029).
- Pourquoi : le réveil mouvement sur SOL casse l’idée à la hausse de D-029 ; on suit la baisse vers le bas du jour (~96,93 €). Gain = perte possible, arrêt ~1,6 % ≤ 2 %.

**D-030b — Équilibrée (pas de place maintenant)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2,173.32 € (−2,25 %) avant 2,256.70 € (+1,5 %), d’ici 22h00 CEST. Confiance moyenne (~60 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.008995 ETH à 2,223.35 € (≈ 20 €), rachat visé 2,173.32 €, prix d’arrêt fixe 2,256.70 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte)
- Avis Research : décidé seul — brief 14h44 déjà baissier sur ETH ; D-024b/D-028a vont avec nous.
- Pourquoi : ETH reste le plus fragile ; on prolonge la baisse déjà ouverte. Gain 1,5× la perte (2,25 % vs 1,5 %).

**D-030c — Risquée (pas de place ; aucune risquée ouverte)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 96.09 € (−2 %) avant 99.04 € (+1 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.101984 SOL à 98.055 € (≈ 10 €), rachat visé 96.09 €, prix d’arrêt fixe 99.04 € ; 1 seule risquée à la fois (aucune ouverte)
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte)
- Avis Research : décidé seul — même mouvement SOL.
- Pourquoi : même sens que la prudente, arrêt plus serré (1 %) et gain 2× ; seulement après la prudente si place.

Valables jusqu’à **17:37** (30 min). Passé ce délai, Risk n’ouvre rien et me prévient.
- 2026-10-09 17:09 PM-Predict — D-030, ventes de SOL : avant mon prix d'entrée (98,06 € à 17h05), SOL avait déjà baissé de 0,8 % depuis son plus haut de 16h34 (98,84 €). C'est noté pour la piste « vendre après une baisse déjà faite » que Compound vérifie.
- 2026-10-09 17h10 PM-Risk : D-023 BTC hausse fermée en simu (idée morte selon Predict, prix contre), vente 73 927,97 €, résultat −0,08 €. D-030 non ouverte : SOL déjà à 97,76 €, à ce prix la prudente gagne moins que ce qu'elle risque et l'arrêt de la risquée dépasse 1 % ; l'équilibrée dépassait déjà ses limites (arrêt 1,53 %, gain 1,47× la perte). 25 € libres.

### 2026-10-09 17:10 | BTC-EUR + SOL-EUR | D-031 — 3 PROPOSITIONS (demande de Risk : 25 € libérés par D-023)
Prix (17:09) : BTC 73 956 € · ETH 2 220 € · SOL 97,89 €. Ouverts : D-024b et D-028a (deux ventes d'ETH, 25 €). Je n'ajoute pas d'ETH, pour ne pas mettre tout le plafond sur la même idée. Valables jusqu'à 17h40.

**D-031a — Prudente**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 74 843 € (+1,2 %) avant 73 069 € (−1,2 %), d'ici 22h00 CEST.
- Décision : SIMULER — achat de 0,000203 BTC à 73 956 € (≈ 15 €), prix visé 74 843 €, prix d'arrêt fixe 73 069 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

**D-031b — Équilibrée**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 96,32 € (−1,6 %) avant 98,87 € (+1,0 %), d'ici 22h00 CEST.
- Décision : SIMULER — vente de 0,102 SOL à 97,89 € (≈ 10 €), rachat visé 96,32 €, prix d'arrêt fixe 98,87 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Baisse déjà faite avant l'entrée : −0,96 % depuis le plus haut de 16h34 (98,84 €).

**D-031c — Risquée (n'entre pas après a + b)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75 435 € (+2,0 %) avant 73 217 € (−1,0 %), d'ici 22h00 CEST.
- Décision : SIMULER seulement s'il reste de la place — achat de 0,000135 BTC à 73 956 € (≈ 10 €), visé 75 435 €, arrêt 73 217 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)

- Avis Research : pas demandé, parce que c'est une relance de prix sans nouvelle info (brief de 15h05 toujours valable).
- Pourquoi : un achat de BTC équilibre les deux ventes d'ETH déjà ouvertes, puisque si tout le marché remonte, l'un compense les autres. SOL reste le plus faible des trois. La taille des deux simus fait 25 €, soit la place libre.
- 2026-10-09 17h11 PM-Risk : D-031a (prudente) achat BTC 15 € à 73 981,11 €, visé 74 843, arrêt resserré à 73 120 (au lieu de 73 069) pour garder un gain au moins égal à la perte au prix réel ; D-031b (équilibrée) vente SOL 10 € à 97,93 €, visé 96,32, arrêt 98,87. Rappel 22h. Place 50/50 €. Risquée non ouverte (plus de place).

- 2026-10-09 17:40 PM-Predict — Renumérotation finale (demande de Quentin) : D-025 = 15h39 (rappel 22h00, valable) ; D-026 = 15h36 (ventes de SOL, risquée lancée, valable) ; D-027 = ancienne D-026 de 15h38 (ventes BTC, annulée) ; D-032 = ancienne D-025 de 15h40 (rappels 17h/20h, annulée). Dorénavant : numéro = plus grand numéro du carnet + 1.

- 2026-10-09 18:16 PM-Predict — Revue D-024b (rappel 17h passé) : ETH 2 231 € contre entrée 2 232,70 € → à peine avec nous, pas contre nous → idée pas morte, on laisse jusqu'à l'arrêt 2 255 € ou le visé 2 197 €. Les +3 % en 24 h datent d'avant nos ventes ; depuis 15h ETH est plat (2 212–2 234). D-028a (arrêt 2 270 €) inchangée.


### 2026-10-09 18:21 | BTC-EUR + ETH-EUR | D-033 — Sonnette mouvement >0,5 % ETH depuis D-031 (3 propositions)
Prix au moment de la décision (relevé 18:21) : BTC 74,093.67 € · ETH 2,231.07 € · SOL 98.26 €.
Haut/bas du jour (ticks) : BTC 74,389–72,709 · ETH 2,239–2,201 · SOL 99.31–96.92.
Place libre : ≈ 0 € sur 50 € (ouverts : D-024b ETH 10 € · D-028a ETH 15 € · D-031a BTC 15 € · D-031b SOL 10 € = 50 €). Réel interdit.
Mouvement depuis D-031 : ETH 2 220,50 € → 2 231,63 € (+0,5 %). Les propositions D-031 ouvertes restent ; on en prépare 3 nouvelles pour quand une place se libère.
Avis Research : pas demandé — rebond ETH clair (+0,5 % vers le haut du jour) ; le brief 14h44 reste baissier sur ETH, on ne coupe pas tant que les arrêts tiennent.

**Ouverts / rappels :**
- **D-024b** ETH baisse : rappel 17h00 **passé**, prix encore **légèrement avec nous** (2,231 € < entrée 2 232,70 €) → idée **pas morte**, laisser jusqu’à arrêt 2 255 € / visé 2 197 €.
- **D-028a** ETH baisse : rappel 22h00 pas passé, prix un peu **contre** (2,231 € > entrée 2 225,87 €) → laisser courir (arrêt 2 270 €).
- **D-031a** BTC hausse : rappel 22h00, prix **avec nous** (74,094 € > entrée 73 981 €) → laisser.
- **D-031b** SOL baisse : rappel 22h00, prix **contre** (98.26 € > entrée 97,93 €, arrêt 98,87 € proche) → Risk surveille l’arrêt.

**D-033a — Prudente (pas de place maintenant ; prioritaire dès qu’une place se libère)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75,205 € (+1.50 %) avant 72,982 € (−1.50 %), d’ici 22h00 CEST. Confiance moyenne (~60 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : achat de 0.000337 BTC à 74,093.67 € (≈ 25 €), prix visé 75,205 €, prix d’arrêt fixe 72,982 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Prix visé vs plus haut du jour : +1.10 % au-dessus du haut (74,389 €)
- Avis Research : décidé seul — ETH rebondit, BTC suit un peu au-dessus de l’entrée D-031a.
- Pourquoi : le mouvement ETH est un rebond vers le haut du jour ; on renforce l’idée BTC déjà ouverte plutôt que d’ajouter de l’ETH (déjà 25 € de ventes). Gain = perte possible, arrêt 1,5 % ≤ 2 %.

**D-033b — Équilibrée (pas de place maintenant)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2 180,00 € (−2,29 %) avant 2 264,00 € (+1,48 %), d’ici 22h00 CEST. Confiance moyenne (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.008964 ETH à 2,231.07 € (≈ 20 €), rachat visé 2 180,00 €, prix d’arrêt fixe 2 264,00 € (corrigé 18h22 à la demande de Risk : arrêt 1,48 %, gain 1,55× la perte)
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte)
- Avant l’entrée : ETH a **monté** de 0,5 % depuis la référence D-031 (2 220,50 €) — on vend après un rebond, pas après une baisse. À 0.34 % sous le plus haut du jour (2,239 €). Prix visé à -0.93 % du plus bas du jour (2,201 €).
- Avis Research : décidé seul — brief 14h44 baissier sur ETH ; D-024b/D-028a encore ouvertes.
- Pourquoi : si le rebond échoue sous le haut du jour (~2 239 €), on prolonge la baisse. Gain 1,5× la perte (2,25 % vs 1,5 %). Pas de sens contraire sur ETH.

**D-033c — Risquée (pas de place ; aucune risquée ouverte)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75,576 € (+2.00 %) avant 73,353 € (−1.00 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : achat de 0.000135 BTC à 74,093.67 € (≈ 10 €), prix visé 75,576 €, prix d’arrêt fixe 73,353 € ; 1 seule risquée à la fois (aucune ouverte)
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte)
- Prix visé vs plus haut du jour : +1.60 % au-dessus du haut (74,389 €)
- Avis Research : décidé seul — même sens que la prudente, arrêt plus serré.
- Pourquoi : même idée BTC, arrêt 1 % et gain 2× ; seulement après la prudente si place.

Valables jusqu’à **18:51** (30 min). Passé ce délai, Risk n’ouvre rien et me prévient.


### 2026-10-09 19:25 | ETH-EUR + SOL-EUR | D-034 — Sonnette mouvement >0,5 % ETH depuis D-033 (3 propositions)
Prix au moment de la décision (relevé 19:25) : BTC 73,698.51 € · ETH 2,216.70 € · SOL 97.71 €.
Haut/bas du jour (ticks) : BTC 74,389–72,709 · ETH 2,239–2,201 · SOL 99.31–96.92.
Place libre : ≈ 0 € sur 50 € (ouverts : D-024b ETH 10 € · D-028a ETH 15 € · D-031a BTC 15 € · D-031b SOL 10 € = 50 €). Réel interdit (soir, hors 15h–17h).
Mouvement depuis D-033 : ETH 2 228,76 € → 2 217,23 € (−0,52 %) ; au relevé 2 216,70 € (−0,64 % vs entrée D-033 2 231,07 €).
Avis Research : pas demandé — baisse ETH claire (−0,5 %) ; brief 14h44 déjà baissier sur ETH.

**Ouverts / rappels :**
- **D-024b** ETH baisse : rappel 17h00 **passé**, prix **avec nous** (2 217 € < entrée 2 232,70 €) → idée **pas morte**, laisser jusqu’à arrêt 2 255 € / visé 2 197 €.
- **D-028a** ETH baisse : rappel 22h00 pas passé, prix **avec nous** (2 217 € < entrée 2 225,87 €) → laisser.
- **D-031a** BTC hausse : rappel 22h00, prix un peu **contre** (73 699 € < entrée 73 981 €) → laisser (rappel pas passé).
- **D-031b** SOL baisse : rappel 22h00, prix **avec nous** (97,71 € < entrée 97,93 €) → laisser.

**D-034a — Prudente (pas de place maintenant ; prioritaire dès qu’une place se libère)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2,176.80 € (−1,80 %) avant 2,256.60 € (+1,80 %), d’ici 22h00 CEST. Confiance moyenne (~60 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.011278 ETH à 2,216.70 € (≈ 25 €), rachat visé 2,176.80 €, prix d’arrêt fixe 2,256.60 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Avant l’entrée : ETH a **déjà baissé** de 0,64 % depuis l’entrée D-033 (2 231,07 €) et de 0,98 % depuis le plus haut du jour (2 238,65 €).
- Prix visé vs plus bas du jour : -1.11 % par rapport au bas (2 201 €).
- Avis Research : décidé seul — mouvement ETH baissier clair (−0,5 %).
- Pourquoi : on suit la baisse ETH déjà en cours (D-024b/D-028a avec nous). Gain = perte possible, arrêt 1,8 % ≤ 2 %.

**D-034b — Équilibrée (pas de place maintenant)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 95.51 € (−2,25 %) avant 99.18 € (+1,50 %), d’ici 22h00 CEST. Confiance moyenne (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.204687 SOL à 97.71 € (≈ 20 €), rachat visé 95.51 €, prix d’arrêt fixe 99.18 €
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte)
- Avant l’entrée : SOL a **déjà baissé** de 1,61 % depuis le plus haut du jour (99,31 €).
- Prix visé vs plus bas du jour : -1.46 % par rapport au bas (96,93 €).
- Avis Research : décidé seul — même biais baissier ; D-031b déjà ouverte dans ce sens.
- Pourquoi : SOL suit souvent ETH ; on prolonge la baisse. Gain 1,5× la perte (2,25 % vs 1,5 %). Pas de sens contraire sur SOL.

**D-034c — Risquée (pas de place ; aucune risquée ouverte)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2,172.37 € (−2,00 %) avant 2,238.87 € (+1,00 %), d’ici 22h00 CEST. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.004511 ETH à 2,216.70 € (≈ 10 €), rachat visé 2,172.37 €, prix d’arrêt fixe 2,238.87 € ; 1 seule risquée à la fois (aucune ouverte)
- Heure limite : 2026-10-09 22:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte)
- Avant l’entrée : même baisse ETH déjà faite (−0,64 % depuis D-033).
- Prix visé vs plus bas du jour : -1.31 % par rapport au bas (2 201 €).
- Avis Research : décidé seul — même sens que la prudente, arrêt plus serré.
- Pourquoi : même idée ETH, arrêt 1 % et gain 2× ; seulement après la prudente si place. Pas de proposition contraire sur ETH.

Valables jusqu’à **19:55** (30 min). Passé ce délai, Risk n’ouvre rien et me prévient.

### 2026-10-09 21h39 | D-035 — Sonnette mouvement SOL (−0,51 % depuis D-034)

**Déclencheur :** mouvement > 0,5 % SOL 97,75 € → 97,25 € (−0,51 %), 6e réveil mouvement du jour. Prix (21:37) : BTC 73,550.05 € · ETH 2,213.91 € · SOL 97.24 €.
Haut/bas du jour : BTC 74,389/73,242 · ETH 2,239/2,212 · SOL 99.31/97.24.
Place libre : ≈ 0 € sur 50 € (ouverts : D-024b ETH 10 € · D-028a ETH 15 € · D-031a BTC 15 € · D-031b SOL 10 € = 50 €). Réel interdit (soir, hors 15h–17h).

Avis Research : pas demandé — baisse SOL claire (−0,5 %, au plus bas du jour) ; D-031b déjà avec nous.

**Ouverts / rappels :**
- **D-024b** ETH baisse : rappel 17h00 **passé**, prix **avec nous** (2,214 € < entrée 2 232,70 €) → idée **pas morte**, laisser jusqu’à arrêt 2 255 € / visé 2 197 €.
- **D-028a** ETH baisse : rappel 22h00, prix **avec nous** (2,214 € < entrée 2 225,87 €) → laisser.
- **D-031a** BTC hausse : rappel 22h00, prix **contre** (73,550 € < entrée 73 981 €) → laisser (rappel pas passé).
- **D-031b** SOL baisse : rappel 22h00, prix **avec nous** (97.24 € < entrée 97,93 €) → laisser.

**D-035a — Prudente (pas de place maintenant ; prioritaire dès qu’une place se libère)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 95.30 € (−2,00 %) avant 99.18 € (+2,00 %), d’ici 10h00 CEST le 10/10. Confiance moyenne (~60 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.257096 SOL à 97.24 € (≈ 25 €), rachat visé 95.30 €, prix d’arrêt fixe 99.18 €
- Heure limite : 2026-10-10 10:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Avant l’entrée : SOL a **déjà baissé** de 0.52 % depuis D-034 (97,75 €) et de 2.08 % depuis le plus haut du jour (99.31 €).
- Prix visé vs plus bas du jour : -2.00 % par rapport au bas (97.24 €).
- Avis Research : décidé seul — mouvement SOL baissier clair (−0,5 %), au plus bas du jour.
- Pourquoi : on prolonge la baisse SOL déjà ouverte (D-031b avec nous). Gain = perte possible, arrêt 2 %.

**D-035b — Équilibrée (pas de place maintenant)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2164.10 € (−2,25 %) avant 2247.12 € (+1,50 %), d’ici 10h00 CEST le 10/10. Confiance moyenne (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.009034 ETH à 2213.91 € (≈ 20 €), rachat visé 2164.10 €, prix d’arrêt fixe 2247.12 €
- Heure limite : 2026-10-10 10:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte)
- Avant l’entrée : ETH a **déjà baissé** de 1.10 % depuis le plus haut du jour (2,239 €).
- Prix visé vs plus bas du jour : -2.18 % par rapport au bas (2,212 €).
- Avis Research : décidé seul — même biais baissier ; D-024b/D-028a déjà ouvertes dans ce sens.
- Pourquoi : ETH reste faible près du bas du jour. Gain 1,5× la perte. Pas de sens contraire sur ETH.

**D-035c — Risquée (pas de place ; aucune risquée ouverte)**
- Idée : à la baisse (on vend des pièces qu’on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 95.30 € (−2,00 %) avant 98.21 € (+1,00 %), d’ici 10h00 CEST le 10/10. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.102838 SOL à 97.24 € (≈ 10 €), rachat visé 95.30 €, prix d’arrêt fixe 98.21 € ; 1 seule risquée à la fois (aucune ouverte)
- Heure limite : 2026-10-10 10:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte)
- Avant l’entrée : même baisse SOL déjà faite (−0.52 % depuis D-034).
- Prix visé vs plus bas du jour : -2.00 % par rapport au bas (97.24 €).
- Avis Research : décidé seul — même sens que la prudente, arrêt plus serré.
- Pourquoi : même idée SOL, arrêt 1 % et gain 2× ; seulement après la prudente si place. Pas de proposition contraire sur SOL.

Valables jusqu’à **22:09** (30 min). Passé ce délai, Risk n’ouvre rien et me prévient.

### 2026-10-10 00h03 | D-036 — Sonnette heure_limite D-024b ETH

**Déclencheur :** heure limite passée pour D-024b (ETH idée à la baisse, trade rx-paper-2026-10-09T130833Z-8d63c1ab, rappel 17h00 le 9/10). Prix au ring ~2 217,77 € ; au relevé 00:02 : BTC 73,603.15 € · ETH 2,215.045 € · SOL 97.04 €.
Haut/bas séance 9 oct (ticks) : BTC 74,389–72,709 · ETH 2,239–2,201 · SOL 99.31–96.80.
Place libre : ≈ 0 € sur 50 € (ouverts : D-024b ETH 10 € · D-028a ETH 15 € · D-031a BTC 15 € · D-031b SOL 10 € = 50 €). Réel interdit (nuit).

Avis Research : pas demandé — décision évidente d’après le prix vs entrée/arrêt.

**Verdict D-024b pour @PM-Risk (dans les 5 min) : GARDER.**
- Idée à la baisse / Sens Vente ; entrée 2 232,70 € · arrêt 2 255 € · visé 2 197 €.
- Heure rappel 17h00 **passée**, mais prix **avec nous** (2,215.05 € < 2 232,70 €, ≈ +0,8 % latent) → idée **pas morte**. Laisser jusqu’à l’arrêt 2 255 € ou le visé 2 197 €.

**Autres ouverts :**
- **D-028a** ETH baisse : rappel 22h00 passé, prix **avec nous** (2,215.05 € < 2 225,87 €) → **garder**.
- **D-031a** BTC hausse : rappel 22h00 **passé**, prix **contre nous** (73,603 € < entrée 73 981 €) → **idée morte** — Risk peut fermer pour libérer ~15 €.
- **D-031b** SOL baisse : rappel 22h00 passé, prix **avec nous** (97.04 € < 97,93 €) → **garder**.

**D-036a — Prudente (pas de place maintenant ; prioritaire dès qu’une place se libère, surtout si D-031a fermée)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : SOL touche 95.10 € (−2,00 %) avant 98.98 € (+2,00 %), d’ici 10h00 CEST le 10/10. Confiance moyenne (~60 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.257626 SOL à 97.04 € (≈ 25 €), rachat visé 95.10 €, prix d’arrêt fixe 98.98 €
- Heure limite : 2026-10-10 10:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Avant l’entrée : SOL a **déjà baissé** de 2.29 % depuis le plus haut du jour (99.31 €).
- Prix visé vs plus bas du jour : -1.76 % par rapport au bas (96.80 €).
- Avis Research : décidé seul — heure limite claire ; biais baisse intact (D-031b avec nous).
- Pourquoi : on prolonge la baisse SOL déjà ouverte. Gain = perte possible, arrêt 2 %.

**D-036b — Équilibrée (pas de place maintenant)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : ETH touche 2165.21 € (−2,25 %) avant 2248.27 € (+1,50 %), d’ici 10h00 CEST le 10/10. Confiance moyenne (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.009029 ETH à 2215.05 € (≈ 20 €), rachat visé 2165.21 €, prix d’arrêt fixe 2248.27 €
- Heure limite : 2026-10-10 10:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte)
- Avant l’entrée : ETH a **déjà baissé** de 1.05 % depuis le plus haut du jour (2,239 €).
- Prix visé vs plus bas du jour : -1.64 % par rapport au bas (2,201 €).
- Avis Research : décidé seul — même biais ; D-024b/D-028a déjà ouvertes dans ce sens.
- Pourquoi : ETH reste sous l’entrée des ventes ouvertes. Gain 1,5× la perte. Pas de sens contraire sur ETH.

**D-036c — Risquée (pas de place ; aucune risquée ouverte)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : SOL touche 95.10 € (−2,00 %) avant 98.01 € (+1,00 %), d’ici 10h00 CEST le 10/10. Confiance faible (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.10305 SOL à 97.04 € (≈ 10 €), rachat visé 95.10 €, prix d’arrêt fixe 98.01 € ; 1 seule risquée à la fois (aucune ouverte)
- Heure limite : 2026-10-10 10:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte)
- Avant l’entrée : même baisse SOL déjà faite (−2.29 % depuis le haut).
- Prix visé vs plus bas du jour : -1.76 % par rapport au bas (96.80 €).
- Avis Research : décidé seul — même sens que la prudente, arrêt plus serré.
- Pourquoi : même idée SOL, arrêt 1 % et gain 2× ; seulement après la prudente si place. Pas de proposition contraire sur SOL.

Valables jusqu’à **00:33** (30 min). Passé ce délai, Risk n’ouvre rien et me prévient.

Prix d’entrée de secours si trop tard : SOL vente à 96,75 € (zone sous), visé 94,82 €, arrêt 98,69 €.

```json
{"suivi": "D-036", "heure": "2026-10-10T00:06:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "revue des ouverts : D-024b gardée ; D-031a fermée (idée morte) à 73 586,39 €, résultat −0,09 €"}
{"suivi": "D-036", "proposition": "a", "heure": "2026-10-10T00:06:40+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "vente SOL 13,40 € (0,1382 SOL, tout le SOL simulé disponible) à 96,96 €, visé 95,10, arrêt resserré à 98,82 (au lieu de 98,98) pour garder un gain au moins égal à la perte au prix réel ; rappel 10h00"}
{"suivi": "D-036", "proposition": "b", "heure": "2026-10-10T00:06:40+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place (1,60 € libres)"}
{"suivi": "D-036", "proposition": "c", "heure": "2026-10-10T00:06:40+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place (1,60 € libres)"}
```


### 2026-10-10 00:33 | SOL-EUR + ETH-EUR | D-037 — Rebond SOL +0,6 % : 3 propositions baisse (plafond plein)

```json
{"id":"D-037","heure":"2026-10-10T00:33:00+02:00","paires":["SOL-EUR","ETH-EUR"],"declencheur":{"type":"sonnette_mouvement","detail":"SOL +0,6 % depuis D-036 (96,95 → 97,53)"},"resume":"Rebond SOL +0,6 % : 3 propositions baisse (plafond plein)","type":"propositions","prix_releves":{"heure":"00:33","BTC-EUR":73721.35,"ETH-EUR":2222.22,"SOL-EUR":97.585},"place_libre_eur":1.6,"reel_permis":false,"reel_raison":"week-end + aucune sorte n'a passé le test du passé","avis_research":"pas demandé : rebond de prix sans nouvelle info (brief 15h05 toujours le dernier)","pourquoi":"SOL a rebondi de 0,6 % depuis D-036 alors que D-031b et D-036a sont encore ouvertes à la baisse : le rebond offre une meilleure entrée pour prolonger la baisse. ETH reste sous les entrées des ventes ouvertes. Place libre ≈ 1,60 € : propositions prêtes dès qu'une place se libère (prudente d'abord).","ouverts_revus":[{"id":"D-024b","verdict":"vivante","texte":"ETH vente ; rappel 17h passé ; prix avec nous (2 222 < 2 232,70) → garder"},{"id":"D-028a","verdict":"vivante","texte":"ETH vente ; rappel 22h passé ; prix avec nous → garder"},{"id":"D-031b","verdict":"vivante","texte":"SOL vente ; rappel 22h passé ; prix avec nous (97,59 < 97,93) → garder"},{"id":"D-036a","verdict":"vivante","texte":"SOL vente ; rappel 10h pas encore ; prix un peu contre (97,59 > 96,96) mais sous l'arrêt 98,82 → garder"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"SOL-EUR","idee":"à la baisse","sens":"vente","montant_eur":25.0,"quantite":0.2562,"prix_entree":97.58,"prix_vise":95.63,"prix_arret":99.53,"heure_limite":"2026-10-10T12:00:00+02:00","prevision":"SOL touche 95.63 € (−2,00 %) avant 99.53 € (+2,00 %), d'ici 12h00","confiance":{"mot":"moyenne","pct":58},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"baisse déjà faite avant l'entrée : -1.74 % depuis le plus haut (99,31 €) ; visé vs plus bas : -1.21 % (96,80 €) ; prioritaire dès place"},{"lettre":"b","niveau":"équilibrée","paire":"ETH-EUR","idee":"à la baisse","sens":"vente","montant_eur":20.0,"quantite":0.009,"prix_entree":2222.22,"prix_vise":2172.22,"prix_arret":2255.55,"heure_limite":"2026-10-10T12:00:00+02:00","prevision":"ETH touche 2172.22 € (−2,25 %) avant 2255.55 € (+1,50 %), d'ici 12h00","confiance":{"mot":"moyenne","pct":55},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"baisse déjà faite avant l'entrée : -0.73 % depuis le plus haut (2 238,65 €) ; visé vs plus bas : -1.32 % (2 201 €)"},{"lettre":"c","niveau":"risquée","paire":"SOL-EUR","idee":"à la baisse","sens":"vente","montant_eur":10.0,"quantite":0.10248,"prix_entree":97.58,"prix_vise":95.63,"prix_arret":98.56,"heure_limite":"2026-10-10T12:00:00+02:00","prevision":"SOL touche 95.63 € (−2,00 %) avant 98.56 € (+1,00 %), d'ici 12h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"même sens que la prudente, arrêt 1 % ; aucune risquée ouverte ; baisse avant entrée -1.74 % ; visé vs bas -1.21 %"}],"valable_jusqua":"01:03","statut":"active"}
```

**Déclencheur :** sonnette mouvement SOL +0,6 % depuis D-036 (96,95 → 97,53 €). Prix au relevé 00:33 : BTC 73,721.35 € · ETH 2,222.22 € · SOL 97.585 €.
Haut/bas : séance 9 oct BTC 74 389–72 709 · ETH 2 239–2 201 · SOL 99,31–96,80 ; nuit 10 oct (début) BTC 73,721–73,568 · ETH 2222–2213 · SOL 97,59–96,91.
Place libre : ≈ 1,60 € sur 50 € (ouverts : D-024b 10 € · D-028a 15 € · D-031b 10 € · D-036a 13,40 € = 48,40 €). Réel interdit (week-end).

Avis Research : pas demandé — rebond sans nouvelle info.

**Ouverts :**
- **D-024b** ETH : vivante (prix avec nous) → garder
- **D-028a** ETH : vivante → garder
- **D-031b** SOL : vivante → garder
- **D-036a** SOL : vivante (un peu contre mais sous l'arrêt) → garder

**D-037a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : SOL touche 95.63 € (−2,00 %) avant 99.53 € (+2,00 %), d'ici 12h00 CEST le 10/10. Confiance moyenne (~58 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.2562 SOL à 97.58 € (≈ 25 €), rachat visé 95.63 €, prix d'arrêt fixe 99.53 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Avant l'entrée : SOL a **déjà baissé** de -1.74 % depuis le plus haut (99,31 €).
- Prix visé vs plus bas du jour : -1.21 % par rapport au bas (96,80 €).
- Avis Research : décidé seul — rebond SOL offre une meilleure entrée pour prolonger D-031b/D-036a.
- Pourquoi : on vend le rebond. Gain = perte possible, arrêt 2 %.

**D-037b — Équilibrée (pas de place)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : ETH touche 2172.22 € (−2,25 %) avant 2255.55 € (+1,50 %), d'ici 12h00 CEST le 10/10. Confiance moyenne (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.009 ETH à 2222.22 € (≈ 20 €), rachat visé 2172.22 €, prix d'arrêt fixe 2255.55 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte)
- Avant l'entrée : ETH a **déjà baissé** de -0.73 % depuis le plus haut (2 238,65 €).
- Prix visé vs plus bas du jour : -1.32 % par rapport au bas (2 201 €).
- Avis Research : décidé seul — D-024b/D-028a déjà ouvertes dans ce sens.
- Pourquoi : ETH sous les entrées des ventes. Gain 1,5× la perte. Pas de sens contraire sur ETH.

**D-037c — Risquée (pas de place ; aucune risquée ouverte)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : SOL touche 95.63 € (−2,00 %) avant 98.56 € (+1,00 %), d'ici 12h00 CEST le 10/10. Confiance faible (~52 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.10248 SOL à 97.58 € (≈ 10 €), rachat visé 95.63 €, prix d'arrêt fixe 98.56 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte)
- Avant l'entrée : même baisse SOL déjà faite (-1.74 % depuis le haut).
- Prix visé vs plus bas du jour : -1.21 % par rapport au bas (96,80 €).
- Avis Research : décidé seul — même sens que la prudente, arrêt plus serré.
- Pourquoi : même idée SOL, arrêt 1 % et gain 2× ; seulement après la prudente si place.

Valables jusqu'à **01:03** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : SOL vente à 96,90 € (zone sous), visé 95,00 €, arrêt 98,84 €.

```json
{"suivi": "D-037", "proposition": "c", "heure": "2026-10-10T00:38:00+02:00", "par": "PM-Predict", "statut": "en_attente_de_place", "texte": "arrêt corrigé à 98,55 € (au lieu de 98,56) à la demande de Risk : 0,99 % et gain 2,01× la perte ; mais plus de SOL simulé à vendre tant que D-031b et D-036a sont ouvertes"}
{"suivi": "D-037", "proposition": "a", "heure": "2026-10-10T00:38:00+02:00", "par": "PM-Predict", "statut": "en_attente_de_place", "texte": "pas ouvrable tant que D-031b et D-036a sont ouvertes (plus de SOL simulé à vendre) ; l'équilibrée ETH passe en premier"}
```

### 2026-10-10 02:06 | ETH-EUR | D-038 — ETH casse 2219,6 € : 3 ventes ETH (plafond plein)

```json
{"id":"D-038","heure":"2026-10-10T02:06:48+02:00","paires":["ETH-EUR"],"declencheur":{"type":"sonnette_zone","detail":"Z-ETH-2219.6 ETH sous 2219,6 € (2219,49 €)"},"resume":"ETH casse 2219,6 € : 3 ventes ETH (plafond plein, pas de SOL)","type":"propositions","prix_releves":{"heure":"02:04","BTC-EUR":73710.3,"ETH-EUR":2219.13,"SOL-EUR":97.245},"place_libre_eur":1.6,"reel_permis":false,"reel_raison":"aucune sorte n'a passé le test du passé ; week-end hors 15h–17h","avis_research":"pas demandé : cassage de zone évident, prolonge D-024b/D-028a vers le visé","pourquoi":"ETH vient de passer sous 2 219,60 €. Les ventes D-024b et D-028a restent vivantes (prix vers le visé). Pas de SOL à vendre tant que D-031b et D-036a sont ouvertes. Place libre 1,60 € : propositions en attente. Pas de sens contraire sur ETH.","ouverts_revus":[{"id":"D-024b","verdict":"vivante","texte":"vente ETH ; rappel passé mais prix vers 2 197 € (maintenant 2 219 €) — idée pas morte"},{"id":"D-028a","verdict":"vivante","texte":"vente ETH ; rappel passé mais prix vers 2 181 € — idée pas morte"},{"id":"D-031b","verdict":"vivante","texte":"vente SOL ; rappel passé, prix 97,25 € vers 96,32 € — idée pas morte"},{"id":"D-036a","verdict":"vivante","texte":"vente SOL ; rappel 10h00 ; prix un peu au-dessus de l'entrée (96,96) mais loin de l'arrêt — idée pas morte"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"ETH-EUR","idee":"à la baisse","sens":"vente","montant_eur":20,"quantite":0.009013,"prix_entree":2219.13,"prix_vise":2175.86,"prix_arret":2262.4,"heure_limite":"2026-10-10T12:00:00+02:00","prevision":"ETH touche 2175.86 € (−1.95 %) avant 2262.4 € (+1.95 %), d'ici 12h00","confiance":{"mot":"moyenne","pct":58},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"baisse déjà faite avant l'entrée : -0.18 % depuis le plus haut du jour (2223.03 €) ; visé -1.68 % vs bas du jour (2213.005 €) ; inventaire ETH ~21 €"},{"lettre":"b","niveau":"équilibrée","paire":"ETH-EUR","idee":"à la baisse","sens":"vente","montant_eur":20,"quantite":0.009013,"prix_entree":2219.13,"prix_vise":2170.86,"prix_arret":2251.31,"heure_limite":"2026-10-10T12:00:00+02:00","prevision":"ETH touche 2170.86 € (−2.18 %) avant 2251.31 € (+1.45 %), d'ici 12h00","confiance":{"mot":"moyenne","pct":55},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"même sens que D-024b/D-028a ; visé -1.9 % vs bas du jour ; après la prudente si place + pièces"},{"lettre":"c","niveau":"risquée","paire":"ETH-EUR","idee":"à la baisse","sens":"vente","montant_eur":10,"quantite":0.004506,"prix_entree":2219.13,"prix_vise":2176.97,"prix_arret":2240.21,"heure_limite":"2026-10-10T12:00:00+02:00","prevision":"ETH touche 2176.97 € (−1.90 %) avant 2240.21 € (+0.95 %), d'ici 12h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"aucune risquée ouverte ; arrêt 0,95 % ; visé -1.63 % vs bas du jour"}],"valable_jusqua":"02:36","statut":"active"}
```

- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH continue sous 2 219,60 € vers ~2 176 € avant de remonter vers l'arrêt, d'ici 12h00. Confiance moyenne (~58 % sur la prudente).
- Décision : NE PAS SIMULER maintenant — plafond plein (1,60 € libres) ; prêt dès place + pièces ETH. Pas de vente SOL (D-031b/D-036a ouvertes).
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Avis Research : pas demandé — cassage de zone évident, prolonge les ventes ETH ouvertes.
- Pourquoi : la zone Z-ETH-2219.6 a sonné ; D-024b/D-028a restent vivantes ; on propose 3 ventes ETH, pas de sens contraire.

**D-038a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : ETH touche 2175.86 € (−1.95 %) avant 2262.4 € (+1.95 %), d'ici 12h00 CEST le 10/10. Confiance moyenne (~58 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.009013 ETH à 2219.13 € (≈ 20 €), rachat visé 2175.86 €, prix d'arrêt fixe 2262.4 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Avant l'entrée : ETH a **déjà baissé** de -0.18 % depuis le plus haut du jour (2223.03 €).
- Prix visé vs plus bas du jour : -1.68 % par rapport au bas (2213.005 €).
- Avis Research : décidé seul — cassage sous 2 219,60 €.
- Pourquoi : on vend la cassure. Gain = perte possible, arrêt ~1,95 %.

**D-038b — Équilibrée (pas de place)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : ETH touche 2170.86 € (−2.18 %) avant 2251.31 € (+1.45 %), d'ici 12h00 CEST le 10/10. Confiance moyenne (~55 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.009013 ETH à 2219.13 € (≈ 20 €), rachat visé 2170.86 €, prix d'arrêt fixe 2251.31 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt 1,5 %, gain ≥ 1,5× la perte)
- Avant l'entrée : même baisse ETH déjà faite (-0.18 % depuis le haut du jour).
- Prix visé vs plus bas du jour : -1.9 % par rapport au bas (2213.005 €).
- Avis Research : décidé seul — même sens que D-024b/D-028a.
- Pourquoi : gain 1,5× la perte. Pas de sens contraire sur ETH.

**D-038c — Risquée (pas de place ; aucune risquée ouverte)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : ETH touche 2176.97 € (−1.90 %) avant 2240.21 € (+0.95 %), d'ici 12h00 CEST le 10/10. Confiance faible (~52 %).
- Décision : NE PAS SIMULER maintenant — plafond plein ; prêt : vente de 0.004506 ETH à 2219.13 € (≈ 10 €), rachat visé 2176.97 €, prix d'arrêt fixe 2240.21 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt 1 %, gain ≥ 2× la perte)
- Avant l'entrée : même baisse ETH déjà faite (-0.18 % depuis le haut du jour).
- Prix visé vs plus bas du jour : -1.63 % par rapport au bas (2213.005 €).
- Avis Research : décidé seul — même idée, arrêt plus serré.
- Pourquoi : arrêt 0,95 % et gain 2× ; seulement après la prudente si place.

Valables jusqu'à **02:36** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : ETH vente à 2 212,50 € (zone sous), visé 2 170 €, arrêt 2 252 €.

### 2026-10-10 02:55 | ETH-EUR | D-039 — SOL +0,5 % : 3 ventes ETH (plafond plein)

```json
{"id":"D-039","heure":"2026-10-10T02:55:00+02:00","paires":["ETH-EUR"],"declencheur":{"type":"sonnette_mouvement","detail":"SOL +0,50 % depuis D-038 (97,25 → 97,75 €)"},"resume":"SOL +0,5 % : 3 ventes ETH (plafond plein, pas de SOL)","type":"propositions","prix_releves":{"heure":"02:55","BTC-EUR":73711.7,"ETH-EUR":2222.88,"SOL-EUR":97.74},"place_libre_eur":1.6,"reel_permis":false,"reel_raison":"aucune sorte n'a passé le test du passé ; week-end hors 15h–17h","avis_research":"pas demandé : rebond SOL de 0,5 % évident, prolonge les ventes ETH ouvertes","pourquoi":"SOL a rebondi de +0,5 % depuis D-038 et touche le haut du jour (97,75 €). Les ventes D-024b/D-028a restent vivantes (ETH encore sous les entrées). D-031b/D-036a SOL : rappel passé ou proche, prix un peu contre sur D-036a mais loin de l'arrêt — idées pas mortes. Pas de SOL à vendre. Place libre 1,60 € : propositions en attente. Pas de sens contraire sur ETH.","ouverts_revus":[{"id":"D-024b","verdict":"vivante","texte":"vente ETH ; rappel passé ; prix 2222.88 € vers 2197 € — idée pas morte"},{"id":"D-028a","verdict":"vivante","texte":"vente ETH ; rappel passé ; prix vers 2181 € — idée pas morte"},{"id":"D-031b","verdict":"vivante","texte":"vente SOL entrée 97,93 ; prix 97.74 € vers 96,32 ; arrêt 98,87 — idée pas morte"},{"id":"D-036a","verdict":"vivante","texte":"vente SOL entrée 96,96 ; prix un peu contre (97.74) mais loin de l'arrêt 98,82 ; rappel 10h00 — idée pas morte"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"ETH-EUR","idee":"à la baisse","sens":"vente","montant_eur":20,"quantite":0.008997,"prix_entree":2222.88,"prix_vise":2179.53,"prix_arret":2266.22,"heure_limite":"2026-10-10T12:00:00+02:00","confiance":{"mot":"moyenne","pct":56},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"baisse déjà faite avant l'entrée : -0.01 % depuis le plus haut du jour (2223.06 €) ; visé -1.51 % vs bas du jour (2213.005 €) ; pas de SOL à vendre (D-031b/D-036a)","prevision":"ETH touche 2179.53 € (-1.95 %) avant 2266.22 € (1.95 %), d'ici 12h00"},{"lettre":"b","niveau":"équilibrée","paire":"ETH-EUR","idee":"à la baisse","sens":"vente","montant_eur":20,"quantite":0.008997,"prix_entree":2222.88,"prix_vise":2174.53,"prix_arret":2255.11,"heure_limite":"2026-10-10T12:00:00+02:00","confiance":{"mot":"moyenne","pct":55},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"baisse déjà faite avant l'entrée : -0.01 % depuis le plus haut du jour (2223.06 €) ; visé -1.74 % vs bas du jour (2213.005 €) ; pas de SOL à vendre (D-031b/D-036a)","prevision":"ETH touche 2174.53 € (-2.17 %) avant 2255.11 € (1.45 %), d'ici 12h00"},{"lettre":"c","niveau":"risquée","paire":"ETH-EUR","idee":"à la baisse","sens":"vente","montant_eur":10,"quantite":0.004499,"prix_entree":2222.88,"prix_vise":2180.64,"prix_arret":2243.99,"heure_limite":"2026-10-10T12:00:00+02:00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"baisse déjà faite avant l'entrée : -0.01 % depuis le plus haut du jour (2223.06 €) ; visé -1.46 % vs bas du jour (2213.005 €) ; pas de SOL à vendre (D-031b/D-036a)","prevision":"ETH touche 2180.64 € (-1.90 %) avant 2243.99 € (0.95 %), d'ici 12h00"}],"valable_jusqua":"03:25","statut":"active"}
```

- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH reste sous pression vers ~2179.53 € avant l'arrêt, d'ici 12h00. Confiance moyenne (~56 % sur la prudente).
- Décision : simuler si place (en attente de place) — plafond plein (1,60 € libres) ; prêt dès place + pièces ETH. Pas de vente SOL (D-031b/D-036a ouvertes).
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Avis Research : pas demandé — rebond SOL de 0,5 %, on prolonge les ventes ETH.
- Pourquoi : SOL a touché le haut du jour ; D-024b/D-028a restent vivantes ; on propose 3 ventes ETH, pas de sens contraire.

**D-039a — Prudente (pas de place; ; prioritaire dès place)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : ETH touche 2179.53 € (-1.95 %) avant 2266.22 € (1.95 %), d'ici 12h00. Confiance moyenne (~56 %).
- Décision : simuler si place (en attente de place) — prêt : vente de 0.008997 ETH à 2222.88 € (≈ 20 €), rachat visé 2179.53 €, prix d'arrêt fixe 2266.22 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : prudente
- Avant l'entrée : ETH a **déjà baissé** de -0.01 % depuis le plus haut du jour (2223.06 €).
- Prix visé vs plus bas du jour : -1.51 % par rapport au bas (2213.005 €).
- Avis Research : décidé seul — rebond SOL, on garde le biais baisse ETH.
- Pourquoi : baisse déjà faite avant l'entrée : -0.01 % depuis le plus haut du jour (2223.06 €) ; visé -1.51 % vs bas du jour (2213.005 €) ; pas de SOL à vendre (D-031b/D-036a).

**D-039b — Équilibrée (pas de place)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : ETH touche 2174.53 € (-2.17 %) avant 2255.11 € (1.45 %), d'ici 12h00. Confiance moyenne (~55 %).
- Décision : simuler si place (en attente de place) — prêt : vente de 0.008997 ETH à 2222.88 € (≈ 20 €), rachat visé 2174.53 €, prix d'arrêt fixe 2255.11 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : équilibrée
- Avant l'entrée : ETH a **déjà baissé** de -0.01 % depuis le plus haut du jour (2223.06 €).
- Prix visé vs plus bas du jour : -1.74 % par rapport au bas (2213.005 €).
- Avis Research : décidé seul — rebond SOL, on garde le biais baisse ETH.
- Pourquoi : baisse déjà faite avant l'entrée : -0.01 % depuis le plus haut du jour (2223.06 €) ; visé -1.74 % vs bas du jour (2213.005 €) ; pas de SOL à vendre (D-031b/D-036a).

**D-039c — Risquée (pas de place; ; aucune risquée ouverte)**
- Idée : à la baisse
- Sens : Vente
- Prévision mesurable : ETH touche 2180.64 € (-1.90 %) avant 2243.99 € (0.95 %), d'ici 12h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : vente de 0.004499 ETH à 2222.88 € (≈ 10 €), rachat visé 2180.64 €, prix d'arrêt fixe 2243.99 €
- Heure limite : 2026-10-10 12:00 (rappel seulement)
- Niveau : risquée
- Avant l'entrée : ETH a **déjà baissé** de -0.01 % depuis le plus haut du jour (2223.06 €).
- Prix visé vs plus bas du jour : -1.46 % par rapport au bas (2213.005 €).
- Avis Research : décidé seul — rebond SOL, on garde le biais baisse ETH.
- Pourquoi : baisse déjà faite avant l'entrée : -0.01 % depuis le plus haut du jour (2223.06 €) ; visé -1.46 % vs bas du jour (2213.005 €) ; pas de SOL à vendre (D-031b/D-036a).

Valables jusqu'à **03:25** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : ETH vente à 2216.21 € (zone sous), visé 2179.53 €, arrêt 2255.11 €.

### 2026-10-10 07:59 | BTC-EUR + SOL-EUR | D-040 — SOL casse 98,03 € : rebond — 3 achats (plafond plein)

```json
{"id":"D-040","heure":"2026-10-10T07:59:00+02:00","paires":["BTC-EUR","SOL-EUR"],"declencheur":{"type":"sonnette_zone","detail":"Z-SOL-98.03 SOL au-dessus 98,03 € (98,32 €)"},"resume":"SOL casse 98,03 € : rebond — 3 achats (plafond plein, pas de vente SOL)","type":"propositions","prix_releves":{"heure":"07:59","BTC-EUR":73946.79,"ETH-EUR":2229.97,"SOL-EUR":98.34},"place_libre_eur":1.6,"reel_permis":false,"reel_raison":"aucune sorte n'a passé le test du passé ; samedi hors 15h–17h","avis_research":"pas demandé : cassure 98,03 € = rebond fort évident (raison de la zone)","pourquoi":"SOL a passé 98,03 € (98,32 €) : rebond fort. On revoit les shorts SOL : D-031b idée morte (rappel passé + prix contre). D-036a encore vivante mais sous pression (près de l'arrêt 98,82, rappel 10h00). Pas de SOL à vendre. Place libre 1,60 €. On propose 3 achats dans le sens du rebond (BTC et SOL), pas de vente SOL.","ouverts_revus":[{"id":"D-024b","verdict":"vivante","texte":"vente ETH ; prix 2229,97 € encore sous l'entrée 2232,7 — idée pas morte mais sous pression (haut du jour)"},{"id":"D-028a","verdict":"vivante","texte":"vente ETH ; prix un peu contre l'entrée 2225,87 — sous pression (haut du jour), idée pas morte"},{"id":"D-031b","verdict":"morte","texte":"vente SOL ; rappel 22h passé + prix 98,34 € contre (entrée 97,93, vers arrêt 98,87) après cassure 98,03 — Risk peut fermer"},{"id":"D-036a","verdict":"vivante","texte":"vente SOL ; rappel 10h00 ; prix 98,34 contre entrée 96,96, près de l'arrêt 98,82 — sous pression, pas encore morte"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"BTC-EUR","idee":"à la hausse","sens":"achat","montant_eur":25,"quantite":0.000338,"prix_entree":73946.79,"prix_vise":75426.0,"prix_arret":72468.0,"heure_limite":"2026-10-10T16:00:00+02:00","prevision":"BTC touche 75426.0 € (+2,00 %) avant 72468.0 € (−2,00 %), d'ici 16h00","confiance":{"mot":"moyenne","pct":58},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"rebond marché (BTC haut du jour) ; visé +2.00 % vs haut du jour (73946.79 €) ; prioritaire dès place"},{"lettre":"b","niveau":"équilibrée","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":20,"quantite":0.203376,"prix_entree":98.34,"prix_vise":100.55,"prix_arret":96.87,"heure_limite":"2026-10-10T16:00:00+02:00","prevision":"SOL touche 100.55 € (+2,25 %) avant 96.87 € (−1,50 %), d'ici 16h00","confiance":{"mot":"moyenne","pct":56},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"cassure 98,03 € ; déjà monté +1.48 % depuis le bas du jour (96.905 €) ; visé +2.25 % vs haut (98.34 €) ; pas de vente SOL (inventaire / D-036a)"},{"lettre":"c","niveau":"risquée","paire":"BTC-EUR","idee":"à la hausse","sens":"achat","montant_eur":10,"quantite":0.000135,"prix_entree":73946.79,"prix_vise":75426.0,"prix_arret":73208.0,"heure_limite":"2026-10-10T16:00:00+02:00","prevision":"BTC touche 75426.0 € (+2,00 %) avant 73208.0 € (−1,00 %), d'ici 16h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"aucune risquée ouverte ; arrêt 0,999 % ; visé +2.00 % vs haut du jour ; après la prudente si place"}],"valable_jusqua":"08:29","statut":"active"}
```

- Idée : à la hausse (on achète, puis on revend plus haut)
- Sens : Achat
- Prévision mesurable : BTC et SOL continuent le rebond après la cassure SOL 98,03 €, vers les visés avant les arrêts, d'ici 16h00. Confiance moyenne (~58 % sur la prudente).
- Décision : simuler si place (en attente de place) — plafond plein (1,60 € libres) ; prêt dès place. Pas de vente SOL (D-036a ouverte + inventaire ~0). D-031b idée morte → Risk peut fermer (~10 €).
- Heure limite : 2026-10-10 16:00 (rappel seulement)
- Avis Research : pas demandé — cassure 98,03 € = rebond fort évident (raison de la zone).
- Pourquoi : SOL au-dessus de 98,03 € ; on suit le rebond avec 3 achats ; on ne vend pas de SOL.

**D-040a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75426.0 € (+2,00 %) avant 72468.0 € (−2,00 %), d'ici 16h00. Confiance moyenne (~58 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.000338 BTC à 73946.79 € (≈ 25 €), visé 75426.0 €, arrêt 72468.0 €
- Heure limite : 2026-10-10 16:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Prix visé vs plus haut du jour : +2.00 % par rapport au haut (73946.79 €).
- Avis Research : décidé seul — rebond après cassure SOL.
- Pourquoi : BTC au haut du jour avec SOL/ETH ; gain = perte possible, arrêt 2 %.

**D-040b — Équilibrée (pas de place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100.55 € (+2,25 %) avant 96.87 € (−1,50 %), d'ici 16h00. Confiance moyenne (~56 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.203376 SOL à 98.34 € (≈ 20 €), visé 100.55 €, arrêt 96.87 €
- Heure limite : 2026-10-10 16:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt ≤1,5 %, gain ≥ 1,5× la perte)
- Déjà monté : +1.48 % depuis le bas du jour (96.905 €).
- Prix visé vs plus haut du jour : +2.25 % par rapport au haut (98.34 €).
- Avis Research : décidé seul — cassure 98,03 €.
- Pourquoi : on achète la cassure. Gain 1,5× la perte. Pas de vente SOL.

**D-040c — Risquée (pas de place ; aucune risquée ouverte)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75426.0 € (+2,00 %) avant 73208.0 € (−1,00 %), d'ici 16h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.000135 BTC à 73946.79 € (≈ 10 €), visé 75426.0 €, arrêt 73208.0 €
- Heure limite : 2026-10-10 16:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt ≤1 %, gain ≥ 2× la perte)
- Prix visé vs plus haut du jour : +2.00 % par rapport au haut (73946.79 €).
- Avis Research : décidé seul — même rebond BTC, arrêt plus serré.
- Pourquoi : arrêt ~1 % et gain 2× ; seulement après la prudente si place.

Valables jusqu'à **08:29** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : BTC achat à 73725 € (zone sous), visé 75426.0 €, arrêt 72468.0 €.

```json
{"suivi": "D-040", "heure": "2026-10-10T08:05:00+02:00", "par": "PM-Risk", "statut": "fermée", "texte": "revue des ouverts : D-031b fermée (idée morte) à 98,19 €, −0,04 € ; D-036a fermée (idée morte) à 98,19 €, −0,18 €"}
{"suivi": "D-040", "proposition": "a", "heure": "2026-10-10T08:05:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "achat BTC 25 € à 73 917,97 €, visé 75 426, arrêt 72 468, rappel 16h00"}
{"suivi": "D-040", "proposition": "b", "heure": "2026-10-10T08:05:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place après la prudente (50/50 €)"}
{"suivi": "D-040", "proposition": "c", "heure": "2026-10-10T08:05:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place après la prudente (50/50 €)"}
```

### 2026-10-09 20:45 | Bilan Compound — scores + test du passé (soir)

**Scores Predict (ticks 30 s, premier seuil)** — horizons 22h laissés ouverts :
- **perdu** : D-023 (idée morte, aucun seuil), D-024a (idée morte / fin contre), D-024c (arrêt 15h36, non ouverte), D-026 risquée (arrêt 16h22), D-028c (arrêt 20h32, non ouverte), D-029c (arrêt 20h35, non ouverte) ; D-021 déjà perdu le matin
- **annulé** : D-024b (17h, aucun seuil, fin dans le sens — trade encore ouvert), D-027×3, D-032×3, D-002, D-003
- **en attente (22h)** : D-025a/b/c, D-026a/b, D-028a/b, D-029a/b, D-030a/b/c, D-031a/b/c, D-033a/b/c, D-034a/b/c
- Totaux scorecard : **3 gagnés / 8 perdus / 17 annulés** (taux 27 %)

**Research 14h44/15h05** (horizon 17h) : R-BTC **perdu**, R-ETH **annulé**, R-SOL **perdu** (Predict a basculé SOL en baisse après 15h36).

**Risk** : refus D-024c et D-028c **utiles** (arrêts auraient touché). 

**Scan** : SOL −1,2 % en 15h–17h vu via alertes arrêts ; pas de gros trou dans le créneau.

**Simu du jour** : fermés D-021 −0,13 · D-024a −0,20 · D-026 −0,11 · D-023 −0,08 = **−0,52 €** ; ouverts D-024b 10 € · D-028a 15 € · D-031a 15 € · D-031b 10 € (50/50 €). **Live 0.**
Essais (ouverts+fermés, hors rétro) : hausse ~3 (D-023, D-024a, D-031a) ; baisse ~5 (D-021, D-024b, D-026, D-028a, D-031b) — loin de ~20/sorte. Créneau 15h–17h : **au moins une simu** (ok). Nuits sans décision sous plafond : **0** (nuit 8→9 = D-021).

**Vitesse sonnettes-trade** (routine_runs + journaux) :
- Predict : toutes ≤ ~3,5 min (ok)
- Risk : Z-SOL-97.9 **+5,6 min** ⚠️ (>5) ; Z-BTC-74166 **~5,0 min** ⚠️ limite ; autres ok
- Rien de « je fais X » laissé sans suite côté Predict/Risk sur les sonnettes du jour

**Test du passé — piste « sans prix visé + stop suiveur, sans sortie 22h »** (demandée 8–9 oct) :
- Tentative 9 oct ~20h45 : `backtest.sh` avec `--tp 0 --trail 1.5 --exit-hour -1 --max-bars 168` sur rebond/cassure ETH/SOL/BTC.
- **Échec source prix** : Binance `api.binance.com` répond **451** (geo-block) ; repli OKX ~2 mois seulement (pas 1 an / moitiés non jugables). **Aucun chiffre inventé.**
- **Réutilisation** des essais du 8 oct (`/workspace/compound_2026-10-08/trailing_stop/`, variante `trail1.5_noTP` / `fixed_noTP`) : **encore avec sortie 22h** (pas le vrai « sans 22h »).
  - Rebond ETH : ~19 trades, H2 négative → **ne passe pas**
  - Rebond BTC : 11 trades → **ne passe pas**
  - Rebond SOL `maker_touch` trail noTP : +5,98 %, 23 trades, H1/H2 >0 → proche, mais **robust / frais immédiats** à confirmer ; live déjà bloqué
  - Cassure : plusieurs cas maker positifs sur 2 moitiés, mais `maker_touch` / `taker` souvent H1 <0 → **ne passe pas** au critère équipe complet (surtout achat immédiat + touch)
- **Verdict Compound** : la piste sans prix visé + suiveur **ne débloque pas le réel** ce soir. Simulation toujours permise. **À refaire sans sortie 22h** dès que Binance (ou cache 1 an) est dispo — ne pas inventer les chiffres.

**Observations à surveiller** (pas des règles) : (a) acheter une crypto seule quand BTC/ETH/SOL baissent ensemble (D-024a) ; (b) cible nuit −1 % vs 1,5 %.

- 2026-10-10 00h04 PM-Predict — sonnette occupe (3× heure_limite D-028a/D-031a/D-031b + zone Z-SOL-96.95) : déjà traité dans D-036
- 2026-10-10 02h10 PM-Predict — sonnette zone Z-SOL-97.35 SOL au-dessus 97.35 : déjà traité dans D-038
- 2026-10-10 08h04 PM-Predict — sonnette occupe (mouvement SOL + zones Z-BTC-73933 / Z-ETH-2229.5) : déjà traité dans D-040

```json
{"suivi": "D-036", "proposition": "a", "heure": "2026-10-10T08:05:00+02:00", "par": "PM-Predict", "statut": "simulée", "texte": "idée morte : SOL à 98,19 € contre entrée 96,96 € (+1,27 % contre nous) et D-040 attend la hausse ; Risk peut fermer avant l'achat SOL de D-040b"}
```

### 2026-10-10 09:05 | SOL-EUR + BTC-EUR | D-041 — Passage 9h : rebond de nuit — 3 achats (plafond plein)

```json
{"id":"D-041","heure":"2026-10-10T09:05:00+02:00","paires":["SOL-EUR","BTC-EUR"],"declencheur":{"type":"nuit","detail":"Passage du matin 9h — nuit BTC +0,49 % · ETH +0,64 % · SOL +1,19 %"},"resume":"Passage 9h : rebond de nuit — 3 achats (plafond plein 0 € libre)","type":"propositions","prix_releves":{"heure":"09:05","BTC-EUR":73844.47,"ETH-EUR":2225.565,"SOL-EUR":98.03},"place_libre_eur":0,"reel_permis":false,"reel_raison":"aucune sorte n'a passé le test du passé ; samedi hors 15h–17h","avis_research":"brief d'hier 14h44 encore le plus récent (week-end) : SOL à la hausse, BTC à la hausse, ETH à la baisse — confiance faible ; pas de brief du jour","pourquoi":"Nuit en hausse (SOL le plus fort +1,19 %). D-040a BTC achat déjà ouvert 25 €. Les deux ventes ETH (D-024b, D-028a) restent vivantes (prix encore avec nous) mais rappels d'hier dépassés. Place libre 0 €. On propose 3 achats dans le sens du rebond (SOL et BTC), en attente de place. Pas de vente SOL (rebond).","ouverts_revus":[{"id":"D-024b","verdict":"vivante","texte":"vente ETH 10 € ; rappel 17h00 hier passé ; prix 2225,57 € encore sous l'entrée 2232,7 (−0,32 %) — idée pas morte ; Risk jette un œil"},{"id":"D-028a","verdict":"vivante","texte":"vente ETH 15 € ; rappel 22h00 hier passé ; prix ≈ entrée 2225,87 — idée pas morte ; Risk jette un œil"},{"id":"D-040a","verdict":"vivante","texte":"achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 16h00 ; prix 73844 (−0,10 %) — idée pas morte"},{"id":"D-031b","verdict":"morte","texte":"vente SOL déjà fermée par Risk (idée morte 06h04)"},{"id":"D-036a","verdict":"morte","texte":"vente SOL déjà fermée par Risk (idée morte 06h04)"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":25,"quantite":0.255024,"prix_entree":98.03,"prix_vise":99.99,"prix_arret":96.56,"heure_limite":"2026-10-10T16:00:00+02:00","prevision":"SOL touche 99.99 € (+2.00 %) avant 96.56 € (−1.50 %), d'ici 16h00","confiance":{"mot":"moyenne","pct":58},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"nuit SOL +1,19 % ; déjà +1.16 % depuis le bas du jour (96.905 €) ; prioritaire dès place"},{"lettre":"b","niveau":"équilibrée","paire":"BTC-EUR","idee":"à la hausse","sens":"achat","montant_eur":20,"quantite":0.000271,"prix_entree":73844.47,"prix_vise":75505.98,"prix_arret":72736.81,"heure_limite":"2026-10-10T16:00:00+02:00","prevision":"BTC touche 75505.98 € (+2.25 %) avant 72736.81 € (−1.50 %), d'ici 16h00","confiance":{"mot":"moyenne","pct":55},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"D-040a déjà ouvert 25 € BTC ; celle-ci seulement si place (après revue des ventes ETH) ; nuit BTC +0,49 %"},{"lettre":"c","niveau":"risquée","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":10,"quantite":0.10201,"prix_entree":98.03,"prix_vise":99.99,"prix_arret":97.05,"heure_limite":"2026-10-10T16:00:00+02:00","prevision":"SOL touche 99.99 € (+2.00 %) avant 97.05 € (−1.00 %), d'ici 16h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"aucune risquée ouverte ; arrêt ≤1 % ; après la prudente si place"}],"valable_jusqua":"09:35","statut":"active"}
```

- Idée : à la hausse (on achète, puis on revend plus haut)
- Sens : Achat
- Prévision mesurable : SOL et BTC continuent le rebond de nuit (SOL +1,19 %, BTC +0,49 %), vérifié à 16h00
- Décision : simuler si place (en attente de place)
- Heure limite : 16h00 le 10/10 (rappel seulement)
- Pourquoi : nuit en hausse, SOL le plus fort ; plafond plein (0 € libre) ; D-040a BTC déjà ouvert ; ventes ETH vivantes mais rappels d'hier dépassés


```json
{"suivi": "D-024", "proposition": "b", "heure": "2026-10-10T09:12:00+02:00", "par": "PM-Predict", "statut": "simulée", "texte": "rappel dépassé, idée vivante : ETH 2 225,36 € sous l'entrée 2 232,70 € ; nouveau rappel 2026-10-10 14:00 ; arrêt 2 255 € et visé 2 197 € inchangés"}
{"suivi": "D-028", "proposition": "a", "heure": "2026-10-10T09:12:00+02:00", "par": "PM-Predict", "statut": "simulée", "texte": "rappel dépassé, idée vivante : ETH 2 225,36 € juste sous l'entrée 2 225,87 € ; nouveau rappel 2026-10-10 14:00 ; arrêt 2 270 € et visé 2 181 € inchangés"}
```

```json
{"suivi": "D-041", "heure": "2026-10-10T09:35:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "expirée à 09h35 : plafond plein (50/50 €)"}
```

### 2026-10-10 18:12 | ETH-EUR + SOL-EUR + BTC-EUR | D-042 — ETH +0,7 % : ventes ETH mortes ; 3 achats rebond (plafond plein)

```json
{"id": "D-042", "heure": "2026-10-10T18:12:35+02:00", "paires": ["ETH-EUR", "SOL-EUR", "BTC-EUR"], "declencheur": {"type": "sonnette_mouvement", "detail": "ETH +0,67 % depuis D-041 (2224,96 → 2239,86)"}, "resume": "ETH +0,7 % : ventes ETH mortes ; 3 achats rebond (plafond plein)", "type": "propositions", "prix_releves": {"heure": "18:12", "BTC-EUR": 74081.29, "ETH-EUR": 2239.73, "SOL-EUR": 98.47}, "place_libre_eur": 0, "reel_permis": false, "reel_raison": "aucune sorte n'a passé le test du passé ; samedi hors 15h–17h", "avis_research": "pas demandé : mouvement de prix évident (ETH +0,7 %, les trois au haut du jour) ; brief week-end d'hier encore le plus récent", "pourquoi": "ETH a monté +0,7 % depuis D-041 et touche le haut du jour. Les deux ventes ETH (D-024b, D-028a) ont le rappel passé et le prix contre nous → idées mortes pour Risk. D-040a BTC reste vivante (prix avec nous). Place 0 € ; si Risk ferme les ventes (~25 €), on enchaîne 3 achats dans le sens du rebond.", "ouverts_revus": [{"id": "D-024b", "verdict": "morte", "texte": "vente ETH 10 € ; rappel 14h00 passé ; prix 2239.73 € contre entrée 2232,7 (+0.31 %) — idée morte ; Risk peut fermer"}, {"id": "D-028a", "verdict": "morte", "texte": "vente ETH 15 € ; rappel 14h00 passé ; prix 2239.73 € contre entrée 2225,87 (+0.62 %) — idée morte ; Risk peut fermer"}, {"id": "D-040a", "verdict": "vivante", "texte": "achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 16h00 passé ; prix 74081 (+0.22 %) — idée pas morte, on laisse courir"}], "propositions": [{"lettre": "a", "niveau": "prudente", "paire": "SOL-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 25, "quantite": 0.253884, "prix_entree": 98.47, "prix_vise": 100.44, "prix_arret": 96.99, "heure_limite": "2026-10-10T22:00:00+02:00", "prevision": "SOL touche 100.44 € (+2.00 %) avant 96.99 € (-1.50 %), d'ici 22h00", "confiance": {"mot": "moyenne", "pct": 58}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "déjà +1.61 % depuis le bas du jour (96.905 €) ; visé +2.00 % vs haut du jour ; prioritaire dès place (~25 € si ventes ETH fermées)"}, {"lettre": "b", "niveau": "équilibrée", "paire": "BTC-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 20, "quantite": 0.00027, "prix_entree": 74081.29, "prix_vise": 75748.12, "prix_arret": 72970.07, "heure_limite": "2026-10-10T22:00:00+02:00", "prevision": "BTC touche 75748.12 € (+2.25 %) avant 72970.07 € (-1.50 %), d'ici 22h00", "confiance": {"mot": "moyenne", "pct": 55}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "D-040a déjà ouvert 25 € BTC ; celle-ci seulement si place après fermeture ventes ETH ; visé +2.25 % vs haut du jour"}, {"lettre": "c", "niveau": "risquée", "paire": "ETH-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 10, "quantite": 0.004465, "prix_entree": 2239.73, "prix_vise": 2284.52, "prix_arret": 2217.33, "heure_limite": "2026-10-10T22:00:00+02:00", "prevision": "ETH touche 2284.52 € (+2.00 %) avant 2217.33 € (-1.00 %), d'ici 22h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "seulement après fermeture D-024b/D-028a (pas de sens contraire) ; déjà +1.21 % depuis le bas du jour ; aucune risquée ouverte ; arrêt ≤1 %"}], "valable_jusqua": "18:42", "statut": "active"}
```

- Idée : à la hausse (on achète, puis on revend plus haut)
- Sens : Achat
- Prévision mesurable : après ETH +0,7 % depuis D-041, le rebond continue ; SOL/BTC/ETH touchent leurs visés avant les arrêts, d'ici 22h00. Confiance moyenne (~58 % sur la prudente).
- Décision : simuler si place (en attente de place) — plafond plein (0 € libres) ; ~25 € se libèrent si Risk ferme D-024b et D-028a (idées mortes). D-040a BTC on laisse courir.
- Heure limite : 2026-10-10 22:00 (rappel seulement)
- Avis Research : pas demandé — mouvement ETH +0,7 % et hauts du jour évidents (brief week-end d'hier encore le plus récent).
- Pourquoi : le prix monte ; on coupe les ventes ETH mortes et on propose 3 achats dans le même sens.

**D-042a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100.44 € (+2.00 %) avant 96.99 € (-1.50 %), d'ici 22h00. Confiance moyenne (~58 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.253884 SOL à 98.47 € (≈ 25 €), visé 100.44 €, arrêt 96.99 €
- Heure limite : 2026-10-10 22:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Déjà monté : +1.61 % depuis le bas du jour (96.905 €).
- Prix visé vs plus haut du jour : +2.00 % par rapport au haut (98.47 €).
- Avis Research : décidé seul — rebond ETH/SOL.
- Pourquoi : SOL au haut du jour avec ETH ; gain > perte possible.

**D-042b — Équilibrée (pas de place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75748.12 € (+2.25 %) avant 72970.07 € (-1.50 %), d'ici 22h00. Confiance moyenne (~55 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.00027 BTC à 74081.29 € (≈ 20 €), visé 75748.12 €, arrêt 72970.07 €
- Heure limite : 2026-10-10 22:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt ≤1,5 %, gain ≥ 1,5× la perte)
- Prix visé vs plus haut du jour : +2.25 % par rapport au haut (74082.51 €).
- Avis Research : décidé seul — même rebond.
- Pourquoi : D-040a déjà ouvert ; celle-ci seulement s'il reste de la place. Gain 1,5× la perte.

**D-042c — Risquée (pas de place ; après fermeture ventes ETH)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : ETH touche 2284.52 € (+2.00 %) avant 2217.33 € (-1.00 %), d'ici 22h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.004465 ETH à 2239.73 € (≈ 10 €), visé 2284.52 €, arrêt 2217.33 €
- Heure limite : 2026-10-10 22:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt ≤1 %, gain ≥ 2× la perte)
- Déjà monté : +1.21 % depuis le bas du jour (2213.005 €).
- Prix visé vs plus haut du jour : +1.99 % par rapport au haut (2239.865 €).
- Avis Research : décidé seul — cassure haut ETH après ventes mortes.
- Pourquoi : arrêt ~1 % et gain 2× ; seulement après D-024b/D-028a fermées.

Valables jusqu'à **18:42** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : SOL achat à 98.17 € (zone sous), visé 100.44 €, arrêt 96.99 €.
```json
{"suivi": "D-042", "heure": "2026-10-10T18:14:00+02:00", "par": "PM-Risk", "statut": "fermée", "texte": "revue des ouverts : D-024b fermée (idée morte) à 2 240,07 €, −0,04 € ; D-028a fermée (idée morte) à 2 240,07 €, −0,11 €"}
{"suivi": "D-042", "proposition": "a", "heure": "2026-10-10T18:14:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "achat SOL 25 € à 98,475 €, visé 100,44, arrêt 96,99, rappel 22h00"}
{"suivi": "D-042", "proposition": "b", "heure": "2026-10-10T18:14:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place après la prudente (50/50 €)"}
{"suivi": "D-042", "proposition": "c", "heure": "2026-10-10T18:14:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place après la prudente (50/50 €)"}
```


```json
{"suivi": "D-040", "proposition": "a", "heure": "2026-10-10T18:37:00+02:00", "par": "PM-Predict", "statut": "simulée", "texte": "rappel 16h00 passé, idée vivante : BTC 74 123 € au-dessus de l'entrée 73 918 € ; nouveau rappel 2026-10-10 22:00 ; visé 75 426 € et arrêt 72 468 € inchangés"}
```


### 2026-10-11 07:35 | SOL-EUR + ETH-EUR + BTC-EUR | D-043 — SOL casse 98,17 € : D-042a morte ; 3 propositions si place

```json
{"id": "D-043", "heure": "2026-10-11T07:35:00+02:00", "paires": ["SOL-EUR", "ETH-EUR", "BTC-EUR"], "declencheur": {"type": "sonnette_zone", "detail": "Z-SOL-98.17 (SOL sous 98,17 € → 97,85 €)"}, "resume": "SOL casse 98,17 € : D-042a morte ; 3 propositions si place", "type": "propositions", "prix_releves": {"heure": "07:33", "BTC-EUR": 74141.39, "ETH-EUR": 2238.525, "SOL-EUR": 97.86}, "place_libre_eur": 0, "reel_permis": false, "reel_raison": "aucune sorte n'a passé le test du passé ; dimanche hors 15h–17h", "avis_research": "pas demandé : cassure de zone évidente (SOL sous 98,17 €) ; brief Research encore celui du 9 oct.", "pourquoi": "SOL a cassé la zone d'urgence 98,17 € (97,85 €). D-042a (achat SOL) a le rappel 22h00 passé et le prix contre (−0,63 %) → idée morte pour Risk. D-040a BTC reste vivante (+0,30 %) : nouveau rappel 14h00. Plafond plein (0 €) ; si Risk ferme D-042a (~25 €), on enchaîne la prudente ETH d'abord.", "ouverts_revus": [{"id": "D-040a", "verdict": "vivante", "texte": "achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 22h00 passé ; prix 74141 (+0,30 %) — idée pas morte ; nouveau rappel 14h00"}, {"id": "D-042a", "verdict": "morte", "texte": "achat SOL 25 € ; rappel 22h00 passé ; prix 97.86 € contre entrée 98,475 (−0,63 %) — idée morte ; Risk peut fermer"}], "propositions": [{"lettre": "a", "niveau": "prudente", "paire": "ETH-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 25, "quantite": 0.011168, "prix_entree": 2238.53, "prix_vise": 2283.3, "prix_arret": 2193.75, "heure_limite": "2026-10-11T14:00:00+02:00", "prevision": "ETH touche 2283.3 € (+2.00 %) avant 2193.75 € (−2.00 %), d'ici 14h00", "confiance": {"mot": "moyenne", "pct": 56}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "prioritaire dès place (~25 € si D-042a fermée) ; ETH tient près du haut hier (2240.89) ; visé +1.89 % vs haut hier"}, {"lettre": "b", "niveau": "équilibrée", "paire": "SOL-EUR", "idee": "à la baisse", "sens": "vente", "montant_eur": 20, "quantite": 0.204374, "prix_entree": 97.86, "prix_vise": 95.66, "prix_arret": 99.33, "heure_limite": "2026-10-11T14:00:00+02:00", "prevision": "SOL touche 95.66 € (−2,25 %) avant 99.33 € (+1,50 %), d'ici 14h00", "confiance": {"mot": "faible", "pct": 54}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "seulement après fermeture D-042a (pas de sens contraire) ; baisse déjà faite avant l'entrée : −0.74 % depuis haut hier 98.585 ; visé -1.28 % vs bas hier"}, {"lettre": "c", "niveau": "risquée", "paire": "BTC-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 10, "quantite": 0.000135, "prix_entree": 74141.39, "prix_vise": 75624.22, "prix_arret": 73399.98, "heure_limite": "2026-10-11T14:00:00+02:00", "prevision": "BTC touche 75624.22 € (+2,00 %) avant 73399.98 € (−1,00 %), d'ici 14h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "aucune risquée ouverte ; D-040a déjà 25 € BTC ; visé +1.99 % vs haut hier ; arrêt ≤1 %, gain 2×"}], "valable_jusqua": "08:05", "statut": "active"}
```

- Idée : à la hausse sur ETH/BTC ; à la baisse sur SOL (on vend des pièces qu'on a, puis on rachète plus bas) — après fermeture D-042a
- Sens : Achat (a, c) / Vente (b)
- Prévision mesurable : après cassure SOL 98,17 €, D-042a est morte ; ETH et BTC tiennent ; SOL peut encore baisser. Confiance moyenne (~56 % sur la prudente).
- Décision : simuler si place (en attente de place) — plafond plein (0 € libres) ; ~25 € se libèrent si Risk ferme D-042a (idée morte). D-040a BTC on laisse courir (nouveau rappel 14h00).
- Heure limite : 2026-10-11 14:00 (rappel seulement)
- Avis Research : pas demandé — cassure de zone SOL évidente (brief du 9 oct. encore le plus récent).
- Pourquoi : SOL casse le niveau d'urgence ; on coupe l'achat SOL mort et on propose ETH achat en priorité, puis vente SOL et petit achat BTC.

**D-043a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : ETH touche 2283.3 € (+2,00 %) avant 2193.75 € (−2,00 %), d'ici 14h00. Confiance moyenne (~56 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.011168 ETH à 2238.53 € (≈ 25 €), visé 2283.3 €, arrêt 2193.75 €
- Heure limite : 2026-10-11 14:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Prix visé vs plus haut du jour (hier) : +1.89 % par rapport au haut (2240.89 €).
- Avis Research : décidé seul — ETH tient pendant que SOL casse.
- Pourquoi : ETH plus solide que SOL ; gain = perte possible.

**D-043b — Équilibrée (pas de place ; après fermeture D-042a)**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 95.66 € (−2,25 %) avant 99.33 € (+1,50 %), d'ici 14h00. Confiance faible (~54 %).
- Décision : simuler si place (en attente de place) — prêt : vente de 0.204374 SOL à 97.86 € (≈ 20 €), visé 95.66 €, arrêt 99.33 €
- Heure limite : 2026-10-11 14:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt ≤1,5 %, gain ≥ 1,5× la perte)
- Baisse déjà faite avant l'entrée : −0.74 % depuis le haut hier (98.585 €).
- Prix visé vs plus bas du jour (hier) : -1.28 % par rapport au bas (96.905 €).
- Avis Research : décidé seul — cassure 98,17 €.
- Pourquoi : seulement après D-042a fermée ; gain 1,5× la perte.

**D-043c — Risquée (pas de place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75624.22 € (+2,00 %) avant 73399.98 € (−1,00 %), d'ici 14h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.000135 BTC à 74141.39 € (≈ 10 €), visé 75624.22 €, arrêt 73399.98 €
- Heure limite : 2026-10-11 14:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt ≤1 %, gain ≥ 2× la perte)
- Prix visé vs plus haut du jour (hier) : +1.99 % par rapport au haut (74151.28 €).
- Avis Research : décidé seul — BTC tient.
- Pourquoi : arrêt 1 % et gain 2× ; D-040a déjà ouverte.

Valables jusqu'à **08:05** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : ETH achat à 2231.81 € (zone sous), visé 2283.3 €, arrêt 2193.75 €.

```json
{"suivi": "D-040", "proposition": "a", "heure": "2026-10-11T07:35:00+02:00", "par": "PM-Predict", "statut": "simulée", "texte": "rappel 22h00 passé, idée vivante : BTC 74141 € au-dessus de l'entrée 73 918 € ; nouveau rappel 2026-10-11 14:00 ; visé 75 426 € et arrêt 72 468 € inchangés"}
```

```json
{"suivi": "D-042", "proposition": "a", "heure": "2026-10-11T07:35:00+02:00", "par": "PM-Predict", "statut": "simulée", "texte": "rappel 22h00 passé, idée morte : SOL 97.86 € sous l'entrée 98,475 € (−0,63 %) — Risk peut fermer ; arrêt 96,99 € et visé 100,44 € inchangés"}
```
- 07:36 PM-Predict — sonnette occupe (heure_limite D-040a×2, heure_limite D-042a, mouvement SOL -0,7 %): déjà traité dans D-043
```json
{"suivi": "D-043", "heure": "2026-10-11T07:37:00+02:00", "par": "PM-Risk", "statut": "fermée", "texte": "revue des ouverts : D-042a fermée (idée morte) à 97,75 €, −0,21 € ; D-040a gardée, rappel 14h00"}
{"suivi": "D-043", "proposition": "a", "heure": "2026-10-11T07:37:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "achat ETH 25 € à 2 237,49 €, visé 2 283,30, arrêt 2 193,75, rappel 14h00"}
{"suivi": "D-043", "proposition": "b", "heure": "2026-10-11T07:37:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place après la prudente ; règle d'essai SOL non applicable (plus haut bourse depuis 05h36 : 97,93 €, baisse < 1 %)"}
{"suivi": "D-043", "proposition": "c", "heure": "2026-10-11T07:37:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place après la prudente (50/50 €)"}
```



### 2026-10-11 09:04 | SOL-EUR + BTC-EUR + ETH-EUR | D-044 — Passage 9h : nuit calme — 3 achats (plafond plein)

```json
{"id": "D-044","heure": "2026-10-11T09:04:00+02:00","paires": ["SOL-EUR","BTC-EUR","ETH-EUR"],"declencheur": {"type": "nuit","detail": "Passage du matin 9h — nuit calme (trou ticks 19h→07h32) : BTC +0,24 % · ETH +0,11 % · SOL −0,05 % depuis fin 10/10"},"resume": "Passage 9h : nuit calme — 3 achats (plafond plein 0 € libre)","type": "propositions","prix_releves": {"heure": "09:04","BTC-EUR": 74266.22,"ETH-EUR": 2237.815,"SOL-EUR": 98.08},"place_libre_eur": 0,"reel_permis": false,"reel_raison": "aucune sorte n'a passé le test du passé ; dimanche hors 15h–17h","avis_research": "brief du 9 oct. 14h44 encore le plus récent (week-end) : SOL à la hausse, BTC à la hausse, ETH à la baisse — confiance faible ; pas de brief du jour","pourquoi": "Nuit calme (BTC un peu plus haut, SOL plat). D-040a BTC et D-043a ETH restent vivantes (rappels 14h00 pas encore passés). Place libre 0 €. On propose 3 achats (SOL et BTC) en attente de place. Pas de vente SOL (pas de chute >1 % sur 2 h).","ouverts_revus": [{"id": "D-040a","verdict": "vivante","texte": "achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 14h00 ; prix 74266 (+0.47 %) — idée pas morte ; on laisse le rappel 14h00"},{"id": "D-043a","verdict": "vivante","texte": "achat ETH 25 € ; entrée 2237,49, visé 2283,30, arrêt 2193,75, rappel 14h00 ; prix 2237.82 (+0.01 %) — idée pas morte ; on laisse le rappel 14h00"}],"propositions": [{"lettre": "a","niveau": "prudente","paire": "SOL-EUR","idee": "à la hausse","sens": "achat","montant_eur": 25,"quantite": 0.254894,"prix_entree": 98.08,"prix_vise": 100.04,"prix_arret": 96.12,"heure_limite": "2026-10-11T18:00:00+02:00","prevision": "SOL touche 100.04 € (+2,00 %) avant 96.12 € (−2,00 %), d'ici 18h00","confiance": {"mot": "moyenne","pct": 55},"decision": "simuler_si_place","statut": "en_attente_de_place","note": "prioritaire dès place ; bas matin 97,555 € ; déjà +0,54 % depuis ce bas ; visé +1,48 % vs haut hier 98,585"},{"lettre": "b","niveau": "équilibrée","paire": "BTC-EUR","idee": "à la hausse","sens": "achat","montant_eur": 20,"quantite": 0.000269,"prix_entree": 74266.22,"prix_vise": 75937.21,"prix_arret": 73152.23,"heure_limite": "2026-10-11T18:00:00+02:00","prevision": "BTC touche 75937.21 € (+2,25 %) avant 73152.23 € (−1,50 %), d'ici 18h00","confiance": {"mot": "faible","pct": 53},"decision": "simuler_si_place","statut": "en_attente_de_place","note": "D-040a déjà ouvert 25 € BTC ; seulement si place ; nuit BTC +0,24 % ; visé +2,41 % vs haut hier 74151"},{"lettre": "c","niveau": "risquée","paire": "SOL-EUR","idee": "à la hausse","sens": "achat","montant_eur": 10,"quantite": 0.101958,"prix_entree": 98.08,"prix_vise": 100.04,"prix_arret": 97.1,"heure_limite": "2026-10-11T18:00:00+02:00","prevision": "SOL touche 100.04 € (+2,00 %) avant 97.1 € (−1,00 %), d'ici 18h00","confiance": {"mot": "faible","pct": 52},"decision": "simuler_si_place","statut": "en_attente_de_place","note": "aucune risquée ouverte ; arrêt ≤1 %, gain 2× ; après la prudente si place"}],"valable_jusqua": "09:34","statut": "active"}
```

- Idée : à la hausse (on achète, puis on revend plus haut)
- Sens : Achat
- Prévision mesurable : SOL et BTC tiennent / continuent un peu après une nuit calme ; vérifié à 18h00
- Décision : simuler si place (en attente de place)
- Heure limite : 2026-10-11 18:00 (rappel seulement)
- Pourquoi : nuit calme (BTC +0,24 %, SOL plat) ; plafond plein (0 € libre) ; D-040a et D-043a vivantes (rappels 14h00) ; pas de vente SOL (pas de chute >1 % sur 2 h)
- Avis Research : brief du 9 oct. encore le plus récent (week-end)

**D-044a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100.04 € (+2,00 %) avant 96.12 € (−2,00 %), d'ici 18h00. Confiance moyenne (~55 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.254894 SOL à 98.08 € (≈ 25 €), visé 100.04 €, arrêt 96.12 €
- Heure limite : 2026-10-11 18:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Pourquoi : rebond depuis le bas matin 97,555 € ; gain = perte possible.

**D-044b — Équilibrée (pas de place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75937.21 € (+2,25 %) avant 73152.23 € (−1,50 %), d'ici 18h00. Confiance faible (~53 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.000269 BTC à 74266.22 € (≈ 20 €), visé 75937.21 €, arrêt 73152.23 €
- Heure limite : 2026-10-11 18:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt ≤1,5 %, gain ≥ 1,5× la perte)
- Pourquoi : D-040a déjà ouvert ; seulement si place ; gain 1,5× la perte.

**D-044c — Risquée (pas de place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 100.04 € (+2,00 %) avant 97.1 € (−1,00 %), d'ici 18h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.101958 SOL à 98.08 € (≈ 10 €), visé 100.04 €, arrêt 97.1 €
- Heure limite : 2026-10-11 18:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt ≤1 %, gain ≥ 2× la perte)
- Pourquoi : aucune risquée ouverte ; arrêt 1 % et gain 2×.

Valables jusqu'à **09:34** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : SOL achat à 97.79 € (zone sous), visé 100.04 €, arrêt 96.12 €.


{"suivi": "D-044", "proposition": "a", "heure": "2026-10-11T09:08:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "conforme à la prudente (25 €, arrêt 2,0 %, gain = perte) mais plafond plein 50/50 € ; rien ne se libère avant 09:34"}
{"suivi": "D-044", "proposition": "b", "heure": "2026-10-11T09:08:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "conforme à l'équilibrée (20 €, arrêt 1,50 %, gain 1,5×) mais plafond plein"}
{"suivi": "D-044", "proposition": "c", "heure": "2026-10-11T09:08:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "conforme à la risquée (10 €, arrêt 1,0 %, gain 2×) mais plafond plein"}

### 2026-10-11 11:03 | SOL-EUR + BTC-EUR + ETH-EUR | D-045 — SOL casse 97,79 € : D-044a caduque ; achat plus bas (plafond plein)

```json
{"id":"D-045","heure":"2026-10-11T11:03:00+02:00","paires":["SOL-EUR","BTC-EUR","ETH-EUR"],"declencheur":{"type":"sonnette_zone","detail":"Z-SOL-97.79 (SOL sous 97,79 € → 97,69 €)"},"resume":"SOL casse 97,79 € : D-044a caduque ; achat SOL plus bas + BTC (plafond plein)","type":"propositions","prix_releves":{"heure":"11:03","BTC-EUR":74092.51,"ETH-EUR":2232.525,"SOL-EUR":97.755},"place_libre_eur":0,"reel_permis":false,"reel_raison":"aucune sorte n'a passé le test du passé ; dimanche hors 15h–17h","avis_research":"pas demandé : cassure de zone évidente (SOL sous 97,79 €) ; brief Research encore celui du 9 oct.","pourquoi":"SOL a cassé la zone 97,79 € (plan D-044). L'entrée D-044a à 98,08 € est caduque : on propose un achat plus bas près du bas du jour (97,555 €). D-040a BTC et D-043a ETH restent vivantes (rappels 14h00 pas encore passés). Place 0 €. Pas de vente SOL (déjà près du bas du jour ; baisse 2 h seulement −0,33 %).","ouverts_revus":[{"id":"D-040a","verdict":"vivante","texte":"achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 14h00 ; prix 74093 (+0,24 %) — idée pas morte ; on laisse le rappel 14h00"},{"id":"D-043a","verdict":"vivante","texte":"achat ETH 25 € ; entrée 2237,49, visé 2283,30, arrêt 2193,75, rappel 14h00 ; prix 2232,53 (−0,22 %) — rappel pas passé ; idée pas morte ; on laisse le rappel 14h00"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":25,"quantite":0.255741,"prix_entree":97.755,"prix_vise":99.71,"prix_arret":95.8,"heure_limite":"2026-10-11T18:00:00+02:00","prevision":"SOL touche 99,71 € (+2,00 %) avant 95,80 € (−2,00 %), d'ici 18h00","confiance":{"mot":"moyenne","pct":55},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"D-044a entrée 98,08 caduque ; achat plus bas ; déjà +0,20 % depuis bas jour 97,555 ; visé +1,66 % vs haut jour 98,08 ; prioritaire dès place"},{"lettre":"b","niveau":"équilibrée","paire":"BTC-EUR","idee":"à la hausse","sens":"achat","montant_eur":20,"quantite":0.00027,"prix_entree":74092.51,"prix_vise":75759.59,"prix_arret":72981.12,"heure_limite":"2026-10-11T18:00:00+02:00","prevision":"BTC touche 75759,59 € (+2,25 %) avant 72981,12 € (−1,50 %), d'ici 18h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"D-040a déjà ouvert 25 € BTC ; seulement si place ; visé +2,01 % vs haut jour 74266"},{"lettre":"c","niveau":"risquée","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":10,"quantite":0.102297,"prix_entree":97.755,"prix_vise":99.71,"prix_arret":96.78,"heure_limite":"2026-10-11T18:00:00+02:00","prevision":"SOL touche 99,71 € (+2,00 %) avant 96,78 € (−1,00 %), d'ici 18h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"aucune risquée ouverte ; arrêt ≤1 %, gain 2× ; après la prudente si place"}],"valable_jusqua":"11:33","statut":"active"}
```

- Idée : à la hausse (on achète, puis on revend plus haut)
- Sens : Achat
- Prévision mesurable : après cassure SOL 97,79 €, achat plus bas près du bas du jour ; SOL/BTC touchent leurs visés avant les arrêts, d'ici 18h00. Confiance moyenne (~55 % sur la prudente).
- Décision : simuler si place (en attente de place) — plafond plein (0 € libres). D-040a et D-043a on laisse courir (rappels 14h00).
- Heure limite : 2026-10-11 18:00 (rappel seulement)
- Avis Research : pas demandé — cassure de zone SOL évidente (brief du 9 oct. encore le plus récent).
- Pourquoi : SOL casse le plan d'entrée D-044 ; on propose un achat plus bas, pas une vente (déjà près du bas du jour).

**D-045a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 99,71 € (+2,00 %) avant 95,80 € (−2,00 %), d'ici 18h00. Confiance moyenne (~55 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.255741 SOL à 97.755 € (≈ 25 €), visé 99.71 €, arrêt 95.8 €
- Heure limite : 2026-10-11 18:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Déjà monté : +0,20 % depuis le bas du jour (97,555 €).
- Prix visé vs plus haut du jour : +1,66 % par rapport au haut (98,08 €).
- Avis Research : décidé seul — cassure zone, achat plus bas.
- Pourquoi : D-044a à 98,08 € caduque ; on rachète plus bas près du support du jour.

**D-045b — Équilibrée (pas de place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75759,59 € (+2,25 %) avant 72981,12 € (−1,50 %), d'ici 18h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.00027 BTC à 74092.51 € (≈ 20 €), visé 75759.59 €, arrêt 72981.12 €
- Heure limite : 2026-10-11 18:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt ≤1,5 %, gain ≥ 1,5× la perte)
- Prix visé vs plus haut du jour : +2,01 % par rapport au haut (74266 €).
- Avis Research : décidé seul — même révision.
- Pourquoi : D-040a déjà ouvert ; celle-ci seulement s'il reste de la place. Gain 1,5× la perte.

**D-045c — Risquée (pas de place ; après prudente)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 99,71 € (+2,00 %) avant 96,78 € (−1,00 %), d'ici 18h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.102297 SOL à 97.755 € (≈ 10 €), visé 99.71 €, arrêt 96.78 €
- Heure limite : 2026-10-11 18:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt ≤1 %, gain ≥ 2× la perte)
- Déjà monté : +0,20 % depuis le bas du jour (97,555 €).
- Prix visé vs plus haut du jour : +1,66 % par rapport au haut (98,08 €).
- Avis Research : décidé seul — même achat plus bas, stop plus serré.
- Pourquoi : aucune risquée ouverte ; arrêt ~1 % et gain 2×.

Valables jusqu'à **11:33** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : SOL achat à 97,46 € (zone sous), visé 99,71 €, arrêt 95,80 €.


{"suivi": "D-044", "proposition": "a,b,c", "heure": "2026-10-11T11:07:00+02:00", "par": "PM-Risk", "statut": "remplacée", "texte": "remplacée par D-045 (D-044a caduque selon Predict)"}
{"suivi": "D-045", "proposition": "a", "heure": "2026-10-11T11:07:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plafond plein 50/50 € ; arrêt 95,80 = 2,005 % (arrondi) — à l'ouverture, arrêt resserré à 95,81"}
{"suivi": "D-045", "proposition": "b", "heure": "2026-10-11T11:07:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plafond plein ; arrêt 72981 = 1,501 % — à l'ouverture, arrêt resserré à 72982"}
{"suivi": "D-045", "proposition": "c", "heure": "2026-10-11T11:07:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plafond plein ; arrêt 96,78 = 1,002 % — à l'ouverture, arrêt resserré à 96,79"}


### 2026-10-11 14:18 | BTC-EUR + ETH-EUR + SOL-EUR | D-046 — Rappel D-040a : on garde BTC ; 3 achats si place

```json
{"id":"D-046","heure":"2026-10-11T14:18:00+02:00","paires":["BTC-EUR","ETH-EUR","SOL-EUR"],"declencheur":{"type":"demande_risk","detail":"heure_limite D-040a BTC rappel 14h00 passé"},"resume":"Rappel D-040a : on garde BTC ; D-043a aussi ; 3 achats si place","type":"propositions","prix_releves":{"heure":"14:18","BTC-EUR":74243.775,"ETH-EUR":2237.91,"SOL-EUR":98.0},"place_libre_eur":0,"reel_permis":false,"reel_raison":"aucune sorte n'a passé le test du passé ; dimanche hors 15h–17h","avis_research":"pas demandé : rappel d'heure limite évident (prix vs entrée) ; brief encore celui du 9 oct.","pourquoi":"Rappel 14h00 passé pour D-040a. BTC à 74 244 € est au-dessus de l'entrée 73 918 (+0,44 %) et encore sous le visé 75 426 (+1,59 % restant) → idée pas morte, on garde avec nouveau rappel 22h00. D-043a ETH plat (+0,02 %) → on garde aussi, rappel 22h00. Place 0 €. On propose 3 achats (SOL et BTC) en attente de place. Pas de vente SOL (chute 2 h = 0 %).","ouverts_revus":[{"id":"D-040a","verdict":"vivante","texte":"achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 14h00 passé ; prix 74244 (+0,44 %) — idée pas morte ; nouveau rappel 22h00"},{"id":"D-043a","verdict":"vivante","texte":"achat ETH 25 € ; entrée 2237,49, visé 2283,30, arrêt 2193,75, rappel 14h00 passé ; prix 2237,91 (+0,02 %) — idée pas morte ; nouveau rappel 22h00"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":25,"quantite":0.255102,"prix_entree":98.0,"prix_vise":99.96,"prix_arret":96.04,"heure_limite":"2026-10-11T22:00:00+02:00","prevision":"SOL touche 99.96 € (+2,00 %) avant 96.04 € (−2,00 %), d'ici 22h00","confiance":{"mot":"moyenne","pct":55},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"prioritaire dès place ; déjà +0.51 % depuis bas jour 97.505 ; visé +1.92 % vs haut jour 98.08"},{"lettre":"b","niveau":"équilibrée","paire":"BTC-EUR","idee":"à la hausse","sens":"achat","montant_eur":20,"quantite":0.000269,"prix_entree":74243.77,"prix_vise":75914,"prix_arret":73131,"heure_limite":"2026-10-11T22:00:00+02:00","prevision":"BTC touche 75914 € (+2,25 %) avant 73131 € (−1,50 %), d'ici 22h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"D-040a déjà ouvert 25 € BTC ; seulement si place ; visé +2.22 % vs haut jour 74266.22"},{"lettre":"c","niveau":"risquée","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":10,"quantite":0.102041,"prix_entree":98.0,"prix_vise":99.96,"prix_arret":97.02,"heure_limite":"2026-10-11T22:00:00+02:00","prevision":"SOL touche 99.96 € (+2,00 %) avant 97.02 € (−1,00 %), d'ici 22h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"aucune risquée ouverte ; arrêt ≤1 %, gain 2× ; après la prudente si place"}],"valable_jusqua":"14:48","statut":"active"}
```

**Déclencheur :** heure limite passée pour D-040a (BTC idée à la hausse, rappel 14h00). Prix au relevé 14:16 : BTC 74243.775 € · ETH 2237.91 € · SOL 98.0 €.
Haut/bas du jour (ticks) : BTC 74266.22–74053.755 · ETH 2239.46–2230.495 · SOL 98.08–97.505.
Place libre : **0 €** sur 50 € (ouverts : D-040a BTC 25 € · D-043a ETH 25 €). Réel interdit (dimanche).

Avis Research : pas demandé — prix vs entrée clair.

**Verdict D-040a pour @PM-Risk (dans les 5 min) : GARDER.**
- Idée à la hausse / Sens Achat ; entrée 73 918 € · arrêt 72 468 € · visé 75 426 €.
- Rappel 14h00 **passé**, mais prix **avec nous** (74 244 € > 73 918, +0,44 %) → idée **pas morte**. Nouveau rappel **22h00**.

**Autre ouvert :**
- **D-043a** ETH hausse : rappel 14h00 passé, prix plat (+0,02 %) → **garder**, nouveau rappel **22h00**.

**Décision :** simuler si place (en attente de place) — plafond plein (0 € libres). D-040a et D-043a on laisse courir (rappel 22h00).

**D-046a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 99.96 € (+2,00 %) avant 96.04 € (−2,00 %), d'ici 22h00. Confiance moyenne (~55 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.255102 SOL à 98.0 € (≈ 25 €), visé 99.96 €, arrêt 96.04 €
- Heure limite : 2026-10-11 22:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Déjà monté : +0.51 % depuis le bas du jour (97.505 €).
- Prix visé vs plus haut du jour : +1.92 % par rapport au haut (98.08 €).
- Pourquoi : pas de SOL ouvert ; rebond possible près du haut du jour. Gain = perte possible.

**D-046b — Équilibrée (pas de place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : BTC touche 75914 € (+2,25 %) avant 73131 € (−1,50 %), d'ici 22h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.000269 BTC à 74243.77 € (≈ 20 €), visé 75914 €, arrêt 73131 €
- Heure limite : 2026-10-11 22:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt ≤1,5 %, gain ≥ 1,5× la perte)
- Prix visé vs plus haut du jour : +2.22 % par rapport au haut (74266.22 €).
- Pourquoi : D-040a déjà ouvert ; celle-ci seulement s'il reste de la place. Gain 1,5× la perte.

**D-046c — Risquée (pas de place ; après prudente)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 99.96 € (+2,00 %) avant 97.02 € (−1,00 %), d'ici 22h00. Confiance faible (~52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.102041 SOL à 98.0 € (≈ 10 €), visé 99.96 €, arrêt 97.02 €
- Heure limite : 2026-10-11 22:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt ≤1 %, gain ≥ 2× la perte)
- Pourquoi : aucune risquée ouverte ; arrêt ~1 % et gain 2×.

Valables jusqu'à **14:48** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : SOL achat à 97,71 € (zone sous), visé 99.96 €, arrêt 96.04 €.


- 14:19 PM-Predict — sonnette heure_limite D-043a ETH : déjà traité dans D-046

{"suivi": "D-046", "proposition": "rappels", "heure": "2026-10-11T14:21:00+02:00", "par": "PM-Risk", "statut": "gardées", "texte": "D-040a BTC et D-043a ETH gardées, nouveau rappel 22h00"}
{"suivi": "D-046", "proposition": "a,b,c", "heure": "2026-10-11T14:21:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "conformes (arrêts 2,0 % / 1,50 % / 1,0 %, gains 1× / 1,5× / 2×) mais plafond plein 50/50 €"}

### 2026-10-12 07:33 | BTC-EUR + ETH-EUR + SOL-EUR | D-047 — Rappel D-040a : on garde BTC ; achat ETH + vente SOL (25 € libres)

```json
{"id": "D-047", "heure": "2026-10-12T07:33:00+02:00", "paires": ["BTC-EUR", "ETH-EUR", "SOL-EUR"], "declencheur": {"type": "heure_limite", "detail": "heure_limite D-040a BTC rappel 22h00 (11/10) passé"}, "resume": "Rappel D-040a : on garde BTC ; achat ETH 15 € + vente SOL 10 €", "type": "propositions", "prix_releves": {"heure": "07:31", "BTC-EUR": 74847.405, "ETH-EUR": 2280.485, "SOL-EUR": 100.415}, "haut_bas_jour": {"BTC-EUR": {"haut": 75128.01, "bas": 74364.48}, "ETH-EUR": {"haut": 2293.41, "bas": 2255.38}, "SOL-EUR": {"haut": 101.06, "bas": 98.62}}, "place_libre_eur": 25, "reel_permis": false, "reel_raison": "aucune sorte n'a passé le test du passé ; hors 15h–17h ; pas de contrôle extérieur du signal de vie", "avis_research": "pas demandé : rappel évident (prix avec nous) ; dernier brief du 9 oct. ; trou de relevés 19h55–07h30", "pourquoi": "Rappel 22h00 passé pour D-040a. BTC à 74 847 € est au-dessus de l'entrée 73 918 (+1,26 %) et à 0,77 % du visé 75 426 → idée pas morte, on garde avec nouveau rappel 14h00. D-043a ETH a touché son visé cette nuit : 25 € libres. Nuit en hausse (SOL +1,8 % depuis son bas, ETH +1,1 %, BTC +0,6 %), puis petit recul depuis 07h. On propose un achat ETH (moins monté, sa hausse de nuit tient) et des ventes SOL (le plus monté, recule déjà depuis 101 €). Prudente 15 € + risquée 10 € = 25 € libres.", "ouverts_revus": [{"id": "D-040a", "verdict": "vivante", "texte": "achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 22h00 (11/10) passé ; prix 74847 (+1,26 %) — idée pas morte ; on garde, nouveau rappel 14h00 (12/10)"}, {"id": "D-043a", "verdict": "fermée", "texte": "achat ETH 25 € fermé par Risk au prix visé 2283,30 € (touché à 04h18 pendant le trou de relevés) — gagné"}], "propositions": [{"lettre": "a", "niveau": "prudente", "paire": "ETH-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 15, "quantite": 0.006579, "prix_entree": 2280.0, "prix_vise": 2325.6, "prix_arret": 2234.4, "heure_limite": "2026-10-12T14:00:00+02:00", "prevision": "ETH touche 2325.60 € (+2,00 %) avant 2234.40 € (−2,00 %), d'ici 14h00", "confiance": {"mot": "moyenne", "pct": 55}, "decision": "simuler", "statut": "proposée", "note": "gain espéré ≈ +0,02 € | perte max 0,30 € | coût ≈ 0,02 € ; visé +1,40 % au-dessus du haut du jour 2293,41"}, {"lettre": "b", "niveau": "équilibrée", "paire": "SOL-EUR", "idee": "à la baisse", "sens": "vente", "montant_eur": 20, "quantite": 0.199203, "prix_entree": 100.4, "prix_vise": 98.14, "prix_arret": 101.9, "heure_limite": "2026-10-12T14:00:00+02:00", "prevision": "SOL touche 98.14 € (−2,25 %) avant 101.90 € (+1,49 %), d'ici 14h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "seulement si la prudente n'est pas ouverte (place 25 €) ; SOL avait déjà baissé de 0,64 % depuis son plus haut de 2 h (101,06), moins de 1 % donc pas d'attente ; visé 0,49 % sous le bas du jour 98,62 ; gain espéré ≈ +0,07 € | perte max 0,30 € | coût ≈ 0,02 €"}, {"lettre": "c", "niveau": "risquée", "paire": "SOL-EUR", "idee": "à la baisse", "sens": "vente", "montant_eur": 10, "quantite": 0.099602, "prix_entree": 100.4, "prix_vise": 98.39, "prix_arret": 101.4, "heure_limite": "2026-10-12T14:00:00+02:00", "prevision": "SOL touche 98.39 € (−2,00 %) avant 101.40 € (+1,00 %), d'ici 14h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler", "statut": "proposée", "note": "aucune risquée ouverte ; SOL avait déjà baissé de 0,64 % depuis son plus haut de 2 h (101,06) ; visé 0,23 % sous le bas du jour 98,62 ; gain espéré ≈ +0,05 € | perte max 0,10 € | coût ≈ 0,01 €"}], "valable_jusqua": "08:03", "statut": "active"}
```

**Déclencheur :** heure limite passée pour D-040a (BTC idée à la hausse, rappel 22h00 du 11/10). Prix au relevé 07:31 : BTC 74847.405 € · ETH 2280.485 € · SOL 100.415 €.
Haut/bas du jour (bougies 1 h depuis 00h00, trou de relevés 19h55–07h30) : BTC 75128.01–74364.48 · ETH 2293.41–2255.38 · SOL 101.06–98.62.
Place libre : **25 €** sur 50 € (ouvert : D-040a BTC 25 € ; D-043a ETH fermé au visé à 04h18). Réel interdit.

Avis Research : pas demandé — le rappel est évident (prix avec nous) ; dernier brief du 9 oct.

**Verdict D-040a pour @PM-Risk (dans les 5 min) : GARDER.**
- Idée : à la hausse / Sens : Achat ; entrée 73 918 € · arrêt 72 468 € · visé 75 426 €.
- Rappel 22h00 **passé**, mais prix **avec nous** (74 847 € > 73 918, +1,26 %, visé à 0,77 %) → idée **pas morte**. Nouveau rappel **2026-10-12 14:00**.

**Décision :** simuler — prudente D-047a puis risquée D-047c (15 € + 10 € = 25 € libres) ; équilibrée D-047b seulement si la prudente n'est pas ouverte.

**D-047a — Prudente (15 €)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : ETH touche 2325.60 € (+2,00 %) avant 2234.40 € (−2,00 %), d'ici 14h00. Confiance moyenne (55 %).
- Décision : simuler — achat de 0.006579 ETH à 2280.00 € (≈ 15 €), visé 2325.60 €, arrêt 2234.40 €
- Heure limite : 2026-10-12 14:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Gain espéré ≈ +0,02 € | perte max 0,30 € | coût aller-retour ≈ 0,02 €.
- Prix visé vs plus haut du jour : +1,40 % au-dessus du haut (2293.41 €).
- Pourquoi : ETH a moins couru que SOL cette nuit et sa hausse tient ; notre achat ETH d'hier a touché son visé.

**D-047b — Équilibrée (20 €, seulement si la prudente n'est pas ouverte)**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 98.14 € (−2,25 %) avant 101.90 € (+1,49 %), d'ici 14h00. Confiance faible (52 %).
- Décision : simuler si place (en attente de place) — vente de 0.199203 SOL à 100.40 € (≈ 20 €), visé 98.14 €, arrêt 101.90 €
- Heure limite : 2026-10-12 14:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt ≤1,5 %, gain ≥ 1,5× la perte)
- Déjà baissé avant l'entrée : −0,64 % depuis le plus haut de 2 h (101.06 €), moins de 1 % donc pas d'attente de 30 min.
- Prix visé vs plus bas du jour : 0,49 % sous le bas (98.62 €).
- Gain espéré ≈ +0,07 € | perte max 0,30 € | coût aller-retour ≈ 0,02 €.
- Pourquoi : SOL est le plus monté cette nuit (+1,8 % depuis son bas) et recule déjà depuis 101 €.

**D-047c — Risquée (10 €)**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL touche 98.39 € (−2,00 %) avant 101.40 € (+1,00 %), d'ici 14h00. Confiance faible (52 %).
- Décision : simuler — vente de 0.099602 SOL à 100.40 € (≈ 10 €), visé 98.39 €, arrêt 101.40 €
- Heure limite : 2026-10-12 14:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt ≤1 %, gain ≥ 2× la perte)
- Déjà baissé avant l'entrée : −0,64 % depuis le plus haut de 2 h (101.06 €).
- Prix visé vs plus bas du jour : 0,23 % sous le bas (98.62 €).
- Gain espéré ≈ +0,05 € | perte max 0,10 € | coût aller-retour ≈ 0,01 €.
- Pourquoi : aucune risquée ouverte ; recul de SOL depuis 101 €, arrêt 1 % et gain 2×.

Valables jusqu'à **08:03** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : ETH achat à 2262 € (zone sous), visé 2307.24 €, arrêt 2216.76 € ; SOL vente à 100.76 € (zone au-dessus).

- 07h34 PM-Predict — sonnette sans_decision 07h31 : déjà traité dans D-047

{"suivi": "D-047", "proposition": "rappel", "heure": "2026-10-12T07:36:00+02:00", "par": "PM-Risk", "statut": "gardée", "texte": "D-040a BTC gardée, nouveau rappel 14h00"}
{"suivi": "D-047", "proposition": "a", "heure": "2026-10-12T07:36:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "achat ETH 15 € à 2278,90 (proposé 2280), arrêt 2234,40 (1,96 %), visé 2325,60 ; rappel 14h00"}
{"suivi": "D-047", "proposition": "b", "heure": "2026-10-12T07:36:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "seulement si la prudente n'était pas ouverte"}
{"suivi": "D-047", "proposition": "c", "heure": "2026-10-12T07:36:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "vente SOL 10 € à 100,44 (proposé 100,40), arrêt 101,40 (0,96 %), visé 98,39 (gain 2,1×) ; règle d'essai SOL non concernée (baisse 0,64 % < 1 %) ; rappel 14h00"}

### 2026-10-12 09:11 | SOL-EUR + ETH-EUR + BTC-EUR | D-048 — Passage 9h : nuit douce — achat SOL + vente ETH (plafond plein)

```json
{"id":"D-048","heure":"2026-10-12T09:11:00+02:00","paires":["SOL-EUR","ETH-EUR","BTC-EUR"],"declencheur":{"type":"nuit","detail":"Passage du matin 9h — nuit douce (depuis ~19h 11/10) : BTC +0.32 % · ETH +0.88 % · SOL +0.37 %"},"resume":"Passage 9h : nuit douce — achat SOL + vente ETH (plafond plein 0 € libre)","type":"propositions","prix_releves":{"heure":"09:11","BTC-EUR":75063.755,"ETH-EUR":2294.565,"SOL-EUR":100.57499999999999},"haut_bas_jour":{"BTC-EUR":{"haut":75177.46,"bas":74364.48},"ETH-EUR":{"haut":2296.62,"bas":2255.38},"SOL-EUR":{"haut":101.06,"bas":98.62}},"place_libre_eur":0,"reel_permis":false,"reel_raison":"aucune sorte n'a passé le test du passé ; hors 15h–17h ; pas de contrôle extérieur du signal de vie","avis_research":"pas demandé : passage 9h clair ; dernier brief du 9 oct. 14h44 (pas de brief du jour encore)","pourquoi":"Nuit douce (ETH le plus fort +0.88 %, BTC/SOL ~+0,3 %). D-040a BTC (+1.55 %, visé à 0.48 %), D-047a ETH (+0.69 %) et D-047c SOL vente (légèrement contre, prix 100.57 vs entrée 100.44) restent vivantes — rappels 14h00 pas encore passés. Place libre 0 €. Pas de nouvelle vente SOL (D-047c déjà ouverte ; pièces SOL limitées). On propose achat SOL et vente ETH en attente de place. Risquée seulement après fermeture de D-047c (1 risquée à la fois).","ouverts_revus":[{"id":"D-040a","verdict":"vivante","texte":"achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 14h00 ; prix 75064 (+1.55 %) — idée pas morte ; on laisse le rappel 14h00"},{"id":"D-047a","verdict":"vivante","texte":"achat ETH 15 € ; entrée 2278.9, visé 2325.6, arrêt 2234.4, rappel 14h00 ; prix 2294.57 (+0.69 %) — idée pas morte ; on laisse le rappel 14h00"},{"id":"D-047c","verdict":"vivante","texte":"vente SOL 10 € ; entrée 100.44, visé 98.39, arrêt 101.4, rappel 14h00 ; prix 100.57 (légèrement contre) — idée pas morte ; on laisse le rappel 14h00"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":25,"quantite":0.248571,"prix_entree":100.57499999999999,"prix_vise":102.59,"prix_arret":98.57,"heure_limite":"2026-10-12T18:00:00+02:00","prevision":"SOL touche 102.59 € (+2.00 %) avant 98.57 € (−1.99 %), d'ici 18h00","confiance":{"mot":"moyenne","pct":55},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"prioritaire dès place ; visé +1.51 % vs haut du jour 101.06 ; gain espéré ≈ +0.50 € | perte max 0.50 € | coût ≈ 0,02 €"},{"lettre":"b","niveau":"équilibrée","paire":"ETH-EUR","idee":"à la baisse","sens":"vente","montant_eur":20,"quantite":0.008716,"prix_entree":2294.57,"prix_vise":2242.94,"prix_arret":2328.98,"heure_limite":"2026-10-12T18:00:00+02:00","prevision":"ETH touche 2242.94 € (−2.25 %) avant 2328.98 € (+1.50 %), d'ici 18h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"près du haut du jour ; baisse déjà faite avant l'entrée : −0.09 % depuis le haut 2296.62 ; pas de vente SOL (D-047c ouverte) ; gain espéré ≈ +0.45 € | perte max 0.30 € | coût ≈ 0,02 €"},{"lettre":"c","niveau":"risquée","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":10,"quantite":0.099428,"prix_entree":100.57499999999999,"prix_vise":102.59,"prix_arret":99.57,"heure_limite":"2026-10-12T18:00:00+02:00","prevision":"SOL touche 102.59 € (+2.00 %) avant 99.57 € (−1.00 %), d'ici 18h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"en_attente_de_place","note":"une risquée déjà ouverte (D-047c) → seulement après sa fermeture ; arrêt ≤1 %, gain 2× ; gain espéré ≈ +0.20 € | perte max 0.10 € | coût ≈ 0,01 €"}],"valable_jusqua":"09:41","statut":"active"}
```

**Déclencheur :** passage du matin 9h. Prix au relevé 09:11 : BTC 75063.755 € · ETH 2294.565 € · SOL 100.57499999999999 €.
Haut/bas du jour (bougies 1 h) : BTC 75177.46–74364.48 · ETH 2296.62–2255.38 · SOL 101.06–98.62.
Place libre : **0 €** sur 50 € (ouverts : D-040a BTC 25 € + D-047a ETH 15 € + D-047c SOL 10 €). Réel interdit.

Avis Research : pas demandé — passage 9h ; dernier brief du 9 oct.

**Ouverts revus (rappels 14h00 pas encore passés) :**
- D-040a BTC achat — **vivante** (+1.55 %, visé à 0.48 %) ; on laisse le rappel 14h00
- D-047a ETH achat — **vivante** (+0.69 %) ; on laisse le rappel 14h00
- D-047c SOL vente — **vivante** (légèrement contre) ; on laisse le rappel 14h00
- Aucune idée morte.

- Idée : à la hausse / à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Achat / Vente
- Prévision mesurable : SOL continue un peu à la hausse ; ETH près du haut peut reculer ; vérifié à 18h00
- Décision : simuler si place (en attente de place)
- Heure limite : 2026-10-12 18:00 (rappel seulement)
- Pourquoi : nuit douce ; plafond plein ; pas de vente SOL en plus (D-047c ouverte) ; 3 propositions prêtes dès place

**D-048a — Prudente (pas de place ; prioritaire dès place)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 102.59 € (+2.00 %) avant 98.57 € (−1.99 %), d'ici 18h00. Confiance moyenne (55 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.248571 SOL à 100.57499999999999 € (≈ 25 €), visé 102.59 €, arrêt 98.57 €
- Heure limite : 2026-10-12 18:00 (rappel seulement)
- Niveau : prudente (≤25 €, arrêt ≤2 %, gain ≥ 1× la perte)
- Gain espéré ≈ +0.50 € | perte max 0.50 € | coût aller-retour ≈ 0,02 €.
- Pourquoi : SOL a moins monté que ETH cette nuit ; place attendue si un trade se ferme.

**D-048b — Équilibrée (pas de place)**
- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : ETH touche 2242.94 € (−2.25 %) avant 2328.98 € (+1.50 %), d'ici 18h00. Confiance faible (52 %).
- Décision : simuler si place (en attente de place) — prêt : vente de 0.008716 ETH à 2294.57 € (≈ 20 €), visé 2242.94 €, arrêt 2328.98 €
- Heure limite : 2026-10-12 18:00 (rappel seulement)
- Niveau : équilibrée (≤20 €, arrêt ≤1,5 %, gain ≥ 1,5× la perte)
- Déjà baissé avant l'entrée : −0.09 % depuis le plus haut du jour (2296.62 €).
- Gain espéré ≈ +0.45 € | perte max 0.30 € | coût aller-retour ≈ 0,02 €.
- Pourquoi : ETH près du haut du jour après la plus forte hausse de nuit ; pas de vente SOL (D-047c déjà ouverte).

**D-048c — Risquée (pas de place ; après fermeture D-047c)**
- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL touche 102.59 € (+2.00 %) avant 99.57 € (−1.00 %), d'ici 18h00. Confiance faible (52 %).
- Décision : simuler si place (en attente de place) — prêt : achat de 0.099428 SOL à 100.57499999999999 € (≈ 10 €), visé 102.59 €, arrêt 99.57 €
- Heure limite : 2026-10-12 18:00 (rappel seulement)
- Niveau : risquée (≤10 €, arrêt ≤1 %, gain ≥ 2× la perte)
- Pourquoi : une risquée déjà ouverte (D-047c) ; ouvrir seulement après sa fermeture ; arrêt 1 % et gain 2×.

Valables jusqu'à **09:41** (30 min). Passé ce délai, Risk n'ouvre rien et me prévient.

Prix d'entrée de secours si trop tard : SOL achat à 99,58 € (zone sous), visé 102.59 €, arrêt 98.57 € ; ETH vente à 2301.45 € (zone au-dessus).

{"suivi": "D-048", "proposition": "a,b,c", "heure": "2026-10-12T09:16:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plafond plein 50/50 € ; D-040a, D-047a, D-047c gardées (rappel 14h00)"}

### 2026-10-12 14:45 | ETH-EUR + SOL-EUR + BTC-EUR | D-049 — Zone ETH au plus bas : D-047a morte ; 3 achats creux

```json
{"id":"D-049","heure":"2026-10-12T14:45:00+02:00","paires":["ETH-EUR","SOL-EUR","BTC-EUR"],"declencheur":{"type":"sonnette_zone","detail":"Z-ETH-2273.9 sous 2273.9 (prix 2261,97 → 2265)"},"resume":"Zone ETH touchée au plus bas du jour — D-047a idée morte ; 3 achats creux","type":"propositions","prix_releves":{"heure":"14:45","BTC-EUR":74020.61,"ETH-EUR":2265.0,"SOL-EUR":98.61},"haut_bas_jour":{"BTC-EUR":{"haut":75201.665,"bas":73969.52},"ETH-EUR":{"haut":2299.85,"bas":2261.97},"SOL-EUR":{"haut":100.855,"bas":98.565}},"place_libre_eur":10.0,"reel_permis":false,"reel_raison":"aucune sorte n'a passé le test du passé ; contrôle extérieur du signal de vie absent","avis_research":"pas demandé : ETH au plus bas du jour pile sur la zone d'achat D-048 — décision claire","pourquoi":"ETH a cassé 2 273,90 € et touche le plus bas du jour (~2 262 €). D-047a (achat ETH 15 €) a passé son rappel 14h00 avec le prix contre (−0,6 %) → idée morte (Risk ferme). D-047c SOL vente vient de gagner au visé (+0,19 €) → 10 € libres, 25 € après fermeture D-047a. D-040a BTC encore légèrement au-dessus de l'entrée → vivante, nouveau rappel 20h00. On rachète les creux : ETH (zone), SOL (plus bas du jour), BTC (près du bas).","ouverts_revus":[{"id":"D-040a","verdict":"vivante","texte":"achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 14h00 passé ; prix 74021 (+0.14 %) — idée pas morte ; nouveau rappel 20h00"},{"id":"D-047a","verdict":"morte","texte":"achat ETH 15 € ; entrée 2278.9, visé 2325.6, arrêt 2234.4, rappel 14h00 passé ; prix 2265.00 (-0.61 %) — prix contre nous → idée morte ; Risk ferme"},{"id":"D-047c","verdict":"fermée","texte":"vente SOL 10 € fermée au visé vers 12h42 (+0,19 €) — place libérée"}],"propositions":[{"lettre":"a","niveau":"prudente","paire":"ETH-EUR","idee":"à la hausse","sens":"achat","montant_eur":25,"quantite":0.011038,"prix_entree":2265.0,"prix_vise":2310.3,"prix_arret":2219.7,"heure_limite":"2026-10-12T20:00:00+02:00","prevision":"ETH touche 2310.3 € (+2.00 %) avant 2219.7 € (−2.00 %), d'ici 20h00","confiance":{"mot":"moyenne","pct":55},"decision":"simuler","statut":"proposée","note":"après fermeture D-047a (place 25 €) ; au plus bas du jour 2261.97 ; visé +0.45 % vs haut du jour ; gain espéré ≈ +0.50 € | perte max 0.50 € | coût ≈ 0,02 €"},{"lettre":"b","niveau":"équilibrée","paire":"SOL-EUR","idee":"à la hausse","sens":"achat","montant_eur":20,"quantite":0.202819,"prix_entree":98.61,"prix_vise":100.81,"prix_arret":97.14,"heure_limite":"2026-10-12T20:00:00+02:00","prevision":"SOL touche 100.81 € (+2.23 %) avant 97.14 € (−1.49 %), d'ici 20h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"proposée","note":"au plus bas du jour 98.56 après D-047c gagnante ; visé -0.04 % vs haut du jour ; gain espéré ≈ +0.45 € | perte max 0.30 € | coût ≈ 0,02 €"},{"lettre":"c","niveau":"risquée","paire":"BTC-EUR","idee":"à la hausse","sens":"achat","montant_eur":10,"quantite":0.0001351,"prix_entree":74020.61,"prix_vise":75499.83,"prix_arret":73281,"heure_limite":"2026-10-12T20:00:00+02:00","prevision":"BTC touche 75499.83 € (+2.00 %) avant 73281 € (−1.00 %), d'ici 20h00","confiance":{"mot":"faible","pct":52},"decision":"simuler_si_place","statut":"proposée","note":"près du bas du jour 73970 ; D-040a déjà ouverte sur BTC ; visé +0.40 % vs haut du jour ; gain espéré ≈ +0.20 € | perte max 0.10 € | coût ≈ 0,01 €"}],"valable_jusqua":"15:14","statut":"active"}
```

- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : ETH +2.00 % / −2.00 % d'ici 20h00 (aussi SOL et BTC en propositions b/c)
- Décision : simuler si place (en attente de place) pour b/c ; simuler a après fermeture D-047a — visé 2310.3 / arrêt 2219.7 (ETH)
- Heure limite : 2026-10-12 20:00 (rappel seulement)
- Avis Research : pas demandé : ETH au plus bas du jour sur la zone d'achat — décision claire
- Pourquoi : ETH a cassé 2 273,90 € et touche le plus bas du jour (~2 262 €). D-047a (achat ETH 15 €) a passé son rappel 14h00 avec le prix contre (−0,6 %) → idée morte (Risk ferme). D-047c SOL vente vient de gagner au visé (+0,19 €) → 10 € libres, 25 € après fermeture D-047a. D-040a BTC encore légèrement au-dessus de l'entrée → vivante, nouveau rappel 20h00. On rachète les creux : ETH (zone), SOL (plus bas du jour), BTC (près du bas).

**D-049a — Prudente (simuler après fermeture D-047a)**
- Achat ETH 25 € @ 2265.0 → visé 2310.3 / arrêt 2219.7 / rappel 20h00

**D-049b — Équilibrée (simuler si place)**
- Achat SOL 20 € @ 98.61 → visé 100.81 / arrêt 97.14 / rappel 20h00

**D-049c — Risquée (simuler si place)**
- Achat BTC 10 € @ 74020.61 → visé 75499.83 / arrêt 73281 / rappel 20h00
- 14h46 PM-Predict — sonnette occupe (mouvement + sans_decision) : déjà traité dans D-049

```json
{"suivi": "D-049", "proposition": "D-047a", "heure": "2026-10-12T14:47:00+02:00", "par": "PM-Risk", "statut": "fermée", "texte": "achat ETH 15 € fermé idée morte (rappel 14h00 passé, prix contre) : vendu à 2265,64 (entrée 2278,90) ; résultat −0,10 € (−0,68 %, frais compris)"}
{"suivi": "D-049", "proposition": "rappel", "heure": "2026-10-12T14:47:00+02:00", "par": "PM-Risk", "statut": "gardée", "texte": "D-040a BTC gardée, nouveau rappel 20h00"}
{"suivi": "D-049", "proposition": "a", "heure": "2026-10-12T14:47:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "achat ETH 25 € à 2265,00 (marché 2265,87), arrêt 2219,70 (2,0 %), visé 2310,30 ; rappel 20h00 ; position rx-paper-2026-10-12T124716Z-3cf7905b"}
{"suivi": "D-049", "proposition": "b", "heure": "2026-10-12T14:47:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place (plafond 50 € plein : BTC 25 € + ETH 25 €)"}
{"suivi": "D-049", "proposition": "c", "heure": "2026-10-12T14:47:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place (plafond 50 € plein : BTC 25 € + ETH 25 €)"}
```

```json
{"suivi": "D-047", "proposition": "a", "heure": "2026-10-12T14:47:00+02:00", "par": "PM-Predict", "statut": "simulée", "texte": "idée pas morte finalement : on garde l'achat ETH (arrêt et visé inchangés), nouveau rappel 2026-10-12 20:00"}
{"suivi": "D-049", "proposition": "a", "heure": "2026-10-12T14:47:00+02:00", "par": "PM-Predict", "statut": "annulée", "texte": "retirée : même pari que D-047a, ce serait payer les frais deux fois (remarque Orchestrator)"}
```
```json
{"suivi": "D-049 correction", "proposition": "a,c", "heure": "2026-10-12T14:48:00+02:00", "par": "PM-Risk", "statut": "correction", "texte": "Predict a retiré D-049a et demandé de garder D-047a à 14h47, mais le message est arrivé après l'exécution (D-047a déjà fermée, D-049a déjà ouverte) ; Risk garde D-049a (même pari ETH, entrée plus basse 2265 vs 2278,9) pour ne pas payer les frais une troisième fois ; D-049c reste pas_simulée (plafond 50 € plein)"}
```

```json
{"suivi": "D-047", "proposition": "a", "heure": "2026-10-12T14:48:00+02:00", "par": "PM-Predict", "statut": "fermée", "texte": "correction : Risk avait déjà fermé à 14h47 à 2 265,64 € (−0,10 € frais compris) avant mon retrait ; mon suivi de 14h47 ne vaut pas"}
{"suivi": "D-049", "proposition": "a", "heure": "2026-10-12T14:48:00+02:00", "par": "PM-Predict", "statut": "simulée", "texte": "correction : ouverte par Risk à 14h47 à 2 265,00 €, arrêt 2 219,70 €, visé 2 310,30 €, rappel 2026-10-12 20:00 ; on la garde (défaire coûterait des frais une 3e fois)"}
```

### 2026-10-12 15:25 | BTC-EUR + ETH-EUR + SOL-EUR | D-050 — Avant session : au plus bas du jour, petite baisse prévue ; vente SOL si place

```json
{"id": "D-050", "heure": "2026-10-12T15:25:00+02:00", "paires": ["BTC-EUR", "ETH-EUR", "SOL-EUR"], "declencheur": {"type": "prevision_du_jour", "detail": "prévision avant session 15h–17h (routine 14h55, lancée 15h22) ; brief Research 14h44 du 12/10"}, "resume": "Avant session : 3 cryptos au plus bas du jour — petite baisse prévue ; on garde BTC et ETH ; vente SOL si place", "type": "propositions", "prix_releves": {"heure": "15:24", "BTC-EUR": 73818.96, "ETH-EUR": 2260.05, "SOL-EUR": 98.43}, "haut_bas_jour": {"BTC-EUR": {"haut": 75201.67, "bas": 73798.2}, "ETH-EUR": {"haut": 2299.85, "bas": 2258.51}, "SOL-EUR": {"haut": 100.86, "bas": 98.43}}, "place_libre_eur": 0, "reel_permis": false, "reel_raison": "aucune sorte n'a passé le test du passé ; contrôle extérieur du signal de vie absent", "avis_research": "brief 14h44 du jour lu (fait ~15h04) : 3 idées à la hausse (BTC faible, ETH faible, SOL moyenne) — pas d'accord, voir pourquoi ; jour férié US (Columbus Day), pas de chiffres à 14h30, inflation US mercredi", "pourquoi": "À 15h22 les trois cryptos cassent leur plus bas du jour (BTC 73 798 €, ETH 2 258,5 €, SOL 98,43 €), après une baisse régulière depuis ce matin (BTC −1,8 % depuis 75 202 €) ; c'est une des raisons de prudence de Research elle-même. Je ne suis pas d'accord avec ses 3 idées à la hausse : +1,5 % en moins de 2 h arrive rarement (meilleur mouvement moyen +0,47 %, bilan Compound), et nos achats dans les creux ont souvent perdu ces jours-ci. Les 2 achats ouverts restent vivants (arrêts encore à ~1,8 % sous le prix) ; plafond plein, donc seule une vente SOL de 20 € est proposée si de la place se libère. Pas d'annonce US à 15h30 hormis l'ouverture de la Bourse ; chiffres de l'inflation US mercredi 14h30.", "ouverts_revus": [{"id": "D-040a", "verdict": "vivante", "texte": "achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468 ; prix 73819 (−0,13 %) ; arrêt encore à −1,83 % — idée pas morte ; rappel 20h00 inchangé"}, {"id": "D-049a", "verdict": "vivante", "texte": "achat ETH 25 € ; entrée 2265.0, visé 2310.3, arrêt 2219.7 ; prix 2260.05 (−0,22 %) ; arrêt encore à −1,79 % — idée pas morte ; rappel 20h00 inchangé"}], "previsions": [{"id": "D-050-BTC", "paire": "BTC-EUR", "sens": "DOWN", "prevision": "BTC touche 73450 € (−0.50 %) avant 74188 € (+0.50 %), d'ici 17h00", "seuil_pct": 0.5, "horizon": "2026-10-12T17:00:00+02:00", "confiance": {"mot": "faible", "pct": 53}, "trade": "aucun (pas de BTC à vendre ; plafond plein)", "research": "Research : hausse 73911 → 75020 (+1,5 %), arrêt 73172, avant 17h, faible — pas d'accord"}, {"id": "D-050-ETH", "paire": "ETH-EUR", "sens": "DOWN", "prevision": "ETH touche 2248.75 € (−0.50 %) avant 2271.35 € (+0.50 %), d'ici 17h00", "seuil_pct": 0.5, "horizon": "2026-10-12T17:00:00+02:00", "confiance": {"mot": "faible", "pct": 53}, "trade": "aucun (achat ETH D-049a déjà ouvert ; plafond plein)", "research": "Research : hausse 2261 → 2295 (+1,5 %), arrêt 2239, avant 17h, faible — pas d'accord"}, {"id": "D-050a", "paire": "SOL-EUR", "sens": "DOWN", "prevision": "SOL touche 96.95 € (−1.50 %) avant 99.90 € (+1.49 %), d'ici 20h00", "seuil_pct": 1.5, "horizon": "2026-10-12T20:00:00+02:00", "confiance": {"mot": "faible", "pct": 54}, "trade": "vente SOL 20 € si place", "research": "Research : hausse 98.63 → 100.11 (+1,5 %), arrêt 97.16, avant 17h, moyenne — pas d'accord"}], "propositions": [{"lettre": "a", "niveau": "prudente", "paire": "SOL-EUR", "idee": "à la baisse", "sens": "vente", "montant_eur": 20, "quantite": 0.20319, "prix_entree": 98.43, "prix_vise": 96.95, "prix_arret": 99.9, "heure_limite": "2026-10-12T20:00:00+02:00", "prevision": "SOL touche 96.95 € (−1.50 %) avant 99.90 € (+1.49 %), d'ici 20h00", "confiance": {"mot": "faible", "pct": 54}, "decision": "simuler_si_place", "statut": "proposée", "note": "plafond plein (0 €) : seulement si de la place se libère avant 15h55 ; pièces SOL dispo ~0,241 ; SOL −0,4 % sous son haut des 2 h (pas d'attente 30 min) ; gain espéré ≈ +0,30 € | perte max ≈ 0,30 € | coût ≈ 0,02 € → avance presque nulle (~+0,00 €)"}], "creneau_15_17": "2 simulations ouvertes pendant le créneau (D-040a, D-049a ouverte 14h47) ; plafond 50 € plein, pas de nouvelle ouverture possible sans place", "valable_jusqua": "15:55", "statut": "active"}
```

- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : BTC −0,50 % (73 450) avant +0,50 % (74 188) d'ici 17h00 ; ETH −0,50 % (2 248,75) avant +0,50 % (2 271,35) d'ici 17h00 ; SOL −1,50 % (96,95) avant +1,49 % (99,90) d'ici 20h00
- Décision : simuler si place (en attente de place) — vente SOL 20 € à 98,43, prix visé (rachat) 96,95, prix d'arrêt 99,90 ; BTC et ETH : pas de nouveau trade, on garde D-040a et D-049a
- Heure limite : 2026-10-12 20:00 (rappel seulement)
- Gain espéré ≈ +0,30 € | perte max ≈ 0,30 € | coût aller-retour ≈ 0,02 € (avance presque nulle, permise en simulation) — réel interdit
- Avis Research : brief 14h44 du jour — pas d'accord avec ses 3 idées à la hausse (raison ci-dessous)
- Pourquoi : À 15h22 les trois cryptos cassent leur plus bas du jour (BTC 73 798 €, ETH 2 258,5 €, SOL 98,43 €), après une baisse régulière depuis ce matin (BTC −1,8 % depuis 75 202 €) ; c'est une des raisons de prudence de Research elle-même. Je ne suis pas d'accord avec ses 3 idées à la hausse : +1,5 % en moins de 2 h arrive rarement (meilleur mouvement moyen +0,47 %, bilan Compound), et nos achats dans les creux ont souvent perdu ces jours-ci. Les 2 achats ouverts restent vivants (arrêts encore à ~1,8 % sous le prix) ; plafond plein, donc seule une vente SOL de 20 € est proposée si de la place se libère. Pas d'annonce US à 15h30 hormis l'ouverture de la Bourse ; chiffres de l'inflation US mercredi 14h30.

**Trades ouverts revus**
- D-040a achat BTC 25 € : prix 73 819 (−0,13 %), vivante, on laisse courir, rappel 20h00.
- D-049a achat ETH 25 € : prix 2 260,05 (−0,22 %), vivante, on laisse courir, rappel 20h00.

**D-050a — Prudente (simuler si place, valable jusqu'à 15h55)**
- Vente SOL 20 € (0,20319 SOL) @ 98,43 → rachat visé 96,95 / arrêt 99,90 / rappel 20h00

```json
{"suivi": "D-050", "proposition": "rappel", "heure": "2026-10-12T15:26:00+02:00", "par": "PM-Risk", "statut": "gardée", "texte": "D-040a BTC gardée (rappel 20h00) ; D-049a ETH gardée (rappel 20h00)"}
{"suivi": "D-050", "proposition": "a", "heure": "2026-10-12T15:26:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "vente SOL 20 € prudente à 98,43, visé 96,95, arrêt 99,90 : conforme aux limites prudente (arrêt 1,49 % ≤ 2 %, gain ≈ perte) mais pas simulée pour l'instant : plafond 50 € plein ; ne sera ouverte que si 20 € se libèrent avant 15h55, sinon expirée"}
```

### 2026-10-12 20:46 | ETH-EUR + SOL-EUR + BTC-EUR | D-051 — Rappels 20h00 : D-049a morte, D-040a gardée ; ventes SOL/ETH (25 € libres)

```json
{"id": "D-051", "heure": "2026-10-12T20:46:00+02:00", "paires": ["ETH-EUR", "SOL-EUR", "BTC-EUR"], "declencheur": {"type": "sonnette_heure_limite", "detail": "rappels 20h00 D-040a (BTC) et D-049a (ETH), sonnés à 20h43"}, "resume": "Rappels 20h00 : D-049a morte, D-040a gardée ; ventes SOL/ETH avec 25 € libres", "type": "propositions", "prix_releves": {"heure": "20:44", "BTC-EUR": 73857.17, "ETH-EUR": 2251.54, "SOL-EUR": 96.53}, "haut_bas_jour": {"BTC-EUR": {"haut": 75201.67, "bas": 73680.74}, "ETH-EUR": {"haut": 2299.85, "bas": 2248.83}, "SOL-EUR": {"haut": 100.86, "bas": 96.52}}, "place_libre_eur": 0, "place_apres_fermeture_eur": 25, "reel_permis": false, "reel_raison": "aucune sorte n'a passé le test du passé ; contrôle extérieur du signal de vie absent ; hors 15h–17h", "avis_research": "pas demandé : décision claire (règle des rappels) ; dernier brief Research 14h44 (3 idées à la hausse)", "pourquoi": "Rappels de 20h00 passés pour les 2 achats. ETH est à −0,6 % sous l'entrée, tout près du bas du jour, et j'avais prévu une petite baisse à 15h25 : l'achat ETH D-049a est une idée morte. BTC D-040a est à plat (−0,08 %, moins que les frais) avec l'arrêt encore à 1,9 % : on le garde, nouveau rappel demain 9h00. La baisse continue depuis ce matin (BTC −1,8 %, ETH −2,1 %, SOL −4,3 % depuis le haut du jour) et ma prévision de baisse SOL de 15h25 s'est réalisée : avec les 25 € libérés, je propose des ventes (SOL, puis ETH). Notre taux de réussite est bas (3 sur 11), donc confiance faible et petites tailles. Trou dans le relevé des prix de 19h17 à 20h43 (signalé à Risk). Avis Research pas demandé : décision claire avec la règle des rappels.", "ouverts_revus": [{"id": "D-040a", "verdict": "vivante", "texte": "achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 20h00 passé ; prix 73857 (−0,08 %, à plat, moins que les frais) ; arrêt encore à −1,88 % — on garde ; nouveau rappel 2026-10-13 09:00"}, {"id": "D-049a", "verdict": "morte", "texte": "achat ETH 25 € ; entrée 2265.0, visé 2310.3, arrêt 2219.7, rappel 20h00 passé ; prix 2251.5 (−0,60 %) — prix contre nous et ma prévision de 15h25 était à la baisse → idée morte ; Risk ferme (≈ −0,17 € frais compris)"}], "propositions": [{"lettre": "a", "niveau": "prudente", "paire": "SOL-EUR", "idee": "à la baisse", "sens": "vente", "montant_eur": 20, "quantite": 0.20719, "prix_entree": 96.53, "prix_vise": 95.08, "prix_arret": 97.97, "heure_limite": "2026-10-13T09:00:00+02:00", "prevision": "SOL touche 95.08 € (−1.50 %) avant 97.97 € (+1.49 %), d'ici 2026-10-13 09h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler", "statut": "proposée", "note": "après fermeture D-049a (25 € libres) ; SOL a déjà baissé de 4,29 % depuis le haut du jour 100,855 et de 0,81 % depuis son haut des 2 h 97,32 (moins de 1 %, pas d'attente 30 min) ; visé 1,49 % sous le bas du jour 96,515 ; pièces SOL dispo ~0,241 ; gain espéré ≈ +0,30 € | perte max ≈ 0,30 € | coût ≈ 0,02 €"}, {"lettre": "b", "niveau": "équilibrée", "paire": "ETH-EUR", "idee": "à la baisse", "sens": "vente", "montant_eur": 20, "quantite": 0.008883, "prix_entree": 2251.5, "prix_vise": 2217.7, "prix_arret": 2274.0, "heure_limite": "2026-10-13T09:00:00+02:00", "prevision": "ETH touche 2217.7 € (−1.50 %) avant 2274.0 € (+1.00 %), d'ici 2026-10-13 09h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler_si_place", "statut": "proposée", "note": "seulement si a n'est pas ouverte (20 € ne tiennent pas avec a) ; ETH a déjà baissé de 2,10 % depuis le haut du jour 2299,85 ; visé 1,38 % sous le bas du jour 2248,83 ; gain 1,50 × la perte ; pas un rachat dans le même sens que D-049a : on passe de la hausse à la baisse, comme prévu à 15h25 (D-050) ; gain espéré ≈ +0,30 € | perte max ≈ 0,20 € | coût ≈ 0,02 €"}, {"lettre": "c", "niveau": "risquée", "paire": "ETH-EUR", "idee": "à la baisse", "sens": "vente", "montant_eur": 5, "quantite": 0.002221, "prix_entree": 2251.5, "prix_vise": 2206.4, "prix_arret": 2274.0, "heure_limite": "2026-10-13T09:00:00+02:00", "prevision": "ETH touche 2206.4 € (−2.00 %) avant 2274.0 € (+1.00 %), d'ici 2026-10-13 09h00", "confiance": {"mot": "faible", "pct": 51}, "decision": "simuler", "statut": "proposée", "note": "tient dans les 5 € restants après a ; aucune risquée ouverte ; ETH a déjà baissé de 2,10 % depuis le haut du jour ; visé 1,89 % sous le bas du jour 2248,83 ; gain 2,00 × la perte ; même remarque que b (passage hausse → baisse, pas un rachat) ; gain espéré ≈ +0,10 € | perte max ≈ 0,05 € | coût ≈ 0,01 €"}], "valable_jusqua": "21:16", "statut": "active"}
```

- Idée : à la baisse (on vend des pièces qu'on a, puis on rachète plus bas)
- Sens : Vente
- Prévision mesurable : SOL −1,50 % (95,08) avant +1,49 % (97,97) d'ici 2026-10-13 09h00 ; ETH −1,50 % (2 217,7) avant +1,00 % (2 274,0) d'ici 2026-10-13 09h00 (risquée : −2,00 % à 2 206,4)
- Décision : simuler — a vente SOL 20 € à 96,53, prix visé (rachat) 95,08, prix d'arrêt 97,97 ; c vente ETH 5 € à 2 251,5, visé 2 206,4, arrêt 2 274,0 ; b vente ETH 20 € simuler si place (en attente de place), visé 2 217,7, arrêt 2 274,0. D-049a : idée morte (Risk ferme). D-040a : on garde, nouveau rappel 2026-10-13 09:00.
- Heure limite : 2026-10-13 09:00 (rappel seulement)
- Gain espéré ≈ +0,30 € (a) / +0,30 € (b) / +0,10 € (c) | perte max ≈ 0,30 / 0,20 / 0,05 € | coût aller-retour ≈ 0,02 / 0,02 / 0,01 € — réel interdit
- Avis Research : pas demandé — décision claire avec la règle des rappels (dernier brief 14h44, 3 idées à la hausse)
- Pourquoi : Rappels de 20h00 passés pour les 2 achats. ETH est à −0,6 % sous l'entrée, tout près du bas du jour, et j'avais prévu une petite baisse à 15h25 : l'achat ETH D-049a est une idée morte. BTC D-040a est à plat (−0,08 %, moins que les frais) avec l'arrêt encore à 1,9 % : on le garde, nouveau rappel demain 9h00. La baisse continue depuis ce matin (BTC −1,8 %, ETH −2,1 %, SOL −4,3 % depuis le haut du jour) et ma prévision de baisse SOL de 15h25 s'est réalisée : avec les 25 € libérés, je propose des ventes (SOL, puis ETH). Notre taux de réussite est bas (3 sur 11), donc confiance faible et petites tailles. Trou dans le relevé des prix de 19h17 à 20h43 (signalé à Risk). Avis Research pas demandé : décision claire avec la règle des rappels.

**Trades ouverts revus**
- D-040a achat BTC 25 € : prix 73 857 (−0,08 %), à plat, on garde, nouveau rappel 2026-10-13 09:00.
- D-049a achat ETH 25 € : prix 2 251,5 (−0,60 %), idée morte, Risk ferme.

**D-051a — Prudente (simuler après fermeture D-049a)**
- Vente SOL 20 € (0,20719 SOL) @ 96,53 → rachat visé 95,08 / arrêt 97,97 / rappel 2026-10-13 09:00
- Baisse déjà faite avant l'entrée : −4,29 % depuis le haut du jour, −0,81 % depuis le haut des 2 h (pas d'attente 30 min). Visé 1,49 % sous le bas du jour.

**D-051b — Équilibrée (simuler si place)**
- Vente ETH 20 € (0,008883 ETH) @ 2 251,5 → rachat visé 2 217,7 / arrêt 2 274,0 / rappel 2026-10-13 09:00
- Baisse déjà faite : −2,10 % depuis le haut du jour. Visé 1,38 % sous le bas du jour. Seulement si a n'est pas ouverte.

**D-051c — Risquée (simuler, 5 €)**
- Vente ETH 5 € (0,002221 ETH) @ 2 251,5 → rachat visé 2 206,4 / arrêt 2 274,0 / rappel 2026-10-13 09:00
- Baisse déjà faite : −2,10 % depuis le haut du jour. Visé 1,89 % sous le bas du jour.
- Ce qui a changé par rapport à D-049a : on ne rachète pas dans le même sens, on passe de l'idée à la hausse à l'idée à la baisse, comme prévu à 15h25.

```json
{"suivi": "D-051", "proposition": "D-049a", "heure": "2026-10-12T20:48:00+02:00", "par": "PM-Risk", "statut": "fermée", "texte": "achat ETH 25 € fermé idée morte : vendu à 2249,30 (entrée 2265,00) ; résultat −0,20 € (−0,79 %, frais compris) ; trou 19h17–20h43 vérifié (state/price_gaps.jsonl) : ETH bas 2241,80 > arrêt 2219,70, haut 2253,71 < visé 2310,30 → rien franchi"}
{"suivi": "D-051", "proposition": "rappel", "heure": "2026-10-12T20:48:00+02:00", "par": "PM-Risk", "statut": "gardée", "texte": "D-040a BTC gardée, nouveau rappel 13/10 09h00 ; trou 19h17–20h43 : BTC bas 73741,77 > arrêt 72468, haut 73955,13 < visé 75426 → rien franchi"}
{"suivi": "D-051", "proposition": "a", "heure": "2026-10-12T20:48:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "vente SOL 20 € à 96,53 (marché 96,345), arrêt 97,97 (1,49 %), visé 95,08 ; rappel 13/10 09h00 ; SOL dispo 0,2413 ≥ 0,2072 ; position rx-paper-2026-10-12T184805Z-72bcb36d"}
{"suivi": "D-051", "proposition": "b", "heure": "2026-10-12T20:48:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "seulement si la prudente n'était pas ouverte (a ouverte)"}
{"suivi": "D-051", "proposition": "c", "heure": "2026-10-12T20:48:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "vente ETH 5 € à 2251,50 (marché 2249,42), arrêt 2274,00 (1,00 %), visé 2206,40 (gain 2×) ; rappel 13/10 09h00 ; ETH dispo 0,02086 ≥ 0,00222 ; passage hausse→baisse sur ETH expliqué par Predict (pas un rachat même sens) ; position rx-paper-2026-10-12T184805Z-35368452"}
```

```json
{"suivi": "D-051 correction", "proposition": "a", "heure": "2026-10-12T20:48:00+02:00", "par": "PM-Risk", "statut": "correction", "texte": "D-051a ouverte à 20h48 avant la règle d'attente 30 min (SOL −1,00 % sous son haut 2 h) ; Risk la garde car le prix d'entrée 96,53 est la limite qu'on aurait exigée à 21h13 et la refermer coûterait des frais. Leçon : Risk attend que les questions du groupe soient réglées avant d'exécuter."}
{"suivi": "D-051 correction", "proposition": "b", "heure": "2026-10-12T20:48:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plafond plein (50/50 €)"}
```


### 2026-10-12 20:50 | Bilan Compound — scores + test du passé (soir)
- **Predict du jour** : D-050 BTC/ETH **perdus** (seuil inverse +0,5 % avant 17h) ; D-050a SOL **gagné** (−1,5 % à 16h49). Total cumulé **6 gagnés / 10 perdus = 38 %**.
- **Research 14h44** : BTC/ETH **annulés** (aucun seuil) ; SOL **perdu** (arrêt 97,16 à 16h40) — idée SOL **non simulée** (plafond), coût 0 €. Predict avait raison sur SOL baisse.
- **Risk** : fermetures idée morte utiles (D-047a −0,10 ; D-049a −0,20) ; règle « fermer puis racheter » appliquée ; 1 cas compté (D-047a→D-049a, −0,30 €).
- **Scan** : SOL −1,7 % vu 15h–17h ; 4 trous ordinateur figé (20/10/6/13 min) — récurrents ; aucun arrêt/visé manqué.
- **Simu** : 4 fermés du jour (D-043a +0,49 ; D-047c +0,19 ; D-047a −0,10 ; D-049a −0,20). Ouverts : D-040a, D-051a, D-051c. Live 0.
- **Créneau 15h–17h** : simus déjà ouvertes ; aucune nouvelle (plafond plein).
- **Nuits sans décision sous plafond** : 0.
- **Test du passé** : pas de nouveau test (aucune sorte nouvelle / réglage changé) — réutilise bilans 8–11 oct. : **aucune sorte ne passe** ; réel interdit. `vt_verdict.py --all` relancé (toujours non sauf 1 breakout SOL fragile hors critères équipe complets).
- **Verdict** : **rien ne change** (hausse 8 essais, baisse 9 ; <20).


### 2026-10-13 07:27 | ETH-EUR + SOL-EUR + BTC-EUR | D-052 — BTC au-dessus de 74 120 : ventes de la nuit au visé, D-040a gardée ; achats ETH/SOL (25 € libres)

```json
{"id": "D-052", "heure": "2026-10-13T07:27:00+02:00", "paires": ["ETH-EUR", "SOL-EUR", "BTC-EUR"], "declencheur": {"type": "sonnette_zone", "detail": "Z-BTC-74120 (BTC au-dessus de 74 120 € à 74 997 €, 07h24)"}, "resume": "BTC au-dessus de 74 120 : D-051a/c fermées au visé cette nuit, D-040a gardée ; achats ETH/SOL (25 € libres)", "type": "propositions", "prix_releves": {"heure": "07:25", "BTC-EUR": 74877.82, "ETH-EUR": 2262.42, "SOL-EUR": 96.915}, "haut_bas_jour": {"BTC-EUR": {"haut": 75000.0, "bas": 72555.0}, "ETH-EUR": {"haut": 2269.07, "bas": 2157.33}, "SOL-EUR": {"haut": 97.12, "bas": 91.09}}, "place_libre_eur": 25, "reel_permis": false, "reel_raison": "aucune sorte n'a passé le test du passé ; hors 15h–17h", "avis_research": "pas demandé : décision claire, pas de nouvelle info depuis le brief du 12/10 14h44", "pourquoi": "Cette nuit, l'ordinateur a gelé de 20h58 à 07h23 ; le rattrapage montre que nos 2 ventes D-051a (SOL) et D-051c (ETH) ont touché leur prix visé (+0,28 € et +0,10 €), donc 25 € sont libres. Après un creux à 02h50, les 3 cryptos sont remontées fort (BTC +3,2 %, ETH +4,9 %, SOL +6,4 %) et sont au plus haut du jour : je propose de petits achats ETH et SOL pour suivre cette remontée, avec confiance faible car on achète en haut. BTC D-040a va dans notre sens, à 0,73 % de son visé. Avis Research pas demandé : décision claire, pas de nouvelle info depuis le brief d'hier.", "ouverts_revus": [{"id": "D-040a", "verdict": "vivante", "texte": "achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 09h00 pas encore passé ; prix 74878 (+1,30 %), visé à 0,73 % — on laisse courir"}], "propositions": [{"lettre": "a", "niveau": "prudente", "paire": "ETH-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 20, "quantite": 0.00885, "prix_entree": 2260.0, "prix_vise": 2294.0, "prix_arret": 2226.2, "heure_limite": "2026-10-13T15:00:00+02:00", "prevision": "ETH touche 2294.0 € (+1.50 %) avant 2226.2 € (−1.50 %), d'ici 2026-10-13 15h00", "confiance": {"mot": "faible", "pct": 53}, "decision": "simuler", "statut": "proposée", "note": "ETH est remonté de +4,9 % depuis le bas de la nuit 2 157 (02h50) ; entrée juste sous le prix ; visé 1,10 % au-dessus du haut du jour 2 269,07 ; gain 1,0 × la perte ; arrêt arrondi vers l'entrée ; gain espéré ≈ +0,30 € | perte max ≈ 0,30 € | coût ≈ 0,02 €"}, {"lettre": "b", "niveau": "équilibrée", "paire": "SOL-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 20, "quantite": 0.206612, "prix_entree": 96.8, "prix_vise": 98.98, "prix_arret": 95.35, "heure_limite": "2026-10-13T15:00:00+02:00", "prevision": "SOL touche 98.98 € (+2.25 %) avant 95.35 € (−1.50 %), d'ici 2026-10-13 15h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler_si_place", "statut": "proposée", "note": "seulement si a n'est pas ouverte (20 € ne tiennent pas avec a) ; SOL remonté de +6,4 % depuis le bas de la nuit 91,09 ; visé 1,91 % au-dessus du haut du jour 97,12 ; gain 1,50 × la perte ; gain espéré ≈ +0,45 € | perte max ≈ 0,30 € | coût ≈ 0,02 €"}, {"lettre": "c", "niveau": "risquée", "paire": "SOL-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 5, "quantite": 0.051653, "prix_entree": 96.8, "prix_vise": 98.72, "prix_arret": 95.84, "heure_limite": "2026-10-13T15:00:00+02:00", "prevision": "SOL touche 98.72 € (+1.98 %) avant 95.84 € (−0.99 %), d'ici 2026-10-13 15h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler", "statut": "proposée", "note": "tient dans les 5 € restants après a ; aucune risquée ouverte ; visé 1,65 % au-dessus du haut du jour 97,12 ; gain 2,0 × la perte ; arrêt arrondi vers l'entrée ; gain espéré ≈ +0,10 € | perte max ≈ 0,05 € | coût ≈ 0,01 €"}], "valable_jusqua": "07:57", "statut": "active"}
```

- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : ETH +1,50 % (2 294,0) avant −1,50 % (2 226,2) d'ici 2026-10-13 15h00 ; SOL +2,25 % (98,98) avant −1,50 % (95,35) d'ici 2026-10-13 15h00 (risquée : +1,98 % à 98,72 avant −0,99 % à 95,84)
- Décision : simuler — a achat ETH 20 € à 2 260,0, prix visé 2 294,0, prix d'arrêt 2 226,2 ; c achat SOL 5 € à 96,80, visé 98,72, arrêt 95,84 ; b achat SOL 20 € simuler si place (en attente de place), visé 98,98, arrêt 95,35. D-040a : on garde (rappel 09:00 inchangé).
- Heure limite : 2026-10-13 15:00 (rappel seulement)
- Gain espéré ≈ +0,30 € (a) / +0,45 € (b) / +0,10 € (c) | perte max ≈ 0,30 / 0,30 / 0,05 € | coût aller-retour ≈ 0,02 / 0,02 / 0,01 € — réel interdit
- Avis Research : pas demandé — décision claire, pas de nouvelle info depuis le brief du 12/10 14h44
- Pourquoi : Cette nuit, l'ordinateur a gelé de 20h58 à 07h23 ; le rattrapage montre que nos 2 ventes D-051a (SOL) et D-051c (ETH) ont touché leur prix visé (+0,28 € et +0,10 €), donc 25 € sont libres. Après un creux à 02h50, les 3 cryptos sont remontées fort (BTC +3,2 %, ETH +4,9 %, SOL +6,4 %) et sont au plus haut du jour : je propose de petits achats ETH et SOL pour suivre cette remontée, avec confiance faible car on achète en haut. BTC D-040a va dans notre sens, à 0,73 % de son visé. Avis Research pas demandé : décision claire, pas de nouvelle info depuis le brief d'hier.

**Trades ouverts revus**
- D-040a achat BTC 25 € : prix 74 878 (+1,30 %), visé 75 426 à 0,73 %, on garde ; rappel 2026-10-13 09:00 inchangé.
- D-051a vente SOL et D-051c vente ETH : fermées au prix visé pendant la nuit (rattrapage du trou 20h58–07h23).

**D-052a — Prudente (simuler)**
- Achat ETH 20 € (0,00885 ETH) @ 2 260,0 → visé 2 294,0 / arrêt 2 226,2 / rappel 2026-10-13 15:00
- Visé 1,10 % au-dessus du haut du jour 2 269,07.

**D-052b — Équilibrée (simuler si place)**
- Achat SOL 20 € (0,206612 SOL) @ 96,80 → visé 98,98 / arrêt 95,35 / rappel 2026-10-13 15:00
- Visé 1,91 % au-dessus du haut du jour 97,12. Seulement si a n'est pas ouverte.

**D-052c — Risquée (simuler, 5 €)**
- Achat SOL 5 € (0,051653 SOL) @ 96,80 → visé 98,72 / arrêt 95,84 / rappel 2026-10-13 15:00
- Visé 1,65 % au-dessus du haut du jour 97,12.

- 07h28 PM-Predict — sonnette occupe (zones Z-ETH-2260.5 + Z-SOL-96.95, mouvement, sans décision 4 h) : déjà traité dans D-052

**Suivi PM-Risk 07:29** — a et c simulées, b pas simulée ; exposition 50/50 € (D-040a 25 + D-052a 20 + D-052c 5)

```json
{"suivi": "D-052", "proposition": "a", "heure": "2026-10-13T07:29:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "achat ETH 20 € (0,00885) à 2260,0 (marché 2262,8, +0,12 %), arrêt 2226,2 (1,50 %), visé 2294,0 ; rappel 13/10 15h00 ; bas 2 h 2231,47 (05h30), haut 2 h 2269,07 (07h23) — règle d'attente non applicable aux achats ; position rx-paper-2026-10-13T052909Z-7311633d"}
```

```json
{"suivi": "D-052", "proposition": "b", "heure": "2026-10-13T07:29:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "seulement si la prudente n'était pas ouverte (a ouverte) ; pas de place sous le plafond 50 €"}
```

```json
{"suivi": "D-052", "proposition": "c", "heure": "2026-10-13T07:29:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "achat SOL 5 € (0,051653) à 96,80 (marché 97,09, +0,30 %, à la limite du seuil), arrêt 95,84 (0,99 %), visé 98,72 (gain 2×) ; rappel 13/10 15h00 ; bas 2 h 95,60 (05h29), haut 2 h 97,09 (07h22) ; exposition après 50/50 € ; position rx-paper-2026-10-13T052909Z-a03d58a6"}
```

### 2026-10-13 09:15 | SOL-EUR + BTC-EUR + ETH-EUR | D-053 — Passage 9h : nuit en hausse, petit repli ; D-040a gardée ; 3 achats si place

```json
{"id": "D-053", "heure": "2026-10-13T09:15:00+02:00", "paires": ["SOL-EUR", "BTC-EUR", "ETH-EUR"], "declencheur": {"type": "nuit", "detail": "Passage du matin 9h — nuit depuis hier 20h58 : BTC +1,34 % · ETH +0,50 % · SOL +0,43 % ; ce matin depuis 07h23 léger repli BTC −0,29 % · ETH −0,20 % · SOL −0,47 %"}, "resume": "Passage 9h : nuit en hausse, petit repli ; D-040a gardée ; 3 achats si place (plafond plein)", "type": "propositions", "prix_releves": {"heure": "09:15", "BTC-EUR": 74782.635, "ETH-EUR": 2261.125, "SOL-EUR": 96.74}, "haut_bas_jour": {"BTC-EUR": {"haut": 75000.0, "bas": 72555.0}, "ETH-EUR": {"haut": 2269.07, "bas": 2157.33}, "SOL-EUR": {"haut": 97.195, "bas": 91.09}}, "place_libre_eur": 0, "reel_permis": false, "reel_raison": "aucune sorte n'a passé le test du passé ; hors 15h–17h", "avis_research": "pas demandé : passage 9h ; dernier brief Research 12/10 14h44 (3 idées à la hausse) — pas de brief du jour encore", "pourquoi": "Nuit en hausse depuis hier soir (BTC +1,34 %, ETH +0,50 %, SOL +0,43 %), puis petit repli ce matin (surtout SOL −0,47 %). Rappel 09h00 passé pour D-040a : BTC à 74 783 € est encore au-dessus de l'entrée 73 918 (+1,17 %) et à 0,86 % du visé 75 426 → idée pas morte, on garde avec nouveau rappel 15h00. D-052a ETH et D-052c SOL ouvertes ce matin restent vivantes (prix à plat). Place libre 0 €. Pas de vente ETH ni SOL (achats déjà ouverts sur ces paires). On propose 3 achats sur petit repli, en attente de place. Confiance faible (on a acheté près des hauts cette nuit).", "ouverts_revus": [{"id": "D-040a", "verdict": "vivante", "texte": "achat BTC 25 € ; entrée 73918, visé 75426, arrêt 72468, rappel 09h00 passé ; prix 74783 (+1,17 %) — idée pas morte ; nouveau rappel 15h00"}, {"id": "D-052a", "verdict": "vivante", "texte": "achat ETH 20 € ; entrée 2260, visé 2294, arrêt 2226,2, rappel 15h00 ; prix 2261.12 (+0,05 %) — idée pas morte ; on laisse le rappel 15h00"}, {"id": "D-052c", "verdict": "vivante", "texte": "achat SOL 5 € ; entrée 96,80, visé 98,72, arrêt 95,84, rappel 15h00 ; prix 96.74 (−0,06 %) — idée pas morte (écart négligeable) ; on laisse le rappel 15h00"}], "propositions": [{"lettre": "a", "niveau": "prudente", "paire": "SOL-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 25, "quantite": 0.259067, "prix_entree": 96.5, "prix_vise": 97.95, "prix_arret": 95.06, "heure_limite": "2026-10-13T17:00:00+02:00", "prevision": "SOL touche 97.95 € (+1.50 %) avant 95.06 € (−1.49 %), d'ici 2026-10-13 17h00", "confiance": {"mot": "faible", "pct": 53}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "prioritaire dès ~25 € libres (ex. D-040a au visé) ; SOL −0,47 % depuis 07h23 ; visé 0,78 % au-dessus du haut du jour 97,195 ; gain ≈ perte ; D-052c déjà 5 € SOL hausse ; gain espéré ≈ +0,37 € | perte max ≈ 0,37 € | coût ≈ 0,02 €"}, {"lettre": "b", "niveau": "équilibrée", "paire": "BTC-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 20, "quantite": 0.000268, "prix_entree": 74650.0, "prix_vise": 76330.0, "prix_arret": 73531.0, "heure_limite": "2026-10-13T17:00:00+02:00", "prevision": "BTC touche 76330.0 € (+2.25 %) avant 73531.0 € (−1.50 %), d'ici 2026-10-13 17h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "D-040a déjà ouvert 25 € BTC ; seulement si place ; nuit BTC +1,34 % depuis hier 20h58 ; gain 1,50 × la perte ; gain espéré ≈ +0,45 € | perte max ≈ 0,30 € | coût ≈ 0,02 €"}, {"lettre": "c", "niveau": "risquée", "paire": "SOL-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 10, "quantite": 0.103627, "prix_entree": 96.5, "prix_vise": 98.43, "prix_arret": 95.54, "heure_limite": "2026-10-13T17:00:00+02:00", "prevision": "SOL touche 98.43 € (+2.00 %) avant 95.54 € (−0.99 %), d'ici 2026-10-13 17h00", "confiance": {"mot": "faible", "pct": 52}, "decision": "simuler_si_place", "statut": "en_attente_de_place", "note": "une risquée déjà ouverte (D-052c) → seulement après sa fermeture ; arrêt ≤1 %, gain ≈ 2× ; gain espéré ≈ +0,20 € | perte max ≈ 0,10 € | coût ≈ 0,01 €"}], "valable_jusqua": "09:45", "statut": "active"}
```

- Idée : à la hausse
- Sens : Achat
- Prévision mesurable : SOL +1,50 % (97.95) avant −1,49 % (95.06) d'ici 17h00 ; BTC +2,25 % (76330) avant −1,50 % (73531) d'ici 17h00 (risquée SOL : +2,00 % à 98.43 avant −0,99 % à 95.54)
- Décision : simuler si place (en attente de place) — a achat SOL 25 € à 96.5, visé 97.95, arrêt 95.06 ; b achat BTC 20 € à 74650, visé 76330, arrêt 73531 ; c achat SOL 10 € à 96.5, visé 98.43, arrêt 95.54 (après fermeture D-052c). D-040a : on garde, nouveau rappel 15:00. D-052a/c : on laisse.
- Heure limite : 2026-10-13 17:00 (rappel seulement)
- Gain espéré ≈ +0,37 € (a) / +0,45 € (b) / +0,19 € (c) | perte max ≈ 0,37 / 0,30 / 0,10 € | coût aller-retour ≈ 0,02 / 0,02 / 0,01 € — réel interdit
- Avis Research : pas demandé — passage 9h ; dernier brief 12/10 14h44 (3 hausses) ; pas de brief du jour encore
- Pourquoi : Nuit en hausse depuis hier soir (BTC +1,34 %, ETH +0,50 %, SOL +0,43 %), puis petit repli ce matin (surtout SOL −0,47 %). Rappel 09h00 passé pour D-040a : BTC à 74 783 € est encore au-dessus de l'entrée 73 918 (+1,17 %) et à 0,86 % du visé 75 426 → idée pas morte, on garde avec nouveau rappel 15h00. D-052a ETH et D-052c SOL ouvertes ce matin restent vivantes (prix à plat). Place libre 0 €. Pas de vente ETH ni SOL (achats déjà ouverts sur ces paires). On propose 3 achats sur petit repli, en attente de place. Confiance faible (on a acheté près des hauts cette nuit).

**Trades ouverts revus**
- D-040a achat BTC 25 € : prix 74783 (+1,17 %), visé à 0,86 %, on garde, nouveau rappel 15:00.
- D-052a achat ETH 20 € : prix 2261.12 (+0,05 %), vivante, rappel 15:00.
- D-052c achat SOL 5 € : prix 96.74 (−0,06 %), vivante, rappel 15:00.

**D-053a — Prudente (simuler si place)**
- Achat SOL 25 € (0.259067 SOL) @ 96.5 → visé 97.95 / arrêt 95.06 / rappel 2026-10-13 17:00
- Visé 0,78 % au-dessus du haut du jour 97,195. Prioritaire dès ~25 € libres.

**D-053b — Équilibrée (simuler si place)**
- Achat BTC 20 € (0.000268 BTC) @ 74650 → visé 76330 / arrêt 73531 / rappel 2026-10-13 17:00
- D-040a déjà ouvert ; seulement si place.

**D-053c — Risquée (simuler si place ; après D-052c)**
- Achat SOL 10 € (0.103627 SOL) @ 96.5 → visé 98.43 / arrêt 95.54 / rappel 2026-10-13 17:00
- Une risquée déjà ouverte (D-052c) → seulement après sa fermeture.


### Suivi PM-Risk 09:15 — D-053
```json
{"suivi": {"id": "D-053", "heure": "2026-10-13T09:15+02:00", "D-040a": "garder, rappel 15:00", "a": "refusé, pas de place (50/50 €)", "b": "refusé, pas de place", "c": "refusé, D-052c risquée encore ouverte et pas de place", "mode": "simulation"}}
```

```json
{"suivi": {"date": "2026-10-13T10:37:00+02:00", "type": "arret_experience", "raison": "arrêt expérience (Quentin)", "fermetures": [{"decision_id": "D-040a", "pair": "BTC-EUR", "position_id": "rx-paper-2026-10-10T060455Z-b93c34c9", "prix_entree": 73917.97, "prix_sortie": 74907.65, "pnl_eur": 0.309555}, {"decision_id": "D-052a", "pair": "ETH-EUR", "position_id": "rx-paper-2026-10-13T052909Z-7311633d", "prix_entree": 2260.0, "prix_sortie": 2261.94, "pnl_eur": -0.002841}, {"decision_id": "D-052c", "pair": "SOL-EUR", "position_id": "rx-paper-2026-10-13T052909Z-a03d58a6", "prix_entree": 96.8, "prix_sortie": 96.84, "pnl_eur": -0.002935}], "pnl_fermetures_eur": 0.303779, "positions_ouvertes": 0, "cash_eur": 499.030271, "equity_eur": 499.030271, "total_pnl_eur": -0.9697, "stop": "/workspace/predict-market-bot/STOP", "watcher": "arrêté (watch_stops pid 2421281 sorti seul en idle à 10:36:58, 0 position)", "mode": "paper"}}
```
