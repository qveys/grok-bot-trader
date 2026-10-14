#!/usr/bin/env python3
"""raw/*.json + run dirs (after vt_verdict.py --all) -> results.csv + tables.md"""
import json
from pathlib import Path
import pandas as pd, numpy as np
from run_all import jobs, nm, RAW, OUT, MID

def comp(x): return (float(np.prod(1 + np.asarray(x, float) / 100)) - 1) * 100 if len(x) else 0.0

def trades_of(s, strat):
    rd = Path(s["run_dir"])
    if strat == "sell_rebuy":
        t = pd.read_csv(rd / "artifacts" / "cycles.csv")
        return pd.DataFrame({"entry": pd.to_datetime(t.sell_time_utc), "net_pct": t.coin_gain_pct, "reason": t.reason})
    if "fill_model" in s:
        t = pd.read_csv(rd / "artifacts" / f"fill_{s['fill_model']['mode']}_trades.csv")
        if not len(t): return pd.DataFrame(columns=["entry", "net_pct", "reason"])
        return pd.DataFrame({"entry": pd.to_datetime(t.entry), "net_pct": t.net_pct, "reason": t.reason})
    rows, op = [], None
    for x in (rd / "artifacts" / "fills.jsonl").read_text().splitlines():
        if not x.strip(): continue
        f = json.loads(x)
        if f["action"] == "open": op = f
        elif f["action"] == "close" and op is not None:
            g = float(f["notional"]) - float(op["notional"]); fe = float(op["fee"]) + float(f["fee"])
            rows.append({"entry": pd.Timestamp(op["timestamp"]), "net_pct": (g - fe) / float(op["notional"]) * 100, "reason": f.get("reason")}); op = None
    return pd.DataFrame(rows, columns=["entry", "net_pct", "reason"])

def verdict(s, strat):
    rd = Path(s["run_dir"])
    f = rd / ("summary.json" if strat == "sell_rebuy" else "run_card.json")
    try:
        v = json.loads(f.read_text()).get("verdict_equipe") or {}
    except Exception:
        v = {}
    return v or s.get("verdict_equipe") or {}

rows = []
for pair, strat, sc, v, args in jobs:
    name = nm(pair, strat, sc, v)
    try:
        s = json.loads((RAW / f"{name}.json").read_text())
        assert s.get("status") == "ok", s
    except Exception as e:
        rows.append({"pair": pair, "strategy": strat, "scenario": sc, "variant": v, "error": str(e)[:200]}); continue
    t = trades_of(s, strat)
    if len(t): t["entry"] = pd.to_datetime(t["entry"]).dt.tz_localize(None)
    t.to_csv(RAW / f"{name}.trades.csv", index=False)
    h1, h2 = t[t.entry < MID], t[t.entry >= MID]
    if strat == "sell_rebuy":
        net, mdd, n, wr, ex = s["coin_gain_vs_hold_pct"], s["max_drawdown_coins_pct"], s["cycles"], s["win_rate_pct"], s["rebuy_reasons"]
    else:
        net, mdd, n, wr, ex = s["total_return_pct"], s["max_drawdown_pct"], s["trades"], s["win_rate_pct"], s["exit_reasons"]
    vd = verdict(s, strat)
    fm = s.get("fill_model", {})
    rows.append({"pair": pair, "strategy": strat, "scenario": sc, "variant": v, "net_pct": round(net, 2),
                 "net_from_trades_pct": round(comp(t.net_pct), 2), "trades": n, "win_rate": wr,
                 "h1_pct": round(comp(h1.net_pct), 2), "h1_n": len(h1), "h2_pct": round(comp(h2.net_pct), 2), "h2_n": len(h2),
                 "maxdd_tool_pct": mdd, "maxdd_capital_5pct": round(abs(mdd) * 0.05, 3),
                 "worst_trade_pct": round(t.net_pct.min(), 3) if len(t) else None,
                 "avg_hold_h": None if strat != "sell_rebuy" else s.get("avg_hours_out_of_market"),
                 "verdict": vd.get("test_du_passe_reussi"), "verdict_reasons": "; ".join(vd.get("raisons", [])),
                 "v_h1": vd.get("moitie_1_pct"), "v_h2": vd.get("moitie_2_pct"),
                 "exits": json.dumps(ex), "replica_ok": (fm.get("old_all_filled_replica_check") or {}).get("matches_engine"),
                 "warnings": "; ".join(s.get("warnings", [])), "run_dir": s["run_dir"]})
df = pd.DataFrame(rows)
df.to_csv(OUT / "results.csv", index=False)
print("rows", len(df), "errors", df["error"].notna().sum() if "error" in df else 0)
