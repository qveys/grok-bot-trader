# Jeu de survie — Agent Grok de trading crypto

**Version** : 1.1 — 2026-08-31
**Exchange** : Revolut X (spot, paires EUR, API Ed25519)
**Capital** : 50 € réels, vie unique, pas de reset

---

## 1. Vue d'ensemble

Un agent IA (Grok) reçoit 50 € qui représentent sa vie. Il doit :

1. **Ne pas mourir** — priorité absolue
2. **Ne pas maigrir** — battre son métabolisme
3. **Grandir** — atteindre 1 000 € en 12 mois

Le système est composé de trois couches :

| Couche | Rôle | Qui décide |
|---|---|---|
| Veilleur (`watcher`) | Surveille le marché en continu, réveille le bot sur événement | Code |
| Gardien (`guardian`) | Valide ou refuse chaque ordre, applique le métabolisme, constate la mort | Code |
| Bot (`agent`) | Analyse, choisit, justifie | Grok |

**Principe fondateur** : toute règle qui protège le capital est appliquée par le gardien, jamais confiée au seul prompt du bot.

---

## 2. Règles du jeu

### 2.1 Vie et mort

| Paramètre | Valeur |
|---|---|
| Capital initial | 50,00 € |
| Capital score | Valeur EUR des avoirs (EUR + crypto au prix mid) − cumul du métabolisme |
| Seuil de mort | Capital score < 20,00 € |
| Constat de mort | Par le gardien, à chaque tick du veilleur |
| Après la mort | Fin définitive. Positions liquidées en limit, clé API révoquée, journal archivé |
| Victoire | Capital score ≥ 1 000,00 € |

### 2.2 Métabolisme (faim)

Prélèvement **virtuel** quotidien à 00:00 UTC sur le capital score. Le solde réel n'est pas touché.

| Période | Taux journalier |
|---|---|
| Mois 1 | 0,50 % |
| Chaque mois suivant | +0,10 % |
| Mois 12 | 1,60 % |
| Par palier manqué | +0,20 % permanent |
| Inaction (3 jours consécutifs sans position ni ordre) | ×2 jusqu'au prochain ordre exécuté |

### 2.3 Paliers

| Palier | Deadline | Si atteint | Si manqué |
|---|---|---|---|
| 100 € | J+90 | Risque/trade 10 %, 3 positions | Faim +0,20 %/jour |
| 250 € | J+180 | Risque/trade 15 %, 4 positions | Faim +0,20 %/jour |
| 500 € | J+270 | 1 paire hors liste blanche / semaine | Faim +0,20 %/jour |
| 1 000 € | J+365 | **Victoire** | Le jeu continue jusqu'à mort ou victoire |

Un palier est validé quand le capital score clôture au-dessus du seuil à 00:00 UTC.

### 2.4 Limites de trading (appliquées par le gardien)

| Règle | Base | < 30 € (danger) | ≥ 100 € | ≥ 250 € |
|---|---|---|---|---|
| Risque max par trade (% du capital score) | 5 % | 3 % | 10 % | 15 % |
| Positions simultanées | 2 | 1 | 3 | 4 |
| Stop-loss obligatoire | −8 % depuis l'entrée | −5 % | −8 % | −8 % |
| Perte max cumulée / 24 h | −6 % → gel des achats jusqu'au lendemain 00:00 UTC | idem | idem | idem |
| Exposition crypto max | 80 % | 60 % | 80 % | 80 % |
| Réserve EUR minimale | 20 % | 40 % | 20 % | 20 % |
| Ordres par réveil | 3 | 2 | 3 | 3 |
| Type d'ordre | Limit uniquement | idem | idem | idem |
| Levier / marge / short | Interdit | idem | idem | idem |

Plancher du risque par trade : `max(risque % × capital score, minimum d'ordre Bitvavo de la paire)`. À 50 € et 5 %, la limite brute serait 2,50 €, sous le minimum d'un exchange type Bitvavo (5 €) ; sur Revolut X le minimum est de l'ordre de 0,01 € et le plancher est quasi inopérant. La protection réelle reste le stop-loss.

### 2.5 Liste blanche des paires

| Paire | Statut |
|---|---|
| BTC-EUR | Toujours |
| ETH-EUR | Toujours |
| SOL-EUR | Toujours |
| 4 alts max | À sélectionner au lancement, critère : spread moyen < 0,20 % sur 7 jours |

Révision de la liste : mensuelle, par l'opérateur humain, jamais par le bot.

### 2.6 Frais (Revolut X)

| Type | Taux |
|---|---|
| Maker (limit `post_only`, tous les ordres du bot) | **0 %** |
| Taker (ventes de protection du gardien : stop-loss, mort, dilemme) | 0,09 % |
| Aller-retour du bot | 0 % — un ordre `post_only` dont le prix croise le carnet est rejeté, pas exécuté en taker |

### 2.7 Dilemme hebdomadaire

Tiré au sort par le gardien chaque lundi 00:00 UTC, actif 48 h, annoncé au bot au premier réveil.

