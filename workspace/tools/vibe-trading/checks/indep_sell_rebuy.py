"""Independent re-computation of a sell_rebuy run from its saved OHLCV + config (does not import vt_sellrebuy).
Usage: .venv/bin/python checks/indep_sell_rebuy.py <run_dir>"""
import json, sys
from pathlib import Path
import pandas as pd

run = Path(sys.argv[1]); cfg = json.loads((run / "config.json").read_text()); P = cfg["params"]
px = pd.read_csv(next((run / "artifacts").glob("ohlcv_*.csv")), parse_dates=["trade_date"], index_col="trade_date")
loc = (px.index + pd.to_timedelta(P["tf_hours"], unit="h")).tz_localize("UTC").tz_convert(P["tz"])
c = px["close"]; rb = round(P["rise_hours"] / P["tf_hours"]); tb = round(P["trend_ma"] / P["tf_hours"])
start = px.index.searchsorted(pd.Timestamp(cfg["start"]))
coins = cfg["coins0"]; state = None; n = 0; wins = 0
rows = list(px.itertuples())
for j in range(start, len(rows)):
    r = rows[j]
    if state is None and j - 1 >= start:
        i = j - 1
        rise = c.iloc[i] / c.iloc[i - rb] - 1 >= P["rise"] / 100 - 1e-12
        trend = P["trend_ma"] <= 0 or c.iloc[i] < c.iloc[i - tb + 1:i + 1].mean()
        h = loc[i].hour + loc[i].minute / 60
        sess = P["sess"][0] < 0 or (P["sess"][0] <= h < P["sess"][1])
        wd = (not P["weekdays"]) or loc[i].weekday() < 5
        if rise and trend and sess and wd:
            sp = r.open; q = coins * P["chunk"] / 100; coins -= q
            fx = P.get("fixed_fee_eur", 0.0)
            state = dict(j=j, q=q, eur=q * sp * (1 - P.get("maker_slip", 0.0)) * (1 - P["maker_fee"]) - fx, sp=sp)
    if state is not None:
        stop, tgt = state["sp"] * (1 + P["stop"] / 100), state["sp"] * (1 - P["dip"] / 100)
        buy = None
        if P["max_hours"] and j > state["j"] and (j - state["j"]) * P["tf_hours"] >= P["max_hours"]:
            buy = (r.open, True)
        elif r.high >= stop:
            buy = (max(r.open, stop), True)
        elif r.low <= tgt:
            buy = (tgt, False)
        if buy:
            p, tk = buy
            f, sl = (P["taker_fee"], P["taker_slip"]) if tk else (P["maker_fee"], P.get("maker_slip", 0.0))
            qb = (state["eur"] - P.get("fixed_fee_eur", 0.0)) / (p * (1 + sl) * (1 + f)); coins += qb; n += 1; wins += qb > state["q"]; state = None
if state is not None:
    p = rows[-1].close; qb = (state["eur"] - P.get("fixed_fee_eur", 0.0)) / (p * (1 + P["taker_slip"]) * (1 + P["taker_fee"])); coins += qb; n += 1; wins += qb > state["q"]
s = json.loads((run / "summary.json").read_text())
print(f"independent: cycles {n} wins {wins} coins_end {coins:.10f} | tool: cycles {s['cycles']} wins {s['wins']} coins_end {s['coins_end']:.10f}")
print("MATCH" if n == s["cycles"] and wins == s["wins"] and abs(coins - s["coins_end"]) < 1e-12 * max(1.0, coins) else "MISMATCH")
