# grok-guardian

Gardien du jeu de survie — agent Grok de trading crypto sur Bitvavo.
Implémente `regles-jeu-grok-trading.md` et `mise-en-place-acces-portefeuille.md`.
Exchange par défaut : **Revolut X** (0 % maker via `post_only`) ; Bitvavo reste disponible via `EXCHANGE=bitvavo`.

## Arborescence

| Fichier | Rôle |
|---|---|
| `guardian/config.py` | Constantes du jeu (seuils, tiers, métabolisme, paliers, dilemmes) + chargement env |
| `guardian/revolutx.py` | Client Revolut X, signature Ed25519, **liste blanche d'endpoints** (l'API n'a de toute façon aucun endpoint de retrait) |
| `guardian/bitvavo.py` | Client Bitvavo (HMAC-SHA256), même interface — solution de repli |
| `guardian/state.py` | État persistant (`state.json`) et journal append-only (`journal.log`) |
| `guardian/rules.py` | Capital score, tier en vigueur, métabolisme, paliers, dilemmes |
| `guardian/validator.py` | Contrôles V1..V10 sur chaque ordre proposé |
| `guardian/agent.py` | Construction du contexte de réveil, validation de forme des décisions |
| `guardian/api.py` | API HTTP pour le Grok Bot : `GET /wake`, `POST /decision`, token Bearer |
| `guardian/guardian.py` | Boucle du veilleur : réconciliation, stop-loss, réveils, exécution, mort |
| `guardian/__main__.py` | Point d'entrée `python -m guardian` |
| `tests/` | Client Bitvavo simulé + tests de fumée hors ligne |
| `deploy/` | Unité systemd, env d'exemple, instructions à coller dans le Grok Bot |

## Installation — mode mono-machine (ordinateur du Grok Bot)

Déploiement retenu : tout dans `/workspace/guardian`, sans systemd.

```bash
mkdir -p /workspace/guardian && cd /workspace/guardian
# déposer : guardian/ requirements.txt deploy/ (depuis l'archive)
cp deploy/grok-bot.env.example .env        # puis remplir ; mode 600
mv private.pem /workspace/guardian/private.pem && chmod 600 private.pem .env
bash deploy/harden.sh "<ta clé publique SSH>"   # séparation des privilèges (voir doc §7.1)
# STOP : vérifier ssh admin@machine + sudo, puis retirer sudo à box (commande affichée)
sudo -u guardian bash deploy/run.sh   # bootstrap venv + démarrage supervisé
bash deploy/run.sh status
tail -f guardian.out
```

`run.sh` relance le gardien après un crash (30 s de backoff) et s'arrête
définitivement sur halt, mort ou victoire en créant le fichier `HALTED` —
il refuse alors tout redémarrage tant que ce fichier existe.

**Modèle de risque de ce mode, à connaître :** le bot a le terminal de la machine
qui héberge son gardien et sa clé. Les contrôles V1..V10 et les interdits des
instructions ne sont plus une barrière technique mais une règle du jeu que le bot
peut techniquement violer. Borne dure restante : l'API Revolut X n'a aucun endpoint
de retrait, le pire cas absolu est la perte des 50 €. La persistance du processus
et l'horloge dépendent de la machine Grok Bot (produit en bêta) : vérifier en dry_run
que le gardien survit aux cycles de vie de la machine. Le déploiement séparé
(serveur dédié + reverse proxy TLS, unité systemd fournie dans `deploy/`) reste
la variante recommandée si l'intégrité du jeu prime.

## Tests hors ligne (7 tests, dont signature Ed25519 et liste blanche)

```bash
python3 tests/test_smoke.py        # ou : python -m pytest tests/
```

## Modes

| `GUARDIAN_MODE` | Comportement |
|---|---|
| `dry_run` | Appels Bitvavo en lecture, appels Grok réels, ordres validés et journalisés mais **non envoyés**. Les positions ne bougent donc pas : ce mode sert à mesurer le coût Grok et à relire les décisions, pas à tester les stops |
| `live` | Le jeu |
| `halt` | Annule les ordres ouverts et sort |

Le processus sort avec le code 42 en cas de halt, mort ou victoire ; le superviseur (et systemd via `RestartPreventExitStatus=42 43`) ne le relance pas.

## Codes de sortie

| Code | Signification |
|---|---|
| 0 | Arrêt manuel (SIGTERM/SIGINT) |
| 42 | Halt, mort constatée ou victoire — lire la dernière ligne du journal |
| 43 | L'état indique déjà une mort ; rien à faire |
| autre | Crash — le superviseur relance après 30 s |

## Intégration Grok Bot (plateforme d'agents, bêta 2026)

Grok Bot ne s'appelle pas par API : c'est un agent permanent sur sa propre machine cloud.
L'architecture est donc inversée — le bot vient chercher son travail chez le gardien :

| Endpoint | Rôle |
|---|---|
| `GET /wake` | 200 + contexte si un réveil est en attente, 204 sinon. Le bot poll toutes les 5 min |
| `POST /decision` | Le JSON de décision ; 409 si le `decision_id` ne correspond plus |

- Token Bearer partagé (`GUARDIAN_API_TOKEN`), à générer avec `openssl rand -hex 32`.
- Le gardien écoute sur 127.0.0.1 : exposer via un reverse proxy TLS (Caddy, nginx). Jamais en HTTP nu.
- Réveil sans réponse après `GUARDIAN_WAKE_TIMEOUT_MINUTES` (30 par défaut) = hold.
- Les stop-loss et la mort ne dépendent pas du bot : la latence de polling ne touche jamais la survie.
- Les instructions à coller dans la configuration du bot sont dans `deploy/grok-bot-instructions.md`.

Coût : l'accès Grok Bot passe par un abonnement (120–300 $/mois selon la formule au lancement de la bêta),
soit 15 à 70 fois le capital du jeu sur 12 mois. À assumer comme coût de plateforme, pas comme coût du jeu.

## Points à vérifier avant le live

| Point | Où |
|---|---|
| Le Grok Bot tient-il un cycle de polling fiable toutes les 5 min ? (produit en bêta) | 48 h de `dry_run`, lignes `wake_opened` vs `decision:` du journal |
| Schéma des ordres TPSL natifs Revolut X (non documenté dans la référence publique lue) | Amélioration future : remplacer les stops logiciels par des TPSL côté exchange. En attendant, stops logiciels testés |
| Statuts d'ordre exacts renvoyés par `GET /1.0/orders/{id}` (new/partially_filled/filled/cancelled/rejected) | Premier `dry_run` puis premiers ordres live |
| Taux de rejet des `post_only` du bot | Journal, lignes `order_error` — si trop de rejets, élargir la consigne de placement du bot |
| Précision d'arrondi du montant en base asset | `_base_amount` s'appuie sur `base_step` de `/1.0/configuration/pairs` ; un rejet pour précision apparaîtrait en `order_error` |
| Latence réelle réveil -> décision | Écart d'horodatage `wake_opened` -> `decision:` dans le journal |

## Décision de conception à connaître

**Le risque max par trade a un plancher égal au minimum d'ordre de l'exchange** (`max(risque % × capital, minimum de la paire)`). Décisif sur Bitvavo (minimum 5 €), quasi inopérant sur Revolut X (minimum ~0,01 €). **Ordres du bot en `post_only`** : 0 % de frais, rejet si le prix croise le carnet ; les ventes de protection passent en `allow_taker` (0,09 %) parce que la survie prime sur les frais.
