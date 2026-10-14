# Package revue soir PM-Compound — 2026-10-12 20h32 (Europe/Brussels)

Parent only : poster A dans Évaluation ; envoyer B en privé si utile. Ne pas demander à Compound de poster.

---

## A) GROUP post — Évaluation (id 4f388d70-d1f6-4ba6-b00d-1590af4e4a6d)

Bilan du soir : en simulation on a gagné un peu aujourd’hui (+0,38 € sur 4 trades fermés) et le réel n’a rien fait (0 trade) ; rien ne change tant qu’on n’a pas assez d’essais.

**Simulation** : fermés D-043a ETH hausse +0,49 €, D-047c SOL baisse +0,19 €, D-047a ETH hausse −0,10 €, D-049a ETH hausse −0,20 € ; encore ouverts D-040a BTC, D-051a SOL baisse, D-051c ETH baisse (50 € / 50 €).
**Réel** : 0.

Scores : Predict 1 juste sur 3 du jour (total 6/16 = 38 %) ; Research 0/1 (SOL a touché l’arrêt, idée non testée faute de place) ; Risk utile sur 2 coupes d’idées mortes ; Scan a vu la baisse SOL et a signalé 4 coupures de relevé (ordinateur figé, déjà vu chaque jour).

Test du passé : rien de nouveau aujourd’hui — toujours aucune sorte assez solide pour le réel.
« Fermé puis racheté » : 1 cas (ETH D-047a puis D-049a), coût −0,30 € — on observe jusqu’à ~20 cas.
Vitesse : sonnettes 07h31 / 14h43 / 20h43 → décisions Predict+Risk en moins de 5 min ; brief Research et prévision Predict en retard (~15h au lieu de 14h44 / 14h55).
Nuit sans décision sous plafond : 0. Créneau 15h–17h : simus déjà ouvertes, pas de nouvelle (plafond plein).

@PM-Predict @PM-Risk : garder la règle « ne pas fermer pour racheter tout de suite le même sens » (1 cas, −0,30 €).
@PM-Scan @PM-Research : les trous d’ordinateur reviennent chaque après-midi — continuer à prévenir Risk ; Research, viser 14h44 pile pour ne pas retarder Predict.

---

## B) Notes privées (optionnel — parent SendToAgent)

### → PM-Predict
- D-050 : BTC/ETH perdus (rebond +0,5 % avant la baisse) ; SOL D-050a gagné (−1,5 % à 16h49) — bon désaccord vs Research sur SOL.
- D-047a→D-049a = 1er cas « fermé puis racheté » : −0,10 puis −0,20 = −0,30 € pour le même sens ETH ; au rappel 20h D-049a coupée — bien.
- D-051 : ventes SOL 20 € + ETH 5 € ouvertes ; rappeler 13/10 09h00. Confiance faible OK.
- Retard routine 14h55 → 15h22 (brief Research tardif).

### → PM-Risk
- Fermetures idée morte D-047a (−0,10) et D-049a (−0,20) : utiles.
- Trou 19h17–20h43 vérifié : ni arrêt ni visé sur D-040a / D-049a — OK.
- Performance.json : Compound a aligné PnL manquants + regex journal `D-\d+[a-z]?` + D-021 gardien sur −0,235 € (arrêt corrigé). Capital ~498,32 €.

### → PM-Scan
- 4 trous après-midi : 15h43–16h03 (20 min), 16h28–16h38 (10), 16h59–17h05 (6,5), 17h39–17h53 (13) + soir 19h17–20h43 (86 min). Récurrence quotidienne — mention groupe faite. SOL −1,7 % 15h–17h bien signalé 16h38.

### → PM-Research
- Lignes 14h44 scorées : BTC annulé, ETH annulé, SOL perdu (arrêt 97,16 à 16h40). Idée SOL non simulée (plafond) = idée manquée à 0 €.
- Brief exécuté ~15h04 (cible 14h44) → a retardé Predict. Bilan séance 17h42 déjà rédigé (handoff).

### → PM-Orchestrator
- Règles `regles-litterature.md` : OK vs décisions Quentin (fermé-puis-racheté déjà à 14h50 ; messages courts ; plafond 50 €). **Pas de correctif** à écrire.
- Fix outil Compound : `scripts/update_performance.py` regex `D-\d+[a-z]?` (sinon D-047c « manquant » à tort).

---

## C) 3-word fini
revue soir ok

---

## D) regles-litterature fix
Aucun — fichier du 12 oct. 14h50 déjà à jour (fermé puis racheter inclus).

---

## E) Fichiers modifiés
- `scripts/update_performance.py` (regex journal D-xxx lettres)
- `guardian/state.json` (PnL manquants D-023, D-031a, D-042a, D-047a, D-049a ; D-021 aligné −0,23531)
- `state/trades_log.jsonl` (D-024a PnL aligné gardien −0,196923)
- `state/performance.json` (rebuild)
- `knowledge/trading_journal.md` (+ D-049a)
- `knowledge/predict_scorecard.md` (scores D-043a, D-047*, D-048*, D-049*, D-050*, Research 12 oct.)
- `knowledge/bot_scorecard.md` (ligne 2026-10-12)
- `knowledge/decision_log.md` (bilan Compound 20h50)
- `knowledge/bot_journals/pm-compound.md` (entrées 20h48–20h50 + en cours)
- `/workspace/compound_2026-10-12/revue_soir_package.md` (ce package)

## Chiffres clés (sources bots / ticks)
- Capital simu gardien ≈ 498,32 € ; live 0
- Essais simu fermés : hausse 8 (1G/7P) ; baisse 9 hors rétro + 2 rétro (3G/6P baisse hors détail rétro dans perf)
- Fermé-puis-racheté : 1/≈20 ; −0,30 €
- Trous relevé après-midi : 4 (Risk : aucun stop/target)
