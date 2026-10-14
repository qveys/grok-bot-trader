#!/bin/bash
B=/workspace/tools/vibe-trading/backtest.sh
cd /workspace/compound_2026-10-08/out 2>/dev/null || { mkdir -p /workspace/compound_2026-10-08/out; cd /workspace/compound_2026-10-08/out; }
COM="--tf 1H --session 15-17 --tz Europe/Brussels --weekdays"
D13="--sl 1.5 --tp 3 --trend 200"
declare -A PER=( [full]="--days 365" [h1]="--start 2025-10-08 --end 2026-04-07" [h2]="--start 2026-04-08 --end 2026-10-07" )
declare -A MOD=( [all]="--costs revolutx-maker" [touch]="--costs revolutx-maker --fill touch" [rate50]="--costs revolutx-maker --fill-rate 50 --seed 1" [taker]="" )
jobs_list=()
for S in "reb ETH-EUR team_rebound" "reb SOL-EUR team_rebound" "brk ETH-EUR team_breakout"; do
 set -- $S; n=$1; p=$2; st=$3
 for per in full h1 h2; do for m in all touch rate50 taker; do
  echo "$B run --pair $p --strategy $st $COM $D13 ${PER[$per]} ${MOD[$m]} --json > ${n}_${p%%-*}_${per}_${m}.json 2> ${n}_${p%%-*}_${per}_${m}.err"
 done; done
 # Grok Bot control (as given, default tp/sl/trend)
 echo "$B run --pair $p --tf 1H --days 365 --strategy $st --costs revolutx-maker --session 15-17 --tz Europe/Brussels --weekdays --fill touch --json > ctl_${n}_${p%%-*}.json 2> ctl_${n}_${p%%-*}.err"
 # no 22h exit (Quentin 8 oct): exit by sl/tp or after 7 days
 for m in touch taker; do
  echo "$B run --pair $p --strategy $st $COM $D13 --days 365 ${MOD[$m]} --exit-hour -1 --max-bars 168 --json > ${n}_${p%%-*}_no22_${m}.json 2> ${n}_${p%%-*}_no22_${m}.err"
 done
done > cmds.txt
xargs -P 4 -I{} bash -c '{}' < cmds.txt
echo DONE
