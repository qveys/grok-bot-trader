# Mise en place et accès au portefeuille

**Projet** : Jeu de survie — Agent Grok de trading crypto
**Version** : 1.2 — 2026-08-31
**Document lié** : `regles-jeu-grok-trading.md`

---

## 1. Principe d'accès

Une seule règle gouverne tout ce document : **Grok ne touche jamais au portefeuille**.

| Acteur | Accès à l'exchange (Revolut X) | Détient la clé API | Peut passer un ordre |
|---|---|---|---|
| Opérateur humain (Quentin) | App Revolut / Revolut X web | Non (la crée, ne la stocke pas) | Oui, mais ne doit pas (voir 8.2) |
| Gardien (`guardian`, code) | API REST | **Oui, seul détenteur** | Oui, après validation |
| Veilleur (`watcher`, code) | API REST, lecture seule via le gardien | Non (utilise le client du gardien) | Non |
| Bot (`agent`, Grok) | Aucun | **Non** | Non — produit un JSON de décision, rien d'autre |

Le bot reçoit un contexte texte et renvoie un JSON. Il n'a ni outil, ni accès réseau vers l'exchange, ni connaissance de la clé. Si Grok est compromis, manipulé ou halluciné, le pire qu'il puisse faire est proposer un ordre que le gardien refusera.

---

## 2. Compte exchange — Revolut X

### 2.1 Activation

| Étape | Action | Note |
|---|---|---|
| C1 | Depuis le compte Revolut existant, activer Revolut X (exchange.revolut.com ou app Revolut X) | Pas de nouveau KYC : mêmes identifiants Revolut. Disponible en Belgique (EEA) |
| C2 | Vérifier la présence des paires EUR (BTC/EUR, ETH/EUR, SOL/EUR) | Fait — vérification validée |
| C3 | Transférer exactement 50 € du compte Revolut principal vers Revolut X, dans l'app | Geste humain unique ; ce transfert n'existe pas dans l'API |

### 2.2 Isolation du capital

Le solde Revolut X est distinct du compte Revolut principal, et l'API ne voit que
l'exchange (`GET /1.0/balances`). Le compte courant, les vaults et le reste des avoirs
Revolut sont structurellement hors de portée de la clé. Ne garder sur Revolut X que
les 50 € du jeu : tout euro supplémentaire fausserait le capital score.

---

## 3. Clé API

### 3.1 Création (procédure officielle Revolut X)

| Étape | Action |
|---|---|
| K1 | Sur le serveur du gardien : `openssl genpkey -algorithm ed25519 -out private.pem` puis `openssl pkey -in private.pem -pubout -out public.pem` |
| K2 | `private.pem` → `/workspace/guardian/secrets/private.pem`, mode 600. Il ne quitte jamais ce serveur |
| K3 | exchange.revolut.com/account/api-keys → créer une clé, coller le contenu complet de `public.pem` (lignes BEGIN/END incluses) |
| K4 | Permission : trading. **Désactiver l'option d'usage via MCP/CLI** : seul le gardien utilise cette clé |
| K5 | Si une restriction IP est proposée, y mettre l'IP fixe du serveur |
| K6 | Copier la clé API (64 caractères) → `REVX_API_KEY` |

### 3.2 Pourquoi le retrait n'est pas un risque API

L'API Revolut X ne contient **aucun endpoint de retrait, de dépôt ou de transfert**
(catégories exhaustives : market data, account data en lecture, trading). Une clé
« trading » ne peut donc pas sortir les fonds : ce n'est pas une permission à
désactiver, c'est structurel. Réserve : c'est l'état actuel de l'API ; la liste
blanche d'endpoints du gardien (5.2) et la rotation à 90 jours couvrent une
évolution future.

### 3.3 Avantage de la signature Ed25519

Revolut ne reçoit que la clé publique. Contrairement à un secret partagé HMAC,
la clé privée ne transite jamais : une fuite côté Revolut ne compromet pas la
signature des requêtes.

### 3.4 STOP gate obligatoire

Avant le premier `live` : ouvrir exchange.revolut.com/account/api-keys et vérifier
visuellement que la clé du gardien est en permission trading, sans usage MCP/CLI,
et qu'aucune autre clé inconnue n'existe. Vérification manuelle et bloquante.

