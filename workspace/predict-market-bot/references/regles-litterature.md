# Règles d’équipe — VERROUILLÉES (version du 13 oct. 2026, 10h36)

> **Fichier unique de référence.** Chaque bot le lit avant de travailler. Toute nouvelle décision de Quentin y est ajoutée par PM-Orchestrator (ou PM-Compound), puis annoncée aux bots.
>
> **Comment lire ce fichier :** chaque règle dit à quoi elle s’applique.
> **(Simulation)** = trades pour de faux, sans vrai argent. **(Réel)** = trades avec de l’argent réel (le « live »). **(Les deux)** = simulation et réel.

## Règles pour les deux (simulation et réel)

1. **Les 2 règles officielles de Quentin :**
   - **Faire fructifier le capital** (gain net, après les coûts d’achat et de vente).
   - **Ne jamais faire faillite.**

   Tout le reste, ce sont des gardes-fous.
2. **Décision écrite avant chaque trade** : gain espéré, perte max, coût aller-retour, oui/non, pourquoi. Sans décision écrite, pas de trade.
3. **Un trade se ferme seulement à son prix d’arrêt ou à son prix visé.** Rien d’autre ne le ferme.
4. **L’heure limite n’est qu’un rappel.** Le gardien ne ferme jamais un trade à cette heure-là : il prévient Predict, qui regarde si l’idée tient encore, et Risk décide.
5. **Pas de fermeture à heure fixe** (la fermeture de 22h a été retirée par Quentin le 8 oct. 2026). Un trade peut rester ouvert après 17h, la nuit et le week-end, jusqu’à son prix visé ou son prix d’arrêt. Le surveillant de Risk fait la sortie jour et nuit.
6. **Les bilans séparent toujours** les résultats **simulés** et les résultats **réels**.
7. **Paires autorisées** : **BTC-EUR**, **ETH-EUR**, **SOL-EUR**. Pas de Polymarket ni de Kalshi (interdit en Belgique).
8. **Noms des idées** : **idée à la hausse** = on achète, puis on revend plus haut ; **idée à la baisse** = on vend des pièces qu’on a déjà, puis on les rachète plus bas. Chaque trade est noté simplement **Achat** ou **Vente**.

## Simulation

1. **Un petit avantage suffit**, à la hausse comme à la baisse. La règle « gain espéré ≥ 3× les coûts » ne s’applique pas en simulation.
2. **Prix d’arrêt obligatoire** pour chaque simulation.
3. **Plafond : 50 € au total, toutes cryptos ensemble**, ouverts en même temps. BTC, ETH et SOL bougent ensemble, donc Risk les compte comme **un seul risque**. **Une simu fait 25 € au maximum** (5 % du capital), et toutes les simus ouvertes ensemble font **50 € au maximum** (Risk, 9 oct. 2026, 14h07).
4. **Pas de plafond sur le nombre de simulations par jour.**
5. **Simulation permise à toute heure**, jour et nuit, week-end compris. Déclenchée par les sonneries de prix, sans nouvelle routine.
6. **Au moins une simulation dans chaque créneau 15h–17h.**
7. **Nouveau passage de Predict chaque matin à 9h** : Predict propose une simulation (à la hausse ou à la baisse), ou dit en une phrase pourquoi il n’y en a pas.
8. **Le test du passé ne bloque pas la simulation** : une sorte de trade qui a échoué au test reste permise en simulation (validé Quentin, 8 oct. 2026).
9. **But** : arriver vite à ~20 essais par sorte de trade. C’est à partir de là qu’on juge une sorte de trade, et qu’on peut la mettre en pause.

## Réel (live)

**Aujourd’hui, aucune sorte de trade n’a réussi le test du passé : le réel est donc interdit pour toutes.**

Un trade réel n’est permis que si **toutes** ces conditions sont remplies :

1. **Test du passé réussi** pour cette sorte de trade (voir plus bas), écrit dans le carnet des décisions.
2. **Gain espéré ≥ 3× les coûts** aller-retour, avec un gain espéré clairement positif.
3. **Un seul trade réel par jour.** L’équipe le prépare via le process LIVE_ONCE ; Quentin n’a plus à dire « passe en live ».
4. **Mise minimum : 8 €.**
5. **Max 5 % du capital par trade.**
6. **Cagnotte réelle de départ : 100 à 300 € exposés au maximum.**
7. **Seulement entre 15h et 17h** (pour l’instant). L’outil de Risk refuse l’ordre hors de ce créneau. L’heure exacte sera décidée dans ~2 semaines, d’après les heures qui bougent le plus (chiffres de Scan, jugés par Compound).
8. **Jamais dans les 15 minutes après une grosse annonce** (14h30 chiffres US, 15h30 ouverture de la Bourse US, Fed).
9. **La sonnette de Risk doit marcher.** Pas de vrai achat sans elle.
10. **Accord de Risk** sur la décision écrite, avec des prix à jour.

Et ensuite :

- Si le réel est clairement pire que la simulation après **20** trades → STOP.
- La vente automatique au prix d’arrêt ne compte pas comme le trade réel du jour.

## Espérance (avant chaque trade)

