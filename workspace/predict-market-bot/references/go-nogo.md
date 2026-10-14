# Go / no-go — Revolut X first

Paper (or tiny size) until all minimum thresholds pass.

## Go (minimum, all required)
- N trades ≥ 50 (target 100), excluding self-tests
- Forecast/edge quality tracked (Brier or equivalent hit-rate vs baseline)
- Win rate ≥ 55% AND profit factor ≥ 1.3 after fees/spread
- Max drawdown < 8% of paper bankroll
- Sharpe > 1.0 if enough days (comfort > 1.5)
- All fills through validate_risk / equivalent; no bypass
- Kill switch STOP honored

## No-go
- Edge worse than baseline after 30+ signals
- Drawdown ≥ 8% or daily loss ≥ 15%
- Profit factor < 1.0 after 50 trades
- Cannot explain why PnL is not luck

## Live start
- Explicit user authorization
- Max exposure ~100–300 EUR initially
- Quarter-Kelly, ≤5%/position
- Review after 20 live trades; if live << paper → STOP

## Scale
- 50+ live trades meeting same thresholds before sizing up

Venue order: Revolut X now; MetaMask/on-chain later. Polymarket/Kalshi trading off for Belgium.


See also locked team rules: `references/regles-litterature.md` (expectancy, journal, 15%/8%).
