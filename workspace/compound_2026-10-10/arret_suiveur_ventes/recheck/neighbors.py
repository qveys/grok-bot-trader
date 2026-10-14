"""Neighbours of the best sell candidate (trail 1.5, start 0.5, target 3 %), costs revolutx (realistic)."""
import json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
OUT = Path(__file__).resolve().parent / "neighbors"
BT = "/workspace/tools/vibe-trading/backtest.sh"
START = {"ETH-EUR": ["--coins", "0.011"], "SOL-EUR": ["--coins", "0.241"], "BTC-EUR": ["--eur", "25"]}
VAR = {f"trail{t}_start{s}": ["--trail", t, "--trail-start", s] for t in ["1.25", "1.5", "1.75"] for s in ["0.3", "0.5", "0.7", "1.0"]}
VAR["fixed"] = []
jobs = [(p, v, a) for p in START for v, a in VAR.items()]
def run(j):
    p, v, a = j
    cmd = [BT, "run", "--pair", p, "--tf", "1H", "--days", "365", "--end", "2026-10-07", "--strategy", "sell_rebuy", "--json", "--costs", "revolutx"] + START[p] + a
    s = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
    (OUT / f"{p}_{v}.json").write_text(json.dumps(s))
    return {"pair": p, "variant": v, "net": s["coin_gain_vs_hold_pct"], "n": s["cycles"], "h1": s["moitie_1_pct"], "h2": s["moitie_2_pct"], "verdict": s["verdict_equipe"]["test_du_passe_reussi"]}
with ThreadPoolExecutor(8) as ex:
    r = pd.DataFrame(list(ex.map(run, jobs)))
r.to_csv(OUT / "neighbors.csv", index=False)
for k in ["net", "h1", "h2"]:
    p = r.pivot_table(index="variant", columns="pair", values=k); p["SUM"] = p.sum(axis=1); print(k); print(p.round(2))
