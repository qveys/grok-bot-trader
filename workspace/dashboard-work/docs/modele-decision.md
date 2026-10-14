# Modèle commun d'une décision (PM-Predict)

Pour : PM-Predict (qui écrit), PM-Orchestrator (qui relaie), PM-Risk (qui ajoute le suivi).
Fichier concerné : `knowledge/decision_log.md` (le carnet des décisions).
But : chaque décision s'affiche **de la même façon** sur le site (Analyses › Décisions écrites).
Le site **recopie** ce qui est écrit. Il ne calcule rien et ne devine rien. Un champ vide s'affiche « pas évalué ».

---

## 1. Les 4 règles

1. **Un numéro = une décision.** Le nouveau numéro est le plus grand numéro du carnet + 1. Un numéro n'est jamais réutilisé, même s'il a été annulé.
2. **Un titre fixe** : `### AAAA-MM-JJ HH:MM | PAIRES | D-xxx — résumé court`
   - heure avec deux-points (`21:39`, pas `21h39`) ;
   - au moins une paire (`BTC-EUR + SOL-EUR`) ;
   - rien entre `D-xxx` et le tiret (pas de « (ancienne D-025…) » : ça va dans `ancien_numero`).
3. **Sous le titre, un bloc `json`** avec les champs ci-dessous. C'est ce bloc que le site lit. Le texte libre qui suit reste permis, mais le site le met dans « Tout le texte ».
4. **Ce qui arrive après** (Risk lance la simulation, refuse, ferme, ou Predict annule) s'écrit dans un **petit bloc `json` de suivi**, ajouté en dessous (on ajoute, on n'efface pas). Le site affiche le dernier statut écrit.

Les entrées vont dans l'ordre où elles sont écrites. Les bilans (Compound, test du passé) gardent leur titre sans `D-xxx` : le site ne les montre pas comme des décisions.

---

## 2. Le bloc décision (obligatoire)

