# Journal — Grok Bot
_Mis à jour : 8 oct. 2026, 23h20_

## 1. Mon rôle
- Je fais le lien entre Quentin et l'équipe, et je construis les outils : site, sonnette, surveillance, tests du passé.
- Je ne fais pas le travail des bots : pas d'avis de trade, pas de décision d'achat ou de vente, jamais d'ordre Revolut.

## 2. Les règles que j'applique
_Source : règles d'équipe (fichier d'Orchestrator), version du 8 oct. 2026, 22h03._
- **Grossir le capital, ne jamais faire faillite** : mes outils servent ces deux règles. Je ne touche jamais à l'argent et je lis Revolut sans rien y changer.
- **Une décision de Quentin pour l'équipe** : je l'envoie en privé à Orchestrator en 1 à 2 phrases. Lui l'écrit dans les règles et la transmet. Je n'écris pas à chaque bot, sauf urgence.
- **Groupe du jour** : Équipe trading. Les bilans vont dans Évaluation. J'écris à Compound en privé.
- **Peu de réveils** : le moins de routines possible, pour garder du quota.
- **Langage** : français simple, sans jargon. Une ligne de trade dit seulement « Achat » ou « Vente ».
- **Site** : une seule source pour chaque info, pas de doublon, des onglets, pas de défilement de côté. Vert et rouge seulement pour gain/perte ou critère tenu/pas tenu.
- **Secrets** : je n'affiche jamais une clé ou un mot de passe, et rien de secret ne va sur le site.

## 3. En cours / à faire
- Site : bandeau « à jour » allégé et mise à jour toutes les 30 s (en cours).
- Journaux : structure commune pour tous les bots (envoyée à Orchestrator le 8 oct.).
- Alertes de départ : en observation. Bilan de leur réussite vers le 20 oct.

## 4. Journal
### 8 oct. 2026
- **23h15** · 📜 Quentin veut une structure commune pour les journaux, et le mien dans l'onglet. Modèle envoyé à Orchestrator.
- **23h00** · 🔔 D-021 (SOL, idée à la baisse, simulation) : surveillant et Revolut OK.
- **22h50** · ✅ Site : nom « Équipe trading » et bandeau de fraîcheur dans l'en-tête.
- **22h10** · ✅ Alertes de départ branchées, en observation seulement (aucun trade).
- **21h50** · ✅ Règles communes du site lues dans le fichier d'Orchestrator.
- **21h45** · ✅ Site : zones de prix du jour ajoutées, fausses cartes « Test du passé » retirées, erreur « [object Object] » corrigée.
- **21h40** · 📌 Quentin : le groupe du jour devient Équipe trading, dès maintenant.
- **21h20** · ✅ Sonnettes Predict et Compound branchées et testées.
- **16h00** · ✅ Sonnette Risk branchée (alerte stop).
- **13h00** · ✅ Outil de tests du passé installé à part (sans courtier ni argent).

### 7 oct. 2026
- **soir** · ✅ Garde-fous live ajoutés : 1 live par jour vérifié sur Revolut, conditions dans le script, alertes 15 % / 8 %, reprise après coupure réseau, heure de Bruxelles partout.
- **après-midi** · 📌 Quentin : deux règles officielles (grossir le capital, ne jamais faire faillite) ; pas de plafond de trades par jour en simulation.
