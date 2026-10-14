#!/usr/bin/env python3
"""Pour un jour donné, montre de combien chaque paire a bougé heure par heure (écart haut/bas en %).
Usage: python3 scripts/heures_qui_bougent.py [AAAA-MM-JJ]  (par défaut: hier)"""
import json, sys, collections, datetime, pathlib
day = sys.argv[1] if len(sys.argv) > 1 else (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
f = pathlib.Path(__file__).resolve().parent.parent / f"state/price_ticks/{day}.jsonl"
if not f.exists():
    print(f"{day}: pas de relevé de prix"); sys.exit(0)
d = collections.defaultdict(list)
for l in open(f):
    if l.strip():
        r = json.loads(l); d[(r["pair"], r["ts"][11:13])].append(r["mid"])
parts = []
for p in ["BTC-EUR", "ETH-EUR", "SOL-EUR"]:
    hs = {h: (max(v) - min(v)) / min(v) * 100 for (pp, h), v in d.items() if pp == p}
    if not hs: continue
    top = sorted(hs.items(), key=lambda x: -x[1])[:2]
    parts.append(f"{p.split('-')[0]} {top[0][0]}h ({top[0][1]:.1f} %)" + (f", puis {top[1][0]}h ({top[1][1]:.1f} %)" if len(top) > 1 else ""))
print(f"{day} heures qui ont le plus bougé : " + " ; ".join(parts))
