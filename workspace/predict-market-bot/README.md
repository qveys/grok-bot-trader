# predict-market-bot

Paper-first crypto + prediction-market workspace.

**EN:** Primary venue is **Revolut X crypto spot (paper)**: scan public BTC-EUR / ETH-EUR / SOL-EUR prices with `scripts/scan_crypto.py`, research directional spot edge, then paper-fill via guardian only (`trading=false`). Polymarket scan remains discovery-only and is geo-blocked for Belgium trading.  
**FR:** La venue principale est **Revolut X crypto spot (paper)** : scanner les prix publics BTC-EUR / ETH-EUR / SOL-EUR avec `scripts/scan_crypto.py`, rechercher un edge directionnel spot, puis paper-fill via guardian uniquement (`trading=false`). Le scan Polymarket reste discovery-only et est géo-bloqué pour le trading en Belgique.

**Do not confuse with** `/workspace/bot` (Revolut trading game) — this tree is only `/workspace/predict-market-bot/`.

## Quick start / Démarrage rapide

```bash
cd /workspace/predict-market-bot

# 1) Kill switch status (exit 0 = allowed, 2 = STOP present)
python3 scripts/kill_check.py

# 2) Primary: scan crypto spot (public tickers) → state/last_scan.json
python3 scripts/scan_crypto.py
#    Optional discovery-only (geo-blocked trading): python3 scripts/scan_markets.py

# 3) Kelly size
python3 scripts/kelly_size.py --p 0.62 --b 0.6667 --bankroll 500 --fraction 0.25

# 4) Paper trade (runs validate_risk first)
python3 scripts/paper_trade.py \
  --side yes --market-id demo-1 --price 0.45 --size-eur 10 \
  --p-model 0.62 --p-market 0.45

# 5) Performance snapshot
python3 scripts/performance.py
```

### French

1. Vérifier le kill switch : `python3 scripts/kill_check.py`
2. Scanner crypto (primaire) : `python3 scripts/scan_crypto.py` — Polymarket discovery-only : `scan_markets.py`
3. Trader en papier : `python3 scripts/paper_trade.py ...`
4. Mesurer : `python3 scripts/performance.py`

## Kill switch

```bash
touch /workspace/predict-market-bot/STOP   # halt all validated trades
rm /workspace/predict-market-bot/STOP      # allow trading again (when intentional)
```

`validate_risk.py` rejects if `STOP` exists. See `STOP.example`.

## Flip to live / Passer en live

Only when ready (EU/Belgium regulatory caution — see `references/platforms.md`):

1. Put API secrets in env (never in chat) — template: `.env.example`
2. Change **`MODE`** file contents from `paper` to `live`
3. Ensure **`STOP` is absent**
4. Align `config.json` platform URLs (Kalshi demo → prod only if intentional)
5. Live order adapters are **out of scope** of the core stdlib scripts; keep paper until an explicit live executor is added and reviewed

## Layout

- `config.json` — risk, scan, platform defaults  
- `scripts/` — kelly, validate, scan, paper trade, performance, kill check  
- `state/` — ledger, positions, logs, performance  
- `references/` — formulas, platforms, pipeline  
- `knowledge/failure_log.md` — post-mortems  

## Safety

- Default `MODE=paper`; conservative Kelly / exposure caps in `config.json`
- Stdlib only for core risk/paper path (no pip required)
- Never paste secrets into chat — use Grok Bot secret-request / `process.env`
- Stop watcher (`guardian/scripts/watch_stops.py`): all opens; paper auto-close, live = urgent wake only (no silent dump)
