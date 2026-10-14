# Score Predictions (mesurable)

Après chaque **horizon** (ou après une vente liée), Compound note :
- **gagné** = le prix a touché le seuil dans le sens prévu avant la fin d’horizon
- **perdu** = le prix a touché le seuil inverse (ou l’horizon finit contre)
- **annulé** = pas de trade / hors horizon / décision non mesurable

Predict doit écrire dans chaque décision : **direction + horizon + seuil %** (ex. BTC +1,5 % / −1,5 % avant 20h).

## Totaux (mis à jour par Compound)
- 2026-10-13T09:15:00+02:00 D-053a/b/c : **en attente** (passage 9h ; D-040a GARDER rappel 15h00 ; D-052a/c vivantes ; plafond plein ; achat SOL 25 € / BTC 20 € si place / SOL 10 € après D-052c) — horizon 17h00 le 13/10
- 2026-10-13T07:27:00+02:00 D-052a/b/c : **en attente** (zone Z-BTC-74120 ; D-051a/c fermées au visé cette nuit ; D-040a GARDER ; 25 € libres ; achat ETH 20 € / achat SOL 20 € si place / achat SOL 5 €) — horizon 15h00 le 13/10
- 2026-10-12T20:46:00+02:00 D-051a/b/c : **en attente** (heure_limite D-040a GARDER ; D-049a idée morte ; 25 € libres après fermeture ; vente SOL 20 € / vente ETH 20 € si place / vente ETH 5 €) — horizon 09h00 le 13/10
- 2026-10-12T15:25:00+02:00 D-050 : **scoré** — BTC **perdu**, ETH **perdu**, SOL D-050a **gagné** (Compound 20h48)
- 2026-10-12T14:45:00+02:00 D-049a/b/c : **scoré** — a **annulé** (fermé idée morte −0,20 €) ; b/c **annulés** (pas simulées)
- 2026-10-12T09:11:00+02:00 D-048a/b/c : **annulés** (pas simulées, plafond plein)
- 2026-10-12T07:33:00+02:00 D-047a/b/c : **scoré** — a **annulé** (idée morte −0,10 €) ; b **annulé** ; c **gagné** (+0,19 € cible)
- 2026-10-11T14:18:00+02:00 D-046a/b/c : **en attente** (heure_limite D-040a GARDER ; D-043a GARDER ; plafond plein 0 € ; 3 achats SOL/BTC) — horizon 22h00 le 11/10
- 2026-10-11T11:03:00+02:00 D-045a/b/c : **en attente** (zone Z-SOL-97.79 ; plafond plein 0 € ; achat SOL plus bas après cassure D-044) — horizon 18h00 le 11/10
- 2026-10-11T09:04:00+02:00 D-044a/b/c : **en attente** (passage 9h ; plafond plein 0 € ; 3 achats SOL/BTC nuit calme) — horizon 18h00 le 11/10
- 2026-10-10T09:05:00+02:00 D-041a/b/c : **en attente** (passage 9h ; plafond plein 0 € ; 3 achats rebond SOL/BTC) — horizon 16h00 le 10/10
- 2026-10-10T07:59:00+02:00 D-040a/b/c : **en attente** (zone Z-SOL-98.03 ; plafond plein ; 3 achats rebond BTC/SOL ; D-031b idée morte) — horizon 16h00 le 10/10
- 2026-10-10T02:55:00+02:00 D-039a/b/c : **en attente** (mouvement SOL +0,5 % ; plafond plein ; 3 ventes ETH) — horizon 12h00 le 10/10
- 2026-10-10T00:03 D-036a/b/c : **en attente** (plafond plein ; heure_limite D-024b GARDER ; D-031a idée morte) — horizon 10h00 le 10/10
- 2026-10-09T21:39 D-035a/b/c : **en attente** (plafond plein ; mouvement SOL −0,51 %) — horizon 10h00 le 10/10

| gagné | perdu | annulé | taux de réussite (gagné / (gagné+perdu)) |
|------:|------:|-------:|------------------------------------------:|
| 6 | 10 | 25 | 38 % (6 / 16) |

## Entrées

### 2026-10-12 | R-BTC | BTC-EUR (Research)
- Prévision : UP / horizon 17h00 / cible 75 020 · arrêt 73 172 · départ 73 911
- Résultat : **annulé**
- Prix à l’échéance : ~73 852 € à 17h00 — aucun seuil (haut séance ~74 285)
- Note (1 ligne) : idée hausse brief 14h44 ; pas simulée (D-040a déjà ouverte / plafond) ; coût 0 €

### 2026-10-12 | R-ETH | ETH-EUR (Research)
- Prévision : UP / horizon 17h00 / cible 2 295 · arrêt 2 239 · départ 2 261
- Résultat : **annulé**
- Prix à l’échéance : ~2 257 € à 17h00 — aucun seuil (haut séance ~2 272)
- Note (1 ligne) : idée hausse brief 14h44 ; pas simulée (D-049a déjà ouverte / plafond) ; coût 0 €

