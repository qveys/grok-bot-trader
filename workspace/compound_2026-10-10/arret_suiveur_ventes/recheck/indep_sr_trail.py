#!/usr/bin/env python3
"""Independent re-computation of a sell_rebuy run (written from the rules, does NOT import vt_sellrebuy):
plain Python loop over the saved OHLCV, with fixed safety, trailing level, trail start (breakeven floor) and dip 0.
Also splits the result into quarters (by sell time). Usage: python3 indep_sr_trail.py <run_dir> [...]"""
import csv, json, sys
from datetime import datetime, timedelta
from pathlib import Path

def load(run):
    f = next((run / "artifacts").glob("ohlcv_*.csv"))
    rows = []
    with open(f) as fh:
        for r in csv.DictReader(fh):
            rows.append((datetime.fromisoformat(r["trade_date"][:19]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
    return rows

def recompute(run):
    cfg = json.loads((run / "config.json").read_text()); P = cfg["params"]
    assert P["sess"][0] < 0 and not P["weekdays"] and P["chunk"] == 100 and P["sell_fill"] == "open" and P["fill"] == "all"
    R = load(run)
    t0 = datetime.fromisoformat(cfg["start"])
    start = next(i for i, r in enumerate(R) if r[0] >= t0)
    rb, tb = int(P["rise_hours"]), int(P["trend_ma"])
    fee_m, fee_t, sl_t = P["maker_fee"] + 0, P["taker_fee"], P["taker_slip"]
    if P.get("swap_mode"):
        fee_m = fee_t; sl_t = P["taker_slip"]
    coins = cfg["coins0"]; cyc = None; out = []
    for j in range(start, len(R)):
        t, o, h, l, c = R[j]
        if cyc is None and j - 1 >= start:
            i = j - 1
            ci = R[i][4]
            rise = ci / R[i - rb][4] - 1 >= P["rise"] / 100 - 1e-12
            ma = sum(R[k][4] for k in range(i - tb + 1, i + 1)) / tb
            if rise and ci < ma and coins > 0:
                ms = P["maker_slip"] if not P.get("swap_mode") else sl_t
                eur = coins * o * (1 - ms) * (1 - fee_m)
                cyc = {"j": j, "t": t, "sp": o, "q": coins, "eur": eur, "low": o}
                coins = 0.0
        if cyc is not None:
            sp = cyc["sp"]
            lvl, why = sp * (1 + P["stop"] / 100), "safety"
            if P["trail"] > 0:
                tl = cyc["low"] * (1 + P["trail"] / 100)
                if P.get("trail_start", 0) > 0:
                    tl = min(tl, sp) if cyc["low"] <= sp * (1 - P["trail_start"] / 100) else 1e18
                if tl < lvl:
                    lvl, why = tl, "trailing"
                cyc["low"] = min(cyc["low"], l)   # this candle's low counts from the next candle
            buy = None
            if h >= lvl:
                buy = (max(o, lvl), True, why)
            elif P["dip"] > 0 and l <= sp * (1 - P["dip"] / 100):
                buy = (sp * (1 - P["dip"] / 100), False, "target")
            if buy:
                px, taker, why = buy
                f, s = (fee_t, sl_t) if taker else (fee_m, P["maker_slip"] if not P.get("swap_mode") else sl_t)
                qb = cyc["eur"] / (px * (1 + s) * (1 + f))
                out.append((cyc["t"], (qb / cyc["q"] - 1) * 100, why)); coins = qb; cyc = None
    if cyc is not None:
        px = R[-1][4]; qb = cyc["eur"] / (px * (1 + sl_t) * (1 + fee_t)); out.append((cyc["t"], (qb / cyc["q"] - 1) * 100, "end")); coins = qb
    return cfg, coins, out

def comp(x):
    f = 1.0
    for p in x: f *= 1 + p / 100
    return (f - 1) * 100

if __name__ == "__main__":
    Q = [datetime(2025, 10, 7), datetime(2026, 1, 7), datetime(2026, 4, 7), datetime(2026, 7, 7), datetime(2026, 10, 8)]
    for a in sys.argv[1:]:
        run = Path(a); cfg, coins, out = recompute(run)
        s = json.loads((run / "summary.json").read_text())
        g = (coins / cfg["coins0"] - 1) * 100
        q = [comp([p for t, p, _ in out if Q[k] <= t < Q[k + 1]]) for k in range(4)]
        qn = [sum(1 for t, *_ in out if Q[k] <= t < Q[k + 1]) for k in range(4)]
        ok = abs(coins - s["coins_end"]) < 1e-9 * max(1, coins) and len(out) == s["cycles"]
        print(json.dumps({"run": run.name, "pair": cfg["pair"], "params": {k: cfg["params"][k] for k in ("dip", "stop", "trail", "trail_start") if k in cfg["params"]},
                          "indep_gain_pct": round(g, 3), "tool_gain_pct": s["coin_gain_vs_hold_pct"], "indep_cycles": len(out), "tool_cycles": s["cycles"],
                          "MATCH": ok, "quarters_pct": [round(x, 2) for x in q], "quarters_n": qn}))
