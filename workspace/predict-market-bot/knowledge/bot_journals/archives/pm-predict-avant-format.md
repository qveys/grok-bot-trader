# Journal — PM-Predict

## 2026-10-07

- **Matin** — Cycles : avis « pas de trade » ETH/SOL (avant BTC dans la whitelist). Style français simple demandé.
- **~14h30** — Règles : gain ≥ 3× coût ; carnet de décisions avant ; simulation large / live rare ; 15h–17h = simu seulement (consensus A) ; live éventuel Fed ~20h.
- **~14h50** — Point avant 15h : penche vers ne pas forcer un achat (attente Fed).
- **~15h10** — Scan raté → pas de nouvelle décision sans prix frais. Process live noté.
- **~15h17** — Décisions écrites : **D-004 BTC** / **D-005 ETH** / **D-006 SOL** → toutes **pas acheter** (simu seulement). ETH sous 2300 € : pas de rachat ; Risk a fermé le simulé test.

- **~15h19** — Journal Compound reçu pour vente ETH simu (~−0,83 €). Leçon notée pour les prochains avis (pas de rachat impulsif après stop).

- **~15:48** — Exercice anticipatif demandé par Quentin. **D-007 BTC UP ±1,5 % / 22h** · **D-008 ETH DOWN ±1,5 % / 22h** · **D-009 SOL UP ±1,5 % / 22h**. Maths croisées (probas × gain/perte × coût × Kelly) → **aucun achat** (EV < 3× coût). Compound score à 22h.

- **~19:48** — Brief Fed Orchestrator : **D-010/011/012 PAS ACHETER** (réseau coupé depuis 17h25, pas de mid frais → pas de nouvelle prévision mesurable). Forecasts D-007/008/009 restent à scorer à 22h si ticks reviennent.
Wed Oct  7 20:40:51 CEST 2026
- **~20h40** — Bilan Fed Orchestrator : rappel D-010/011/012 PAS ACHETER (pas de prix frais). D-007/008/009 toujours en attente de score si ticks reviennent avant/à 22h.
- **~21h09** — Scan a comblé le trou 17h25–21h07 (minutes Binance) : aucun seuil ±1,5 % touché pour D-007/008/009. Ma proposition « annulé » ne tient plus ; Compound note à 22h32.

## 2026-10-08

- **~13h17** — Demande Orchestrator/Compound : 2 idées ETH/SOL écrites (D-013 rebond dans la tendance ETH+SOL, D-014 cassure dans la tendance ETH). Testées sur 1 an : gagnantes seulement avec ordres qui attendent (0 frais), perdantes ou nulles avec frais immédiats. À confirmer par Compound 22h32 + Risk.
- **~14:34** — Exercice quotidien (brief Research 14h33 + actus + ticks) : **D-015 BTC / D-016 ETH / D-017 SOL = DOWN ±0,5 % d’ici 17h** → PAS ACHETER. Étape « lire les actus » ajoutée avant chaque avis.
- **~15:59** — D-018 : idée « vendre haut, racheter plus bas » écrite (3 prix). Aujourd’hui PAS VENDRE. Compound teste à 22h32.
- **~17:24** — Bilan provisoire (ticks 30 s) : D-015 BTC baisse touchée à 15h42 (73 183 €), D-016 ETH à 15h39, D-017 SOL à 15h02 → 3/3 dans le bon sens (score officiel : Compound). Nouvelles règles validées par Quentin : simulation séparée du live (petit avantage suffit, 25 € max, prix d’arrêt, ≥1 simulation par créneau) ; live garde test du passé + 3× coût + 1/jour + sonnette Risk. Noms : « idée à la hausse » / « idée à la baisse ». Routine mise à jour.
- **~17:28** — Leçon (Risk) : simulations ouvertes en même temps = 25 € max au total (BTC/ETH/SOL = un seul risque). Je partage la taille si plusieurs idées.
- **~17:31** — D-019/D-020 rétro : choix = séparer en deux (~12,4 € chacun), écarts presque égaux à 14h34. Demandé à Risk de réduire les tailles.

## 2026-10-08 ~21h21 — Sonnette branchée
- Essai OK (Grok Bot). Routine « Sonnette Predict » active ; ne plus toucher adresse/clé.
- 6 zones posées jusqu’à demain 22h : BTC 72000↓/74000↑, ETH 2150↓/2250↑, SOL 95↓/100↑.

## 2026-10-08 ~21h32 — Bilan Compound
- Prévisions du jour : 3/3 justes (total 3 justes, 1 fausse, 75 %).
- Leçon : je garde le format court. Avant de proposer une sorte de trade pour le live, je teste les deux moitiés de l'année. Si le filtre de tendance laisse trop peu de trades (2-3/an), je le dis et l'idée reste en simulation.

## 2026-10-08 ~21h33 — Brief Research chiffré
- Dès demain, Research donne une ligne chiffrée par crypto (idée, prix actuel/visé/arrêt, heure limite, confiance).
- Ma prévision 14h55 part de cette ligne ; si je ne suis pas d'accord, je l'écris clairement avec mes prix pour que Compound note les deux avis.

## 2026-10-08 ~21h39 — Bilan Compound (soir)
- D-015/016/017 : 3/3 justes confirmé.
- D-013 : outil ne peut pas tester le filtre « moyenne 200 h » sur rebond → je garde le rebond en simu sans ce filtre ; autre réglage seulement s'il est testable sur le passé.
- D-018 : gain moyen < 3× frais → reste simu seulement.
- Avis pause : règle Quentin 17h = toutes sortes simulables ; ~20 essais utiles.

## 2026-10-08 ~21h44 — Groupe Équipe trading
- Routines « Prédiction avant session » et « Sonnette Predict » mises à jour : postent dans Équipe trading, plus dans PM Pipeline. Bilans restent dans Évaluation. Sonnette retestée OK.

## 2026-10-08 ~22h14 — Heure limite
- Le gardien de Risk ferme seul un trade à son heure limite. Mes deux routines ajoutent la ligne « - Heure limite : » à chaque décision (futur, pas trop courte), prix d'arrêt fixe gardé.

## 2026-10-08 23h00 — D-021 simulation de nuit
- Quentin veut des décisions pour la nuit. Idée à la baisse SOL : vente 0,15 SOL à 98,00 €, rachat 96,53 €, arrêt fixe 99,47 €, heure limite demain 10h. Confiance faible (~55 - (suite) Confiance faible, environ 55 pour cent. Environ 10 € du plafond gardés pour une zone de nuit.

## 2026-10-08 23h05 — Heure limite = rappel
- Quentin : l'heure limite ne ferme plus un trade (seuls prix d'arrêt et prix visé). Risk a coupé la fermeture auto. Je revois D-021 dans ma prévision de 14h55 ; la prévision reste notée à 10h. Routine 14h55 mise à jour. Sonnette pas modifiée (le fichier de règles fait foi).