### 2026-10-12 | R-SOL | SOL-EUR (Research)
- Prévision : UP / horizon 17h00 / cible 100,11 · arrêt 97,16 · départ 98,63
- Résultat : **perdu**
- Prix : arrêt 97,16 touché à 16h40 (97,11 €) ; idée **non simulée** (plafond plein) — idée Research manquée, coût 0 €
- Note (1 ligne) : Predict était en désaccord (baisse D-050a, gagnée)

**Research du 12 oct. (mesurable) : 0 gagné / 1 perdu / 2 annulés.**


### 2026-10-12 | D-051a | SOL-EUR
- Prévision : DOWN / horizon 2026-10-13 09h00 CEST / −1.50 % avant +1.49 % (cible 95.08 · inverse 97.97)
- Prix départ (entrée prévue) : 96.53 €
- Résultat : en attente
- Note (1 ligne) : prudente vente 20 € ; simuler ; Research pas demandé

### 2026-10-12 | D-051b | ETH-EUR
- Prévision : DOWN / horizon 2026-10-13 09h00 CEST / −1.50 % avant +1.00 % (cible 2217.7 · inverse 2274.0)
- Prix départ (entrée prévue) : 2251.5 €
- Résultat : en attente
- Note (1 ligne) : équilibrée vente 20 € ; simuler_si_place ; Research pas demandé

### 2026-10-12 | D-051c | ETH-EUR
- Prévision : DOWN / horizon 2026-10-13 09h00 CEST / −2.00 % avant +1.00 % (cible 2206.4 · inverse 2274.0)
- Prix départ (entrée prévue) : 2251.5 €
- Résultat : en attente
- Note (1 ligne) : risquée vente 5 € ; simuler ; Research pas demandé

### 2026-10-12 | D-050-BTC | BTC-EUR
- Prévision : DOWN / horizon 17h00 CEST / −0.50 % avant +0.50 % (cible 73450 · inverse 74188)
- Prix départ : 73818.96 €
- Résultat : **perdu**
- Note (1 ligne) : seuil inverse +0,50 % touché à 16h06 (74 202 €) avant −0,50 % ; ticks 30 s

### 2026-10-12 | D-050-ETH | ETH-EUR
- Prévision : DOWN / horizon 17h00 CEST / −0.50 % avant +0.50 % (cible 2248.75 · inverse 2271.35)
- Prix départ : 2260.05 €
- Résultat : **perdu**
- Note (1 ligne) : seuil inverse +0,50 % touché à 16h10 (2 272 €) avant −0,50 % ; ticks 30 s

### 2026-10-12 | D-050a | SOL-EUR
- Prévision : DOWN / horizon 20h00 CEST / −1.50 % avant +1.49 % (cible 96.95 · inverse 99.90)
- Prix départ (entrée prévue) : 98.43 €
- Résultat : **gagné**
- Note (1 ligne) : seuil −1,50 % touché à 16h49 (96,94 €) avant +1,49 % ; ticks 30 s

### 2026-10-12 | D-049a | ETH-EUR
- Prévision : UP / horizon 20h00 CEST / +2.00 % avant −2.00 % (cible 2310.3 · inverse 2219.7)
- Prix départ (entrée prévue) : 2265.0 €
- Résultat : **annulé**
- Note (1 ligne) : horizon 20h : ni visé 2310,3 ni arrêt 2219,7 ; fermé idée morte −0,20 € à 20h48

### 2026-10-12 | D-049b | SOL-EUR
- Prévision : UP / horizon 20h00 CEST / +2.23 % avant −1.49 % (cible 100.81 · inverse 97.14)
- Prix départ (entrée prévue) : 98.61 €
- Résultat : **annulé**
- Note (1 ligne) : pas simulée (plafond plein)

### 2026-10-12 | D-049c | BTC-EUR
- Prévision : UP / horizon 20h00 CEST / +2.00 % avant −1.00 % (cible 75499.83 · inverse 73281)
- Prix départ (entrée prévue) : 74020.61 €
- Résultat : **annulé**
- Note (1 ligne) : pas simulée (plafond plein)


### 2026-10-12 | D-048a | SOL-EUR
- Prévision : UP / horizon 18h00 CEST / +2.00 % avant −1.99 % (cible 102.59 · inverse 98.57)
- Prix départ (entrée prévue) : 100.57499999999999 €
- Résultat : **annulé**
- Note (1 ligne) : pas simulée (plafond plein)

### 2026-10-12 | D-048b | ETH-EUR
- Prévision : DOWN / horizon 18h00 CEST / −2.25 % avant +1.50 % (cible 2242.94 · inverse 2328.98)
- Prix départ (entrée prévue) : 2294.57 €
- Résultat : **annulé**
- Note (1 ligne) : pas simulée (plafond plein)

### 2026-10-12 | D-048c | SOL-EUR
- Prévision : UP / horizon 18h00 CEST / +2.00 % avant −1.00 % (cible 102.59 · inverse 99.57)
- Prix départ (entrée prévue) : 100.57499999999999 €
- Résultat : **annulé**
- Note (1 ligne) : pas simulée (plafond plein)

