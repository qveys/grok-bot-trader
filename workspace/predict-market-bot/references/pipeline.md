# Pipeline / Pipeline

Five stages. Default gate: **paper-first**. Live requires `MODE=live` **and** no `STOP` file.

```
Scan → Research → Predict → Risk/Execute → Compound
```

## 1. Scan

- Run `scripts/scan_markets.py`.
- Pulls public Polymarket gamma markets; filters by volume, liquidity, days-to-expiry, spread.
- Writes `state/last_scan.json`. Places **no** orders.
- Network errors → empty scan + error note, exit 0.

## 2. Research

- Human / agent reads ranked markets, news, resolution criteria.
- Log hypotheses and data sources (optional entries in `predictions_log.jsonl` later).
- Check platform rules and EU/Belgium access constraints (`references/platforms.md`).

## 3. Predict

- Produce \(p_{\text{model}}\) and confidence.
- Require edge \(p_{\text{model}} - p_{\text{market}} >\) `predict.min_edge` and confidence ≥ `predict.min_confidence`.
- Append forecast rows to `state/predictions_log.jsonl`.

## 4. Risk / Execute

- Size with `scripts/kelly_size.py` (quarter-Kelly by default).
- Gate every order with `scripts/validate_risk.py` (kill switch, MODE, edge, Kelly cap, position/exposure/drawdown/daily-loss/concurrency).
- **Paper:** `scripts/paper_trade.py` simulates fills → `trades_log.jsonl`, `positions.json`, `paper_ledger.json`.
- **Live:** only if `MODE` is `live`, `STOP` absent, secrets present, and legal OK — still call validate first. This repo’s core scripts do not place live orders.

## 5. Compound

- `scripts/update_performance.py` (PM-Compound, 9 oct) → `state/performance.json` : simulation vs live, hausse vs baisse, par sorte de trade (essais vers ~20), capital simulé après chaque trade fermé, rapprochement journal ↔ gardien. À lancer à la revue du soir et après chaque trade fermé. Remplace l’ancien `scripts/performance.py` (ne plus l’utiliser : il écrase le fichier avec 0 trade fermé).
- Update bankroll / sizing inputs; record failures in `knowledge/failure_log.md`.
- Kill switch anytime: `touch /workspace/predict-market-bot/STOP` then `scripts/kill_check.py` (exit 2).

## Gates (summary)

| Check | Paper | Live |
|-------|-------|------|
| `MODE` file | `paper` | `live` |
| `STOP` file | must be absent to trade | must be absent |
| Secrets | not required | required |
| Execution API | never | only after explicit enablement |