- **(Les deux)** Écrire : gain espéré | perte max | coût aller-retour. Sans ces trois chiffres, pas de trade.
- **(Simulation)** Un petit avantage suffit.
- **(Réel)** Acheter seulement si le gain espéré est clairement positif et ≥ **3×** le coût. Sinon, pas d’achat.

## Deux carnets (obligatoires, séparés)

**(Les deux)** Ces carnets servent pour les simulations comme pour le réel.

**1. Carnet des décisions** — `knowledge/decision_log.md`  
Avant chaque achat possible (y compris **PAS ACHETER**) : gain espéré, perte max, coût, oui/non, pourquoi.  
Une idée à la baisse est notée ici **avant la vente**, comme un achat.  
Sans décision écrite → pas d’achat.

**2. Journal des trades** — `knowledge/trading_journal.md`  
Seulement après une **vente** : lien vers la décision, achat, vente, gain/perte, leçon.  
Sans ligne ici → le trade n’est pas « terminé ».

Perte ou erreur technique → aussi dans `knowledge/failure_log.md`.

## Motifs récurrents perdants

**(Les deux)**

1. Après **chaque** perte du même type → écrire pourquoi (journal).
2. On ne juge un type qu’avec assez d’essais : au moins **~20** du même type (sinon le hasard domine).
3. Si sur ces essais le **gain net après coûts** est négatif (ou clairement pire que d’acheter et ne rien faire) → **pause** de ce type + conclusion écrite (ce qu’on change).
4. Avant 20 essais : on peut **ralentir** (pas interdire) après 3 à 5 pertes d’affilée, juste pour forcer la leçon.

## Test du passé (validé Risk, 8 oct. 2026)

**(Réel)** Le test du passé ne bloque que le réel. En simulation, tout reste permis.

- Toute **nouvelle sorte de trade** est rejouée sur **1 an de prix passés, frais compris**, avant tout trade réel. Elle passe seulement si :
  - elle gagne après frais, et fait mieux que « acheter et garder » ;
  - le test contient au moins ~20 opérations ;
  - elle gagne sur les **2 moitiés** de l’année ;
  - la pire baisse reste sous **8 %**, mesurée sur **notre capital avec nos vraies mises** (max 5 % par trade), pas sur le prix de la crypto.
- Le résultat est écrit dans le carnet des décisions. Sans test écrit → pas de réel.
- Test négatif après frais → ce type est **interdit en réel** (sans attendre ~20 essais réels), mais il **reste permis en simulation**.
- Test positif → Compound compare chaque soir le réel au test.
- Un test réussi **ne suffit pas** : toutes les conditions de la section « Réel (live) » restent obligatoires.
- Tant que l’outil ne sait pas simuler des ordres en attente qui ne sont pas tous exécutés, Risk juge sur le **cas le moins favorable** : achats immédiats, frais compris. Une sorte de trade ne passe en réel que si elle reste gagnante dans ce cas-là (Risk, 8 oct. 2026).
- Plus d’exception (Risk, 8 oct. 2026 au soir) : le rebond et la cassure sans filtre peuvent de nouveau être **simulés**.

## Résultats des tests sur un an (bilan Compound, 8 oct. 2026)

- **Rebond ETH, rebond SOL, cassure ETH** : ne passent pas (perdants sur une des 2 moitiés de l’année ; achat immédiat avec frais en perte ou presque nul). → **(Réel)** interdit ; **(Simulation)** permis.
- **Idée à la baisse « vendre haut, racheter plus bas »** (D-018) : ne passe pas (ETH ≈ 0 ; SOL +2,5 €/an mais en perte d’avril à octobre ; gain < 3× frais ; via MetaMask −3 €). → **(Réel)** interdit ; **(Simulation)** permis.
- **Aucune sorte de trade n’est donc autorisée en réel** (situation au 8 oct., inchangée au 9 oct.).
- **(Réel)** Predict : avant de proposer une nouvelle idée pour le réel, vérifier qu’elle gagne sur les 2 moitiés de l’année. En simulation, ce n’est pas demandé.

## Feu vert pour passer au réel à grande échelle (go / no-go après coûts)

**(Réel)** Chiffres à atteindre en simulation avant d’élargir le réel :

- Au moins **50** trades d’essai (cible : 100), sans compter les auto-tests.
- Au moins **55 %** de trades gagnants, et gains totaux ≥ **1,3 fois** les pertes totales, **après** frais.
- Pire baisse du capital sous 8 % ; gains réguliers (ratio de Sharpe > 1,0) si on a assez de jours.

## Anti-faillite (chiffres validés Quentin)

- **(Réel)** Max **5 %** du capital par trade, et **5 % en tout** (environ 25 €) : BTC, ETH et SOL comptent comme un seul risque (Risk, 9 oct. 2026, 14h07).
- **(Les deux)** Perte du jour ≥ **15 %** → STOP pour la journée.
- **(Les deux)** Chute ≥ **8 %** depuis le plus haut → STOP général.
- **(Les deux)** Pendant un STOP : **aucun nouveau trade**, mais les ventes ou rachats au prix d’arrêt restent permis (ils réduisent le risque).
- **(Les deux)** Pas d’argent emprunté (pas de levier). Ordres à prix fixé, qui attendent dans le carnet d’ordres (post-only). Pas d’ordre « au prix du marché », sauf pour freiner une perte.