### 2026-10-12 | D-047a | ETH-EUR
- Prévision : UP / horizon 14h00 CEST / +2.00 % avant −2.00 % (cible 2325.6 · inverse 2234.4)
- Prix départ (entrée prévue) : 2280.0 €
- Résultat : **annulé**
- Note (1 ligne) : horizon 14h : aucun seuil (haut 2299,85) ; fermé idée morte −0,10 € à 14h47

### 2026-10-12 | D-047b | SOL-EUR
- Prévision : DOWN / horizon 14h00 CEST / −2.25 % avant +1.49 % (cible 98.14 · inverse 101.9)
- Prix départ (entrée prévue) : 100.4 €
- Résultat : **annulé**
- Note (1 ligne) : pas simulée (place pour la prudente)

### 2026-10-12 | D-047c | SOL-EUR
- Prévision : DOWN / horizon 14h00 CEST / −2.00 % avant +1.00 % (cible 98.39 · inverse 101.4)
- Prix départ (entrée prévue) : 100.4 €
- Résultat : **gagné**
- Note (1 ligne) : cible 98,39 touchée à 14h42 (trou comblé) ; trade +0,19 €

### 2026-10-11 | D-046a | SOL-EUR
- Prévision : UP / horizon 22h00 CEST / +2,00 % avant −2,00 % (cible 99.96 · inverse 96.04)
- Prix départ (entrée prévue) : 98.0 €
- Résultat : en attente
- Note (1 ligne) : heure_limite D-040a garder ; plafond plein

### 2026-10-11 | D-046b | BTC-EUR
- Prévision : UP / horizon 22h00 CEST / +2,25 % avant −1,50 % (cible 75914 · inverse 73131)
- Prix départ (entrée prévue) : 74243.77 €
- Résultat : en attente
- Note (1 ligne) : en attente de place ; D-040a déjà ouvert

### 2026-10-11 | D-046c | SOL-EUR
- Prévision : UP / horizon 22h00 CEST / +2,00 % avant −1,00 % (cible 99.96 · inverse knowledge/predict_scorecard.md)
- Prix départ (entrée prévue) : 98.0 €
- Résultat : en attente
- Note (1 ligne) : risquée en attente de place ; aucune risquée ouverte


<!--
### YYYY-MM-DD | id (ex. D-007) | PAIRE
- Prévision : direction / horizon / seuils
- Prix départ :
- Résultat : gagné / perdu / annulé
- Prix à l’échéance (ou à la vente) :
- Note (1 ligne) :
-->


### 2026-10-11 | D-045a | SOL-EUR
- Prévision : UP / horizon 18h00 CEST / +2,00 % avant −2,00 % (cible 99,71 · inverse 95,80)
- Prix départ (entrée prévue) : 97,755 €
- Résultat : en attente
- Note (1 ligne) : sonnette Z-SOL-97.79 ; D-044a caduque ; achat plus bas ; plafond plein

### 2026-10-11 | D-045b | BTC-EUR
- Prévision : UP / horizon 18h00 CEST / +2,25 % avant −1,50 % (cible 75759,59 · inverse 72981,12)
- Prix départ (entrée prévue) : 74092,51 €
- Résultat : en attente
- Note (1 ligne) : en attente de place ; D-040a déjà ouvert

### 2026-10-11 | D-045c | SOL-EUR
- Prévision : UP / horizon 18h00 CEST / +2,00 % avant −1,00 % (cible 99,71 · inverse 96,78)
- Prix départ (entrée prévue) : 97,755 €
- Résultat : en attente
- Note (1 ligne) : risquée en attente de place ; aucune risquée ouverte


### 2026-10-11 | D-044a | SOL-EUR
- Prévision : UP / horizon 18h00 CEST / +2,00 % avant −2,00 % (cible 100,04 · inverse 96,12)
- Prix départ (entrée prévue) : 98,08 €
- Résultat : en attente
- Note (1 ligne) : passage 9h ; proposition en attente de place ; nuit calme SOL −0,05 %

### 2026-10-11 | D-044b | BTC-EUR
- Prévision : UP / horizon 18h00 CEST / +2,25 % avant −1,50 % (cible 75937,21 · inverse 73152,23)
- Prix départ (entrée prévue) : 74266,22 €
- Résultat : en attente
- Note (1 ligne) : passage 9h ; en attente de place ; D-040a déjà ouvert

### 2026-10-11 | D-044c | SOL-EUR
- Prévision : UP / horizon 18h00 CEST / +2,00 % avant −1,00 % (cible 100,04 · inverse 97,10)
- Prix départ (entrée prévue) : 98,08 €
- Résultat : en attente
- Note (1 ligne) : passage 9h ; risquée en attente de place ; aucune risquée ouverte




