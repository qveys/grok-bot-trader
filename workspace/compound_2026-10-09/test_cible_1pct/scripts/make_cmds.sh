#!/usr/bin/env bash
# Generates one command per line: <outfile>\t<args>
BT=/workspace/tools/vibe-trading/backtest.sh
COMMON="--tf 1H --end 2026-10-07 --days 365 --session 15-17 --tz Europe/Brussels --weekdays"
for p in BTC ETH SOL; do
 for s in team_rebound team_breakout; do
  for tp in 1 1.5 2 2.25; do for sl in 1 1.5; do
   for c in revolutx-maker revolutx; do
     echo -e "${p}_${s}_tp${tp}_sl${sl}_${c}_fillall.json\t$BT run --pair $p-EUR --strategy $s $COMMON --exit-hour -1 --max-bars 48 --tp $tp --sl $sl --costs $c --json"
   done
   echo -e "${p}_${s}_tp${tp}_sl${sl}_revolutx-maker_filltouch.json\t$BT run --pair $p-EUR --strategy $s $COMMON --exit-hour -1 --max-bars 48 --tp $tp --sl $sl --costs revolutx-maker --fill touch --json"
  done; done
 done
 for tp in 1 1.5 2 2.25; do for sl in 1 1.5; do
  for tm in 200 0; do
   echo -e "${p}_sell_rebuy_tm${tm}_dip${tp}_stop${sl}_revolutx.json\t$BT run --pair $p-EUR --strategy sell_rebuy $COMMON --eur 1000 --trend-ma $tm --dip $tp --stop $sl --max-hours 48 --json"
   echo -e "${p}_sell_rebuy_tm${tm}_dip${tp}_stop${sl}_alltaker.json\t$BT run --pair $p-EUR --strategy sell_rebuy $COMMON --eur 1000 --trend-ma $tm --dip $tp --stop $sl --max-hours 48 --maker-fee 0.0014 --json"
  done
 done; done
done
