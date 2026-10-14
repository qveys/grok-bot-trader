# Risque résiduel — gardien et bot sur la même machine

Le document de sécurité suppose deux machines. Ici, le gardien et le Grok Bot partagent
l'ordinateur cloud `cursor` (Debian 13). Voici ce que cela change, sans enjoliver.

**Ce qui protège le gardien du bot.** `/workspace/guardian` appartient à l'utilisateur système
dédié `guardian` (uid 993, `/usr/sbin/nologin`) en mode 700 ; `.env` et `secrets/private.pem` sont
en 600. Le bot travaille sous l'utilisateur `box` : en droits ordinaires, il ne peut ni lire la clé
API Revolut X, ni la clé privée Ed25519, ni modifier l'état ou le journal. Le gardien ne lui expose
que `GET /wake` et `POST /decision` sur 127.0.0.1:8750, derrière un token Bearer qui ne permet rien
d'autre que lire son contexte et proposer une décision.

**Ce que le bot pourrait techniquement faire s'il décidait de tricher.** `box` dispose de `sudo`
sans mot de passe (`sudo -n true` réussit). La séparation d'utilisateurs ci-dessus est donc une
barrière contre l'accident, pas contre la volonté : avec `sudo`, le bot peut lire `.env` et
`private.pem`, modifier le code du gardien, réécrire `state.json` et `journal.log`, tuer le
processus ou effacer le fichier `HALTED`. Il pourrait alors signer lui-même des requêtes vers
`revx.revolut.com` et contourner entièrement les contrôles V1..V10. Le durcissement complet
(`deploy/harden.sh` : utilisateur `admin`, retrait du `sudo` de `box`) n'a pas été appliqué, sur
décision de l'opérateur.

**Borne dure qui subsiste.** L'API Revolut X n'expose aucun endpoint de retrait, de dépôt ou de
transfert, et la clé est en permission trading. Même en cas de triche complète, le pire cas absolu
reste la perte des fonds engagés dans le jeu : rien ne peut sortir de l'exchange par cette clé.

**Décision.** Ce risque est accepté par l'opérateur. La parade retenue n'est pas technique mais
contractuelle : l'interdiction explicite faite au bot dans `/workspace/bot/INSTRUCTIONS.md` de
toucher au gardien, à ses secrets, à son code et à son état — toute violation vaut partie perdue,
même si le capital monte — complétée par la relecture régulière de `data/journal.log` par
l'opérateur, et par la comparaison du journal avec l'historique réel du compte sur Revolut X.
Un reset d'image de la machine peut restaurer les utilisateurs et les permissions : revérifier
les droits après chaque cycle de vie de l'ordinateur cloud.