### 2026-10-10 | D-041a | SOL-EUR
- Prévision : UP / horizon 16h00 CEST / +2.00 % avant −1.50 % (cible 99.99 · inverse 96.56)
- Prix départ (entrée prévue) : 98.03 €
- Résultat : en attente
- Note (1 ligne) : passage 9h ; proposition en attente de place ; nuit SOL +1,19 %

### 2026-10-10 | D-041b | BTC-EUR
- Prévision : UP / horizon 16h00 CEST / +2.25 % avant −1.50 % (cible 75505.98 · inverse 72736.81)
- Prix départ (entrée prévue) : 73844.47 €
- Résultat : en attente
- Note (1 ligne) : passage 9h ; en attente de place ; D-040a déjà ouvert

### 2026-10-10 | D-041c | SOL-EUR
- Prévision : UP / horizon 16h00 CEST / +2.00 % avant −1.00 % (cible 99.99 · inverse 97.05)
- Prix départ (entrée prévue) : 98.03 €
- Résultat : en attente
- Note (1 ligne) : passage 9h ; risquée en attente de place ; aucune risquée ouverte

### 2026-10-10 | D-036a | SOL-EUR
- Prévision : DOWN / horizon 10h00 CEST / −2,00 % avant +2,00 % (cible 95.10 · inverse 98.98)
- Prix départ (entrée prévue) : 97.04 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; D-024b GARDER ; D-031a idée morte (libère ~15 €)

### 2026-10-10 | D-036b | ETH-EUR
- Prévision : DOWN / horizon 10h00 CEST / −2,25 % avant +1,50 % (cible 2165.21 · inverse 2248.27)
- Prix départ (entrée prévue) : 2215.05 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; prolonge D-024b/D-028a

### 2026-10-10 | D-036c | SOL-EUR
- Prévision : DOWN / horizon 10h00 CEST / −2,00 % avant +1,00 % (cible 95.10 · inverse 98.01)
- Prix départ (entrée prévue) : 97.04 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; aucune risquée ouverte

### 2026-10-09 | D-034a | ETH-EUR
- Prévision : DOWN / horizon 22h00 CEST / −1,80 % avant +1,80 % (cible 2,176.80 · inverse 2,256.60)
- Prix départ (entrée prévue) : 2,216.70 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place (plafond 50 € plein) ; vente après baisse −0,64 % depuis D-033

### 2026-10-09 | D-034b | SOL-EUR
- Prévision : DOWN / horizon 22h00 CEST / −2,25 % avant +1,50 % (cible 95.51 · inverse 99.18)
- Prix départ (entrée prévue) : 97.71 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; SOL déjà −1,61 % depuis le haut du jour

### 2026-10-09 | D-034c | ETH-EUR
- Prévision : DOWN / horizon 22h00 CEST / −2,00 % avant +1,00 % (cible 2,172.37 · inverse 2,238.87)
- Prix départ (entrée prévue) : 2,216.70 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; aucune risquée ouverte



### 2026-10-09 | D-033a | BTC-EUR
- Prévision : UP / horizon 22h00 CEST / ±1.50 % (cible 75,205 · inverse 72,982)
- Prix départ (entrée prévue) : 74,093.67 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place (plafond 50 € plein) ; pas encore ouverte

### 2026-10-09 | D-033b | ETH-EUR
- Prévision : DOWN / horizon 22h00 CEST / cible 2 180,00 (−2.25 %) · inverse 2 264,00 (+1.50 %)
- Prix départ (entrée prévue) : 2,231.07 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; vente après rebond +0,5 % depuis D-031

### 2026-10-09 | D-033c | BTC-EUR
- Prévision : UP / horizon 22h00 CEST / +2.00 % / −1.00 % (cible 75,576 · inverse 73,353)
- Prix départ (entrée prévue) : 74,093.67 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; aucune risquée ouverte

### 2026-10-09 | D-030a | SOL-EUR
- Prévision : DOWN / horizon 22h00 CEST / ±1.59 % (cible 96.50 · inverse 99.61)
- Prix départ (entrée prévue) : 98.055 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place (plafond 50 € plein) ; pas encore ouverte

### 2026-10-09 | D-030b | ETH-EUR
- Prévision : DOWN / horizon 22h00 CEST / cible 2,173.32 (−2,25 %) · inverse 2,256.70 (+1,5 %)
- Prix départ (entrée prévue) : 2,223.35 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; pas encore ouverte

### 2026-10-09 | D-030c | SOL-EUR
- Prévision : DOWN / horizon 22h00 CEST / −2 % / +1 % (cible 96.09 · inverse 99.04)
- Prix départ (entrée prévue) : 98.055 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; aucune risquée ouverte

### 2026-10-09 | D-025a | SOL-EUR
- Prévision : UP / horizon 22h00 CEST / ±2 % (cible 99.16 · inverse 95.28)
- Prix départ (entrée prévue) : 97.22 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place (plafond 50 € plein) ; pas encore ouverte

### 2026-10-09 | D-025b | ETH-EUR
- Prévision : DOWN / horizon 22h00 CEST / cible 2,168 (−2,25 %) · inverse 2,251 (+1,5 %)
- Prix départ (entrée prévue) : 2,217.97 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; pas encore ouverte

