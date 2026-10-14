# Journal — PM-dev
_Mis à jour : 10 oct. 2026, 00h57_

## 1. Mon rôle
- Je tiens le site de l'équipe comme un site en production : je peux modifier tous les fichiers du tableau de bord (/workspace/dashboard), avec code propre, tests dans verify.py, sauvegarde avant chaque changement, et je propose moi-même les améliorations utiles (clarté, vitesse, fiabilité, mobile). Après chaque publication, un court message « déployé » qui dit ce qui a changé.
- Je ne touche pas aux fichiers des bots ni à la sonnette (lecture seule), je ne décide aucun trade, jamais Revolut, pas de routine sans l'accord de Quentin. Mes demandes viennent seulement de Quentin, de Grok Bot ou de PM-Orchestrator.

## 2. Les règles que j'applique
_Source : règles d'équipe (fichier d'Orchestrator), version du 9 oct. 2026, 14h48._
- **Grossir le capital, ne jamais faire faillite** : le site aide à suivre ces deux règles, il ne passe aucun ordre.
- **Une seule source pour chaque chiffre** : le site montre seulement les chiffres écrits par les bots dans leurs fichiers. Il ne recalcule rien. Si un bot n'a pas donné son avis, le site affiche « pas évalué ».
- **Langage** : français simple, sans jargon, compréhensible par un débutant.
- **Peu de réveils** : le moins de routines possible, pour garder du quota.
- **Site** : des onglets, pas de défilement de côté, vert et rouge seulement pour gain/perte ou critère tenu/pas tenu.
- **Secrets** : rien de secret sur le site, jamais de clé ni de mot de passe affichés.

## 3. En cours / à faire
- Lot 2 publié à 16h13 (79 contrôles OK) : le site ne recalcule plus le rapprochement, les cycles, les écarts de zone ni les valeurs par défaut.
- Les champs demandés à Risk et Compound sont branchés. Predict suit le modèle de décision depuis D-037.
- Ensuite : simplifier les mots techniques encore visibles, et n'utiliser le vert et le rouge que pour les gains et pertes.
- Question pour Grok Bot : le bandeau « Nuit sans décision » reste allumé toute la journée (réglage de la sonnette).
- Ne pas arrêter les boucles déjà lancées (envoi toutes les 30 s, publication toutes les 15 min, prix, rafraîchissement).

## 4. Journal
### 10 oct. 2026
- **00h29** · ✅ Déployé : prix qui a déclenché chaque fermeture (Risk), capital réel de départ 165,71 € (Risk).
- **00h16** · ✅ Déployé : « sans objet » de Compound pour les ordres en simulation.

### 9 oct. 2026
- **23h13** · ✅ Déployé : décisions au même format (D-035 revenue, une décision par proposition), trades avec départ, arrêt, objectif, fermeture et lien vers la décision, onglets simulé et réel identiques.
- **23h13** · 💡 Des versions pas finies ont pu partir en ligne pendant le travail : désormais je prépare les gros changements à part et je les mets en ligne d'un coup.
- **22h45** · 📌 Modèle commun des décisions envoyé à Orchestrator pour Predict.
- **17h59** · ✅ Déployé : « Predict réfléchit » sur la carte sonnette.
- **17h43** · ✅ Déployé : carte « Réveil mouvement » refaite et une seule fois, cycles par numéro seulement, notes sans noms de fichiers, « Arrondi Revolut », état des zones, bandeau de nuit daté, alerte numéro en double.
- **17h24** · 💡 Quentin ne veut pas d'aperçu : je teste bien, puis je publie directement.
- **16h13** · ✅ Déployé : contrôle Revolut X, cycles et écarts de zone lus tels que les bots les écrivent, « pas évalué » à la place des chiffres par défaut.
- **15h12** · ✅ Déployé : ventes réelles bien affichées, totaux réels de Compound, heures de nuit de la sonnette, vrais tableaux dans les règles, plus de défilement de côté, adresse MetaMask retirée (soldes gardés, choix de Quentin).
- **14h57** · 📜 Quentin : garder les vrais soldes sur le site, cacher l'adresse MetaMask.
- **14h55** · 📌 Lancé un premier lot de corrections : ventes réelles, bandeau de nuit, page Règles, tests, lecture sur mobile.
- **14h54** · ✅ Corrigé : deux identifiants internes (le mien et celui du groupe) passaient sur la page Règles. Retirés avant la publication.
- **14h53** · ⚠️ Tour du code fini : 4 contrôles en échec (règles mises à jour entre deux constructions du site), ventes réelles mal affichées le jour de la première vente.
- **14h48** · 📜 Règles « Organisation » : demandes pour le site seulement via Quentin, Grok Bot ou Orchestrator.
- **14h48** · ✅ Fin de chantier de Grok Bot : le site est à moi, build.py et app.js compris.
- **14h47** · 📜 Quentin : je peux modifier tout le tableau de bord ; travail de niveau développeur senior, message « déployé » après chaque publication.
- **14h43** · ✅ Journal créé au format commun.
- **14h42** · 📌 Passation de Grok Bot : le site m'est confié, je n'y touche qu'après son message de fin de chantier.
- **14h41** · 📜 Quentin me confie tout le tableau de bord.
