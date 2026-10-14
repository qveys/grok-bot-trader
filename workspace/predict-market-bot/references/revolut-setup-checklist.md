# Checklist Quentin — Revolut X (recommandation appliquée)

## Déjà fait / en cours
- [x] Pivot venue: Revolut X first, MetaMask later
- [x] Polymarket/Kalshi trading disabled (Belgium)
- [x] Go/no-go thresholds saved
- [x] New risk guardian under /workspace/predict-market-bot/guardian/
- [ ] Revolut X API key pair (Ed25519) created and stored as secrets
- [ ] Paper path validated
- [ ] Explicit live authorization

## Ce que tu feras (humain)
1. Sur ta machine: `openssl genpkey -algorithm ed25519 -out private.pem && openssl pkey -in private.pem -pubout -out public.pem`
2. Revolut X → Account → API keys: créer une clé, coller **public.pem** complet
3. Permission: trading only; pas de retrait (l’API n’en a pas); désactiver MCP/CLI si proposé
4. Copier l’API key id/string → on la demandera via carte secrète (jamais dans le chat)
5. La **private.pem** → carte secrète / fichier 600 sur le box (jamais collée en clair dans le chat)
6. Vérifier visuellement qu’aucune autre clé inconnue n’existe

## Règles
- MODE=paper jusqu’à « passe en live »
- touch STOP pour tout couper
- Bot propose; risk/guardian valide; pas d’ordres market / pas de levier