### 2026-10-09 | D-025c | BTC-EUR
- Prévision : UP / horizon 22h00 CEST / +2 % / −1 % (cible 74,511 · inverse 72,320)
- Prix départ (entrée prévue) : 73,050 €
- Résultat : en attente
- Note (1 ligne) : risquée conditionnelle (après fermeture D-023) ; pas encore ouverte



### 2026-10-09 | D-032a | SOL-EUR
- Prévision : UP / horizon 20h00 CEST / ±2 % (cible 99.80 · inverse 95.88)
- Prix départ : 97.84 €
- Résultat : **annulé**
- Prix à l’échéance (ou à la vente) : —
- Note (1 ligne) : version annulée (ancienne D-025 15h40) — numérotation finale

### 2026-10-09 | D-032b | ETH-EUR
- Prévision : DOWN / horizon 20h00 CEST / cible 2165.7 (−2,25 %) · arrêt 2248.7 (+1,5 %)
- Prix départ : 2215.51 €
- Résultat : **annulé**
- Prix à l’échéance (ou à la vente) : —
- Note (1 ligne) : version annulée

### 2026-10-09 | D-032c | SOL-EUR
- Prévision : UP / horizon 20h00 CEST / +2 % (cible 99.80) · arrêt −1 % (96.86)
- Prix départ : 97.84 €
- Résultat : **annulé**
- Prix à l’échéance (ou à la vente) : —
- Note (1 ligne) : version annulée

### 2026-10-07 | D-007 | BTC-EUR
- Prévision : UP / horizon 22h00 CEST / ±1,5 % (cible 75248,59 · inverse 73024,49)
- Prix départ : 74136,54 €
- Résultat : annulé
- Prix à l’échéance (ou à la vente) : 74503,86 € à 22h00 (+0,49 %)
- Note (1 ligne) : aucun seuil touché (bas 73988,88 · haut 74742,20) ; fini dans le bon sens mais sous la cible → ni gagné ni perdu

### 2026-10-07 | D-008 | ETH-EUR
- Prévision : DOWN / horizon 22h00 CEST / ±1,5 % (cible 2251,90 · inverse 2320,48)
- Prix départ : 2286,19 €
- Résultat : perdu
- Prix à l’échéance (ou à la vente) : 2296,09 € à 22h00 (+0,43 %)
- Note (1 ligne) : aucun seuil touché (bas 2266,60 · haut 2304,52) ; horizon fini contre la prévision (baisse prévue, prix monté)

### 2026-10-07 | D-009 | SOL-EUR
- Prévision : UP / horizon 22h00 CEST / ±1,5 % (cible 104,97 · inverse 101,87)
- Prix départ : 103,42 €
- Résultat : annulé
- Prix à l’échéance (ou à la vente) : 103,46 € à 22h00 (+0,04 %)
- Note (1 ligne) : aucun seuil touché (bas 103,27 · haut 104,72) ; quasi à plat → ni gagné ni perdu

### 2026-10-07 | D-004 / D-005 / D-006 | BTC / ETH / SOL
- Prévision : aucune (pas de direction + horizon + seuil) ; contexte « attendre la Fed »
- Résultat : annulé (3) — soirée Fed passée, rien de mesurable
- Note (1 ligne) : D-002 / D-003 notés **annulé** le 9 oct 20h32 (échéance ~11h30 passée ; rien de mesurable)

### 2026-10-07 | D-010 / D-011 / D-012 | BTC / ETH / SOL
- Prévision : annulée par Predict (pas de prix frais à 19h48)
- Résultat : annulé (3)

> Vérif 22h40 : ticks du fichier (16h23–17h25 puis 21h06–22h00) + bougies 1 min Binance 15h48–22h00 pour combler les trous (15h48–16h23, 17h25–21h06). Aucun seuil ±1,5 % touché sur les trois paires.

### 2026-10-08 | D-015 | BTC-EUR
- Prévision : DOWN / horizon 17h00 CEST / ±0.5 % (cible 73191.54 · inverse 73927.14)
- Prix départ : 73559.34 € (14:34)
- Résultat : **gagné**
- Prix à l’échéance (ou à la vente) : 73726,81 € à 17h00 (relevé 30 s) · bas 73058,41 à 15h43 · haut 73821,94 à 15h22 (arrêt 73927,14 jamais touché)
- Note (1 ligne) : cible 73191,54 touchée à **15h42** (73183,22, relevé 30 s ; bougie 1 min Binance aussi 15h42) — Predict notait « pas encore » à 15h41, c’était juste une minute trop tôt

