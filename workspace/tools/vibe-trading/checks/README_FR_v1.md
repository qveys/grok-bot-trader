# Vibe-Trading : tester une règle sur le passé

1. Cet outil rejoue une règle simple (exemple : « acheter quand la moyenne courte passe au-dessus de la moyenne longue ») sur les prix d'avant.
2. Il utilise seulement des prix publics du passé (OKX ou Binance). Il n'est relié à aucun compte, aucun portefeuille, aucune clé.
3. Il ne passe jamais d'ordre. Aucun argent réel n'est utilisé. Il n'a pas besoin de clé d'IA.
4. Le calcul compte des frais (0,1 % à chaque achat et à chaque vente) et un petit écart de prix (0,05 %).
5. Achat simple de la crypto (pas d'emprunt, pas d'effet de levier, pas de vente à découvert).
6. Il affiche : le gain ou la perte en %, le nombre d'opérations, la part d'opérations gagnantes, la pire baisse, les frais payés.
7. Il compare aussi avec « acheter au début et garder jusqu'à la fin ».
8. Attention : un bon résultat sur le passé ne garantit rien pour le futur. Ce n'est pas un conseil d'achat.
9. PM-Predict le lance comme ceci, puis lit le résumé (format JSON) :
   `/workspace/tools/vibe-trading/backtest.sh --pair BTC-EUR --tf 1D --days 365 --strategy sma_cross --fast 20 --slow 50 --json`
10. Paires possibles : BTC-EUR, ETH-EUR, SOL-EUR (ou BTC-USDT…). Durée des bougies : 1D (jour), 4H, 1H.
11. Règles possibles : sma_cross, ema_cross, rsi_revert, buy_hold. Aide : `backtest.sh --help`.
12. Les détails de chaque test sont gardés dans `/workspace/tools/vibe-trading/home/runs/`.