## Pièces disponibles pour les idées à la baisse (8 oct. 2026)

- **(Les deux)** On ne vend que des pièces **non bloquées**. Revolut : ~0,0209 ETH et ~0,241 SOL disponibles (le reste est bloqué). BTC : rien à vendre.
- **(Réel)** Le surveillant ne vend jamais les pièces de Quentin, seulement ce que le système a acheté.

## Revolut X et MetaMask

- **(Les deux)** Revolut X = voie principale.
- **(Les deux)** MetaMask remis au travail (8 oct. 2026) : simulation d’abord ; en réel, mêmes règles que Revolut.
- **(Les deux)** MetaMask : ~0,0397 ETH sur Arbitrum ; garder ~0,001 ETH pour les frais → ~0,0387 ETH vendable.
- **(Les deux)** MetaMask : échanges **uniquement via Uniswap** (~0,1–0,2 % aller-retour). Le bouton « Échanger » de MetaMask (~1,8 % aller-retour) est refusé.
- **(Les deux)** MetaMask : pas de tout petits échanges (le coût mange le gain).

## Horaires (validé Quentin, 8 oct. 2026, mis à jour 9 oct.)

- **(Simulation)** À toute heure, jour et nuit, week-end compris, dans la limite de 25 € par simu et 50 € au total, toutes cryptos ensemble.
- **(Simulation)** **9h** : passage de Predict (une simulation proposée, ou une phrase qui explique pourquoi il n’y en a pas).
- **(Les deux)** **14h44** : brief de Research (après les chiffres US de 14h30).
- **(Les deux)** **14h55** : prévision de Predict (il vérifie que le brief est bien du jour).
- **(Réel)** **15h–17h** : seul créneau où un trade réel peut être **ouvert**.
- **(Simulation)** **15h–17h** : au moins une simulation par créneau.
- **(Réel)** Pas de trade réel dans les 15 minutes après une grosse annonce (14h30 chiffres US, 15h30 ouverture US, Fed).
- **(Les deux)** Les jours de grosse annonce, Research le signale ; une séance en plus seulement si **Quentin donne le feu vert**.
- **(Les deux)** **20h32** (en semaine) : bilan du soir de Compound, test du passé inclus.

## Surveillant, sonnettes et signaux de vie

- **(Les deux)** Le surveillant de Risk démarre **tout seul** après chaque trade, lancé par l’outil qui passe l’ordre. Filets de sécurité : vérification avant chaque nouveau trade + routine Risk de 14h24.
- **(Les deux)** Il lit le relevé commun des prix (toutes les 30 s) ; il ne demande le prix à Revolut que si ce relevé a plus de 2 min de retard.
- **(Réel)** Si le prix d’arrêt est touché, il **vend tout seul**, seulement ce que le système a acheté (jamais les pièces de Quentin). Cette vente ne compte pas comme le trade réel du jour. Quentin n’est prévenu **que si la vente échoue**.
- **(Réel)** Pas de vrai achat tant que la sonnette de Risk ne marche pas.
- **(Les deux)** **Sonnette de Predict** : réveille Predict quand un prix touche une de ses zones (hausse ou baisse). À toute heure, 7 jours sur 7, **max 6 sonneries par jour**. Branchée et testée OK le 8 oct. (Grok Bot). Elle ne sonne que si Predict tient des zones à jour dans son fichier de zones.
- **(Les deux)** **Sonnette « trade fermé »** (branchée et testée OK le 8 oct., Grok Bot) : réveille Compound à chaque trade fermé, max 5 par jour ; bilan court immédiat.
- **(Les deux)** **Signaux de vie** (demandé par Quentin, 8 oct. 2026) : un signal régulier prouve que (1) le surveillant tourne et (2) l’accès à Revolut répond. Seulement quand un trade est ouvert ; sans trade ouvert, rien.
  - Si un signal manque : Risk est réveillé d’abord (relancer ou fermer le trade) ; Quentin n’est prévenu que si ça échoue.
  - Vérification par un petit script, sans routine de bot.
  - Réglages : gardien muet plus de 3 min, ou Revolut sans réponse 2 fois de suite (test toutes les 5 min, jamais d’ordre) → la sonnette de Grok Bot réveille Risk, max 1 fois par problème toutes les 30 min.
  - Aussi si le gardien ne donne **aucun** signe de vie 3 min après l’ouverture d’un trade.
  - Alerte Revolut après 12 min sans nouvelles, seulement si le gardien répond (une seule alerte par problème).

## Façon de travailler par bot

