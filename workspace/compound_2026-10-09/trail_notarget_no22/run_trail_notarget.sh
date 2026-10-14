#!/usr/bin/env bash
set -euo pipefail
BT=/workspace/tools/vibe-trading/backtest.sh
OUT=/workspace/compound_2026-10-09/trail_notarget_no22
export HTTPS_PROXY=http://127.0.0.1:8791 HTTP_PROXY=http://127.0.0.1:8791
: > "$OUT/run.log"
run_one() {
  local pair=$1 strat=$2 tag=$3
  shift 3
  local extra=("$@")
  echo "=== $tag $(date +%H:%M:%S) ===" | tee -a "$OUT/run.log"
  $BT run --pair "$pair" --tf 1H --days 365 --end 2026-10-08 --source ccxt --strategy "$strat" \
    --costs revolutx-maker --session 15-17 --tz Europe/Brussels --weekdays \
    --sl 1.5 --tp 0 --trail 1.5 --exit-hour -1 --max-bars 168 --fill touch --json "${extra[@]}" \
    > "$OUT/${tag}_touch.json" 2>"$OUT/${tag}_touch.err" && echo OK_touch_$tag | tee -a "$OUT/run.log" || echo FAIL_touch_$tag | tee -a "$OUT/run.log"
  $BT run --pair "$pair" --tf 1H --days 365 --end 2026-10-08 --source ccxt --strategy "$strat" \
    --costs revolutx --session 15-17 --tz Europe/Brussels --weekdays \
    --sl 1.5 --tp 0 --trail 1.5 --exit-hour -1 --max-bars 168 --json "${extra[@]}" \
    > "$OUT/${tag}_imm.json" 2>"$OUT/${tag}_imm.err" && echo OK_imm_$tag | tee -a "$OUT/run.log" || echo FAIL_imm_$tag | tee -a "$OUT/run.log"
  $BT robust --pair "$pair" --tf 1H --days 365 --end 2026-10-08 --source ccxt --strategy "$strat" \
    --costs revolutx-maker --session 15-17 --tz Europe/Brussels --weekdays \
    --sl 1.5 --tp 0 --trail 1.5 --exit-hour -1 --max-bars 168 --json "${extra[@]}" \
    > "$OUT/${tag}_robust.json" 2>"$OUT/${tag}_robust.err" && echo OK_robust_$tag | tee -a "$OUT/run.log" || echo FAIL_robust_$tag | tee -a "$OUT/run.log"
}
run_one ETH-EUR team_rebound eth_rebound
run_one SOL-EUR team_rebound sol_rebound
run_one BTC-EUR team_rebound btc_rebound
run_one ETH-EUR team_breakout eth_breakout --trend 200
run_one SOL-EUR team_breakout sol_breakout --trend 200
run_one BTC-EUR team_breakout btc_breakout --trend 200
echo DONE $(date +%H:%M:%S) | tee -a "$OUT/run.log"
