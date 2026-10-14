"""Checks for vt_fill.py (fill model of team_* strategies). Run: .venv/bin/python checks/test_fill.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vt_fill as F

ok = 0
def check(cond, msg):
    global ok
    if not cond:
        print("FAIL", msg); sys.exit(1)
    ok += 1; print("OK ", msg)

# 3 candles on a weekday, UTC 13:00 (= 15:00 Brussels in October). signal on candle 0, limit = close 100.
idx = pd.date_range("2026-10-06 12:00", periods=4, freq="h")  # 14h,15h,16h,17h Brussels
def df(rows): return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx[:len(rows)])
sig = np.array([True, False, False, False])
P = {"tz": "Europe/Brussels", "sess": (15, 17), "weekdays": True, "exit_hour": 22.0, "sl": 1.5, "tp": 1.5,
     "cash": 1000.0, "maker_fee": 0.0, "maker_slip": 0.0, "taker_fee": 0.0009, "taker_slip": 0.0005}

d = df([[99, 100, 98, 100], [100, 100.5, 100.0, 100.2], [100.2, 100.6, 100.0, 100.3], [100.3, 100.4, 100.0, 100.1]])
r = F.simulate(d, sig, 1, P, "touch")
check(len(r["trades"]) == 0 and r["final"] == 1000.0 and r["orders"][0]["filled"] is False,
      "touch: low == limit (only touched) -> not filled, cancelled, no trade, no cost")

d2 = df([[99, 100, 98, 100], [100, 100.5, 99.99, 100.2], [100.2, 100.6, 100.1, 100.3], [100.3, 100.4, 100.1, 100.1]])
r = F.simulate(d2, sig, 1, P, "touch")
check(r["orders"][0]["filled"] and r["trades"][0]["entry_px"] == 100.0, "touch: low strictly below -> filled at the limit")
r = F.simulate(d2, sig, 1, P, "touch", ticks=5)
check(not r["orders"][0]["filled"], "touch --fill-ticks 5: 1 bp through is not enough -> not filled")

d3 = df([[99, 100, 98, 100], [100, 100.2, 99.9, 100.1], [100.1, 101.5, 100.0, 101.0], [101, 101.6, 100.9, 101.2]])
r = F.simulate(d3, sig, 1, P, "touch")
check(r["trades"][0]["reason"] == "take_profit" and r["trades"][0]["exit_maker"] and r["trades"][0]["fees"] == 0,
      "touch: tp sell limit 101.5 not filled at high == 101.5, filled when high 101.6 > 101.5, 0 fee (maker)")

d4 = df([[99, 100, 98, 100], [100, 100.2, 98.0, 98.2], [98, 99, 97, 98], [98, 98, 97, 97]])
r = F.simulate(d4, sig, 1, P, "touch")
t = r["trades"][0]
check(t["reason"] == "stop_loss" and not t["exit_maker"] and abs(t["exit_px"] - 98.5 * (1 - 0.0005)) < 1e-9 and t["fees"] > 0,
      "stop-loss = market order: taker fee + slippage")

sig_many = np.zeros(24 * 60, bool); rng = np.random.default_rng(0)
ix = pd.date_range("2026-01-05", periods=len(sig_many), freq="h")
c = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, len(ix)))); o = np.r_[100, c[:-1]]
hi = np.maximum(o, c) * (1 + rng.uniform(0, 0.005, len(ix))); lo = np.minimum(o, c) * (1 - rng.uniform(0, 0.005, len(ix)))
D = pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c}, index=ix)
sig_many[rng.choice(len(ix), 400, replace=False)] = True
all_ = F.simulate(D, sig_many, 30, P, "all"); r0 = F.simulate(D, sig_many, 30, P, "rate", rate=0)
r100 = F.simulate(D, sig_many, 30, P, "rate", rate=100)
check(len(r0["trades"]) == 0 and r0["final"] == 1000.0, "fill-rate 0 -> no trade at all")
check(abs(r100["final"] - all_["final"]) < 1e-6 and len(r100["trades"]) == len(all_["trades"]),
      "fill-rate 100 -> identical to all filled (same taker stops)")
a1 = F.simulate(D, sig_many, 30, P, "rate", rate=50, seed=1); a2 = F.simulate(D, sig_many, 30, P, "rate", rate=50, seed=1)
check(a1["final"] == a2["final"], "fill-rate 50 --seed 1 reproducible")
st = F.stats(a1, 1000.0)
check(30 <= st["entry_filled_pct"] <= 70 and st["entry_orders_placed"] == len(all_["orders"]),
      f"fill-rate 50: {st['entry_filled_pct']}% of {st['entry_orders_placed']} orders filled (same orders as all filled)")
check(abs(1000 + sum(x["net"] for x in a1["trades"]) - a1["final"]) < 1e-6, "cash = start + sum of trade results")
print(f"\nall {ok} checks passed")
