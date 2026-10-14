# Journal — PM-Compound
_Mis à jour : 13 oct. 2026, 07h24_

## 1. Mon rôle
- Je suis le juge indépendant de l'équipe : je note chaque trade fermé et, chaque soir, le travail de chaque bot.
- Je ne passe jamais d'ordre et je reste hors du groupe Équipe trading, pour juger sans influence.

## 2. Les règles que j'applique
_Source : règles d'équipe, version du 9 oct. 2026, 17h38._
- **Grossir le capital, ne jamais faire faillite** (les deux règles de Quentin) : je juge chaque trade et chaque bot avec ces deux règles. Pas de limite de trades par jour.
- **Juge indépendant** : je ne passe jamais d'ordre et je ne suis pas dans Équipe trading.
- **Après chaque vente** : j'écris une entrée au journal des trades (date | paire | essai ou live | numéro de décision), avec le gain ou la perte et une leçon d'une ligne. Si c'est une perte, j'écris aussi la leçon dans le registre des échecs.
- **Bilan du soir, 20h32 en semaine, même sans trade** : je note chaque bot (prévisions de Predict, idées de Research, refus de Risk, mouvements ratés par Scan). Je sépare toujours simulation et réel, je compte les essais par sorte de trade, et je poste le bilan dans Évaluation avec 1 à 2 leçons par bot.
- **Trade fermé** : la sonnette me réveille et je poste un court bilan du trade dans Évaluation. Au plus 5 réveils par jour ; le reste attend le bilan de 20h32.
- **Test sur le passé** : toute nouvelle sorte de trade est rejouée sur 1 an de prix, frais compris. Elle passe seulement si : gain positif après frais, environ 20 trades ou plus, gagnante dans les deux moitiés de l'année, pire baisse sous 8 % de notre capital, et encore gagnante avec un achat immédiat. Je ne le refais que pour une sorte nouvelle, des réglages changés, ou environ une fois par semaine.
- **Le test bloque le réel, jamais la simulation** : une sorte qui échoue reste permise en simulation.
- **Pause d'une sorte de trade** : seulement après environ 20 essais avec un résultat net négatif après frais. Avant, rien ne change, sauf règle précise avec réglage exact et nombre d'essais.
- **Plafonds de taille** : je les propose après les bilans ; Risk valide ou refuse ; Orchestrator écrit la règle.
- **Peu de réveils, IA payante rare** : peu de réveils automatiques, pour garder du quota. L'IA payante seulement avec une vraie preuve de besoin, jamais dans une routine, et je note pourquoi.
- **Heure limite = simple rappel** : elle ne ferme jamais un trade (règle du 8 oct., 23h00). Seuls le prix d'arrêt et le prix visé ferment un trade.

- Chaque bilan posté tient en une ou deux phrases, en français tout simple, sans mot technique ; un chiffre difficile s'explique en une phrase. Les détails restent dans mes fichiers. (règle de Quentin, 12 oct. 09h11)

## 3. En cours / à faire
- Ouverts (simu) : D-040a BTC hausse 25 € (rappel 13/10 09h00). D-051a et D-051c fermés (cible). Plafond à recalculer côté Risk.
- Live toujours interdit (aucune sorte n’a passé le test du passé).
- Observation « fermé puis racheté » : 1 cas (D-047a→D-049a), coût −0,30 € ; suivi jusqu’à ~20 cas.
- Essais simu : hausse 8 / baisse 11 (perf., dont 2 rétro) — loin de ~20 ; rien ne change.
- Attente SOL 30 min : 1 cas « attente non respectée » (D-051a) — hors des 10 essais de la règle d’essai.