- **Scan** : routine d’observation prolongée jusqu’à 17h53 (4 passages en plus, pas de nouvelle routine) pour voir les mouvements après 17h. Note chaque jour les heures qui ont le plus bougé la veille (leçon du 8 oct.).
- **Research** : brief de 14h44 avec, pour BTC, ETH et SOL, une ligne chiffrée fixe (idée hausse/baisse, prix actuel, prix visé, prix d’arrêt, heure limite, confiance), enregistrée pour la note de Compound (leçon du 8 oct.). Lit le fil d’actus avant chaque brief ; recoupe toute info avec au moins une autre source, jamais un seul post ; donne pour chaque paire une idée à simuler (hausse ou baisse) avec son niveau de confiance.
- **Predict** :
  - **(Simulation)** Chaque matin à **9h** : propose une simulation (à la hausse ou à la baisse), ou dit en une phrase pourquoi il n’y en a pas.
  - **(Les deux)** À 14h55, part de la ligne chiffrée de Research pour chaque crypto. En cas de désaccord, l’écrit clairement, avec sa raison et ses propres prix (Compound note les 2 avis séparément).
  - **(Les deux)** Chaque prévision a une direction, une heure limite (simple rappel) et un seuil en % (sinon Compound la compte « annulée »).
  - **(Les deux)** Chaque décision contient les lignes **Idée**, **Sens**, **Décision**, **Pourquoi** (lues par le tableau de bord). Exemples : « Idée : à la hausse » ou « Idée : à la baisse » ; « Sens : Achat » ou « Sens : Vente » pour le premier trade.
  - **(Les deux)** Une idée à la baisse est notée dans le carnet des décisions **avant la vente**, comme un achat.
- **Risk** : donne son accord avant chaque trade réel, fait tourner le surveillant et sa sonnette, juge les tests du passé.
- **Compound** : évaluateur de toute l’équipe (voir « Organisation »).

## Organisation

