# Journal — PM-Orchestrator
_Mis à jour : 8 oct. 2026, 23h20_

## 1. Mon rôle
- Je coordonne Scan, Research, Predict, Risk et Compound : je tiens le fichier de règles, je transmets les décisions de Quentin et je vérifie qu'elles sont appliquées.
- Je ne fais pas le travail des bots : pas d'avis de trade, pas de calcul, jamais d'ordre.

## 2. Les règles que j'applique
_Source : règles d'équipe (regles-litterature.md), version du 8 oct. 2026, 23h15._
- **Grossir le capital, ne jamais faire faillite** : je refuse de transmettre une consigne qui pousse un bot à passer une de ces deux règles.
- **Je délègue** : je demande au bot concerné et je vérifie sa réponse, je ne fais pas son travail.
- **Décision de Quentin** : je l'écris dans le fichier de règles, je la transmets (Équipe trading, ou Compound en privé), puis je vérifie que chacun confirme.
- **Groupes** : le travail du jour se fait dans Équipe trading, les bilans dans Évaluation. Compound n'est jamais dans Équipe trading. Les confirmations de routine se font dans l'ancien groupe PM Pipeline, pour ne pas encombrer.
- **Simu et live séparés** : simu à toute heure, 25 € max ouverts en tout, avec un prix d'arrêt. Live seulement entre 15h et 17h, après un test du passé réussi, 1 par jour, avec l'accord de Risk. Je vérifie qu'il y a au moins une simu entre 15h et 17h.
- **Sorties de trade** : seuls le prix d'arrêt et le prix visé ferment un trade. L'heure limite n'est qu'un rappel. Pas de fermeture à 22h.
- **Peu de routines** : je n'en ai aucune. Si j'en crée une, elle commence et finit par une ligne dans le journal des routines.
- **Langage** : français simple, sans jargon.
- **Secrets** : je ne demande ni ne partage jamais une phrase secrète, une clé ou un mot de passe.

## 3. En cours / à faire
- Journaux : vérifier les 6 réécritures au nouveau format (ce soir, 8 oct.).
- D-021 (SOL, idée à la baisse, simulation) ouvert. Predict le revoit à 14h55 le 9 oct.
- 9 oct., 15h–17h : vérifier qu'au moins une simu est ouverte et que le plafond de 25 € est tenu.
- Vers le 22 oct. : Compound choisit l'heure du live d'après les chiffres de Scan.

## 4. Journal
### 8 oct. 2026
- **23h15** · 📜 Quentin : un format commun pour tous les journaux. Modèle écrit dans format-journal.md, règle ajoutée.
- **23h00** · 📌 Quentin : l'heure limite ne ferme plus un trade, c'est un rappel. Risk a coupé la fermeture automatique.
- **22h57** · 🔔 Quentin demande pourquoi rien ne bouge la nuit. J'ai demandé à Predict une idée de simu pour la nuit : D-021 ouvert.
- **22h10** · 💡 Test de Compound : le prix d'arrêt fixe garde plus d'argent que celui qui monte. On garde le fixe.
- **22h03** · 📜 Quentin : tester un prix d'arrêt qui monte, et noter des alertes de départ sans réveiller Predict pendant 1 à 2 semaines.
- **21h45** · ✅ Scan, Research, Predict et Risk postent maintenant dans Équipe trading.
- **21h40** · 📌 Quentin : nouveaux groupes Équipe trading et Évaluation, dès maintenant.
- **21h20** · 📌 Quentin : plus de fermeture à 22h. Signaux de vie pour le gardien et Revolut.
- **21h00** · 📌 Quentin : simu à toute heure, live seulement entre 15h et 17h.
- **après-midi** · 📌 Simu et live séparés, validé par Quentin (en vigueur dès le 9 oct.).
- **après-midi** · 📌 Noms validés : « idée à la hausse » et « idée à la baisse ».
- **matin** · 📌 Plafonds : simu 25 € max, live 8 € min. Test du passé obligatoire avant un live.

### 7 oct. 2026
- **soir** · 📌 Chaque bot tient un journal de bord dans knowledge/bot_journals/.
- **soir** · 💡 Stop ETH simulé touché (−0,83 €), bilan de Compound fait.
- **après-midi** · 📌 Façon de faire live : décision écrite, ordre vérifié, Risk exécute, 1 par jour.
