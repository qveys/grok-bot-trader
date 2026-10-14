"""Independent re-computation of team_* runs from the saved OHLCV (no Vibe-Trading code)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

run = Path(sys.argv[1]); cfg = json.loads((run / "config.json").read_text())
code = cfg["codes"][0]; strat = run.name.split("_1H_")[-1]
px = pd.read_csv(run / "artifacts" / f"ohlcv_{code}.csv", parse_dates=["trade_date"], index_col="trade_date")
fee, slip, sl, tp = cfg["taker_rate"], cfg["slippage"], cfg["spot_stop_loss"], cfg["spot_take_profit"]
o, h, l, c = (px[k].to_numpy(float) for k in ("open", "high", "low", "close"))
loc = px.index.tz_localize("UTC").tz_convert("Europe/Brussels")
if strat == "team_rebound":
    chg = pd.Series(c).pct_change(24).shift(1).to_numpy()
    sig = (chg <= -0.03) & (c > o) & (c > np.r_[np.nan, h[:-1]])
else:
    cs = pd.Series(c); hs = pd.Series(h)
    sig = ((cs > hs.rolling(8).max().shift(1)) & (cs > cs.rolling(50).mean())).to_numpy()
ev0 = int(np.searchsorted(px.index, pd.Timestamp(cfg["evaluation_start_date"])))
cash = cfg["initial_cash"]; trades = []; pos = None; busy_day = None
for j in range(ev0, len(px)):            # j = bar where orders fill at the open
    t = loc[j]; i = j - 1                # decision bar = previous, closed candle
    hr = t.hour + t.minute / 60
    if pos and (hr >= 22 or t.date() != pos["day"]):           # time exit at open
        p = o[j] * (1 - slip); cash += pos["q"] * p * (1 - fee); trades.append(("time", p)); pos = None
    if busy_day is not None and (hr >= 22 or t.date() != busy_day):
        busy_day = None
    if pos is None and busy_day is None and i >= 0 and sig[i] and 15 <= hr < 17 and t.weekday() < 5:
        p = o[j] * (1 + slip); q = round(cash / (p * (1 + fee)), 6); cash -= q * p * (1 + fee)
        pos = {"q": q, "e": p, "day": t.date(), "j": j}; busy_day = t.date()
    if pos:
        st, tk = pos["e"] * (1 - sl), pos["e"] * (1 + tp); first = pos["j"] == j
        if l[j] <= st:
            p = (st if first else min(o[j], st)) * (1 - slip); cash += pos["q"] * p * (1 - fee); trades.append(("stop", p)); pos = None
        elif h[j] >= tk:
            p = (tk if first else max(o[j], tk)) * (1 - slip); cash += pos["q"] * p * (1 - fee); trades.append(("tp", p)); pos = None
if pos:
    p = c[-1] * (1 - slip); cash += pos["q"] * p * (1 - fee); trades.append(("end", p))
from collections import Counter
print("independent final", round(cash, 2), "trades", len(trades), dict(Counter(t[0] for t in trades)))
