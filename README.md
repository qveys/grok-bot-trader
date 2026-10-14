# grok-bot-trader : sauvegarde complète

Copie de tout ce qui a été construit sur la boîte Grok Bot : bots de trading crypto (Revolut X), gardien, sonnette, veilleur Cloudflare, tableau de bord, instructions des bots, compétences et routines.

- **Installer sur ton serveur :** [MIGRATION_DOCS/GUIDE_INSTALLATION_FR.md](MIGRATION_DOCS/GUIDE_INSTALLATION_FR.md)
- **Ce qui est inclus ou exclu :** [MIGRATION_DOCS/INVENTAIRE.md](MIGRATION_DOCS/INVENTAIRE.md)

Arborescence :
- `workspace/` : le code et les données (chemin d'origine `/workspace`)
- `home/box/` : instructions des bots, compétences, plugins, scripts revx
- `MIGRATION_DOCS/` : guide, inventaire, routines, captures, archives chiffrées

Aucun secret en clair ici. Les secrets sont dans `MIGRATION_DOCS/encrypted/*.gpg`, et le mot de passe est conservé à part (pas dans ce dépôt).
Déchiffrer : `gpg -d MIGRATION_DOCS/encrypted/secrets.tar.gz.gpg | tar xz -C /`
