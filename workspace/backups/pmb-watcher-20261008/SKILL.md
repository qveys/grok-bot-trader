---
name: Prediction market risk
description: >-
  Use when sizing, validating risk, and paper-executing Revolut X crypto spot
  (guardian validate_order + paper_fill only) or legacy paper_trade paths. Kill switch.
---
# Prediction market — Risk and execution

Use when sizing a trade, validating risk, paper-trading, or (only if explicitly live) placing an order.

## Goal
Deterministic risk gate, then execute only if all checks pass.

## Shared workspace
`/workspace/predict-market-bot/` (+ `guardian/` for Revolut X paper)

## Kill switch and mode
1. If `STOP` exists → reject all new orders.
2. Read `MODE` and `config.json`. Default is **paper**. Keep `platforms.revolut_x.trading=false` unless user explicitly flips live.
3. **Live** only when MODE=live, STOP absent, API secrets configured, and the user explicitly authorized live trading for this session/ask.

## Deux types d’idée
- **Idée à la hausse** (`idea_type: "hausse"`, défaut si absent) : achat puis revente plus haut.
- **Idée à la baisse** (`idea_type` / `kind: "baisse"`) : vente de pièces déjà détenues puis rachat plus bas. Pas l’expression « vendre d’abord ».
- Chaque ligne = `side` `buy` ou `sell` (Achat / Vente).

## Simulation ≠ live
- **Simulation** : taille ≤ 5 % bankroll (≤ 25 € si 500 €), stop obligatoire, exposition totale ≤ 5 % (BTC+ETH+SOL, y compris baisses), paires whitelist, limit post-only. **Pas** de règle gain ≥ 3× coûts.
- **Live** : inchangé (`live_place.py` / `LIVE_ONCE` / expectancy 3×). Ne pas toucher le live depuis le chemin paper.

## Revolut X crypto paper (primary)
**MUST** call:
```bash
python3 guardian/scripts/validate_order.py ...
python3 guardian/scripts/paper_fill.py ...
```
- Never call Revolut live trading APIs from this skill while trading=false / MODE=paper.
- Prefer limit post-only; whitelist BTC-EUR, ETH-EUR, SOL-EUR.
- Inventaire simulé : `guardian/state.json` → `paper_inventory` (refus si qty > stock).
- `watch_stops.py` : long → stop en dessous ; baisse → stop (safety) au-dessus, cible en dessous → rachat auto. `ALLOW_LIVE_AUTO_SELL=False`.

### Exemple idée à la baisse
```bash
echo '{"pair":"SOL-EUR","side":"sell","type":"limit","price":110,"amount_eur":22,"qty":0.2,"idea_type":"baisse","decision_id":"D-018","stop_price":120,"target_price":100,"post_only":true}' \
  | python3 guardian/scripts/paper_fill.py
# puis rachat (ou watch_stops) avec linked_position_id / cycle_id + rebuy_reason
```

## Legacy / event-market paper path
```bash
python3 scripts/kelly_size.py --p ... --b ... --bankroll ... --fraction 0.25
python3 scripts/validate_risk.py
python3 scripts/paper_trade.py ...
```

## Position limits (guardian)
- Max 5 % bankroll / ticket ; exposition totale ≤ 5 % ; journal `trades_log.jsonl` avec les champs hausse/baisse ci-dessus.
- Slippage abort if price moved > max_slippage between signal and fill (live path).
- Max $50/day AI API cost budget.

## Hard rules
- Risk logic lives in Python scripts, not improvised chat math.
- Refusing a bad trade is success.
- Never bypass `validate_order.py` / `validate_risk.py`.
