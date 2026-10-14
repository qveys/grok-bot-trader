# Ca$her — export (14 oct. 2026)

## Profil
- Nom : Ca$her — titre : crypto
- Instructions de profil : « Au démarrage et à chaque cycle, exécute source /workspace/bot/env, lis et applique /workspace/bot/INSTRUCTIONS.md. Les règles du jeu sont dans /workspace/bot/regles-jeu.md. »
- Rôle : trader du jeu de survie crypto sur Revolut X (paires BTC/ETH/SOL-EUR, ordres limit post_only). Décisions uniquement via le gardien (GET /wake, POST /decision sur 127.0.0.1:8750). Ne jamais lire ni afficher les secrets du gardien, ne jamais appeler Revolut directement.

## Routines
### Cycle trader
- Dossier : 181e48b6-12ff-5656-bf92-5f7b21738cd6
- Horaire : toutes les 30 minutes (CRON_TZ=Europe/Brussels */30 * * * *)
- État : EN PAUSE (depuis le 19 sept. 2026, confirmé le 7 oct. 2026 sur ordre de Quentin)
- Texte : je n'ai pas le texte enregistré mot pour mot sous la main (il est stocké côté serveur, pas sur le disque). Ce qu'il dit en substance : source /workspace/bot/env, appliquer INSTRUCTIONS.md et regles-jeu.md, lancer wake.sh ; si NO_WAKE ne rien faire ; sinon écrire decision.json puis decide.sh. Stratégie : garder par défaut, vendre seulement sur règle forcée (danger, stop proche) ou avantage net (sac ≥ +5 % vs entrée, ou retard relatif ≥ ~4 pts), petites ventes SOL au-dessus du prix moyen. Prévenir Quentin si le gardien est down ou si le score passe sous 68 €.

## Mémoire importante
- Jeu : score = valeur du portefeuille − coût de vie cumulé ; mort sous 20 € ; prochain palier 100 €.
- Départ ~79,57 € (1er sept.). Passage en live le 16 sept. (essai 48 h) puis resté en live.
- Ventes réelles SOL-EUR (~0,04 SOL chacune) les 18 et 19 sept., cash monté à ~11,8 €.
- Dernier état connu avant la panne : score ~79,5 €, cash ~11,8 € (19 sept. ~02:00).
- 19 sept. ~02:36 : mise à jour de l'ordinateur cloud a effacé l'ancien gardien (/workspace/guardian, user guardian, /etc/grok-bot). Clé API Revolut X et private.pem manquants, jamais restaurés.
- 6 oct. : nouveau gardien installé = /workspace/predict-market-bot/guardian (mode paper, pipeline PM-*), différent de l'ancien gardien live de Ca$her.
- Achats BTC automatiques de l'arrondi Revolut : ce ne sont pas des trades du bot.

## Compétences
- Aucune compétence propre à Ca$her.
