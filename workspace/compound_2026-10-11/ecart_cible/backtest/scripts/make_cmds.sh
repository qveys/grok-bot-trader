#!/usr/bin/env bash
# Grille cible × arrêt lié par rapport Risk (1 / 1,5 / 2). Une commande par ligne : <fichier>\t<args>
BT=/workspace/tools/vibe-trading/backtest.sh
COMMON="--tf 1H --end 2026-10-07 --days 365 --session 15-17 --tz Europe/Brussels --weekdays"
for p in BTC ETH SOL; do
 for tp in 0.75 1 1.25 1.5 2 2.5 3; do
  for r in 1 1.5 2; do
   sl=$(python3 -c "print(round($tp/$r,4))")
   for s in team_rebound team_breakout; do
     echo -e "${p}_${s}_tp${tp}_r${r}_revolutx.json\t$BT run --pair $p-EUR --strategy $s $COMMON --exit-hour -1 --max-bars 48 --tp $tp --sl $sl --costs revolutx --json"
     echo -e "${p}_${s}_tp${tp}_r${r}_maker-touch.json\t$BT run --pair $p-EUR --strategy $s $COMMON --exit-hour -1 --max-bars 48 --tp $tp --sl $sl --costs revolutx-maker --fill touch --json"
   done
   for tm in 200 0; do
     echo -e "${p}_sell_rebuy_tm${tm}_tp${tp}_r${r}_revolutx.json\t$BT run --pair $p-EUR --strategy sell_rebuy $COMMON --eur 1000 --trend-ma $tm --dip $tp --stop $sl --max-hours 48 --json"
     echo -e "${p}_sell_rebuy_tm${tm}_tp${tp}_r${r}_alltaker.json\t$BT run --pair $p-EUR --strategy sell_rebuy $COMMON --eur 1000 --trend-ma $tm --dip $tp --stop $sl --max-hours 48 --maker-fee 0.0014 --json"
   done
  done
 done
done
