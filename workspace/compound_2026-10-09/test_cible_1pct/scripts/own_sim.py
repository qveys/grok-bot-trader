#!/usr/bin/env python3
"""Independent re-implementation (PM-Compound, 9 oct 2026): target/stop grids on cached Binance 1h EUR candles.
Both directions. long = buy then sell; short = sell owned coins then buy back (result in coins, no borrowing).
Conservative: if one candle touches both levels, stop first. Gaps: fill at open if open is beyond the level.
Safety exit after 48 candles at close (taker). No 22h exit. One position per (rule, direction) at a time."""
import sys, json, itertools
import numpy as np, pandas as pd
OUT = "/workspace/compound_2026-10-09/test_cible_1pct/own_sim"
D = "/workspace/compound_2026-10-09/test_cible_1pct/data"
EVAL_START = pd.Timestamp("2025-10-07 00:00", tz="UTC"); EVAL_END = pd.Timestamp("2026-10-07 23:00", tz="UTC")
SPLIT = pd.Timestamp("2026-04-07 23:30", tz="UTC")
TPS = [1, 1.5, 2, 2.25]; SLS = [1, 1.5]
COSTS = {"maker0": (0, 0, 0), "taker014": (0.0014, 0.0014, 0.0014), "mixed": (0.0014, 0.0, 0.0014)}  # entry, tp exit, stop/time exit
MAXBARS = 48

def load(p):
    df = pd.read_csv(f"{D}/{p}-EUR_1h_binance_cache.csv", parse_dates=["trade_date"])
    df["t"] = df.trade_date.dt.tz_localize("UTC"); return df.set_index("t")

def signals(df):
    c, o, h, l = df.close, df.open, df.high, df.low
    chg = c / c.shift(24) - 1
    ma50, ma200 = c.rolling(50).mean(), c.rolling(200).mean()
    fill = (df.index + pd.Timedelta(hours=1)).tz_convert("Europe/Brussels")
    sess = pd.Series((fill.hour >= 15) & (fill.hour < 17) & (fill.weekday < 5), index=df.index)
    s = {
      ("team_rebound", "long"): (chg.shift(1) <= -0.03) & (c > o) & (c > h.shift(1)) & sess,
      ("team_breakout", "long"): (c > h.rolling(8).max().shift(1)) & (c > ma50) & sess,
      ("mirror_rebound", "short"): (chg.shift(1) >= 0.03) & (c < o) & (c < l.shift(1)) & sess,
      ("mirror_breakout", "short"): (c < l.rolling(8).min().shift(1)) & (c < ma50) & sess,
      ("rise3_ma200", "short"): (chg >= 0.03) & (c < ma200) & sess,
      ("rise3_noma", "short"): (chg >= 0.03) & sess,
    }
    # baseline: candle CLOSING at 15:00 Brussels -> fill at 15:00 open of next candle (= every day 15h)
    base = pd.Series(fill.hour == 15, index=df.index) & (fill.minute == 0)
    base_wd = base & pd.Series(fill.weekday < 5, index=df.index)
    for d in ("long", "short"):
        s[("daily15h", d)] = base; s[("daily15h_weekdays", d)] = base_wd
    return {k: v.fillna(False).to_numpy() for k, v in s.items()}

