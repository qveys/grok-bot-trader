---
name: Prediction market predict
description: >-
  Use when estimating edge vs mid for Revolut X crypto spot (directional) or
  event probability vs odds; emit a signal before risk checks. No execution.
---
# Prediction market — Predict

Use this when estimating true view vs market mid/price and deciding whether there is tradeable edge.

## Goal
Emit trade *signals* only when edge and confidence clear thresholds. No execution.

## Shared workspace
`/workspace/predict-market-bot/` — briefs in `state/research_briefs/`, formulas in `references/formulas.md`, log to `state/predictions_log.jsonl`.

## Revolut X crypto (primary)
- Predict = **directional edge vs mid** (spot), not `p_model` event probability.
- Compare research thesis (bullish/bearish/neutral + conviction) to current mid from last scan / public ticker.
- Edge is the estimated mispricing or expected move vs mid; still require config `predict.min_edge` / `min_confidence` style thresholds (adapt: min_edge as fractional move or edge score from config).
- Signal fields: pair, side (long/short), mid, edge, confidence, rationale — platform `revolut_x_paper`.

## Event markets (if ever used)
- Edge: `edge = p_model - p_market` — trade candidate only if `edge > 0.04`
- EV: `EV = p * b - (1 - p)`
- Brier tracking over time

## Steps
1. Read research brief + current mid/prices from scan.
2. For crypto: produce directional view + confidence vs mid; for events: `p_model` vs `p_market`.
3. If edge/confidence below thresholds, output **no-trade** with reason.
4. Else write signal JSON for Risk.
5. Append to `predictions_log.jsonl`.

## Hard rules
- Calibration over bravado: log every prediction for later review.
- Never size or place the order here — that is Risk.
