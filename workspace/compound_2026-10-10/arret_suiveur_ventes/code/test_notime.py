"""Checks for --no-time-exit, --trail-start and sell_rebuy --dip 0 (added 2026-10-10).
Run: .venv/bin/python checks/test_notime.py  (no network; the engine part uses the cached 1h candles if present)"""
import json, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import vt_fill as F
import vt_sellrebuy as SR

ok = 0
def check(cond, msg):
    global ok
    if not cond:
        print("FAIL", msg); sys.exit(1)
    ok += 1; print("OK ", msg)

# Tuesday 2026-10-06 13:00 UTC = 15h Brussels; 12 candles -> crosses 22h and midnight Brussels
idx = pd.date_range("2026-10-06 13:00", periods=14, freq="h")
P = {"tz": "Europe/Brussels", "sess": (15, 17), "weekdays": True, "exit_hour": 22.0, "sl": 1.5, "tp": 0.0,
     "cash": 1000.0, "maker_fee": 0.0, "maker_slip": 0.0, "taker_fee": 0.0, "taker_slip": 0.0, "all_maker": True}
flat = [100, 100.3, 99.8, 100]
rows = [flat] * 13 + [[100, 100.1, 98.0, 98.2]]          # stop only on the last candle (next day 04h Brussels)
D = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
sig = np.zeros(len(D), bool); sig[0] = True
r22 = F.simulate(D, sig, 1, P, "all")
check(r22["trades"][0]["reason"] == "time_exit", "default: 22h time exit")
rno = F.simulate(D, sig, 1, {**P, "exit_hour": -1.0}, "all")
t = rno["trades"][0]
check(len(rno["trades"]) == 1 and t["reason"] == "stop_loss" and t["exit"] == str(idx[13]) and abs(t["exit_px"] - 98.5) < 1e-9,
      "no time exit: trade held overnight, closed by the stop next day at 98.5")
D2 = pd.DataFrame([flat] * 14, columns=["open", "high", "low", "close"], index=idx)
r_end = F.simulate(D2, sig, 1, {**P, "exit_hour": -1.0}, "all")
check(r_end["trades"][0]["reason"] == "end", "no time exit, nothing hit: closed at the end of the data")
for mode in ("touch", "rate"):
    r = F.simulate(D, sig, 1, {**P, "exit_hour": -1.0}, mode, rate=100.0)
    check(all(x["reason"] != "time_exit" for x in r["trades"]), f"{mode}: no time exit")

# trail start (breakeven-then-trail): entry 100 at candle 1 open
idx6 = pd.date_range("2026-10-06 13:00", periods=6, freq="h")
def df6(r): return pd.DataFrame(r, columns=["open", "high", "low", "close"], index=idx6[:len(r)])
s6 = np.zeros(6, bool); s6[0] = True
Pt = {**P, "trail": 1.0}
rows_a = [[99, 100, 98, 100], [100, 100.4, 99.6, 100.2], [100.2, 100.3, 99.35, 99.5], [99.5, 99.6, 98.0, 98.2]]
a0 = F.simulate(df6(rows_a), s6, 1, Pt, "all")["trades"][0]
a1 = F.simulate(df6(rows_a), s6, 1, {**Pt, "trail_start": 0.5}, "all")["trades"][0]
check(a0["reason"] == "trailing_stop" and abs(a0["exit_px"] - 100.4 * 0.99) < 1e-9, "trail 1% from the start: 99.396")
check(a1["reason"] == "stop_loss" and abs(a1["exit_px"] - 98.5) < 1e-9, "trail start 0.5%: peak +0.4% -> not armed, fixed stop 98.5")
rows_b = [[99, 100, 98, 100], [100, 100.6, 99.8, 100.5], [100.5, 100.55, 99.9, 99.95], [99.95, 100, 98.0, 98.2]]
b1 = F.simulate(df6(rows_b), s6, 1, {**Pt, "trail_start": 0.5}, "all")["trades"][0]
check(b1["reason"] == "trailing_stop" and abs(b1["exit_px"] - 100.0) < 1e-9 and b1["exit"] == str(idx6[2]),
      "trail start 0.5%: peak +0.6% -> armed, stop = max(99.594, entry 100) = 100 (breakeven), hit on candle 2")
check(F.simulate(df6(rows_b), s6, 1, {**Pt, "trail_start": 0.0}, "all")["final"]
      == F.simulate(df6(rows_b), s6, 1, Pt, "all")["final"], "trail start 0 = plain trail, identical")

# sell_rebuy: --dip 0 = no target; trail start mirror
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
deep = [FL, (100, 100.2, 95.0, 95.5), (95.5, 96.0, 95.2, 95.8), (95.8, 96.0, 95.5, 95.9)]
check(ssim(deep)["cycles"][0]["reason"] == "target", "sell_rebuy default: target rebuy at -3%")
c0 = ssim(deep, dip=0.0)["cycles"][0]
check(c0["reason"] == "end", "sell_rebuy --dip 0: no target, open cycle closed at the end of the data")
c1 = ssim(deep, dip=0.0, trail=0.5)["cycles"][0]
check(c1["reason"] == "trailing" and abs(c1["buy_px"] - 95.5) < 1e-9 and c1["j_buy"] == 2,
      "sell_rebuy --dip 0 --trail 0.5: level 95.475, candle 2 opens above it -> rebuy at the open 95.5")
rows_s = [FL, (100, 100.2, 99.6, 99.7), (99.7, 100.6, 99.65, 100.4), (100.4, 101.6, 100.3, 101.5)]
s_tr = ssim(rows_s, trail=1.0)["cycles"][0]
s_ts = ssim(rows_s, trail=1.0, trail_start=0.5)["cycles"][0]
check(s_tr["reason"] == "trailing" and abs(s_tr["buy_px"] - 99.6 * 1.01) < 1e-9, "sell_rebuy trail 1%: 100.596")
check(s_ts["reason"] == "safety" and abs(s_ts["buy_px"] - 101.5) < 1e-9, "sell_rebuy trail start 0.5%: low -0.4% -> not armed, safety 101.5")
rows_s2 = [FL, (100, 100.2, 99.4, 99.5), (99.5, 100.1, 99.45, 100.05), FL]
s2 = ssim(rows_s2, trail=1.0, trail_start=0.5)["cycles"][0]
check(s2["reason"] == "trailing" and abs(s2["buy_px"] - 100.0) < 1e-9, "sell_rebuy trail start: armed -> level min(100.394, sell 100) = 100")

# engine (Vibe-Trading) with --no-time-exit must match the independent replica (vt_fill 'all') - needs cached data
cache = ROOT / "home" / "cache"
if cache.exists():
    for extra in (["--tp", "0"], ["--trail", "1.5", "--tp", "0", "--trail-start", "0.5"]):
        cmd = [str(ROOT / "backtest.sh"), "run", "--pair", "ETH-EUR", "--tf", "1H", "--days", "365", "--end", "2026-10-07",
               "--strategy", "team_breakout", "--no-time-exit", "--costs", "revolutx-maker", "--fill", "touch", "--json"] + extra
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        s = json.loads(p.stdout)
        rc = s["fill_model"]["old_all_filled_replica_check"]
        check(rc["matches_engine"] and "time_exit" not in s["fill_model"]["old_all_filled_engine"]["exit_reasons"]
              and "signal" not in s["fill_model"]["old_all_filled_engine"]["exit_reasons"],
              f"engine --no-time-exit {' '.join(extra)}: replica = engine ({rc['trades']} trades), exits {s['fill_model']['old_all_filled_engine']['exit_reasons']}")
print(f"\nall {ok} checks passed")