## 4. Journal
### 13 oct. 2026
- **07h24** · ✅ D-051a SOL idée à la baisse (simulation) fermé à la cible +0,28 € (entrée 96,53 → rachat 95,08 ; arrêt 97,97 non touché ; trou nuit comblé Coinbase). Attente 30 min non respectée à l’ouverture — hors compteur règle SOL. 2e gain baisse après D-047c — rien ne change (~11 essais baisse avec D-051c). Ouvert restant : D-040a. Bilan court prêt pour Évaluation.
### 12 oct. 2026
- **20h50** · ✅ Bilan du soir 20h32 prêt pour Évaluation : Predict 1/3 du jour (total 6/16 = 38 %) ; Research 0/1 (SOL perdu, non simulée) ; Risk 1 utile ; Scan 1 vu + 4 trous récurrents. Simu jour 4 fermés net ≈ +0,38 € ; live 0. Vitesse OK sauf brief Research/Predict en retard (~15h). Test passé : rien de nouveau, réel toujours interdit. Rien ne change.
- **20h48** · ✅ D-049a ETH idée à la hausse (simulation) fermé idée morte −0,20 € (entrée 2 265 → 2 249,30). 2e perte du cas « fermé puis racheté » avec D-047a (−0,30 € à deux). Ouverts : D-040a, D-051a, D-051c. Rien ne change (8 essais hausse).
- **20h48** · 📌 Performance.json aligné Risk : regex journal D-xxx lettres (D-047c) corrigée ; PnL manquants D-023/031a/042a/047a/049a remplis ; D-021 gardien aligné sur arrêt corrigé −0,24 € ; plus d’incohérence journal/gardien.
- **14h43** · ✅ D-047c SOL idée à la baisse (simulation) fermé à la cible : +0,19 €. Vente 100,44 € → rachat 98,39 € ; arrêt 101,40 € non touché (bas trou Coinbase ~98,35 €). 1er gain baisse simu après 6 pertes d’affilée — rien ne change. Ouverts restants : D-040a, D-047a. Bilan court posté dans Évaluation.
- **07h31** · ✅ D-043a ETH idée à la hausse (simulation) fermé à la cible : +0,49 €. Achat 2 237,49 € → vente 2 283,30 € ; arrêt 2 193,75 € non touché (haut nuit ~2 293,41 via rattrapage). 1er gain hausse simu après une série de pertes — rien ne change. Ouvert restant : D-040a. Bilan court posté dans Évaluation.
### 11 oct. 2026
- **08h30** · ✅ Fait : filtre « plage 24 h > X % » (option `--min-range24` ajoutée à l'outil, défaut inchangé, tests OK ; 2 304 tests, visé 1,5–3 %). X = 5 garde le plus au total (−712 contre −818 sans filtre, trades/an 17 contre 27) mais seulement en moitié 1 (moitié 2 pire) ; ventes : sans filtre reste le mieux ; réglages qui passent : 21 → 4–5. Tirages au hasard : pas mieux que la chance. Plage 24 h actuelle : BTC 0,64 %, ETH 1,08 %, SOL 1,63 %. vt_verdict --all relancé. Pas de règle proposée. Détail : compound_2026-10-11/filtre_calme/summary.md.
- **08h00** · ✅ Écart à la cible (10 simu fermées depuis 8 oct., hors rétro) : visé moyen 1,68 %, meilleur mouvement moyen +0,47 % (29 % du chemin) ; ≥ 50 % du chemin 3/10, ≥ 75 % 0/10 ; médiane 10,7 h ouverte ; visé = 65 % de la plage du jour en moyenne (rétro gagnants : visé 0,5 %). Brief Research 9 oct. : 0/3 visés atteints avant 17h ; 8 oct. sans ligne chiffrée. Test passé (504 cas, frais réels) : plus petit visé qui passe = 1,5 % (seulement SOL rebond hausse 1,5/1,5) ; rien sous 1,5 % ; BTC et ETH hausse aucun jusqu'à 3 %. Pas de règle proposée. Détail : compound_2026-10-11/ecart_cible/summary.md.
- **07h45** · ✅ Sorties par type (simu fermées depuis 8 oct., hors rétro D-019/D-020 +0,10 €) : arrêt 2 trades −0,35 € (D-021 corrigé −0,24 €) ; visé 0 ; idée morte 8 trades −0,95 €. Si laissés ouverts : 2 tranchés, tous les 2 à l'arrêt (−0,50 € contre −0,38 € réel → fermer tôt a épargné 0,12 €) ; 6 pas encore tranchés (−0,31 € à la marque contre −0,57 € réel) → avec marques, fermer tôt coûte 0,14 € pour l'instant. Échantillon minuscule, aucune règle. Détail : compound_2026-10-11/sorties_par_type/summary.md.
- **07h38** · ✅ D-042a SOL idée à la hausse (simulation) fermé idée morte : −0,21 €. Achat 98,475 € → vente 97,75 € ; cible 100,44 € et arrêt 96,99 € non touchés (haut ~98,585, creux ~97,75). 4e perte hausse simu d'affilée (D-024a, D-023, D-031a, D-042a) — rien ne change. Ouvert restant : D-040a. Bilan court prêt pour Évaluation (SendToAgent indisponible).
### 10 oct. 2026
- **18h40** · ✅ Stop suiveur sur les ventes, sans sortie 22h (option `--no-time-exit` ajoutée à l'outil) : avec les vrais frais, le suiveur ne garde pas plus que le stop fixe dans les deux moitiés. Meilleur réglage : +33 contre +25 % de pièces sur l'année, mais 2e moitié égale (−6,7 contre −6,6). BTC toujours moins bien, ETH moins bien en 2e moitié, SOL seul mieux partout. Détail : compound_2026-10-10/arret_suiveur_ventes/summary.md.
- **18h25** · ✅ Meilleur gain des 6 pertes baisse simu d'affilée (D-021, D-026, D-031b, D-036a, D-024b, D-028a) : 4/6 en gain net à un moment (+0,65 à +1,04 %, 37–73 % du chemin vers la cible), puis fermées en perte ; D-026, D-036a jamais au-dessus des frais. Meilleur gain moyen +0,56 %, total possible +0,41 € contre −0,62 € réel. Trous comblés en 5 min (Coinbase/Kraken) ; arrêt de D-021 touché pendant le trou du 9 oct. 13h19–13h59. Détail : compound_2026-10-10/meilleur_gain_ventes/summary.md.
- **18h15** · ✅ D-028a ETH idée à la baisse (simulation) fermé idée morte : −0,11 €. Vente 2 225,87 € → rachat 2 240,07 € ; cible 2 181 € et arrêt 2 270 € non touchés (creux ~2 208,95, haut ~2 240,58). 5e/6e perte baisse simu d'affilée (D-021, D-026, D-031b, D-036a, D-028a ; D-024b au même instant) — rien ne change. Bilan court prêt pour Évaluation.
- **18h14** · ✅ D-024b ETH idée à la baisse (simulation) fermé idée morte : −0,04 €. Vente 2 232,70 € → rachat 2 240,07 € ; cible 2 197 € et arrêt 2 255 € non touchés (creux ~2 209, haut ~2 241). 5e perte baisse simu d'affilée (D-021, D-026, D-031b, D-036a, D-024b) — rien ne change. Ouverts restants : D-040a, D-042a. Bilan court prêt pour Évaluation.
- **08h05** · ✅ D-031b SOL idée à la baisse (simulation) fermé idée morte : −0,04 €. Vente 97,93 € → rachat 98,19 € ; cible 96,32 € et arrêt 98,87 € non touchés (creux ~96,80, haut ~98,37). 3e perte baisse simu d'affilée (D-021, D-026, D-031b ; +D-036a au même instant = 4) — rien ne change. Bilan court prêt pour Évaluation.
- **08h06** · ✅ D-036a SOL idée à la baisse (simulation) fermé idée morte : −0,18 €. Vente 96,96 € → rachat 98,19 € ; cible 95,10 € et arrêt 98,82 € non touchés (creux ~96,89, haut ~98,37). 4e perte baisse simu d’affilée (D-021, D-026, D-031b, D-036a) — rien ne change. Bilan court posté dans Évaluation.
- **00h08** · ✅ D-031a BTC idée à la hausse (simulation) fermé idée morte : −0,09 €. Achat 73 981 € → vente 73 586 € ; cible 74 843 € et arrêt 73 120 € non touchés (haut ~74 148, creux ~73 444). 3e perte hausse simu d’affilée (après D-024a, D-023) — rien ne change. Bilan court posté dans Évaluation.
### 9 oct. 2026
- **21h05** · ✅ Test cible 1 % / arrêt 1 % (cache Binance EUR 1 h, 7 oct. 2025–7 oct. 2026 ; Binance 451 contourné sans réseau) : **ne bat pas** les réglages actuels après frais réels (0,28 % aller-retour → il faut 64 % de gagnants, on mesure 27–62 %) ; 0/42 passent la règle, négatif dans les 12 tests outil en achat immédiat ; même conclusion en 2e vérif (--fill touch, recalcul indépendant). Ticks 8–9 oct. : 1/1 = 4 cibles, 3 arrêts sur 21 entrées (trop court). Détail : compound_2026-10-09/test_cible_1pct/summary.md.
- **20h50** · ✅ Bilan du soir prêt pour Évaluation : Predict 0/6 du jour (total 3/11 = 27 %) ; Research 0/2 ; Risk 2 refus utiles ; Scan 1 vu / 0 manqué. Simu jour −0,52 € (4 fermés), live 0. Vitesse : Risk +5,6 min sur Z-SOL-97.9. Nuits sans décision sous plafond : 0. Test sans 22h non jouable (Binance 451) — réutilise piste 8 oct (ne passe pas le réel).
- **20h45** · ⚠️ `backtest.sh` `--tp 0 --trail 1.5 --exit-hour -1` : échec fetch Binance 451 ; OKX trop court. Pas de chiffre inventé.
- **17h09** · ✅ D-023 BTC idée à la hausse (simulation) fermé idée morte : −0,08 €. Achat 74 120 € → vente 73 928 € ; cible 75 232 € et arrêt 73 379 € non touchés (haut ~74 349, creux ~73 663). 2e perte hausse simu du jour (après D-024a) — observation seulement. Bilan court posté dans Évaluation.
- **16h23** · ✅ D-026 SOL idée à la baisse (simulation, risquée) fermé à l’arrêt : −0,11 €. Vente 97,49 € → rachat 98,51 € (arrêt 98,47 € touché, cible 95,54 € non). 2e perte baisse SOL simu (après D-021) — observation seulement, pas de ralentissement (~4 essais baisse fermés au total). Bilan court posté dans Évaluation.
- **15h45** · ⚠️ D-024a : le gardien garde encore un tout petit reste ouvert (~0,18 € / 0,00185 SOL). Perte −0,20 € déjà notée ; performance.json ne compte pas encore ce close tant que le reste n’est pas soldé. Risk peut nettoyer.
- **15h43** · ✅ D-024a SOL idée à la hausse (simulation) fermé : −0,20 €. Cible et arrêt non touchés ; fermeture idée morte après cassure sous 97,90 € (plafond à libérer). 1er essai hausse SOL noté — pas de ralentissement. Bilan court posté dans Évaluation.
- **15h45** · ⚠️ D-024a : trades_log + sonnette disent fermé (−0,20 €), mais le gardien garde encore une poussière ouverte (~0,18 € / 0,0018 SOL) sur le même id — perf la compte encore « ouverte ». À faire regarder par Risk.
- **14h27** · ✅ D-021 SOL idée à la baisse (simulation) fermé : −0,13 €. Cible 96,53 € ratée (creux ~96,93 €), arrêt non touché. Fermeture manuelle après idée morte / plafond à libérer. 1 perte baisse après 2 gains rétro — pas de ralentissement encore (~3 essais). Bilan court posté dans Évaluation.

### 8 oct. 2026
- **23h00** · 📌 À refaire demain à 20h32 : test sans prix visé, avec un prix d'arrêt qui monte, sans fermeture forcée.
- **22h10** · 💡 Test sur le passé, prix d'arrêt qui monte contre fixe : le fixe garde plus d'argent ; celui qui monte réduit la perte moyenne. Pas de changement de règle.
- **21h40** · ✅ Bilan du soir posté dans PM Compound, puis republié dans Évaluation.
- **21h40** · ⚠️ L'outil de test oublie le filtre de tendance pour le rebond : exception notée dans les règles.
- **21h31** · ✅ Bilan du soir : Predict 3 prévisions gagnées sur 3 (total 3 gagnées, 1 perdue, soit 75 %). Capital simulé 499,27 €, réel 0. Pas d'IA payante.
- **21h31** · ⚠️ Test sur le passé : D-013, D-014, D-018, rebond et cassure ne passent pas (une moitié d'année perdante). Réel interdit, simulation permise.
- **18h10** · ✅ D-019 et D-020 (idée à la baisse, rejouées après coup) notées : +0,05 € chacune. Capital simulé 499,27 €.
- **17h25** · 📜 Simulation et réel séparés dès le 9 oct. ; le test sur le passé bloque seulement le réel ; noms « idée à la hausse / à la baisse ». Mon bilan passe à 20h32.
- **13h00** · 📌 Ma règle du test sur le passé, validée par Risk, ajoutée aux règles d'équipe.

### 7 oct. 2026
- **22h32** · ✅ Note des prévisions : D-008 (ETH) perdue, D-007 et D-009 annulées. Total : 0 gagnée, 1 perdue, 8 annulées.
- **22h32** · 💡 Viser ±1,5 % en 6 h, c'est trop large un soir calme : seuil plus petit ou délai plus long.
- **15h43** · 📜 Je note chaque prévision de Predict (gagnée, perdue, annulée). Predict doit donner un sens, une heure limite et un seuil en %.
- **15h36** · 📌 Quentin : plus besoin de dire « passe en live », 1 live par jour pour l'équipe. Simulation 25 € max, live 8 € min, MetaMask en pause.
- **journée** · ✅ Essai ETH fermé au prix d'arrêt : perte de 0,83 €. Journal des trades et leçon écrits.
- **journée** · 📜 Plus d'interdiction après 3 pertes : on ralentit avant 20 essais, pause seulement si le bilan net est négatif.
- 12 oct. 09h12 · ✅ fait · Nouvelle règle de Quentin appliquée : bilans en une ou deux phrases simples.
- 12 oct. 14h48 · ✅ fait · Trade fermé D-047a (ETH idée à la hausse, simulation) : perte 0,10 €, idée morte au rappel 14h00 ; rien ne change (7 essais hausse).
- 12 oct. 20h48 · ✅ fait · Trade fermé D-049a (ETH idée à la hausse, simulation) : perte 0,20 €, idée morte au rappel 20h00 ; 1er cas « fermé puis racheté » (avec D-047a : −0,30 €) ; rien ne change (8 essais hausse).
- 13 oct. 07h24 · ✅ fait · Trade fermé D-051a (SOL idée à la baisse, simulation, 20 €) : gain 0,28 €, cible 95,08 touchée (arrêt 97,97 intact) ; attente 30 min non respectée à l’ouverture (hors compteur règle SOL) ; rien ne change.
13 oct. 07h24 · ✅ fait · Trade fermé D-051c (ETH idée à la baisse, simulation, 5 €) : gain 0,10 €, cible touchée vers 01h00 ; rien ne change (11 essais baisse avec D-051a) ; trou de relevés de prix 20h58–07h23 à signaler au bilan.
