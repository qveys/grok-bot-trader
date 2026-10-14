# Revolut X — paper first / live only with explicit OK

## EN
- **Paper first.** Keep `MODE=paper` and `platforms.revolut_x.trading=false` until the user
  explicitly authorizes live trading (spoken/written OK naming live).
- **Guardian:** `/workspace/predict-market-bot/guardian/` — validate every order; honor
  `STOP` and `guardian/HALTED`; whitelist ETH-EUR / SOL-EUR; limit post-only; no leverage;
  no market orders.
- **API secrets:** use `process.env` / secret store (`REVOLUT_X_API_KEY`,
  `REVOLUT_X_API_SECRET`, or Ed25519 PEM paths). **Never paste keys, secrets, or PEM
  contents into chat.** See `guardian/.env.example`.
- **Do not** call Revolut live order endpoints from paper scripts.
- Legacy Ca$her under `/workspace/bot/` is separate; do not break those files. This
  guardian does **not** restore deleted `/workspace/guardian` secrets.

## FR
- **Papier d’abord.** `MODE=paper` et `trading=false` jusqu’à autorisation live explicite.
- **Gardien:** chemin ci-dessus; kill switch `STOP` / `HALTED`; paires whitelist;
  limit post-only; pas de levier ni market.
- **Secrets API:** uniquement via `process.env` / coffre — **jamais dans le chat**.
- Pas d’appel API live Revolut depuis les scripts paper. Ancien `/workspace/bot/` intact;
  pas de restauration des secrets de l’ancien `/workspace/guardian`.

## Quick commands
```bash
python3 guardian/scripts/status.py
echo '{"pair":"ETH-EUR","side":"buy","type":"limit","price":2500,"amount_eur":10,"stop_pct":-8}' \
  | python3 guardian/scripts/validate_order.py
python3 guardian/scripts/paper_fill.py --order /tmp/order.json
```