### 2026-10-08 | D-016 | ETH-EUR
- Prévision : DOWN / horizon 17h00 CEST / ±0.5 % (cible 2250.60 · inverse 2273.22)
- Prix départ : 2261.91 € (14:34)
- Résultat : **gagné**
- Prix à l’échéance (ou à la vente) : 2257,19 € à 17h00 (relevé 30 s) · bas 2239,15 à 15h46 · haut 2271,33 à 15h21 (arrêt 2273,22 jamais touché, à 1,9 € près)
- Note (1 ligne) : cible 2250,60 touchée à **15h39** (2249,94, relevé 30 s) ; la bougie 1 min Binance montre déjà une mèche à 2250,00 à 14h50 (un instant, peu de volume) → gagné dans les deux cas ; haut avant la cible 2271,3 < 2273,22 confirmé

### 2026-10-08 | D-017 | SOL-EUR
- Prévision : DOWN / horizon 17h00 CEST / ±0.5 % (cible 100.20 · inverse 101.20)
- Prix départ : 100.70 € (14:34)
- Résultat : **gagné**
- Prix à l’échéance (ou à la vente) : 100,29 € à 17h00 (relevé 30 s) · bas 99,42 à 15h43 · haut 100,86 à 14h43 (arrêt 101,20 jamais touché)
- Note (1 ligne) : cible 100,20 touchée à **15h02** (100,02, relevé 30 s ; bougie 1 min Binance dès 15h01)

> Vérif 2026-10-08 ~21h30 (Compound) : relevé 30 s complet 14h34–17h00 (aucun trou > 90 s, 294 points par paire) + bougies 1 min Binance (EUR) 14h34–17h00. Premier seuil touché = cible baissière pour les trois ; aucun prix d’arrêt touché. D-002 / D-003 : pas de direction ni de seuil → seront « annulé » à leur échéance (9 oct ~11h30), pas encore comptés.


### D-021 — SOL-EUR (simulation de nuit)
- Prévision : DOWN / horizon 2026-10-09 10:00 CEST / −1,5 % avant +1,5 % (cible 96,53 · inverse 99,47)
- Prix départ : 98,00 € (22:57)
- Résultat : **perdu**
- Prix à l’échéance : 98,36 € à 10h00 (au-dessus du prix de départ, donc contre nous) ; ni cible 96,53 ni arrêt 99,47 touchés avant 10h00
- Note (1 ligne) : à l’heure limite le prix allait contre la prévision → perdu (demande de Quentin, notée le 9 oct à 14h26)

### D-023 — BTC-EUR (simulation)
- Prévision : UP / horizon 2026-10-09 17:00 CEST / +1,5 % avant −1 % (cible 75 232 · inverse 73 379)
- Prix départ : 74 120 € (14:29)
- Résultat : **perdu**
- Prix à l’échéance (ou à la vente) : 73 928 € à 17h09 (fermeture idée morte) · à 17h00 mid ≈ 74 119 €
- Note (1 ligne) : ni cible 75 232 ni arrêt 73 379 touchés (haut ticks ~74 349 · creux ~73 663) ; à 17h00 prix ≈ départ → puis fermeture un peu contre ; score perdu


### D-024a — SOL-EUR (prudente, simulation)
- Prévision : UP / horizon 2026-10-09 17:00 CEST / +1,42 % avant −1,41 % (cible 100,09 · inverse 97,30)
- Prix départ : 98,69 € (15:07)
- Résultat : **perdu**
- Prix à l’échéance (ou à la vente) : 97,49 € à 15h43 (fermeture idée morte) · à 17h00 mid 98,25 €
- Note (1 ligne) : ni cible 100,09 ni arrêt 97,30 touchés avant fermeture ; à 17h00 prix sous le départ (98,69→98,25) → perdu


### D-024b — ETH-EUR (équilibrée, simulation)
- Prévision : DOWN / horizon 2026-10-09 17:00 CEST / −1,60 % avant +1,00 % (cible 2 197 · inverse 2 255)
- Prix départ : 2 232,70 € (15:07)
- Résultat : **annulé**
- Prix à l’échéance (ou à la vente) : 2 223,70 € à 17h00 (relevé 30 s) — trade encore ouvert après rappel
- Note (1 ligne) : aucun seuil touché avant 17h00 ; prix un peu dans le bon sens (2 232,70→2 223,70) mais sous la cible → annulé ; le trade simu reste ouvert (rappel seulement)


### D-024c — SOL-EUR (risquée, pas simulée)
- Prévision : UP / horizon 2026-10-09 17:00 CEST / +2,04 % avant −1,00 % (cible 100,70 · inverse 97,70)
- Prix départ : 98,69 € (15:07)
- Résultat : **perdu**
- Prix à l’échéance (ou à la vente) : arrêt 97,70 touché à 15h36:59 (mid 97,70) — proposition non ouverte
- Note (1 ligne) : premier seuil = arrêt (UP) ; refus Risk (plafond) UTILE : aurait perdu ~0,10 €


### D-026a — SOL-EUR (prudente, simulation)
- Prévision : DOWN / horizon 2026-10-09 22:00 CEST / −1.5 % avant +1.5 % (cible 96.23 · inverse 99.17)
- Prix départ : 97.70 € (15:36)
- Résultat : en attente

