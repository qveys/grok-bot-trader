---
name: Prediction market compound
description: >-
  Use after prediction-market trades for post-mortems, failure lessons,
  Brier/win-rate tracking, or nightly performance consolidation.
---
# Prediction market — Compound (learn)

Use after prediction-market trades settle or lose, or for a nightly performance review.

## Goal
Turn every trade—especially losses—into durable lessons and updated metrics.

## Shared workspace
`/workspace/predict-market-bot/` — `state/trades_log.jsonl`, `state/predictions_log.jsonl`, `knowledge/failure_log.md`, `scripts/performance.py`.

## Steps
1. Log/confirm: entry, exit, p_model, outcome, PnL, hold time, conditions.
2. On loss, classify: bad prediction | bad timing | bad execution | external shock.
3. Append a short lesson to `knowledge/failure_log.md` (what to check next time).
4. Run `python3 scripts/performance.py` → update `state/performance.json`.
5. Track: win rate, profit factor, max drawdown, Brier; Sharpe if enough data.

## Targets (guide, not guarantees)
- Win rate ≥ 60%
- Profit factor ≥ 1.5
- Max drawdown < 8% (block new risk if exceeded — tell Risk)
- Brier: lower is better

## Revolut X paper
Compound is unchanged for paper closes: log fills/closes from guardian `paper_fill` / ledger, run `performance.py`, append lessons. No live orders.

## Hard rules
- No new orders from this skill.
- Scan/Research should read failure_log before new cycles.
