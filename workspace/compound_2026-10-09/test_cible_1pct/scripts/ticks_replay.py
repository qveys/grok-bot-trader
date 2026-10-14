#!/usr/bin/env python3
"""Replay Predict decisions of 8-9 Oct 2026 on our own 30 s price records (state/price_ticks).
Entry: at decision time if the price is within 0.15 % of the planned start price, else at the first later
tick that reaches the start price. Then: which comes first, target or stop (mid price; bid/ask check too)."""
import json, pandas as pd
T = "/workspace/predict-market-bot/state/price_ticks/"
rows = [json.loads(l) for f in ("2026-10-08.jsonl", "2026-10-09.jsonl") for l in open(T + f) if l.strip()]
tk = pd.DataFrame(rows); tk["ts"] = pd.to_datetime(tk.ts, utc=True).dt.tz_convert("Europe/Brussels")
tk = tk.sort_values("ts")
# id, pair, dir, local time, start, actual target %, actual stop %
D = [("D-015","BTC","down","2026-10-08 14:34",73559.34,0.5,0.5),("D-016","ETH","down","2026-10-08 14:34",2261.91,0.5,0.5),
     ("D-017","SOL","down","2026-10-08 14:34",100.70,0.5,0.5),("D-021","SOL","down","2026-10-08 22:57",98.00,1.5,1.5),
     ("D-022","BTC","down","2026-10-09 14:02",74200,1.0,1.0),("D-023","BTC","up","2026-10-09 14:29",74120,1.5,1.0),
     ("D-024a","SOL","up","2026-10-09 15:07",98.69,1.42,1.41),("D-024b","ETH","down","2026-10-09 15:07",2232.70,1.6,1.0),
     ("D-024c","SOL","up","2026-10-09 15:07",98.69,2.04,1.0),
     ("D-026a","SOL","down","2026-10-09 15:36",97.70,1.5,1.5),("D-026b","SOL","down","2026-10-09 15:36",97.70,1.5,1.0),
     ("D-026c","SOL","down","2026-10-09 15:36",97.70,2.0,1.0),
     ("D-025a","SOL","up","2026-10-09 15:39",97.22,2.0,2.0),("D-025b","ETH","down","2026-10-09 15:39",2217.97,2.25,1.5),
     ("D-025c","BTC","up","2026-10-09 15:39",73050,2.0,1.0),
     ("D-028a","ETH","down","2026-10-09 16:23",2225.10,2.0,2.0),("D-028b","SOL","up","2026-10-09 16:23",98.38,2.25,1.5),
     ("D-028c","BTC","up","2026-10-09 16:23",74390,2.0,1.0),
     ("D-029a","SOL","up","2026-10-09 16:35",98.63,2.0,2.0),("D-029b","ETH","down","2026-10-09 16:35",2230.08,2.25,1.5),
     ("D-029c","SOL","up","2026-10-09 16:35",98.63,2.0,1.0),
     ("D-030a","SOL","down","2026-10-09 17:07",98.055,1.59,1.59),("D-030b","ETH","down","2026-10-09 17:07",2223.35,2.25,1.5),
     ("D-030c","SOL","down","2026-10-09 17:07",98.055,2.0,1.0),
     ("D-031a","BTC","up","2026-10-09 17:09",73956,1.2,1.2),("D-031b","SOL","down","2026-10-09 17:09",97.89,1.6,1.0),
     ("D-031c","BTC","up","2026-10-09 17:09",73956,2.0,1.0),
     ("D-033a","BTC","up","2026-10-09 18:21",74093.67,1.5,1.5),("D-033b","ETH","down","2026-10-09 18:21",2231.07,2.25,1.5),
     ("D-033c","BTC","up","2026-10-09 18:21",74093.67,2.0,1.0),
     ("D-034a","ETH","down","2026-10-09 19:25",2216.70,1.8,1.8),("D-034b","SOL","down","2026-10-09 19:25",97.71,2.25,1.5),
     ("D-034c","ETH","down","2026-10-09 19:25",2216.70,2.0,1.0)]

def first_hit(s, d, start, tp, sl, col_up="mid", col_dn="mid"):
    TP = start * (1 + tp / 100) if d == "up" else start * (1 - tp / 100)
    ST = start * (1 - sl / 100) if d == "up" else start * (1 + sl / 100)
    px = s[col_up] if d == "up" else s[col_dn]   # up: we sell at bid; down: we buy back at ask
    hit_tp = (px >= TP) if d == "up" else (px <= TP)
    hit_st = (px <= ST) if d == "up" else (px >= ST)
    a = s.ts[hit_tp].min() if hit_tp.any() else None; b = s.ts[hit_st].min() if hit_st.any() else None
    if a is None and b is None: return "aucun", None
    if b is None or (a is not None and a < b): return "cible", a
    return "arret", b

import sys
MODE = sys.argv[1] if len(sys.argv) > 1 else "entry"
out = []
for (i, p, d, t, start, tp, sl) in D:
    s = tk[(tk.pair == f"{p}-EUR") & (tk.ts >= pd.Timestamp(t, tz="Europe/Brussels"))].reset_index(drop=True)
    if s.empty: out.append({"id": i, "pair": p, "dir": d, "entree": "pas de prix"}); continue
    m0 = s.mid.iloc[0]
    if MODE == "decision" or abs(m0 / start - 1) <= 0.0015: k = 0
    else:
        reach = (s.mid <= start) if m0 > start else (s.mid >= start)
        k = int(reach.idxmax()) if reach.any() else None
    if k is None: out.append({"id": i, "pair": p, "dir": d, "start": start, "entree": "prix de départ jamais atteint", "mid_decision": m0}); continue
    s = s.iloc[k:]
    gap = s.ts.diff().dt.total_seconds().max()
    r = {"id": i, "pair": p, "dir": d, "decision": t[5:], "start": start, "entree_t": s.ts.iloc[0].strftime("%d %H:%M"),
         "reglage": f"{tp:g}/{sl:g}", "trou_max_s": round(gap or 0)}
    for lab, (a_, b_) in {"actuel": (tp, sl), "1/1": (1.0, 1.0)}.items():
        res, when = first_hit(s, d, start, a_, b_); r[lab] = res; r[lab + "_t"] = when.strftime("%d %H:%M") if when is not None else ""
        res2, _ = first_hit(s, d, start, a_, b_, "bid", "ask"); r[lab + "_bidask"] = res2
    r["fin_ticks"] = s.ts.iloc[-1].strftime("%d %H:%M")
    out.append(r)
df = pd.DataFrame(out); df.to_csv("/workspace/compound_2026-10-09/test_cible_1pct/ticks_replay_" + MODE + ".csv", index=False)
pd.set_option("display.width", 250); print(df.to_string(index=False))
