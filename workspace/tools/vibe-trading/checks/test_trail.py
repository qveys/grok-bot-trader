"""Checks for the --trail option (trailing stop). Run: .venv/bin/python checks/test_trail.py  (no network)
team_*  (vt_fill.simulate): stop = max(entry*(1-sl), highest high of COMPLETED candles*(1-trail)), never down.
sell_rebuy (vt_sellrebuy.simulate): safety = min(sell*(1+stop), lowest low of COMPLETED candles*(1+trail)), never up."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vt_fill as F
import vt_sellrebuy as SR

ok = 0
def check(cond, msg):
    global ok
    if not cond:
        print("FAIL", msg); sys.exit(1)
    ok += 1; print("OK ", msg)

idx = pd.date_range("2026-10-06 12:00", periods=6, freq="h")  # Tuesday, 14h..19h Brussels
def df(rows): return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx[:len(rows)])
sig = np.zeros(6, bool); sig[0] = True
P = {"tz": "Europe/Brussels", "sess": (15, 17), "weekdays": True, "exit_hour": 22.0, "sl": 1.5, "tp": 0.0,
     "cash": 1000.0, "maker_fee": 0.0, "maker_slip": 0.0, "taker_fee": 0.0, "taker_slip": 0.0, "all_maker": True}
# entry at open of candle 1 = 100; candle 1 high 101; candle 2 drops to 99.4 (low)
rows = [[99, 100, 98, 100], [100, 101, 99.9, 100.8], [100.8, 100.9, 99.4, 99.6], [99.6, 99.8, 98.0, 98.2],
        [98.2, 98.4, 98.1, 98.3], [98.3, 98.4, 98.2, 98.3]]
r_fix = F.simulate(df(rows), sig, 1, P, "all")
r_tr = F.simulate(df(rows), sig, 1, {**P, "trail": 1.5}, "all")
r_off = F.simulate(df(rows), sig, 1, {**P, "trail": 0.0}, "all")
check(r_off["final"] == r_fix["final"] and r_off["trades"] == r_fix["trades"], "trail 0 = fixed stop, identical")
check(r_fix["trades"][0]["reason"] == "stop_loss" and abs(r_fix["trades"][0]["exit_px"] - 98.5) < 1e-9,
      "fixed: stop at 98.5 hit on candle 3")
t = r_tr["trades"][0]
check(t["reason"] == "trailing_stop" and abs(t["exit_px"] - 101 * 0.985) < 1e-9 and t["exit"] == str(idx[2]),
      "trailing 1.5%: peak 101 (candle 1) -> stop 99.485 hit on candle 2 at 99.485")
# same-candle high not used: candle 1 high 101.5 and low 99.9 -> trail stop on candle 1 stays 98.5 (fixed)
rows2 = [[99, 100, 98, 100], [100, 103, 99.0, 102], [102, 102.5, 101.0, 101.2], [101.2, 101.3, 101.1, 101.2],
         [101.2, 101.3, 101.1, 101.2], [101.2, 101.3, 101.1, 101.2]]
t2 = F.simulate(df(rows2), sig, 1, {**P, "trail": 1.5}, "all")["trades"][0]
check(t2["reason"] == "trailing_stop" and t2["exit"] == str(idx[2]) and abs(t2["exit_px"] - 103 * 0.985) < 1e-9,
      "candle 1 (high 103, low 99) not stopped by its own high; candle 2 stopped at 103*0.985=101.455")
# gap down through a raised stop -> filled at the (worse) open
rows3 = [[99, 100, 98, 100], [100, 102, 99.9, 101.8], [99.0, 99.5, 98.9, 99.2]] + [[99.2] * 4] * 3
t3 = F.simulate(df(rows3), sig, 1, {**P, "trail": 1.0}, "all")["trades"][0]
check(t3["reason"] == "trailing_stop" and abs(t3["exit_px"] - 99.0) < 1e-9, "gap below the trailing stop -> exit at the open 99.0")
# stop never goes down: peak kept
rows4 = [[99, 100, 98, 100], [100, 102, 99.9, 101.5], [101.5, 101.6, 100.6, 100.7], [100.7, 100.8, 100.4, 100.5],
         [100.5, 100.6, 100.4, 100.5], [100.5, 100.6, 100.4, 100.5]]
t4 = F.simulate(df(rows4), sig, 1, {**P, "trail": 1.5}, "all")["trades"][0]
check(t4["reason"] == "trailing_stop" and abs(t4["exit_px"] - 102 * 0.985) < 1e-9 and t4["exit"] == str(idx[3]),
      "stop stays at 102*0.985=100.47 after the price falls back (never lowered) -> hit on candle 3")
# random series: cash accounting + trailing never exits below the fixed stop level for the same trade
sig_many = np.zeros(24 * 60, bool); rng = np.random.default_rng(0)
ix = pd.date_range("2026-01-05", periods=len(sig_many), freq="h")
c = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, len(ix)))); o = np.r_[100, c[:-1]]
hi = np.maximum(o, c) * (1 + rng.uniform(0, 0.005, len(ix))); lo = np.minimum(o, c) * (1 - rng.uniform(0, 0.005, len(ix)))
D = pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c}, index=ix)
sig_many[rng.choice(len(ix), 400, replace=False)] = True
for mode in ("all", "touch"):
    a = F.simulate(D, sig_many, 30, {**P, "tp": 1.5, "trail": 1.0, "taker_fee": 0.0009, "taker_slip": 0.0005}, mode)
    check(abs(1000 + sum(x["net"] for x in a["trades"]) - a["final"]) < 1e-6, f"{mode}: cash = start + sum of trade results (trail)")
    b = F.simulate(D, sig_many, 30, {**P, "tp": 1.5, "taker_fee": 0.0009, "taker_slip": 0.0005}, mode)
    check(len(a["orders"]) >= 1 and [x["entry"] for x in a["trades"]][:5] == [x["entry"] for x in b["trades"]][:5],
          f"{mode}: same first entries as the fixed stop")

# ── sell_rebuy mirror ──
def SP(**kw):
    base = dict(rise=3.0, rise_hours=3, trend_ma=0, dip=3.0, stop=1.5, max_hours=0, chunk=100.0, sell_fill="open",
                sess=(-1, -1), weekdays=False, tz="Europe/Brussels", tf_hours=1.0,
                maker_fee=0.0, maker_slip=0.0, taker_fee=0.0, taker_slip=0.0)
    base.update(kw); return base
def ssim(rows, **kw):
    d = pd.DataFrame(rows, columns=["open", "high", "low", "close"], dtype=float)
    s = np.zeros(len(d), bool); s[0] = True
    return SR.simulate(*(d[k].to_numpy() for k in ("open", "high", "low", "close")), s, 0, 1.0, SP(**kw))
FL = (100, 100, 100, 100)
rows = [FL, (100, 100.2, 99.0, 99.2), (99.2, 100.6, 99.1, 100.4), FL]
r0 = ssim(rows); r1 = ssim(rows, trail=1.5)
check(r0["cycles"][0]["reason"] == "end" or r0["cycles"][0]["reason"] != "trailing", "sell_rebuy fixed: no trailing rebuy")
cy = r1["cycles"][0]
check(cy["reason"] == "trailing" and abs(cy["buy_px"] - 99.0 * 1.015) < 1e-9 and cy["j_buy"] == 2,
      "sell_rebuy trailing 1.5%: sell 100, low 99 -> safety lowered to 100.485, hit on candle 2")
check(ssim(rows, trail=0.0)["coins_end"] == r0["coins_end"], "sell_rebuy trail 0 = fixed, identical")
print(f"\nall {ok} checks passed")
