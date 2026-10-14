# Failure Log / Journal des échecs

Template for post-mortems. Append a dated entry after every material loss, false edge, or ops incident.

## Lessons

- Un achat « test » sans vraie décision écrite compte quand même : le stop a bien limité la casse (−0,83 €), mais on ne rachète pas juste après.

## Entries


### 2026-10-07 — ETH stop test (essai)
- **Market / id:** ETH-EUR | rx-paper-2026-10-06T175711Z-d914a46e
- **Thesis:** test pipeline stop (achat 2500 €, stop 2300 €)
- **What we believed (p_model):** n/a (test)
- **What market priced (p_market):** mid ~2293 € à la clôture
- **Size / Kelly fraction used:** 10 € (~2 % d’un capital 500 €)
- **Outcome / PnL:** −0,8274 € (−8,3 %)
- **Root cause:** marché en baisse avant Fed ; achat test sans edge écrit
- **Fix / rule to add:** pas de rachat impulsif après stop ; chaque achat (même essai) doit avoir une décision écrite


### 2026-10-09 — D-021 SOL idée à la baisse (simulation)
- **Market / id:** SOL-EUR | D-021 | rx-paper-2026-10-08T205852Z-1e71faf5
- **Thesis:** idée à la baisse : SOL touche 96,53 € avant 99,47 € (confiance ~55 %), vente 0,15 SOL à 98,00 €
- **What we believed (p_model):** baisse courte après rebond du soir sans nouvelle propre
- **What market priced (p_market):** creux ~96,93 € (cible ratée de ~0,40 €) ; haut ~99,31 € (arrêt 99,47 € non touché) ; clôture rachat 98,77 €
- **Size / Kelly fraction used:** ~14,70 € simulation
- **Outcome / PnL:** −0,13 € (−0,89 %)
- **Root cause:** timing / thèse faible — la baisse n’est pas allée assez loin ; bonne nouvelle Solana le matin a rendu l’idée morte ; fermeture manuelle (time_exit / idée morte), pas stop ni cible
- **Fix / rule to add:** après l’heure rappel, si le prix est contre nous et loin de la cible, couper plutôt que garder le plafond bloqué ; ne pas compter sur une heure limite pour sortir (rappel seulement)

### 2026-10-09 — D-024a SOL idée à la hausse (simulation)
- **Market / id:** SOL-EUR | D-024a | rx-paper-2026-10-09T130833Z-aa77fd43
- **Thesis:** idée à la hausse : SOL touche 100,09 € avant 97,30 € d’ici 17h00 (confiance ~55 %), achat 0,152 SOL à 98,69 €
- **What we believed (p_model):** rebond / hausse courte SOL (brief Research réseau ~17h)
- **What market priced (p_market):** entrée mid ~98,66–98,68 € ; pendant l’ouverture min mid ~97,49 € / max ~98,68 € ; sortie 97,49 € ; arrêt 97,30 € et cible 100,09 € non touchés ; cassure sous zone 97,90 € ~15h37
- **Size / Kelly fraction used:** ~15,00 € simulation
- **Outcome / PnL:** −0,195 € (−1,32 %)
- **Root cause:** timing / thèse contredite — le prix a cassé à la baisse juste après l’achat ; fermeture « idée morte » (pas stop ni cible) pour libérer le plafond face aux nouvelles idées à la baisse
- **Fix / rule to add:** observation seulement (1er essai hausse SOL du jour) — noter si les fermetures « idée morte » avant l’arrêt se répètent sur plusieurs essais avant d’en faire une règle

