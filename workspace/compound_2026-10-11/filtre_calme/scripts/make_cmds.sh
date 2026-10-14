#!/usr/bin/env bash
# Filtre « plage 24 h > X % » (--min-range24) × visé 1,5–3 % × rapports Risk. <fichier>\t<commande>
BT=/workspace/tools/vibe-trading/backtest.sh
COMMON="--tf 1H --end 2026-10-07 --days 365 --session 15-17 --tz Europe/Brussels --weekdays"
for x in 0 1 1.5 2 2.5 3 4 5; do
for p in BTC ETH SOL; do
 for tp in 1.5 2 2.5 3; do
  for r in 1 1.5 2; do
   sl=$(python3 -c "print(round($tp/$r,4))")
   for s in team_rebound team_breakout; do
     echo -e "x${x}_${p}_${s}_tp${tp}_r${r}_revolutx.json\t$BT run --pair $p-EUR --strategy $s $COMMON --exit-hour -1 --max-bars 48 --tp $tp --sl $sl --costs revolutx --min-range24 $x --json"
     echo -e "x${x}_${p}_${s}_tp${tp}_r${r}_maker-touch.json\t$BT run --pair $p-EUR --strategy $s $COMMON --exit-hour -1 --max-bars 48 --tp $tp --sl $sl --costs revolutx-maker --fill touch --min-range24 $x --json"
   done
   for tm in 200 0; do
     echo -e "x${x}_${p}_sell_rebuy_tm${tm}_tp${tp}_r${r}_revolutx.json\t$BT run --pair $p-EUR --strategy sell_rebuy $COMMON --eur 1000 --trend-ma $tm --dip $tp --stop $sl --max-hours 48 --min-range24 $x --json"
     echo -e "x${x}_${p}_sell_rebuy_tm${tm}_tp${tp}_r${r}_alltaker.json\t$BT run --pair $p-EUR --strategy sell_rebuy $COMMON --eur 1000 --trend-ma $tm --dip $tp --stop $sl --max-hours 48 --maker-fee 0.0014 --min-range24 $x --json"
   done
  done
 done
done; done