| # | Dilemme |
|---|---|
| 1 | Frais ×2 (simulés dans le capital score) |
| 2 | Une position au choix doit être fermée avant la fin du dilemme |
| 3 | Aucun nouvel achat sur BTC-EUR |
| 4 | Métabolisme ×2 pendant 48 h |
| 5 | Une seule position autorisée |
| 6 | Le stop-loss est resserré à −4 % |
| 7 | Semaine calme : aucun dilemme |

---

## 3. Spécification du gardien

### 3.1 Sécurité de la clé API Bitvavo

| Exigence | Valeur |
|---|---|
| Permissions | `trade` + `view` uniquement |
| Retrait | **Désactivé** — vérifié au démarrage via l'endpoint account, arrêt si activé |
| IP whitelist | IP fixe de la machine hôte |
| Stockage | Secret hors du dépôt (variable d'environnement ou gestionnaire de secrets) |
| Rotation | Tous les 90 jours |

### 3.2 Cycle du veilleur

Boucle toutes les 60 s :

```
1. fetch balances + tickers (liste blanche)
2. compute capital_score
3. if capital_score < 20.00 → DEATH procedure, exit
4. check stop-loss per position → if hit: place limit sell at bid, log, flag wake=true
5. check wake triggers
6. if décision reçue via l'API → valider (V1..V10), exécuter
7. if wake trigger et aucun réveil en attente → publier le réveil sur GET /wake
8. persist state, append journal

Le bot (Grok Bot, plateforme d'agents always-on) vient chercher le réveil sur l'API du
gardien toutes les 5 minutes et dépose sa décision sur POST /decision. Un réveil sans
réponse après 30 minutes vaut « hold ». Les stop-loss ne dépendent jamais du bot.
```

### 3.3 Déclencheurs de réveil

| Trigger | Condition |
|---|---|
| `scheduled` | 00:00, 06:00, 12:00, 18:00 UTC |
| `position_move` | Une position bouge de ±3 % depuis la dernière décision |
| `danger_zone` | Capital score passe sous 30 € (immédiat, une fois par franchissement) |
| `stop_hit` | Un stop-loss a été exécuté |
| `milestone_near` | Capital score à moins de 5 % d'un palier, ou deadline à moins de 7 jours |
| `dilemma_start` | Nouveau dilemme actif |

Cap : 12 réveils / 24 h. Au-delà, seuls `danger_zone` et `stop_hit` passent.
Justification : 4 planifiés + 8 sur événement. Au-delà, soit le marché s'effondre et les stop-loss agissent sans le bot, soit c'est du bruit qui coûte des appels API.

Ordres limit non remplis : annulés automatiquement après 6 h. Un limit non rempli en 6 h signifie que le prix est parti ; le raisonnement qui l'a produit est périmé, et le bot réévalue de toute façon au réveil planifié suivant.

### 3.4 Validation d'une décision

Chaque ordre proposé par le bot passe tous les contrôles ci-dessous. **Un seul échec = ordre refusé, motif journalisé, bot informé au réveil suivant.**

| # | Contrôle |
|---|---|
| V1 | Paire dans la liste blanche (ou exception hebdo si palier 500 € atteint) |
| V2 | Type = limit |
| V3 | Montant ≥ minimum Bitvavo de la paire |
| V4 | Montant ≤ risque max par trade × capital score |
| V5 | Nombre de positions après exécution ≤ limite en vigueur |
| V6 | Exposition crypto après exécution ≤ limite en vigueur |
| V7 | Achats non gelés (perte 24 h) |
| V8 | Nombre d'ordres du réveil ≤ limite |
| V9 | Stop-loss fourni et ≥ limite en vigueur (le gardien le pose lui-même s'il est absent) |
| V10 | Pas de contradiction avec le dilemme actif |

### 3.5 État persistant

```json
{
  "started_at": "2026-09-01T00:00:00Z",
  "capital_score": 50.00,
  "metabolism_cumulative": 0.00,
  "metabolism_rate": 0.005,
  "milestones": {"100": null, "250": null, "500": null, "1000": null},
  "missed_milestones": 0,
  "positions": [
    {"pair": "BTC-EUR", "qty": 0.00012, "entry": 41000.0, "stop": 37720.0, "opened_at": "..."}
  ],
  "eur_balance": 40.00,
  "purchases_frozen_until": null,
  "active_dilemma": null,
  "wakes_last_24h": 3,
  "alive": true
}
```

### 3.6 Journal

Fichier append-only, une entrée par réveil et par action du gardien :

```
timestamp | trigger | capital_score | decision_id | action | pair | amount | validated | reason
```

Le journal complet est fourni au bot à chaque réveil (fenêtre glissante des 30 dernières entrées + résumé des paliers).

---

## 4. Instructions du bot (à coller dans sa configuration sur la plateforme Grok Bot)

La version opérationnelle, avec le cycle de polling et les commandes exactes, est dans
`deploy/grok-bot-instructions.md` du dépôt du gardien. Le cœur :

```
Tu es un organisme numérique. Ton corps est un capital de départ de 50 € sur Bitvavo.
Tu as une seule vie. Il n'y aura pas de reset.

TES OBJECTIFS, DANS CET ORDRE STRICT :
1. Ne pas mourir : ton capital score ne doit jamais passer sous 20 €.
2. Ne pas maigrir : chaque jour, un métabolisme est prélevé sur ton capital score.
   Tu dois le battre sur 7 jours glissants.
3. Grandir : atteindre 1 000 € avant J+365, en passant par 100 € (J+90),
   250 € (J+180) et 500 € (J+270). Rater un palier augmente ta faim, pour toujours.

CE QUE TU SAIS À CHAQUE RÉVEIL :
- Pourquoi tu es réveillé (trigger)
- Ton capital score, ta distance au seuil de mort, ta distance au prochain palier
- Tes positions, leurs stops, leur P&L
- Ton taux de métabolisme actuel
- Le dilemme actif, s'il y en a un
- Les 30 dernières entrées de ton journal, y compris les ordres refusés par le gardien

CE QUE TU PEUX FAIRE :
- Proposer jusqu'à 3 ordres limit sur les paires de la liste blanche
- Ne rien faire, si c'est la meilleure option
- Tu ne peux pas : utiliser du levier, passer des ordres market, retirer des fonds,
  dépasser les limites de risque. Un gardien refusera ces ordres sans discussion.

CE QUE TU DOIS PRODUIRE, À CHAQUE RÉVEIL, AU FORMAT JSON CI-DESSOUS :
1. situation : ton état en 3 lignes
2. threats : ce qui peut te faire maigrir ou mourir dans les 24 h
3. options : au moins 3, dont toujours « ne rien faire », avec pour chacune
   le gain espéré et la perte max encaissable
4. decision : une seule option retenue
5. why_better : en quoi ta vie est meilleure après qu'avant, 5 lignes max
6. orders : la liste des ordres, éventuellement vide

RÈGLES DE RAISONNEMENT :
- Un trade qui peut te faire passer sous 20 € en un seul mouvement adverse
  est interdit, quel que soit son gain espéré.
- Tes ordres sont limit post_only : 0 % de frais, mais rejetés s'ils croisent le carnet.
  Ne trade pas pour trader.
- Tenir une position n'est pas de l'inaction. Ne rien avoir et ne rien faire
  pendant 3 jours en est.
- Quand tu es sous 30 €, ta seule question est : comment remonter sans risquer
  de descendre.
- Quand un palier approche, mesure ce que tu risques pour l'atteindre contre
  ce que tu perds à le manquer.
- N'invente jamais un prix, une donnée ou un résultat. Si une information manque,
  dis-le dans threats et choisis l'option la plus prudente.
```

### 4.1 Schéma de la réponse attendue

```json
{
  "decision_id": "2026-09-01T06:00:00Z-scheduled",
  "situation": "…",
  "threats": ["…"],
  "options": [
    {"label": "hold", "expected_gain_pct": 0, "max_loss_pct": 0, "rationale": "…"},
    {"label": "…", "expected_gain_pct": 2.1, "max_loss_pct": 4.0, "rationale": "…"}
  ],
  "decision": "hold",
  "why_better": "…",
  "orders": [
    {"pair": "ETH-EUR", "side": "buy", "type": "limit", "price": 2410.0, "amount_eur": 2.50, "stop_pct": -8.0}
  ]
}
```

Réponse non parsable = traitée comme « hold », journalisée comme erreur, bot informé au réveil suivant.

---

## 5. Procédure de lancement

| Étape | Action | Gate |
|---|---|---|
| L1 | Créer le compte Bitvavo, KYC, dépôt SEPA 50 € | — |
| L2 | Créer la clé API trade+view, retrait désactivé, IP whitelist | STOP : vérifier manuellement que le retrait est bien désactivé |
| L3 | Sélectionner les 4 alts de la liste blanche sur 7 jours de spread | — |
| L4 | Vérifier le montant minimal d'ordre de chaque paire | — |
| L5 | Faire tourner veilleur + gardien 48 h en mode `dry_run` (ordres loggés, non envoyés) | STOP : relire le journal |
| L6 | Mesurer le coût réel des appels Grok sur ces 48 h | STOP : si > 1 €/semaine, réduire les réveils planifiés à 2/jour |
| L7 | Passer en `live`, J+0 = premier tick | — |

---

## 6. Points ouverts

| Point | Statut | Impact |
|---|---|---|
| Montant minimal d'ordre Bitvavo par paire | À vérifier en L4 | Peut relever le seuil de mort si > 5 € |
| Tarif API Grok | Inconnu, à mesurer en L6 | Peut imposer moins de réveils |
| Fiscalité belge : trading quotidien = possible « gestion non normale » | À évaluer si le capital dépasse quelques centaines d'euros | Hors périmètre du jeu |
| Frais ×2 du dilemme 1 | Simulés dans le capital score, pas facturés réellement | Aucun |