def simulate(df, sig, direction, tp, sl, cost, tp_through=0.0, both="stop"):
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close")); t = df.index
    fe, ftp, fst = COSTS[cost]; n = len(df); trades = []; i = 0
    ev = (t >= EVAL_START - pd.Timedelta(hours=1)) & (t <= EVAL_END)
    while i < n - 1:
        if not (sig[i] and ev[i]): i += 1; continue
        k = i + 1; e = o[k]
        if direction == "long": TP, ST = e * (1 + tp / 100), e * (1 - sl / 100)
        else: TP, ST = e * (1 - tp / 100), e * (1 + sl / 100)
        TPx = TP * (1 + tp_through) if direction == "long" else TP * (1 - tp_through)
        ex = None; amb = False; mae = 0.0
        for j in range(k, min(n, k + MAXBARS)):
            first = j == k
            if direction == "long":
                hit_st = l[j] <= ST; hit_tp = (h[j] > TPx) if tp_through else (h[j] >= TP)
                mae = min(mae, l[j] / e - 1)
            else:
                hit_st = h[j] >= ST; hit_tp = (l[j] < TPx) if tp_through else (l[j] <= TP)
                mae = min(mae, e / h[j] - 1)
            if hit_st and hit_tp: amb = True
            if hit_st and (not hit_tp or both == "stop"):
                px = ST if first else (min(o[j], ST) if direction == "long" else max(o[j], ST)); ex = (j, px, "stop", fst); break
            if hit_tp:
                px = TP if first else (max(o[j], TP) if direction == "long" else min(o[j], TP)); ex = (j, px, "target", ftp); break
        if ex is None:
            j = min(n - 1, k + MAXBARS - 1); ex = (j, c[j], "time48h" if j == k + MAXBARS - 1 else "end", fst)
        j, px, why, fx = ex
        if direction == "long": net = px * (1 - fx) / (e * (1 + fe)) - 1; mae_net = mae - fe
        else: net = e * (1 - fe) / (px * (1 + fx)) - 1; mae_net = mae - fe  # coins gained vs holding
        trades.append({"entry_t": t[k], "exit_t": t[j], "entry": e, "exit": px, "why": why, "net": net, "mae": min(mae_net, net), "amb": amb})
        i = j + 1 if j > i else i + 1   # new signal only after the exit candle
    return trades

def stats(tr):
    if not tr: return {"n": 0, "net_pct": 0.0, "win": None, "h1": 0.0, "h2": 0.0, "n1": 0, "n2": 0, "dd_tool": 0.0, "q_pos": 0, "amb": 0, "avg": None}
    nets = np.array([x["net"] for x in tr]); eq = 1.0; peak = 1.0; dd = 0.0
    for x in tr:
        dd = min(dd, eq * (1 + x["mae"]) / peak - 1); eq *= 1 + x["net"]; peak = max(peak, eq); dd = min(dd, eq / peak - 1)
    h1 = [x["net"] for x in tr if x["entry_t"] < SPLIT]; h2 = [x["net"] for x in tr if x["entry_t"] >= SPLIT]
    comp = lambda a: (np.prod([1 + v for v in a]) - 1) * 100
    qs = pd.date_range(EVAL_START, EVAL_END + pd.Timedelta(hours=1), periods=5)
    qv = [comp([x["net"] for x in tr if qs[q] <= x["entry_t"] < qs[q + 1]]) for q in range(4)]
    return {"n": len(tr), "net_pct": round(comp(nets), 2), "win": round(float((nets > 0).mean() * 100), 1),
            "h1": round(comp(h1), 2), "h2": round(comp(h2), 2), "n1": len(h1), "n2": len(h2), "dd_tool": round(dd * 100, 2),
            "q_pos": int(sum(v > 0 for v in qv)), "quarters": [round(v, 2) for v in qv], "amb": int(sum(x["amb"] for x in tr)),
            "avg": round(float(nets.mean() * 100), 3),
            "exits": {w: sum(1 for x in tr if x["why"] == w) for w in ("target", "stop", "time48h", "end")}}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "main"
    rows = []
    for p in ("BTC", "ETH", "SOL"):
        df = load(p); S = signals(df)
        for (rule, d), sig in S.items():
            for tp, sl, cost in itertools.product(TPS, SLS, COSTS):
                kw = {}
                if mode == "touch": kw = {"tp_through": 0.001}            # target must trade 0.10% THROUGH
                if mode == "tpfirst": kw = {"both": "tp"}                  # optimistic ordering, to measure sensitivity
                st = stats(simulate(df, sig, d, tp, sl, cost, **kw))
                rows.append({"pair": p, "rule": rule, "dir": d, "tp": tp, "sl": sl, "cost": cost, **st})
    pd.DataFrame(rows).to_csv(f"{OUT}/grid_{mode}.csv", index=False)
    print("rows", len(rows))