- **(Les deux)** **PM-dev** (id `2f0615e8-234f-4f99-839a-ab5f2aa3fe43`, Quentin, 9 oct. 2026, 14h41) développe le tableau de bord (`/workspace/dashboard`, https://pm-pipeline-tableau.pages.dev). Il modifie librement le site (`/workspace/dashboard`), mais lit les fichiers des bots et de la sonnette **sans jamais les modifier**, n'affiche que leurs chiffres sans rien recalculer, se vérifie avant chaque publication (`verify.py`) et n'a pas de routine. Il ne fait ni routine ni alerte : la sonnette reste à Grok Bot. Quand une donnée manque, le site affiche « non évalué » et PM-dev dit à Orchestrator quel bot doit l'écrire.
- **(Les deux)** Le groupe **« PM-dev »** (id `39db92c1-5265-468b-96af-2ae7ea0f1e44`, créé le 9 oct. 2026, 14h47) réunit Grok Bot, PM-dev et Orchestrator pour le travail sur le tableau. PM-dev reçoit ses demandes **seulement de Quentin, de Grok Bot ou d'Orchestrator**. Si un autre bot a besoin de quelque chose sur le site, il passe par Orchestrator. PM-dev n'est pas dans Équipe trading tant que Quentin ne l'y a pas ajouté.

- Quentin parle surtout à Grok Bot. Grok Bot relaie chaque décision de Quentin à PM-Orchestrator, qui la note ici, la transmet aux bots concernés, puis vérifie les confirmations.
- Le groupe de travail du jour s’appelle **Équipe trading** (id b17f28c6-7164-4dee-9b8a-174a0136c0c4, créé le 8 oct. 2026 ; il remplace « PM Pipeline », qui garde seulement l’historique). Membres : Scan, Research, Predict, Risk, Grok Bot, Orchestrator. Depuis le 8 oct. à 21h43 (demandé par Quentin), tout le travail quotidien (scans, briefs, décisions, validations) se fait là.
- **PM-Compound = évaluateur de toute l’équipe** (validé Quentin, 8 oct. 2026). Il **n’est pas** dans **Équipe trading**, exprès (choix de Quentin) : toute info qui le concerne lui est envoyée **en privé**. Chaque soir à 20h32, même sans trade, il note : justesse des prévisions de Predict, idées de Research vérifiées ou non, refus de Risk (perte évitée ou gain raté), mouvements ratés par Scan. Score simple par bot, suivi dans le temps. Il sépare toujours simulation et réel.
- Le groupe **Évaluation** (id 4f388d70-d1f6-4ba6-b00d-1590af4e4a6d, créé le 8 oct. ; il remplace « PM Compound », qui garde seulement l’historique) est le lieu des bilans. Membres : Compound, Predict, Risk, Scan, Research, Orchestrator (pas Grok Bot). Compound y poste 1 à 2 leçons par bot ; chaque bot concerné répond par ce qu’il change ; Orchestrator recopie ici les changements validés.
- Chaque routine commence par `python3 /workspace/tools/routine_log/log.py <bot> "<routine>" demarre` et finit par `... fini "résultat en 3 mots"` (ou `arret "raison"`). Fichier commun : `state/routine_runs.jsonl`.
- Peu de routines (quota de Quentin).
- IA via le compte ChatGPT de Quentin (`ai.sh` de Vibe-Trading) : seulement en cas de vrai besoin, jamais en routine ni en boucle, raison notée dans le journal.

## Idées en cours de test (décisions Quentin, 8 oct. 2026, 22h03)

- **(Les deux) Prix d’arrêt qui suit le gain** : Compound teste sur le passé un prix d’arrêt qui monte avec le gain et ne redescend jamais, et le compare au prix d’arrêt fixe. Il poste le résultat dans Évaluation. Tant que ce test n’est pas fait, on garde le prix d’arrêt fixe.
- **(Les deux) Alertes de départ sans IA (sonnette de Grok Bot)** : deux signaux calculés : (a) prix près du plus haut du jour avec beaucoup d’échanges ; (b) beaucoup d’échanges sans que le prix bouge. Pendant 1 à 2 semaines, la sonnette les **note seulement** et ne réveille pas Predict. Ensuite, on regarde si elles étaient justes avant de les brancher.
- **(Les deux) Piste « sans prix visé »** : reste en pause, puisque sans prix visé elle n’aurait plus de sortie gagnante (seuls le prix d’arrêt et le prix visé ferment un trade).

## Journaux de bord (Quentin, 8 oct. 2026, 23h15)

Tous les journaux de `knowledge/bot_journals/` suivent le même modèle : `references/format-journal.md` (exemple : `grok-bot.md`). Chaque bot réécrit son journal dans ce format dès le 8 oct. au soir, avec ses règles reformulées à sa façon pour montrer qu’il les a comprises et comment il les applique. Ensuite, il tient à jour les sections « règles » et « en cours » dès qu’une règle ou une position change, **en précisant pour chaque règle si elle vaut pour la simulation, le réel ou les deux**. Orchestrator vérifie.

## Sources

Barber & Odean, Carhart, Novy-Marx & Velikov, Barbon & Ranaldo, Adams et al.  
Brief : `/workspace/trading_costs_research_brief.md`.

## Coordination entre bots (Orchestrator, 9 oct. 2026, 14h12, à la demande de Quentin)
- **(Les deux)** Quand une sonnette réveille Predict, Predict ne fait pas d'attente : il décide en 5 minutes avec les prix et le dernier avis de Research, même s'il est court. Le message de Research dans le groupe compte comme un brief, comme le fichier.
- **(Les deux)** **Quand une sonnette réveille Predict et que la décision n'est pas évidente, il demande l'avis de Research**, en privé et en urgence (Quentin, 9 oct. 2026, 14h13). Ce n'est pas obligatoire : si la sonnette est si claire que l'avis de Research ne changerait rien, Predict décide seul et écrit en une phrase pourquoi. Research répond tout de suite en 3 phrases maximum : la nouvelle du moment, le sens et sa confiance. Predict décide dans les 5 minutes après la sonnette. Si Research n'a pas répondu à temps, Predict décide sans lui et le note.
- **(Les deux)** Chaque message de travail finit en nommant le bot suivant et ce qu'il doit faire. Par exemple : « @PM-Risk : valide la vente de 20 € de SOL ».
- **(Simulation)** « Trop tard » n'est pas une raison suffisante. Predict donne aussi le prix auquel il entrerait (par exemple, si BTC redescend à 73 600 €) et y place une nouvelle zone de réveil.
- **(Les deux)** Predict place ses zones **avant** les prix clés, environ 0,3 % avant le haut ou le bas du jour, pour être réveillé à temps et pas une fois le mouvement fini.
- **(Les deux)** Un bot ne dit pas « je fais X » s'il ne le fait pas. S'il change d'avis, il le dit en une phrase avec la raison.
- **(Les deux)** Orchestrator vérifie chaque soir le temps entre une sonnette et la décision de Risk, et signale les retards dans Évaluation.

## Où écrire (Quentin, 9 oct. 2026, 14h23)
- **(Les deux)** Toutes les communications de l'équipe, y compris les annonces, les confirmations et les mesures, passent par **Équipe trading**. Plus aucun message dans « PM Pipeline » ni dans « PM Compound », qui ne gardent que l'historique. Compound poste dans Évaluation et écrit à Orchestrator en privé.

## Autonomie et réveils (Quentin, 9 oct. 2026, 14h26)
- **(Simulation)** La simulation n'a **jamais** besoin de Quentin. On n'a besoin de lui que pour une séance réelle en plus, un changement de plafond ou de règle, et le feu vert du réel. Un bot qui a vraiment besoin de lui envoie à Orchestrator une seule ligne « DEMANDE QUENTIN : … ». Orchestrator la transmet une fois à Grok Bot.
- **(Les deux)** Chaque réveil de Predict ou de Risk se termine soit par une simulation sous le plafond, soit par un prix d'entrée avec une nouvelle zone. Jamais par « rien ».
- **(Les deux)** Predict garde pour chaque paire (BTC, ETH, SOL) au moins une zone de chaque côté, à moins de 1 % du prix, et les remet à jour à chaque décision.
- **(Les deux)** Quand l'heure limite d'un trade arrive, la sonnette réveille Predict. Risk ferme ou garde le trade dans les 5 minutes.
- **(Simulation)** S'il n'y a eu aucune décision depuis 4 h et qu'il reste de la place sous le plafond, la sonnette réveille Predict, 2 fois par nuit au maximum. Une nuit sans décision s'affiche en rouge sur le site. Compound la compte dans son bilan de 20h32, et Orchestrator la signale dans Évaluation.
- **(Simulation)** Prix visé de nuit : **pas de changement** (Compound, 9 oct. 2026, 14h56). Predict garde ses prix visés habituels. Compound vérifie d'abord, sur les prix passés et sur plusieurs nuits, si −1 % fait mieux que −1,5 % après frais. Il ne proposera un changement qu'une fois le résultat vérifié plusieurs fois.

## Comment écrire une règle (Quentin, 9 oct. 2026, 14h31)
- **(Les deux)** Chaque changement de règle s'écrit **avec son réglage détaillé** : les chiffres, les heures, les limites et le fichier qui porte le réglage (par exemple `/workspace/tools/sonnette/config.json`, `config.json`, `guardian/config.json`). Jamais seulement un résumé.
- **(Les deux)** La sonnette est décrite en détail dans `references/sonnette.md`. Pour Predict : toutes les 30 s, de 00h00 à 24h00, 7 jours sur 7, 6 réveils maximum par jour en tout, chaque zone 1 fois par jour. Les sonneries « sans décision » (après 4 h sans décision, 1 toutes les 4 h, 2 par nuit entre 22h00 et 09h00, avec au moins 5 € libres) et « heure limite » (1 fois par trade, Risk tranche en 5 min) comptent dans les 6. Une alerte part si la zone la plus proche est à plus de 1 % du prix.

## Trois propositions à chaque réveil (Quentin, 9 oct. 2026, 14h33 ; critères de Risk, 14h34)
- **(Simulation)** À chaque réveil par la sonnette, Predict fait **3 propositions** : **prudente**, **équilibrée** et **risquée**. Chacune donne la paire, Achat ou Vente, la taille en €, l'entrée, le prix visé, le prix d'arrêt et l'heure limite (rappel seulement). Les trois restent dans le plafond. Cela remplace micro / moyen / vrai trade.
- **(Simulation)** Si aucune ne convient, Predict le dit avec ses raisons, puis donne un prix d'entrée et pose une zone à moins de 1 % du prix (`state/zones_reveil.json`).
- **(Simulation)** Risk juge chaque proposition selon son niveau. Il garde la décision, le plafond (25 € par simu, 50 € au total) et le prix d'arrêt obligatoire. Ses critères par niveau :

| Niveau | Taille max | Arrêt au plus | Gain visé au moins | En plus |
|---|---|---|---|---|
| Prudente | 25 € | 2 % | 1 × la perte possible | — |
| Équilibrée | 20 € | 1,5 % | 1,5 × la perte possible | raison claire |
| Risquée | 10 € | 1 % | 2 × la perte possible | raison précise ; **1 seule risquée ouverte à la fois** |

- **(Simulation)** Si les trois ne tiennent pas ensemble dans les 50 €, Risk garde d'abord la prudente, puis l'équilibrée, puis la risquée. Pour chacune, il répond par son niveau, oui ou non, et la raison en une phrase.

## Une sonnette, une décision (Orchestrator, 9 oct. 2026, 15h45, après les doublons D-025 et D-026)
- **(Les deux)** Un numéro de décision correspond à un seul message de Predict. Si une deuxième sonnette réveille Predict pendant qu'il décide, ou dans les 5 minutes qui suivent, il écrit seulement « déjà traité dans D-0xx ». Il ne fait pas de nouvelles propositions. Le réglage est le verrou de la routine de sonnette de Predict, à ajouter depuis son chat privé avec Quentin.
- **(Les deux)** Si deux messages se contredisent quand même, Risk applique le plus récent que Predict a confirmé dans le groupe. Les autres sont annulés et notés comme tels dans le journal des décisions.
- **(Simulation)** Pour libérer de la place sous les 50 €, Risk ne ferme un trade avant son arrêt que si Predict écrit que l'idée est morte, comme pour D-024a le 9 oct. à 15h43, avec une perte de 0,20 €.
- **(Simulation)** Les propositions en attente de place restent valables 30 minutes après leur message. Par exemple, celles de D-029 (16h30) restent valables jusqu'à 17h00. Passé ce délai, Risk n'ouvre rien : il prévient Predict dans Équipe trading, et Predict renvoie 3 propositions à jour en moins de 5 minutes. (Predict et Risk, 9 oct. 2026, 16h37)
- **(Les deux)** Numéros de décision (Grok Bot pour Quentin, 9 oct. 2026, 17h37) : avant d'écrire une décision, Predict relit `knowledge/decision_log.md` et prend le plus grand numéro D-0xx déjà écrit, plus 1. Un numéro n'est jamais réutilisé, et il ne doit jamais manquer de numéro. Doublons du 9 oct. renumérotés, en gardant le numéro pour la version valable : D-025 de 15h39 (rappel 22h00) reste D-025. D-026 de 15h36 (les ventes de SOL, risquée lancée) reste D-026. D-026 de 15h38 (les ventes de BTC, annulées) devient D-027, comme Predict l'a déjà écrit à 15h48. D-025 de 15h40 (rappel 17h00, annulée) devient D-032, ou le prochain numéro libre si D-032 est déjà pris. Les références sont mises à jour dans les trades, les zones et le score. Grok Bot empêche aussi deux réveils de Predict de tourner en même temps.

## Façon d'écrire une décision (Quentin, via PM-dev, 10 oct. 2026, 00h06)
- **(Les deux)** Chaque nouvelle décision de Predict dans `knowledge/decision_log.md` suit le modèle `/workspace/dashboard/docs/modele-decision.md`. Le titre est toujours `### AAAA-MM-JJ HH:MM | PAIRES | D-xxx — résumé`, avec l'heure écrite avec deux-points. Juste en dessous vient un bloc `json` qui contient : le déclencheur, les prix relevés, la place libre en €, si le réel est permis, l'avis de Research, le pourquoi, les trades ouverts revus, et de 1 à 3 propositions. Chaque proposition donne son niveau, la paire, le sens, le montant en €, le prix d'entrée, le prix visé, l'arrêt, le rappel, la prévision, la confiance et le statut.
- **(Les deux)** Le numéro est le plus grand du carnet plus 1, et il n'est jamais réutilisé. Une décision renumérotée porte `ancien_numero` dans son bloc.
- **(Les deux)** Ce qui se passe ensuite ne modifie pas le texte de la décision : Risk et Predict ajoutent dessous un petit bloc `json` de suivi. Les statuts possibles sont : simulée, pas simulée avec la raison, fermée, expirée, ou annulée avec la raison. Le site affiche le dernier statut écrit.
- **(Les deux)** Les anciennes entrées ne changent pas. Le site les montre telles qu'elles sont écrites, avec « pas évalué » quand un champ manque.
- **(Les deux)** Une seule échelle de confiance pour Predict et Research (fixée par Predict le 10 oct. 2026 à 00h08, écrite dans le modèle de décision) : de 50 à 54 %, c'est faible ; de 55 à 64 %, c'est moyenne ; à partir de 65 %, c'est forte. Sous 50 %, l'idée n'est pas proposée. Research l'applique dans ses briefs à partir de celui du lundi 12 oct. à 14h44.
- **(Les deux)** Champs à écrire pour le site. Risk : sur chaque ligne de fermeture dans `state/trades_log.jsonl`, le prix qui a déclenché la fermeture, et le capital réel de départ dans `guardian/state.json`. Compound : « sans objet » en simulation pour « Ordres des bots » et « Ordres remplis (Revolut X) », et un type (fait, décision, alerte…) sur chaque ligne de son journal.

## Essai : attendre avant une vente de SOL (Risk, accepté par Predict, 10 oct. 2026, 08h07)
- **(Simulation)** Pour une vente de SOL-EUR, si SOL a déjà baissé de plus de 1 % depuis son plus haut des 2 dernières heures, Predict écrit la vente avec une heure d'ouverture au plus tôt 30 minutes plus tard. Elle n'est valable que si, à cette heure-là, SOL n'est pas remonté au-dessus du prix d'entrée prévu. Risk vérifie le prix avant d'ouvrir. Predict le note dans la proposition.
- **(Simulation)** Compound compte ces cas à part. Après 10 essais, il dit si l'attente fait mieux. Sinon, Risk enlève la règle. Le prix d'arrêt ne change pas.
- **(Réel)** Rien ne change.
- **(Les deux)** Bilans de Compound : soit « rien ne change », soit une règle avec le réglage exact et le nombre d'essais. Plus de « ralentir un peu ».

## Ordinateur figé (10 oct. 2026, 18h19)
- **(Réel)** Pas de réel tant que le contrôle extérieur du signal de vie n'existe pas. Il tournera chez Cloudflare, sur une autre machine que la nôtre. Il doit être construit et testé par Grok Bot, avec une alerte par Telegram ou par e-mail, au choix de Quentin. Raison : l'ordinateur s'est figé le 10 oct. de 03h08 à 07h59 puis de 11h58 à 15h08. Pendant ces deux blocages, le signal de vie n'a pas pu sonner. Aucun arrêt ni prix visé n'a été dépassé, et il n'y avait que des simulations ouvertes.
- **(Les deux)** Rappels : le gardien de Risk fait sonner chaque nouveau rappel, même si le trade en a déjà eu un. Corrigé par Risk le 10 oct., après le rappel de 14h00 manqué sur D-024b et D-028a.
- **(Les deux)** Trous dans les relevés (Risk et Scan, 10 oct. 2026, 18h25) : quand le gardien voit un trou de plus de 2 minutes dans ses relevés, il va chercher les prix de la bourse minute par minute pour cette période (en place et testé par Risk le 10 oct. 2026, 18h34). Si un arrêt ou un prix visé a été dépassé, il ferme la simulation à ce prix-là, et il note chaque trou. En double contrôle, Scan cherche les trous au début de chaque passage. S'il en trouve un pendant qu'un trade est ouvert, il prévient Risk dans Équipe trading en donnant les heures. Cas qui a lancé la règle : le 9 oct., entre 13h19 et 13h59, l'arrêt de D-021 à 99,47 € a été dépassé (SOL est monté à 99,86 €), et personne ne l'a vu. Le résultat a été corrigé de −0,13 € à −0,24 €.
- **(Les deux)** Résultat du test de l'arrêt qui suit le gain (Compound, 10 oct. 2026, 18h39) : rien ne change, on garde l'arrêt fixe. Sur les ventes, sur un an, avec les vrais frais et les 3 cryptos ensemble, l'arrêt fixe fait +25 %. Le meilleur arrêt qui suit fait +33 % : il commence à suivre après +0,5 % de gain et ne redescend jamais sous le prix d'entrée. Mais il ne gagne que sur la 1re moitié de l'année (2e moitié : environ −6,6 % pour les deux). Il est fragile : s'il commence à suivre à +0,3 %, le gain tombe presque à zéro. Sur BTC, l'arrêt fixe est toujours meilleur. SOL est la seule crypto où l'arrêt qui suit gagne sur les deux moitiés : à suivre, mais pas une règle. Achats sans prix visé ni heure fixe : 3 cas passent le test (cassure ETH, rebond SOL), mais sur seulement 23 à 40 trades, donc rien ne change.
- **(Les deux)** Test « jours calmes » (Compound, 11 oct. 2026, 08h29) : pas de règle, rien ne change, ni pour le réel ni pour les simulations. Règle testée : « on ne propose que si le mouvement des 24 dernières heures dépasse X % », pour X = 1, 1,5, 2, 2,5, 3, 4 et 5 %, sur les prix d'un an, frais compris, sur les deux moitiés et avec les arrêts de Risk. De 1 à 3 %, presque aucun effet. Avec 5 %, on garde le plus d'argent, avec environ 17 trades par an au lieu de 27, mais seulement sur la 1re moitié de l'année ; la 2e moitié est pire. Pour les ventes, la règle fait pire sur les 3 cryptos. Seul cas meilleur sur les deux moitiés : la cassure BTC avec 5 %, mais seulement 7 trades par an, à suivre. Bilan des prix visés du même jour : en moyenne, le prix visé est à 1,68 % de l'entrée, et le meilleur mouvement en notre faveur fait +0,47 %. Sous 1,5 %, plus rien ne gagne après frais.
- **(Les deux)** Arrondis (Predict et Risk, 11 oct. 2026, 11h07) : Predict arrondit toujours le prix d'arrêt vers le prix d'entrée, jamais dans l'autre sens, pour ne jamais dépasser la limite de perte du niveau. Si un arrêt dépasse quand même la limite d'un centime, Risk le resserre d'un centime avant d'ouvrir. Cas qui a lancé la règle : les 3 propositions de D-045.

## Moins de réveils quand le plafond est plein (Quentin, via Grok Bot, en place le 11 oct. 2026 à 11h47)
- **(Simulation)** Quand il reste moins de 10 € de libre sur les 50 € de simulation, la sonnette ne réveille plus Predict pour une zone touchée ni pour un mouvement de prix. Une zone sautée ne sonne pas plus tard pour le même passage. Le réglage est dans la sonnette de Grok Bot (`/workspace/tools/sonnette/config.json`).
- **(Les deux)** Rien ne change pour les rappels d'heure limite, les réveils « sans décision », les arrêts, les alertes, ni le passage de Predict à 9h.
- Raison : le 11 oct. au matin, Predict a été réveillé 3 fois avec le plafond plein (D-043, D-044 et D-045), et ses 9 propositions ne pouvaient pas s'ouvrir. Le but est de garder peu de réveils.
- **(Les deux)** Rappels groupés (Grok Bot, en place et testé le 11 oct. 2026 à 14h26) : les rappels d'heure limite qui tombent à la même heure partent dans un seul réveil de Predict, qui ne compte qu'une fois dans la limite de 6 réveils par jour. Un rappel déjà traité, ou dont l'heure a changé, ne sonne plus. Le réglage est dans la sonnette de Grok Bot (`/workspace/tools/sonnette/config.json`). Cas qui a lancé la règle : le rappel ETH de D-043a, arrivé en retard à 14h19 alors que Predict l'avait déjà traité dans D-046.


## Messages courts (12 oct. 2026, 09h11, Quentin)
Pour tous : Orchestrator, Scan, Research, Predict, Risk, Compound, dans tous les groupes. Chaque message tient en 1 ou 2 phrases au maximum, en français tout simple, sans mot technique. Si un chiffre ou un mot compliqué est nécessaire, l'expliquer en une phrase comme à quelqu'un qui ne connaît rien au trading. Pas de longues listes ni de détails inutiles. But : Quentin suit tout en lisant vite. Les détails restent dans les fichiers et les journaux, pas dans les messages.
Précision de Quentin (12 oct. 2026, 09h25) : la règle des messages courts ne doit jamais faire perdre d'information. Les détails de travail (prix exacts, arrêts, prix visés, raisons) passent en messages privés entre les bots concernés, au moment où ils en ont besoin, par exemple Predict vers Risk pour chaque proposition. Le groupe garde le résumé court pour Quentin.

## Fermer puis racheter (12 oct. 2026, 14h50, simulation)
Cas du 12 oct. vers 14h46 : achat ETH D-047a fermé (−0,10 €) puis achat ETH D-049a de 25 € ouvert juste après au même creux, donc frais payés deux fois. Règle : Predict ne propose plus de fermer un trade pour racheter tout de suite la même crypto dans le même sens ; il garde avec un nouveau rappel ou abandonne. Risk refuse une telle proposition, sauf si Predict écrit en une phrase ce qui a changé. Compound compte ces cas à part dans ses bilans du soir. Risk attend la réponse quand une question est posée sur une décision avant d'agir.

## ARRÊT DE L'EXPÉRIENCE (13 oct. 2026, 10h35, Quentin via Grok Bot)
Plus aucune simulation ni trade réel. Risk ferme les 3 simulations ouvertes (achat BTC 25 €, achat ETH 20 €, achat SOL 5 €) au prix actuel, pose le fichier STOP et arrête son surveillant. Grok Bot coupe la sonnette. Scan, Research, Predict, Risk et Compound mettent leurs routines en pause. Compound écrit le bilan final. PM-Dev arrête le travail sur le tableau de bord. Rien ne redémarre sans un nouvel accord de Quentin.
