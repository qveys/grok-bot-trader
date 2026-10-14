#!/usr/bin/env python3
"""Fixed stop vs trailing stop vs breakeven-then-trail, with / without target, NO time exit.
team_rebound / team_breakout + sell_rebuy, ETH/SOL/BTC-EUR, 1h, 2025-10-07..2026-10-07 (cache). No orders, no AI."""
import json, subprocess, itertools
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd, numpy as np

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
BT = "/workspace/tools/vibe-trading/backtest.sh"
END, DAYS = "2026-10-07", 365
MID = pd.Timestamp("2026-04-07 12:00")
PAIRS = ["ETH-EUR", "SOL-EUR", "BTC-EUR"]
DIST = ["1.0", "1.5", "2.0"]
TEAM_SCEN = {"M_maker_allfilled": ["--costs", "revolutx-maker"],
             "T_maker_touch": ["--costs", "revolutx-maker", "--fill", "touch"],
             "K_immediate_0.14": ["--costs", "revolutx"],
             "G_guardian_0.05": ["--costs", "revolutx", "--fee", "0.0005", "--slippage", "0"]}
SR_SCEN = {"M_maker_allfilled": ["--costs", "revolutx-maker"],
           "T_maker_touch": ["--costs", "revolutx-maker", "--fill", "touch"],
           "K_revolutx": ["--costs", "revolutx"],                 # sell + target rebuy limit 0 %, stop rebuy market 0.14 %
           "K2_all_0.14": ["--costs", "revolutx", "--fee-pct", "0.14"],  # every leg 0.14 % (all immediate fills)
           "G_guardian_0.05": ["--costs", "revolutx", "--fee-pct", "0.05"]}
NT = ["--no-time-exit"]
TEAM_VAR = {"a_fixed_tp_22h(legacy)": [], "a_fixed_tp": NT, "b_fixed_noTP": NT + ["--tp", "0"]}
SR_VAR = {"a_fixed_tp": [], "b_fixed_noTP": ["--dip", "0"]}
for d in DIST:
    TEAM_VAR[f"c_trail{d}_tp"] = NT + ["--trail", d]
    TEAM_VAR[f"d_trail{d}_noTP"] = NT + ["--trail", d, "--tp", "0"]
    TEAM_VAR[f"e_be{d}_tp"] = NT + ["--trail", d, "--trail-start", "0.5"]
    TEAM_VAR[f"e_be{d}_noTP"] = NT + ["--trail", d, "--trail-start", "0.5", "--tp", "0"]
    SR_VAR[f"c_trail{d}_tp"] = ["--trail", d]
    SR_VAR[f"d_trail{d}_noTP"] = ["--trail", d, "--dip", "0"]
    SR_VAR[f"e_be{d}_tp"] = ["--trail", d, "--trail-start", "0.5"]
    SR_VAR[f"e_be{d}_noTP"] = ["--trail", d, "--trail-start", "0.5", "--dip", "0"]
SR_START = {"ETH-EUR": ["--coins", "0.011"], "SOL-EUR": ["--coins", "0.241"], "BTC-EUR": ["--eur", "25"]}

jobs = []
for pair, strat in itertools.product(PAIRS, ["sell_rebuy", "team_rebound", "team_breakout"]):
    scen, var = (SR_SCEN, SR_VAR) if strat == "sell_rebuy" else (TEAM_SCEN, TEAM_VAR)
    for (sc, sargs), (v, vargs) in itertools.product(scen.items(), var.items()):
        base = ["run", "--pair", pair, "--tf", "1H", "--days", str(DAYS), "--end", END, "--strategy", strat, "--json"]
        base += SR_START[pair] if strat == "sell_rebuy" else ["--session", "15-17", "--tz", "Europe/Brussels", "--weekdays", "--sl", "1.5"]
        jobs.append((pair, strat, sc, v, base + sargs + vargs))

def nm(pair, strat, sc, v): return f"{pair}_{strat}_{sc}_{v}".replace("(", "").replace(")", "")

def run(job):
    pair, strat, sc, v, args = job
    name = nm(pair, strat, sc, v)
    f = RAW / f"{name}.json"
    if f.exists() and f.stat().st_size > 0:
        return name, 0
    p = subprocess.run([BT] + args, capture_output=True, text=True, timeout=900)
    f.write_text(p.stdout)
    (RAW / f"{name}.cmd.txt").write_text("backtest.sh " + " ".join(args) + "\n" + (p.stderr[-2000:] if p.returncode else ""))
    return name, p.returncode

if __name__ == "__main__":
    RAW.mkdir(exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(run, jobs))
    print("runs", len(res), "failed", [r for r in res if r[1] != 0])
    json.dump([[*j[:4], j[4]] for j in jobs], open(OUT / "jobs.json", "w"))