---

## 4. Stockage des secrets

| Règle | Détail |
|---|---|
| Emplacement | Variables `REVX_API_KEY`, `GUARDIAN_API_TOKEN` dans `.env` ; fichier `REVX_PRIVATE_KEY_PATH` (`secrets/private.pem`) |
| Fichier | `/workspace/guardian/.env`, mode `600` |
| Dépôt Git | Jamais. `.env*` et `/etc/grok-bot/` dans `.gitignore` ; scan pré-commit |
| Journal | Le gardien ne logge jamais les headers d'authentification ni le secret |
| Rotation | Tous les 90 jours : nouvelle paire Ed25519 → nouvelle clé sur exchange.revolut.com → mise à jour env → redémarrage → suppression de l'ancienne |
| Copie de secours | Une seule, dans le gestionnaire de mots de passe de l'opérateur |

---

## 5. Authentification technique (Revolut X REST)

Base URL : `https://revx.revolut.com/api`

Chaque requête authentifiée porte trois headers :

| Header | Contenu |
|---|---|
| `X-Revx-API-Key` | La clé API (64 caractères) |
| `X-Revx-Timestamp` | Unix timestamp en millisecondes |
| `X-Revx-Signature` | Signature Ed25519, encodée base64, du message ci-dessous |

Message signé, concaténé **sans séparateur** :
`timestamp + MÉTHODE + path (depuis /api) + query (sans '?') + body JSON minifié`.
Le body doit être sérialisé à l'identique pour la signature et l'envoi. Horloge NTP
obligatoire.

### 5.1 Endpoints utilisés par le gardien

| Endpoint | Usage |
|---|---|
| `GET /1.0/configuration/pairs` | Minimum d'ordre, pas de prix/quantité par paire |
| `GET /1.0/tickers` | Bid/ask/mid pour le capital score et le placement des limit |
| `GET /1.0/balances` | Soldes de l'exchange |
| `GET /1.0/orders/active` | Réconciliation au démarrage |
| `GET /1.0/orders/{id}` | Statut, quantité remplie, prix moyen, frais d'un ordre |
| `POST /1.0/orders` | Ordre limit (`post_only` pour le bot, `allow_taker` pour les protections) |
| `DELETE /1.0/orders/{id}` | Annulation (TTL 6 h, repricing des stops) |
| `DELETE /1.0/orders` | Annulation globale — procédure de mort/halt |

Limites de débit à respecter : 10 placements/s et 1 000/jour, 100 lectures/s.
Le budget du jeu (≤ 3 ordres par réveil, ≤ 12 réveils/jour) en est très loin.

### 5.2 Ce que le gardien n'appelle jamais

Le client HTTP maintient une liste blanche des endpoints du tableau 5.1 ; tout
appel hors liste lève une exception avant l'envoi. L'API n'a pas d'endpoint de
retrait aujourd'hui ; si Revolut en ajoutait un, il resterait inatteignable par
notre code.

---

## 6. Accès au Grok Bot

