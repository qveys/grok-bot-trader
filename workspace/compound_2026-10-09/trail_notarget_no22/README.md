# Retest 9 oct 20h45 — sans prix visé + stop suiveur + sans sortie 22h

Commande visée :
`backtest.sh run --tp 0 --trail 1.5 --exit-hour -1 --max-bars 168` sur team_rebound / team_breakout (ETH, SOL, BTC), touch + immédiat + robust.

## Résultat
- **Binance** (`api.binance.com`) : HTTP **451** geo-block → fetch ccxt en échec.
- **OKX** : historique trop court (~2 mois) → pas de jugement sur 1 an / 2 moitiés.
- **Aucun chiffre inventé** pour le vrai « sans sortie 22h ».

## Repli
Réutiliser `/workspace/compound_2026-10-08/trailing_stop/` variantes `*_noTP` (**encore avec sortie 22h**). Verdict : ne débloque pas le réel (voir decision_log 20h45).