### D-026b — SOL-EUR (équilibrée, simulation)
- Prévision : DOWN / horizon 2026-10-09 22:00 CEST / −1.5 % avant +1.0 % (cible 96.23 · inverse 98.68)
- Prix départ : 97.70 € (15:36)
- Résultat : en attente

### D-026c — SOL-EUR (risquée, simulation)
- Prévision : DOWN / horizon 2026-10-09 22:00 CEST / −2.0 % avant +1.0 % (cible 95.75 · inverse 98.68)
- Prix départ : 97.70 € (15:36)
- Résultat : **perdu**
- Prix à l’échéance (ou à la vente) : 98,51 € à 16h22 (arrêt touché)
- Note (1 ligne) : arrêt 98,47 touché avant cible 95,54 (creux pendant ouverture ~97,54) → perdu ; trade réel simu −0,11 €


### D-027a — BTC-EUR (prudente, simulation)
- Prévision : DOWN / horizon 2026-10-09 18:00 CEST / −1,5 % avant +1,5 % (cible 72663.14 · inverse 74876.24)
- Prix départ : 73769.69 € (15:38)
- Résultat : **annulé**
- Prix à l’échéance (ou à la vente) : —
- Note (1 ligne) : décision annulée (doublon / contraire à D-023) — numérotation finale Predict


### D-027b — SOL-EUR (équilibrée, simulation)
- Prévision : DOWN / horizon 2026-10-09 18:00 CEST / −1,5 % avant +1,0 % (cible 96.23 · inverse 98.672)
- Prix départ : 97.695 € (15:38)
- Résultat : **annulé**
- Prix à l’échéance (ou à la vente) : —
- Note (1 ligne) : décision annulée (doublon)


### D-027c — BTC-EUR (risquée, pas simulée)
- Prévision : DOWN / horizon 2026-10-09 18:00 CEST / −2,0 % avant +1,0 % (cible 72294.3 · inverse 74507.39)
- Prix départ : 73769.69 € (15:38)
- Résultat : **annulé**
- Prix à l’échéance (ou à la vente) : —
- Note (1 ligne) : décision annulée (doublon)


### D-028a — ETH-EUR (prudente, pas simulée — place)
- Prévision : DOWN / horizon 2026-10-09 22:00 CEST / −2,0 % avant +2,0 % (cible 2,180.60 · inverse 2,269.60)
- Prix départ : 2,225.10 € (16:23)
- Résultat : en attente

### D-028b — SOL-EUR (équilibrée, pas simulée — après D-026)
- Prévision : UP / horizon 2026-10-09 22:00 CEST / +2,25 % avant −1,5 % (cible 100.59 · inverse 96.90)
- Prix départ : 98.38 € (16:23)
- Résultat : en attente

### D-028c — BTC-EUR (risquée, pas simulée — risquée D-026 ouverte)
- Prévision : UP / horizon 2026-10-09 22:00 CEST / +2,0 % avant −1,0 % (cible 75,877.80 · inverse 73,646.10)
- Prix départ : 74,390.00 € (16:23)
- Résultat : **perdu**
- Prix à l’échéance (ou à la vente) : arrêt 73 646 touché à 20h32:59 (mid 73 621) — proposition non ouverte
- Note (1 ligne) : premier seuil = arrêt (UP) avant 22h ; refus Risk UTILE : aurait perdu ~0,08 €


### D-029a — SOL-EUR (prudente, pas simulée — place)
- Prévision : UP / horizon 2026-10-09 22:00 CEST / +2,0 % avant −2,0 % (cible 100,60 · inverse 96,66)
- Prix départ : 98,63 € (16:35)
- Résultat : en attente

### D-029b — ETH-EUR (équilibrée, pas simulée — place)
- Prévision : DOWN / horizon 2026-10-09 22:00 CEST / −2,25 % avant +1,5 % (cible 2 179,90 · inverse 2 263,53)
- Prix départ : 2 230,08 € (16:35)
- Résultat : en attente

### D-029c — SOL-EUR (risquée, pas simulée — place)
- Prévision : UP / horizon 2026-10-09 22:00 CEST / +2,0 % avant −1,0 % (cible 100,60 · inverse 97,64)
- Prix départ : 98,63 € (16:35)
- Résultat : **perdu**
- Prix à l’échéance (ou à la vente) : arrêt 97,64 touché à 20h35:29 (mid 97,60) — proposition non ouverte
- Note (1 ligne) : premier seuil = arrêt (UP) avant 22h → perdu


### D-031a — BTC-EUR (prudente) — UP d'ici 22:00 / 74 843 avant 73 069 / départ 73 956 (17:09) — en attente
- D-038 (a/b/c) ETH DOWN — **en attente** (plafond plein ; zone Z-ETH-2219.6) — rappel 12h00
### D-031b — SOL-EUR (équilibrée) — DOWN d'ici 22:00 / 96,32 avant 98,87 / départ 97,89 (17:09) — en attente
### D-031c — BTC-EUR (risquée) — UP d'ici 22:00 / 75 435 avant 73 217 / départ 73 956 (17:09) — en attente