### 2026-10-10 — D-036a SOL idée à la baisse (simulation)
- **Market / id:** SOL-EUR | D-036a | rx-paper-2026-10-09T220647Z-ff0116e3
- **Thesis:** idée à la baisse (prudente) : SOL touche 95,10 € (−2 %) avant 98,82 € (+~1,9 %), d’ici rappel 10h00 ; vente 13,40 € SOL à 96,96 €
- **What we believed (p_model):** prolonger la baisse SOL déjà ouverte (D-031b avec nous) ; place libérée après D-031a
- **What market priced (p_market):** entrée mid ~96,89–97,02 € (00h06) ; pendant l’ouverture min mid ~96,89 € / max mid ~98,37 € ; sortie 98,19 € (08h05) ; cible et arrêt non touchés ; cassure zone 98,03 € ~07h59
- **Size / Kelly fraction used:** 13,40 € simulation (prudente)
- **Outcome / PnL:** −0,183 € (−1,37 %)
- **Root cause:** timing / thèse contredite — vente après une baisse déjà faite ; le prix a presque tout de suite rebondi contre nous jusqu’à ~98,3 € ; fermeture idée morte (pas stop ni cible) quand Predict a basculé vers la hausse (D-040)
- **Fix / rule to add:** observation seulement — 4e perte « idée à la baisse » simu d’affilée (D-021, D-026, D-031b, D-036a) ; loin de ~20 essais → rien ne change ; essai des ventes SOL après une baisse déjà faite suivi à part (règle d'équipe du 10 oct. 08h08)

<!--
### YYYY-MM-DD — short title
- **Market / id:**
- **Thesis:**
- **What we believed (p_model):**
- **What market priced (p_market):**
- **Size / Kelly fraction used:**
- **Outcome / PnL:**
- **Root cause:** (model, liquidity, news, ops, kill-switch miss, …)
- **Fix / rule to add:**
-->

### 2026-10-09 — D-026 SOL idée à la baisse (simulation)
- **Market / id:** SOL-EUR | D-026 | rx-paper-2026-10-09T134330Z-d3f5b95e
- **Thesis:** idée à la baisse (risquée) : SOL touche 95,54 € avant 98,47 € d’ici rappel 22h00 ; vente 10 € SOL à 97,49 €
- **What we believed (p_model):** baisse courte SOL après cassure sous ~97,90 € (sonnette Z-SOL-97.9)
- **What market priced (p_market):** entrée mid ~97,49–97,58 € (15h43) ; pendant l’ouverture min mid ~97,54 € / max ~98,51 € ; sortie 98,51 € (16h22) ; arrêt 98,47 € touché, cible 95,54 € non touchée
- **Size / Kelly fraction used:** 10,00 € simulation (risquée)
- **Outcome / PnL:** −0,115 € (−1,15 %)
- **Root cause:** prix contre nous — SOL a monté jusqu’à l’arrêt en ~40 min ; la baisse espérée n’est pas venue
- **Fix / rule to add:** observation seulement — 2e perte « idée à la baisse » SOL simu (après D-021) ; total baisse fermées ~4 (2 gains rétro D-019/D-020, 2 pertes) ; loin de ~20 essais → pas de pause ; noter si 3–5 pertes de suite avant de ralentir

### 2026-10-09 — D-023 BTC idée à la hausse (simulation)
- **Market / id:** BTC-EUR | D-023 | rx-paper-2026-10-09T123021Z-0f531d4f
- **Thesis:** idée à la hausse : BTC touche 75 232 € (+1,5 %) avant 73 379 € (−1 %), d’ici rappel 17h00 (confiance ~55 %) ; achat 0,000337 BTC à 74 120 €
- **What we believed (p_model):** rebond BTC après rachats forcés / Iran plus calme (brief Research 14h)
- **What market priced (p_market):** entrée mid ~74 128–74 139 € ; pendant l’ouverture max mid ~74 349 € / min mid ~73 663 € ; sortie 73 927,97 € ; cible et arrêt non touchés ; à 17h07 mid ~74 017 € (contre l’entrée)
- **Size / Kelly fraction used:** 24,98 € simulation
- **Outcome / PnL:** −0,079 € (−0,32 %)
- **Root cause:** timing / thèse faible — la hausse n’a pas atteint +1,5 % ; après le rappel 17h le prix était contre → fermeture idée morte (pas stop ni cible)
- **Fix / rule to add:** observation seulement — 2e perte « idée à la hausse » simu du jour (après D-024a SOL) ; loin de ~20 essais → pas de pause ; noter si 3–5 pertes de suite avant de ralentir

### 2026-10-10 — D-031a BTC idée à la hausse (simulation)
- **Market / id:** BTC-EUR | D-031a | rx-paper-2026-10-09T151109Z-ee1fbd85
- **Thesis:** idée à la hausse : BTC touche 74 843 € (+1,2 %) avant 73 069/73 120 € (−1,2 %), d’ici rappel 22h00 ; achat ≈ 15 € BTC à 73 981 €
- **What we believed (p_model):** achat BTC pour équilibrer deux ventes ETH ouvertes ; rebond possible le soir
- **What market priced (p_market):** entrée mid ~74 008–74 046 € (17h11) ; pendant l’ouverture max mid ~74 148 € / min mid ~73 444 € ; à ~22h mid ~73 475 € (contre) ; sortie 73 586,39 € ; cible et arrêt non touchés
- **Size / Kelly fraction used:** 15,00 € simulation (prudente)
- **Outcome / PnL:** −0,095 € (−0,63 %)
- **Root cause:** timing / thèse faible — la hausse n’a pas atteint +1,2 % (plafond ~+0,2 % vs entrée) ; après le rappel 22h le prix était contre → fermeture idée morte (pas stop ni cible)
- **Fix / rule to add:** observation seulement — 3e perte « idée à la hausse » simu d’affilée (D-024a, D-023, D-031a) ; loin de ~20 essais → rien ne change

### 2026-10-10 — D-031b SOL idée à la baisse (simulation)
- **Market / id:** SOL-EUR | D-031b | rx-paper-2026-10-09T151109Z-aa309e18
- **Thesis:** idée à la baisse (équilibrée) : SOL touche 96,32 € (−1,6 %) avant 98,87 € (+1,0 %), d'ici rappel 22h00 ; vente 10 € SOL à 97,93 €
- **What we believed (p_model):** SOL le plus faible des trois ; prolonger la baisse déjà en cours (−0,96 % depuis le haut 16h34)
- **What market priced (p_market):** entrée mid ~97,93 € (17h11) ; pendant l'ouverture min mid ~96,80 € / max mid ~98,37 € ; à ~08h mid ~98,19–98,34 € (contre) ; sortie 98,19 € ; cible et arrêt non touchés ; cassure zone 98,03 € ~07h59
- **Size / Kelly fraction used:** 10,00 € simulation (équilibrée)
- **Outcome / PnL:** −0,037 € (−0,37 %)
- **Root cause:** timing / thèse contredite après le rappel — la baisse a approché la cible (~96,80 vs 96,32) puis SOL a rebondi au-dessus de 98,03 € ; fermeture idée morte (pas stop ni cible)
- **Fix / rule to add:** observation seulement — 3e perte « idée à la baisse » simu d'affilée (D-021, D-026, D-031b ; avec D-036a au même instant = 4) ; loin de ~20 essais → rien ne change

### 2026-10-10 — D-024b ETH idée à la baisse (simulation)
- **Market / id:** ETH-EUR | D-024b | rx-paper-2026-10-09T130833Z-8d63c1ab
- **Thesis:** idée à la baisse (équilibrée) : ETH touche 2 197 € (−1,60 %) avant 2 255 € (+1,00 %), d'ici rappel 17h00 ; vente 10 € ETH à 2 232,70 €
- **What we believed (p_model):** ETH le plus faible de la semaine (sorties des fonds, brief Research 15h05) ; confiance faible (~55 %)
- **What market priced (p_market):** entrée mid ~2 232,65–2 233,80 € (15h08) ; pendant l'ouverture min mid ~2 208,95 € / max mid ~2 240,58 € ; sortie 2 240,07 € ; cible et arrêt non touchés
- **Size / Kelly fraction used:** 10,00 € simulation (équilibrée)
- **Outcome / PnL:** −0,043 € (−0,43 %)
- **Root cause:** timing / thèse faible — la baisse a approché (~2 209 vs 2 197) puis ETH a remonté au-dessus de l'entrée ; fermeture idée morte (pas stop ni cible)
- **Fix / rule to add:** observation seulement — 5e perte « idée à la baisse » simu d'affilée (D-021, D-026, D-031b, D-036a, D-024b) ; loin de ~20 essais → rien ne change

### 2026-10-10 — D-028a ETH idée à la baisse (simulation)
- **Market / id:** ETH-EUR | D-028a | rx-paper-2026-10-09T142449Z-a11eb3ad
- **Thesis:** idée à la baisse (prudente) : ETH touche 2 181 € (−2 %) avant 2 270 € (+2 %), d'ici rappel 22h00 (puis prolongé 14h00 le 10) ; vente 15 € ETH à 2 225,87 €
- **What we believed (p_model):** prolonger la baisse ETH déjà ouverte (D-024b) ; place libre après fermeture D-026
- **What market priced (p_market):** entrée mid ~2 225,87 € (16h24 le 9) ; pendant l'ouverture min mid ~2 208,95 € / max mid ~2 240,58 € ; sortie 2 240,07 € (18h14 le 10) ; cible et arrêt non touchés ; à ~18h12 mid ~2 239,73 € (contre)
- **Size / Kelly fraction used:** 15,00 € simulation (prudente)
- **Outcome / PnL:** −0,111 € (−0,74 %)
- **Root cause:** timing / thèse faible après le rappel — la baisse a approché (~2 209 vs cible 2 181) puis ETH a remonté au-dessus de l'entrée ; fermeture idée morte (pas stop ni cible)
- **Fix / rule to add:** observation seulement — 5e/6e perte « idée à la baisse » simu d'affilée (D-021, D-026, D-031b, D-036a, D-028a ; D-024b au même instant) ; total baisse fermées hors rétro ~6 (toutes en perte), avec rétro ~8 ; loin de ~20 essais → rien ne change

### 2026-10-11 — D-042a SOL idée à la hausse (simulation)
- **Market / id:** SOL-EUR | D-042a | rx-paper-2026-10-10T161433Z-8987ec95
- **Thesis:** idée à la hausse (prudente) : SOL touche 100,44 € (+2 %) avant 96,99 € (−1,5 %), d'ici rappel 22h00 ; achat 25 € SOL à 98,475 €
- **What we believed (p_model):** rebond SOL au haut du jour avec ETH (D-042) ; gain ≥ perte possible
- **What market priced (p_market):** entrée mid ~98,465–98,475 € (18h14 le 10) ; pendant l'ouverture max mid ~98,585 € / min mid ~97,75 € ; sortie 97,75 € (07h37 le 11) ; cible et arrêt non touchés ; cassure zone 98,17 € ~07h33
- **Size / Kelly fraction used:** 25,00 € simulation (prudente)
- **Outcome / PnL:** −0,209 € (−0,84 %)
- **Root cause:** timing / thèse faible après le rappel — la hausse n'a presque pas bougé (plafond ~+0,11 % vs entrée) ; après 22h le prix était contre → fermeture idée morte (pas stop ni cible)
- **Fix / rule to add:** observation seulement — 4e perte « idée à la hausse » simu d'affilée (D-024a, D-023, D-031a, D-042a) ; streak baisse simu inchangé (6 : D-021, D-026, D-031b, D-036a, D-024b, D-028a) ; loin de ~20 essais → rien ne change

### 2026-10-12 — D-047a ETH idée à la hausse (simulation)
- **Market / id:** ETH-EUR | D-047a | rx-paper-2026-10-12T053552Z-16722c7d
- **Thesis:** idée à la hausse (prudente) : ETH touche 2 325,60 € (+2 %) avant 2 234,40 € (−2 %), d'ici rappel 14h00 ; achat 15 € ETH à 2 278,90 €
- **What we believed (p_model):** confiance moyenne 55 % ; ETH moins monté que SOL la nuit, hausse qui tient (D-047)
- **What market priced (p_market):** entrée 2 278,90 € (07h35) ; max mid ~2 299,85 € (09h14, +0,92 %) / min mid ~2 261,97 € (14h42) ; sortie 2 265,64 € (14h47) ; cible et arrêt non touchés
- **Size / Kelly fraction used:** 15,00 € simulation (prudente)
- **Outcome / PnL:** −0,102 € (−0,68 %, frais compris)
- **Root cause:** timing — la hausse a fait moins de la moitié du chemin vers la cible puis ETH est retombé au plus bas du jour avant le rappel ; fermeture idée morte (pas stop ni cible)
- **Fix / rule to add:** observation seulement — hausse simu : 7 essais fermés (1 gain D-043a puis cette perte) ; loin de ~20 essais, pas 3 pertes d'affilée → rien ne change

### 2026-10-12 — D-049a ETH idée à la hausse (simulation)
- **Market / id:** ETH-EUR | D-049a | rx-paper-2026-10-12T124716Z-3cf7905b
- **Thesis:** idée à la hausse (prudente) : ETH touche 2 310,30 € (+2 %) avant 2 219,70 € (−2 %), d'ici rappel 20h00 ; achat 25 € ETH à 2 265,00 € au plus bas du jour (zone D-048)
- **What we believed (p_model):** confiance moyenne 55 % ; rachat du creux après la fermeture de D-047a
- **What market priced (p_market):** entrée 2 265,00 € (14h47) ; max ~2 275,00 € (+0,44 %, trou 15h42–16h03) / ticks max 2 272,49 € (16h11) ; min ~2 241,80 € (trou 19h17–20h43) ; sortie 2 249,30 € (20h48) ; cible et arrêt non touchés
- **Size / Kelly fraction used:** 25,00 € simulation (prudente)
- **Outcome / PnL:** −0,198 € (−0,79 %, frais compris)
- **Root cause:** timing / même pari racheté — la baisse de la journée a continué (Predict lui-même prévoyait une petite baisse à 15h25) ; fermeture idée morte au rappel, 48 min de retard dû au trou de relevés
- **Fix / rule to add:** observation seulement — 1er cas « fermé puis racheté » (D-047a → D-049a) : −0,30 € cumulés, frais payés deux fois ; Risk refuse déjà ce rachat sans explication de Predict. Hausse simu : 8 essais fermés, 2 pertes d'affilée → rien ne change (loin de ~20)
