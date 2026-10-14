#!/usr/bin/env python3
"""Fixed stop vs trailing stop, same entry signals. Raw JSON -> raw/, table -> results.csv. No orders, no AI."""
import json, subprocess, itertools, shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd, numpy as np

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
BT = "/workspace/tools/vibe-trading/backtest.sh"
END, DAYS = "2026-10-07", 365
MID = pd.Timestamp("2026-04-07 12:00")  # middle of 2025-10-07 00:00 .. 2026-10-07 23:00 UTC
PAIRS = ["ETH-EUR", "SOL-EUR", "BTC-EUR"]
SCEN = {  # name -> extra args
    "maker_allfilled": ["--costs", "revolutx-maker"],
    "maker_touch": ["--costs", "revolutx-maker", "--fill", "touch"],
    "taker_market": ["--costs", "revolutx"],
}
TEAM_VARIANTS = {"fixed": [], "trail1.5": ["--trail", "1.5"], "trail0.75": ["--trail", "0.75"],
                 "trail2.25": ["--trail", "2.25"], "trail1.5_noTP": ["--trail", "1.5", "--tp", "0"],
                 "fixed_noTP": ["--tp", "0"]}  # control: is the gain from trailing or just from removing the TP?
SR_VARIANTS = {"fixed": [], "trail1.5": ["--trail", "1.5"], "trail0.75": ["--trail", "0.75"], "trail2.25": ["--trail", "2.25"]}
SR_START = {"ETH-EUR": ["--coins", "0.011"], "SOL-EUR": ["--coins", "0.241"], "BTC-EUR": ["--eur", "25"]}

jobs = []
for pair, strat, (sc, sargs) in itertools.product(PAIRS, ["team_rebound", "team_breakout", "sell_rebuy"], SCEN.items()):
    variants = SR_VARIANTS if strat == "sell_rebuy" else TEAM_VARIANTS
    for v, vargs in variants.items():
        base = ["run", "--pair", pair, "--tf", "1H", "--days", str(DAYS), "--end", END, "--strategy", strat, "--json"]
        if strat == "sell_rebuy":
            base += SR_START[pair]
        else:
            base += ["--session", "15-17", "--tz", "Europe/Brussels", "--weekdays", "--sl", "1.5"]
        jobs.append((pair, strat, sc, v, base + sargs + vargs))

def run(job):
    pair, strat, sc, v, args = job
    name = f"{pair}_{strat}_{sc}_{v}"
    if (RAW / f"{name}.json").exists() and (RAW / f"{name}.json").stat().st_size > 0:
        return name, 0  # already run (raw kept)
    p = subprocess.run([BT] + args, capture_output=True, text=True, timeout=900)
    (RAW / f"{name}.json").write_text(p.stdout)
    (RAW / f"{name}.cmd.txt").write_text("backtest.sh " + " ".join(args) + "\n" + (p.stderr[-2000:] if p.returncode else ""))
    return name, p.returncode

def trades_of(s, strat, sc):
    rd = Path(s["run_dir"])
    if strat == "sell_rebuy":
        t = pd.read_csv(rd / "artifacts" / "cycles.csv")
        return pd.DataFrame({"entry": pd.to_datetime(t.sell_time_utc), "net_pct": t.coin_gain_pct, "reason": t.reason})
    if "fill_model" in s:
        t = pd.read_csv(rd / "artifacts" / f"fill_{s['fill_model']['mode']}_trades.csv")
        return pd.DataFrame({"entry": pd.to_datetime(t.entry), "net_pct": t.net_pct, "reason": t.reason})
    fills = [json.loads(x) for x in (rd / "artifacts" / "fills.jsonl").read_text().splitlines() if x.strip()]
    rows, op = [], None
    for f in fills:
        if f["action"] == "open": op = f
        elif f["action"] == "close" and op is not None:
            gross = float(f["notional"]) - float(op["notional"]); fees = float(op["fee"]) + float(f["fee"])
            rows.append({"entry": pd.Timestamp(op["timestamp"]), "net_pct": (gross - fees) / float(op["notional"]) * 100,
                         "reason": f.get("reason")}); op = None
    return pd.DataFrame(rows, columns=["entry", "net_pct", "reason"])

def comp(x): return (float(np.prod(1 + np.asarray(x) / 100)) - 1) * 100 if len(x) else 0.0

if __name__ == "__main__":
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(run, jobs))
    bad = [r for r in res if r[1] != 0]
    print("runs", len(res), "failed", bad)
    rows = []
    for pair, strat, sc, v, args in jobs:
        name = f"{pair}_{strat}_{sc}_{v}"
        try:
            s = json.loads((RAW / f"{name}.json").read_text())
        except Exception as e:
            rows.append({"pair": pair, "strategy": strat, "scenario": sc, "variant": v, "error": str(e)}); continue
        t = trades_of(s, strat, sc)
        if len(t):
            t["entry"] = pd.to_datetime(t["entry"]).dt.tz_localize(None)
        t.to_csv(RAW / f"{name}.trades.csv", index=False)
        h1, h2 = t[t.entry < MID], t[t.entry >= MID]
        loss = t[t.net_pct <= 0]
        if strat == "sell_rebuy":
            net, mdd, n, wr = s["coin_gain_vs_hold_pct"], s["max_drawdown_coins_pct"], s["cycles"], s["win_rate_pct"]
            reasons = s["rebuy_reasons"]
        else:
            net, mdd, n, wr = s["total_return_pct"], s["max_drawdown_pct"], s["trades"], s["win_rate_pct"]
            reasons = s["exit_reasons"]
        fm = s.get("fill_model", {})
        rows.append({"pair": pair, "strategy": strat, "scenario": sc, "variant": v,
                     "net_pct": round(net, 2), "net_from_trades_pct": round(comp(t.net_pct), 2), "trades": n,
                     "win_rate": wr, "h1_pct": round(comp(h1.net_pct), 2), "h1_trades": len(h1),
                     "h2_pct": round(comp(h2.net_pct), 2), "h2_trades": len(h2),
                     "maxdd_tool_pct": mdd, "maxdd_capital_5pct": round(abs(mdd) * 0.05, 3),
                     "avg_loss_pct": round(loss.net_pct.mean(), 3) if len(loss) else None,
                     "worst_loss_pct": round(t.net_pct.min(), 3) if len(t) else None,
                     "worst_loss_capital_5pct": round(abs(t.net_pct.min()) * 0.05, 3) if len(t) else None,
                     "exits": json.dumps(reasons), "warnings": "; ".join(s.get("warnings", [])),
                     "replica_matches_engine": (fm.get("old_all_filled_replica_check") or {}).get("matches_engine"),
                     "period": " -> ".join(x[:16] for x in s.get("period", [])), "run_dir": s.get("run_dir")})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "results.csv", index=False)
    print(df.drop(columns=["run_dir", "period", "exits", "warnings"]).to_string())