Grok Bot (plateforme xAI d'agents « always-on », bêta depuis août 2026) ne s'appelle pas
par API : le bot vit sur sa propre machine cloud et agit seul. L'architecture est inversée.

| Élément | Valeur |
|---|---|
| Direction | Le bot interroge le gardien : `GET /wake` toutes les 5 min, `POST /decision` |
| Authentification | Token Bearer partagé (`GUARDIAN_API_TOKEN`), généré par `openssl rand -hex 32` |
| Ce que le token permet | Lire le contexte de réveil, proposer une décision — rien d'autre |
| Ce que le bot reçoit | État, positions, journal — **jamais la clé privée de l'exchange** |
| Ce que le bot détient | `GUARDIAN_URL` + le token, dans la configuration de son bot sur la plateforme |
| Transport | HTTPS obligatoire : gardien sur 127.0.0.1, reverse proxy TLS devant (Caddy, nginx) |
| Réveil sans réponse | 30 min -> hold ; stop-loss et mort gérés par le gardien, indépendants du bot |
| Instructions du bot | `deploy/grok-bot-instructions.md`, à coller dans sa configuration |
| Coût | Abonnement plateforme 120–300 $/mois selon la formule (bêta) — 15 à 70 fois le capital du jeu sur 12 mois |

Compromis à connaître : le bot Grok Bot dispose de son propre navigateur et terminal sur
sa machine cloud. Il peut donc consulter des sources de marché en lecture, mais rien dans
ce montage ne lui donne un canal d'action autre que `POST /decision`. Ne jamais lui
communiquer la clé de l'exchange, même « pour aller plus vite ».

---

## 7. Hébergement du gardien — mode mono-machine (choisi)

Le gardien tourne sur l'ordinateur cloud du Grok Bot, dans `/workspace/guardian`,
lancé par `deploy/run.sh` (superviseur bash : relance sur crash, arrêt définitif
sur halt/mort/victoire via le fichier `HALTED`). Pas de systemd, pas de reverse
proxy : l'API du gardien reste sur 127.0.0.1:8750 et le bot la joint en local.

| Élément | Valeur |
|---|---|
| Arborescence | `/workspace/guardian/` : code, `.env` (600), `private.pem` (600), `data/`, `journal.log`, `guardian.out` |
| Démarrage | `sudo -u guardian bash /workspace/guardian/deploy/run.sh` ; le bot le relance via l'unique règle sudoers du watchdog |
| Arrêt de partie | Fichier `HALTED` : `run.sh` refuse tout redémarrage tant qu'il existe |
| Réseau | Aucun port exposé hors de la machine ; sortant vers revx.revolut.com uniquement (non filtrable par nous sur cette machine) |
| Sauvegarde | À prévoir : export périodique de `data/` et `journal.log` hors de la machine (la persistance du /workspace entre cycles de vie du Grok Bot est à vérifier en dry_run) |

### 7.1 Modèle de risque de ce mode — avec séparation des privilèges

Accès SSH direct à la machine confirmé (utilisateur `box`, Debian 13), donc canal
d'administration indépendant du bot. Constat du sondage : `box` a sudo sans mot de
passe — sans durcissement, la séparation d'utilisateurs serait cosmétique.
Durcissement appliqué par `deploy/harden.sh` : utilisateur `admin` (ta clé SSH, sudo),
utilisateur `guardian` propriétaire exclusif de `/workspace/guardian` (700, clé et env
en 600), retrait manuel du sudo de `box` après STOP, et une unique règle sudoers
laissant à `box` le droit de relancer `run.sh` en tant que `guardian` (watchdog).

État après durcissement :

| Propriété | Serveur séparé | Mono-machine durcie |
|---|---|---|
| Le bot ne peut pas lire la clé privée | Garanti | Garanti tant que `box` n'a pas sudo et que l'agent tourne bien comme `box` (à confirmer : `whoami` exécuté par le bot depuis son interface) |
| V1..V10 incontournables | Garanti | Garanti sous les mêmes conditions ; le bot peut toujours parler à revx.revolut.com mais sans clé, il ne peut rien signer |
| Stops indépendants du bot | Garanti | Toujours sur la même machine bêta ; un reset d'image xAI peut restaurer sudoers et utilisateurs — vérifier après chaque cycle de vie |
| Pire cas absolu | Perte des 50 € | **Inchangé** : l'API Revolut X ne peut pas retirer |

Les interdits correspondants figurent dans les instructions du bot ; toute violation
constatée au journal ou à l'historique de l'exchange vaut partie perdue.

### 7.2 Séquence de contrôle au démarrage (inchangée)

```
1. charger les secrets depuis l'env ; échec si l'un manque
2. horodatage serveur (metadata des tickers) → décalage d'horloge < 2 s
3. GET /1.0/balances → vérifier que le compte répond
4. GET /1.0/configuration/pairs → minima et pas des paires de la liste blanche
5. réconcilier l'état local avec les ordres ouverts et le solde réel
   → toute divergence est journalisée ; divergence > 1 € = arrêt et alerte
6. lire le mode : dry_run | live
7. démarrer la boucle du veilleur
```

Variante recommandée si l'intégrité du jeu prime : serveur séparé (IP fixe,
systemd, reverse proxy TLS) — unité systemd conservée dans `deploy/`.

## 8. Accès humain pendant le jeu

### 8.1 Ce que l'opérateur peut faire