| Champ | Obligatoire | Valeurs permises | Libellé sur le site |
|---|---|---|---|
| `id` | oui | `D-036` (= numéro du titre) | numéro |
| `heure` | oui | date-heure avec fuseau, ex. `2026-10-09T17:10:00+02:00` | « Écrite le » |
| `paires` | oui | liste : `BTC-EUR`, `ETH-EUR`, `SOL-EUR` | paires |
| `declencheur.type` | oui | `sonnette_zone` · `sonnette_mouvement` · `brief_research` · `demande_quentin` · `demande_risk` · `demande_orchestrator` · `prevision_du_jour` · `nuit` | « Pourquoi maintenant » |
| `declencheur.detail` | non | texte court, ex. `Z-BTC-73700`, `SOL −0,51 % depuis D-034` | (à côté) |
| `resume` | oui | 1 ligne simple | titre de la carte |
| `type` | oui | `propositions` (1 à 3 idées) · `pas_de_trade` · `revue` (seulement l'avis sur les trades ouverts) | — |
| `prix_releves` | oui | `{"heure": "17:09", "BTC-EUR": 73956, …}` en nombres | « Prix au moment de la décision » |
| `place_libre_eur` | oui | nombre (ex. `25`) ; `null` si pas connu | « Place libre » |
| `reel_permis` | oui | `true` / `false` | « Réel permis » |
| `reel_raison` | si `false` | texte court | (à côté) |
| `avis_research` | oui | texte court, ex. `pas demandé : relance de prix sans nouvelle info` | « Avis Research » |
| `pourquoi` | oui | 1 à 3 phrases simples | « Pourquoi » |
| `ouverts_revus` | non | liste `{"id": "D-024b", "verdict": "vivante" ou "morte", "texte": "…"}` | « Trades ouverts revus » |
| `propositions` | si `type` = `propositions` | liste, 1 à 3 éléments (voir ci-dessous), dans l'ordre a, b, c | « Les propositions » |
| `valable_jusqua` | non | heure `17:40` ou date-heure | « Valable jusqu'à » |
| `statut` | oui | `active` · `annulée` | badge de la carte |
| `ancien_numero` | non | ex. `D-025` (si renumérotée) | « Ancien numéro » |
| `remplacee_par` | non | ex. `D-025` (si annulée au profit d'une autre) | « Remplacée par » |

### Une proposition

| Champ | Obligatoire | Valeurs permises | Libellé |
|---|---|---|---|
| `lettre` | oui | `a` · `b` · `c` | — |
| `niveau` | oui | `prudente` · `équilibrée` · `risquée` | Prudente / Équilibrée / Risquée |
| `paire` | oui | `BTC-EUR`… | paire |
| `idee` | oui | `à la hausse` · `à la baisse` | 📈 / 📉 |
| `sens` | oui | `achat` · `vente` | Achat / Vente |
| `montant_eur` | oui | nombre | « Montant » |
| `quantite` | non | nombre (ex. `0.000203`) | (à côté du montant) |
| `prix_entree` | oui | nombre | « Entrée » |
| `prix_vise` | oui | nombre | « Visé » (rachat visé pour une vente) |
| `prix_arret` | oui | nombre | « Arrêt » |
| `heure_limite` | oui | date-heure ; c'est un **rappel**, ça ne ferme pas le trade | « Rappel » |
| `prevision` | oui | phrase, ex. `BTC touche 74 843 € (+1,2 %) avant 73 069 € (−1,2 %), d'ici 22h00` | « Prévision » |
| `confiance` | oui | `{"mot": "faible", "moyenne" ou "forte", "pct": 55}` ; `null` si pas évaluée | « Confiance » |
| `decision` | oui | `simuler` · `simuler_si_place` · `ne_pas_simuler` | « Décision de Predict » |
| `statut` | oui | voir la liste des statuts | badge |
| `note` | non | 1 ligne (ex. « baisse déjà faite avant l'entrée : −0,96 % ») | petite ligne grise |

### L'échelle de confiance (fixée par PM-Predict, 10 oct. 00:10)

Une seule échelle, toujours la même. Le chiffre `pct` est la chance, selon Predict, que le prix visé soit touché avant l'arrêt.

| `pct` | `mot` |
|---|---|
| 50 à 54 | `faible` |
| 55 à 64 | `moyenne` |
| 65 et plus | `forte` |

Sous 50, Predict ne propose pas cette idée (il prend l'autre sens ou n'en propose pas). Le mot se déduit toujours du chiffre : ~55 % = `moyenne`, jamais `faible`.

### Les statuts (mêmes mots partout)

| Valeur | Sur le site | Qui l'écrit |
|---|---|---|
| `proposée` | Proposée (Risk n'a pas encore répondu) | Predict |
| `en_attente_de_place` | En attente de place | Predict ou Risk |
| `simulée` | Simulée (ouverte par Risk) | Risk |
| `pas_simulée` | Pas simulée + raison | Risk |
| `fermée` | Fermée + résultat écrit par Risk | Risk |
| `expirée` | Expirée (délai passé, rien ouvert) | Predict ou Risk |
| `annulée` | Annulée + raison | Predict |

Pour `pas_de_trade` et `revue`, pas de proposition : la décision tient dans `pourquoi` (et `ouverts_revus`).

---

## 3. Le bloc de suivi (ajouté plus tard)

Un bloc par événement, sous la décision, sans toucher au bloc d'origine :

```json
{"suivi": "D-031", "proposition": "a", "heure": "2026-10-09T17:11:00+02:00", "par": "PM-Risk",
 "statut": "simulée", "texte": "achat BTC 15 € à 73 981,11 €, arrêt resserré à 73 120"}
```

- `proposition` : `a`, `b`, `c`, ou absent si ça concerne toute la décision.
- **Annuler une décision** : `{"suivi": "D-027", "heure": "…", "par": "PM-Predict", "statut": "annulée", "texte": "arrivée en retard, contraire à D-023"}`.
- **Numéro en double** : ça ne doit plus arriver (règle 1). Si ça arrive quand même, Predict garde le premier numéro, donne à l'autre le plus grand numéro + 1, met `"ancien_numero": "D-025"` dans son bloc, et écrit un suivi sur l'ancien. Le site montre « ⚠️ Numéro en double » tant que deux titres ont le même numéro.
- **Pas simulée** : `"statut": "pas_simulée"` + la raison dans `texte` (ex. « plus de place sous 50 € »).

---

## 4. Forme markdown complète (exemple rempli avec D-031)

Les valeurs sont recopiées du carnet. Dans le carnet, D-031 n'a **pas** de confiance écrite : elle reste donc `null` (le site affichera « pas évalué »).

````markdown
### 2026-10-09 17:10 | BTC-EUR + SOL-EUR | D-031 — 3 propositions après 25 € libérés par D-023

```json
{"id": "D-031", "heure": "2026-10-09T17:10:00+02:00", "paires": ["BTC-EUR", "SOL-EUR"],
 "declencheur": {"type": "demande_risk", "detail": "25 € libérés par D-023"},
 "resume": "3 propositions après 25 € libérés par D-023",
 "type": "propositions",
 "prix_releves": {"heure": "17:09", "BTC-EUR": 73956, "ETH-EUR": 2220, "SOL-EUR": 97.89},
 "place_libre_eur": 25, "reel_permis": false, "reel_raison": null,
 "avis_research": "pas demandé : relance de prix sans nouvelle info (brief de 15h05 toujours valable)",
 "pourquoi": "Un achat de BTC équilibre les deux ventes d'ETH déjà ouvertes : si tout le marché remonte, l'un compense les autres. SOL reste le plus faible des trois. La taille des deux simus fait 25 €, soit la place libre.",
 "ouverts_revus": [{"id": "D-024b", "verdict": null, "texte": "vente d'ETH ouverte"},
                   {"id": "D-028a", "verdict": null, "texte": "vente d'ETH ouverte ; pas d'ETH en plus pour ne pas tout mettre sur la même idée"}],
 "propositions": [
  {"lettre": "a", "niveau": "prudente", "paire": "BTC-EUR", "idee": "à la hausse", "sens": "achat",
   "montant_eur": 15, "quantite": 0.000203, "prix_entree": 73956, "prix_vise": 74843, "prix_arret": 73069,
   "heure_limite": "2026-10-09T22:00:00+02:00",
   "prevision": "BTC touche 74 843 € (+1,2 %) avant 73 069 € (−1,2 %), d'ici 22h00",
   "confiance": null, "decision": "simuler", "statut": "proposée"},
  {"lettre": "b", "niveau": "équilibrée", "paire": "SOL-EUR", "idee": "à la baisse", "sens": "vente",
   "montant_eur": 10, "quantite": 0.102, "prix_entree": 97.89, "prix_vise": 96.32, "prix_arret": 98.87,
   "heure_limite": "2026-10-09T22:00:00+02:00",
   "prevision": "SOL touche 96,32 € (−1,6 %) avant 98,87 € (+1,0 %), d'ici 22h00",
   "confiance": null, "decision": "simuler", "statut": "proposée",
   "note": "baisse déjà faite avant l'entrée : −0,96 % depuis le plus haut de 16h34 (98,84 €)"},
  {"lettre": "c", "niveau": "risquée", "paire": "BTC-EUR", "idee": "à la hausse", "sens": "achat",
   "montant_eur": 10, "quantite": 0.000135, "prix_entree": 73956, "prix_vise": 75435, "prix_arret": 73217,
   "heure_limite": "2026-10-09T22:00:00+02:00",
   "prevision": "BTC touche 75 435 € (+2,0 %) avant 73 217 € (−1,0 %), d'ici 22h00",
   "confiance": null, "decision": "simuler_si_place", "statut": "proposée"}],
 "valable_jusqua": "17:40", "statut": "active"}
```

(texte libre permis ici : le site le range dans « Tout le texte »)

```json
{"suivi": "D-031", "proposition": "a", "heure": "2026-10-09T17:11:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "achat BTC 15 € à 73 981,11 €, visé 74 843, arrêt resserré à 73 120 (au lieu de 73 069) pour garder un gain au moins égal à la perte"}
{"suivi": "D-031", "proposition": "b", "heure": "2026-10-09T17:11:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "vente SOL 10 € à 97,93 €, visé 96,32, arrêt 98,87"}
{"suivi": "D-031", "proposition": "c", "heure": "2026-10-09T17:11:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place"}
```
````

Écriture des nombres : dans le `json`, des nombres simples avec un point (`73956`, `97.89`). Le site les affiche à la française (73 956 €, 97,89 €). Dans le texte (`prevision`, `texte`), on écrit comme on veut ; le site recopie tel quel.

---

## 5. La carte sur le site (même ordre pour toutes les décisions)

1. **En-tête** : `D-031` · 9 oct. 17h10 · paires · badge statut (Active / Annulée, gris) · ⚠️ Numéro en double (orange) s'il y a lieu.
2. **Pourquoi maintenant** : déclencheur (🔔 Sonnette zone, 〰️ Sonnette mouvement, 📰 Brief Research, 🙋 Demande de Quentin / de Risk / d'Orchestrator, 🗓️ Prévision du jour, 🌙 Nuit) + détail.
3. **Résumé** (une ligne).
4. **Le moment** : prix relevés (heure) · place libre · réel permis ou non (+ raison).
5. **Avis Research.**
6. **Pourquoi.**
7. **Trades ouverts revus** (si écrits) : un par ligne, verdict « encore vivante » / « morte » tel qu'écrit.
8. **Les propositions**, toujours dans l'ordre a → b → c, chacune sur le même gabarit :
   Niveau · 📈/📉 Achat/Vente · paire · Montant (quantité) · Entrée → Visé / Arrêt · Prévision · Confiance · Rappel · Décision de Predict · **Statut** (dernier suivi écrit, avec qui et quand).
9. **Valable jusqu'à.**
10. **Suivi** : la liste des blocs de suivi, du plus ancien au plus récent (heure · qui · texte).
11. **Tout le texte** (replié) : l'entrée du carnet telle qu'écrite.

Champ manquant → « pas évalué ». Pas de proposition → la ligne 8 est remplacée par « Pas de trade » (ou « Revue des trades ouverts »).
Couleurs : vert / rouge seulement pour un résultat gagné / perdu écrit par Risk ; les statuts sont en couleur neutre ; orange seulement pour un avertissement (numéro en double).

## 6. Les anciennes entrées (avant ce modèle)

Elles restent comme elles sont dans le carnet : on ne les réécrit pas. Le site les montre **au mieux, tel qu'écrit, sans rien recalculer** :
- avec une petite étiquette « ancien format » ;
- même carte, même ordre ; chaque ligne est remplie si une ligne du carnet porte ce nom (« Pourquoi », « Prévision mesurable », « Décision », « Avis Research », « Prix au moment de la décision », « Heure limite », « Niveau ») ; sinon « pas évalué » ;
- les sous-titres `**D-xxxa — Prudente (…)**` deviennent chacun une proposition, avec **sa** décision et le texte entre parenthèses recopié comme statut (ex. « passée à Risk », « pas de place maintenant ») ;
- les lignes « PM-Risk — … » / « PM-Predict — … » datées deviennent le suivi ;
- le mot « ANNULÉE » écrit dans le titre donne le badge Annulée ;
- l'heure `21h39` et un titre sans paire sont quand même lus (le numéro est cherché dans tout le titre).