### D-037a — SOL-EUR (prudente) — DOWN d'ici 12:00 / 95.63 avant 99.53 / départ 97.58 (00:33) — en attente
### D-037b — ETH-EUR (équilibrée) — DOWN d'ici 12:00 / 2172.22 avant 2255.55 / départ 2222.22 (00:33) — en attente
### D-037c — SOL-EUR (risquée) — DOWN d'ici 12:00 / 95.63 avant 98.56 / départ 97.58 (00:33) — en attente


### 2026-10-10 | D-040a | BTC-EUR
- Prévision : UP / horizon 16h00 CEST / +2,00 % avant −2,00 % (cible 75426.0 · inverse 72468.0)
- Prix départ (entrée prévue) : 73946.79 €
- Résultat : en attente
- Note (1 ligne) : proposition en attente de place ; rebond après cassure SOL 98,03 ; D-031b idée morte

### 2026-10-10 | D-040b | SOL-EUR
- Prévision : UP / horizon 16h00 CEST / +2,25 % avant −1,50 % (cible 100.55 · inverse 96.87)
- Prix départ (entrée prévue) : 98.34 €
- Résultat : en attente
- Note (1 ligne) : cassure 98,03 € ; pas de vente SOL ; en attente de place

### 2026-10-10 | D-040c | BTC-EUR
- Prévision : UP / horizon 16h00 CEST / +2,00 % avant −1,00 % (cible 75426.0 · inverse 73208.0)
- Prix départ (entrée prévue) : 73946.79 €
- Résultat : en attente
- Note (1 ligne) : risquée ; aucune risquée ouverte ; en attente de place

## Research — brief 14h44 / 15h05 (scoré comme prévisions, horizon 17h00)

### 2026-10-09 | R-BTC | BTC-EUR (Research)
- Prévision : UP / horizon 17h00 / cible 75 232 · arrêt 73 379 · départ 74 121
- Résultat : **perdu**
- Prix à l’échéance : ≈ 74 119 € à 17h00 — aucun seuil ; fin ≈ à plat / légèrement contre
- Note (1 ligne) : même sens que D-023 (aussi perdu) ; brief confiance faible

### 2026-10-09 | R-ETH | ETH-EUR (Research)
- Prévision : DOWN / horizon 17h00 / cible 2 197 · arrêt 2 263 · départ 2 230
- Résultat : **annulé**
- Prix à l’échéance : 2 223,70 € à 17h00 — aucun seuil ; fin un peu dans le bon sens
- Note (1 ligne) : aligné D-024b (annulé) ; trade simu D-024b encore ouvert

### 2026-10-09 | R-SOL | SOL-EUR (Research)
- Prévision : UP / horizon 17h00 / cible 100,09 · arrêt 97,13 · départ 98,61
- Résultat : **perdu**
- Prix à l’échéance : 98,25 € à 17h00 — aucun seuil ; fin contre (Predict a basculé en baisse via D-026)
- Note (1 ligne) : diverge de Predict après 15h36 (Predict a suivi la cassure SOL à la baisse)

**Research du jour (mesurable) : 0 gagné / 2 perdu / 1 annulé.**

> Vérif Compound 2026-10-09 ~20h45 : ticks 30 s (1 trou ~40 min vers 13h19–14h00, hors fenêtres scorées) ; premier seuil = règle. Horizons 22h00 encore ouverts à 20h45 → laissés « en attente ». Annulées D-027 et D-032. Live 0.

- **D-042** (2026-10-10 18:12) ETH mouvement +0,7 % : D-042a simulée (SOL) ; b/c pas de place — D-042a revue **idée morte** à 07h35 (D-043)

### 2026-10-11 | D-043a | ETH-EUR
- Prévision : UP / horizon 14h00 CEST / +2,00 % avant −2,00 % (cible 2283.3 · inverse 2193.75)
- Prix départ (entrée prévue) : 2238.53 €
- Résultat : **gagné**
- Note (1 ligne) : cible 2283,30 touchée 04h18 (trou nuit comblé) ; trade +0,49 €

### 2026-10-11 | D-043b | SOL-EUR
- Prévision : DOWN / horizon 14h00 CEST / −2,25 % avant +1,50 % (cible 95.66 · inverse 99.33)
- Prix départ (entrée prévue) : 97.86 €
- Résultat : en attente
- Note (1 ligne) : vente seulement après fermeture D-042a ; en attente de place

### 2026-10-11 | D-043c | BTC-EUR
- Prévision : UP / horizon 14h00 CEST / +2,00 % avant −1,00 % (cible 75624.22 · inverse 73399.98)
- Prix départ (entrée prévue) : 74141.39 €
- Résultat : en attente
- Note (1 ligne) : risquée ; D-040a déjà ouverte ; en attente de place

- **D-043** (2026-10-11 07:35) zone SOL 98,17 : 3 propositions (ETH 25 / SOL vente 20 / BTC 10) — **en attente** (horizon 14h00)