- Consulter Revolut X (app ou web) en lecture
- Lire le journal et l'état du gardien
- Arrêter le service (kill switch manuel)
- Réviser la liste blanche une fois par mois
- Révoquer la clé API à tout moment

### 8.2 Ce que l'opérateur ne doit pas faire

| Action | Conséquence |
|---|---|
| Passer un ordre manuel sur le compte | L'état du gardien diverge du solde réel → arrêt au prochain contrôle, ou pire, position sans stop |
| Déposer des fonds | Fausse le capital score, ruine le jeu |
| Modifier l'état persistant à la main | Même effet |
| Donner un ordre au bot en dehors du gardien | Contourne les 10 contrôles de validation |

Toute intervention humaine passe par : arrêt du service → modification → réconciliation au redémarrage.

---

## 9. Modes de fonctionnement

| Mode | Ordres | Appels Grok | Usage |
|---|---|---|---|
| `dry_run` | Construits, validés, journalisés, **non envoyés** | Réels | 48 h minimum avant `live` ; mesure du coût Grok |
| `live` | Envoyés à l'exchange | Réels | Le jeu |
| `halt` | Aucun ; annulation des ordres ouverts | Aucun | Kill switch, incident, mort |

Le passage `dry_run` → `live` est un changement de configuration manuel, avec relecture du journal des 48 h.

---

## 10. Incidents

| Situation | Procédure |
|---|---|
| Suspicion de fuite de clé | exchange.revolut.com/account/api-keys → supprimer la clé (immédiat) → service passe en `halt` par échec d'auth → créer une nouvelle clé → rotation |
| Machine compromise | Supprimer la clé d'abord, s'occuper de la machine ensuite |
| Gardien planté | Le superviseur de `guardianctl.sh` relance après 30 s ; la séquence de contrôle réconcilie ; les stop-loss sont recalculés depuis l'état persistant |
| Exchange indisponible | Le veilleur réessaie toutes les 60 s ; aucun réveil du bot tant que les prix ne sont pas frais ; alerte après 15 min |
| Grok Bot muet | Réveil expiré après 30 min = `hold` ; le gardien surveille les stops ; alerte après 3 réveils expirés d'affilée |
| Décision invalide | `hold`, journalisée comme erreur, motif renvoyé au bot au réveil suivant |
| Token API du gardien compromis | Changer `GUARDIAN_API_TOKEN`, redémarrer, mettre à jour la config du bot. Exposition max : lecture du contexte + propositions d'ordres, toujours validées V1..V10 |
| Mort constatée | Passage en `halt`, liquidation en limit au bid, clé API supprimée par l'opérateur, journal archivé |

---

## 11. Checklist avant J+0

| # | Point | Fait |
|---|---|---|
| 1 | Revolut X activé depuis le compte Revolut (fait) | ☐ |
| 2 | Solde Revolut X vide de tout autre avoir | ☐ |
| 3 | 50,00 € transférés depuis le compte principal, rien de plus | ☐ |
| 4 | `/workspace/guardian` en place sur la machine du Grok Bot ; `run.sh` démarre et `status` répond | ☐ |
| 5 | Paire Ed25519 générée sur le serveur ; clé API trading créée, MCP/CLI désactivé | ☐ |
| 6 | **STOP** : vérification visuelle des clés sur exchange.revolut.com + `deploy/verify_revolutx.py` OK | ☐ |
| 7 | Secrets dans `/etc/grok-bot/env`, mode 600, hors Git | ☐ |
| 8 | API gardien joignable en local uniquement (127.0.0.1:8750) ; aucun port exposé | ☐ |
| 8b | Token gardien généré ; instructions du bot en place, interdits mono-machine inclus | ☐ |
| 9 | Liste blanche : BTC-EUR, ETH-EUR, SOL-EUR + 4 alts, spread vérifié sur les tickers | ☐ |
| 10 | 48 h de `dry_run` terminées, journal relu | ☐ |
| 11 | **STOP** : coût Grok mesuré et accepté | ☐ |
| 12 | Export périodique de `data/` + `journal.log` hors de la machine configuré | ☐ |
| 13 | Persistance de `/workspace` vérifiée sur 48 h de dry_run (redémarrages compris) | ☐ |
| 14 | Passage en `live` | ☐ |
