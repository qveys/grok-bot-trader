# Guardian — Revolut X risk gate / Couche risque

**EN** — Independent, deterministic risk gate for Revolut X spot under `predict-market-bot`.
Does **not** restore the deleted `/workspace/guardian` secrets or HTTP API. Old Ca$her
files under `/workspace/bot/` are left untouched; this path is separate.

- `config.json` — hard limits (whitelist, size, exposure, drawdown, daily loss).
- `state.json` — bankroll/cash/positions/PnL + `paper_inventory` (no secrets).
- `scripts/validate_order.py` — validate an order JSON (stdin or `--order` file).
- `scripts/paper_fill.py` — if validate OK, simulate fill into `state.json` + `../state/trades_log.jsonl`.
- `scripts/status.py` — print a status summary (no secrets).
- `scripts/watch_stops.py` — while **any** open position is tracked (guardian `state.json`,
  `state/positions.json` crypto rows, `live_orders.jsonl`, revx open orders best-effort),
  poll mid ~15s. On stop/target breach: **paper/sim** → close via `paper_fill` + wake; **live** →
  urgent wake only (`mode=live`, « Stop touché en LIVE — vente à faire ») — no silent live
  dump (`ALLOW_LIVE_AUTO_SELL=False`). Exit **10** wakes PM-Risk.
- `scripts/check_alerts.py` — stop / daily-loss / drawdown → `state/alerts_last.json`.
- `scripts/check_buy_wake.py` — Predict BUY awaiting Risk → `state/buy_wake.json`.
- `scripts/start_stop_watch.sh` — nohup wrapper for `watch_stops.py --interval 15`.
- Kill switch: if `../STOP` or `guardian/HALTED` exists → reject all.
- Mode: `../MODE` must be `paper` or `live`.

## Deux types d’idée (validé Quentin, 8 oct)

| Type | `idea_type` | Ouverture | Fermeture |
|------|-------------|-----------|-----------|
| **Idée à la hausse** | `"hausse"` (défaut si absent) | Achat (`side=buy`) | Vente plus haut |
| **Idée à la baisse** | `"baisse"` (ou `kind=baisse`) | Vente de pièces déjà détenues (`side=sell`) | Rachat plus bas (`side=buy`) |

Chaque ligne de journal a `side` `buy` / `sell` (affiché Achat / Vente). Ne plus dire « vendre d’abord ».

**Idée à la baisse** — inventaire simulé dans `state.json` → `paper_inventory` (ETH/SOL Revolut + `metamask_arbitrum.ETH`). Refus si qty > inventaire. `decision_id` obligatoire. Prix d’arrêt = rachat de sécurité **au-dessus** (`stop_price` / `safety_price`) ; cible = rachat **en dessous** (`target_price`). Venue MetaMask Uniswap : frais 0,05 % / échange.

## Simulation ≠ live

**Simulation (`MODE=paper`)** — seulement :
- taille ≤ `max_position_pct` × bankroll (25 € si bankroll 500 €) ;
- prix d’arrêt obligatoire ;
- exposition totale (longs + baisses) ≤ `max_exposure_pct` (5 %) ;
- paires whitelist ; ordre limité post-only.
- **Pas** d’exigence gain ≥ 3× coûts.

**Live** — inchangé (`live_place.py`, `LIVE_ONCE`, `live_day.json`) : espérance ≥ 3× coûts, etc. Ne pas modifier le chemin live depuis ces scripts paper.

## Champs du journal (`state/trades_log.jsonl`)

- Hausse (achat) : `id`, `ts`, `mode`, `pair`, `side`, `idea_type=hausse`, `price`, `amount_eur`, `qty`, `stop_pct` ; à la vente : `realized_pnl_eur` / `pct`, `close_reason`, `linked_position_id`.
- Baisse (vente d’ouverture) : + `idea_type`/`kind=baisse`, `decision_id`, `fee_eur`, `venue`, `stop_price`, `target_price`, `safety_price`.
- Baisse (rachat) : `side=buy`, `cycle_id` + `linked_position_id`, `rebuy_reason` (`target`|`safety`|`time`), `realized_pnl_eur`/`pct`, `coins_gained`, `close_reason`.

## Exemple — simuler une idée à la baisse puis son rachat

```bash
# 1) Vente (ouvre le cycle) — pièces déjà en paper_inventory
echo '{
  "pair":"SOL-EUR","side":"sell","type":"limit","price":110,
  "amount_eur":22,"qty":0.2,"idea_type":"baisse","kind":"baisse",
  "decision_id":"D-018","stop_price":120,"target_price":100,"post_only":true
}' | python3 guardian/scripts/paper_fill.py

# 2) Rachat (ferme) — ou laisser watch_stops le faire au stop/cible
echo '{
  "pair":"SOL-EUR","side":"buy","type":"limit","price":100,
  "amount_eur":20,"qty":0.2,"idea_type":"baisse",
  "linked_position_id":"ID_DE_LA_VENTE","cycle_id":"ID_DE_LA_VENTE",
  "rebuy_reason":"target","post_only":true
}' | python3 guardian/scripts/paper_fill.py

# Gardien (~15 s) : mid ≥ stop → rachat safety ; mid ≤ target → rachat target
./guardian/scripts/start_stop_watch.sh
```

**After opening any position (paper or live), start the stop watcher**:

```bash
python3 guardian/scripts/watch_stops.py --once
./guardian/scripts/start_stop_watch.sh
```

Exit codes: `0` idle/ok, `10` stop/target closed or live wake, `1` hard error.

**FR** — Couche risque déterministe pour le spot Revolut X. Pas de secrets chat, pas d’API live depuis ces scripts. Ordres limit post-only ; whitelist BTC-EUR / ETH-EUR / SOL-EUR ; pas de levier.
