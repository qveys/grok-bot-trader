"""Fill model for team_rebound / team_breakout (resting limit orders may NOT fill).

Used by vt_tools.py when `--fill touch` or `--fill-rate X` is given. The Vibe-Trading engine run
(`--fill all`, old assumption: every order filled) is kept as the baseline; this module replays the
same signals candle by candle on the engine's saved OHLCV with a fill model:

  --fill all      (default) unchanged engine behaviour, every order filled (nothing here is used).
  --fill touch    entry = resting BUY limit at the signal candle's close (minus --limit-offset
                  basis points). Filled only if a later
                  candle's LOW goes strictly BELOW limit*(1 - ticks/10000) within --order-bars
                  candles (and before the exit hour, same day). Filled at the limit price (no price
                  improvement). Otherwise cancelled: no trade, no cost. One order per signal day.
                  Take-profit = resting SELL limit at entry*(1+tp), filled only if HIGH goes strictly
                  ABOVE tp*(1 + ticks/10000), at the tp price. Not checked on the fill candle itself
                  (we do not know if the high came before or after the fill) - conservative.
  --fill-rate X   prices as the old model (entry at next open, tp at tp level) but each resting order
                  (entry and take-profit) is filled with probability X %, drawn once per order
                  (seeded RNG, --seed). An entry not filled = cancelled; a tp not filled = the trade
                  ends by stop or time exit.
  Optional trailing stop (P["trail"] %, 0 = off, vt_tools --trail): stop = max(entry*(1-sl),
  highest high of COMPLETED candles since entry*(1-trail)), never goes down; the current candle's high
  only counts from the next candle (order of high/low inside a candle unknown) - conservative.
  Optional trail start (P["trail_start"] %, vt_tools --trail-start): the trailing level only counts once that
  peak is >= entry*(1+start); from then the stop is never below the entry price (breakeven-then-trail).
  exit_hour < 0 (vt_tools --no-time-exit): no time exit, a trade can last several days (stop / tp / end only).
  In both modes: stop-loss, exit-hour (time) exit and end-of-data exit are MARKET orders (taker fee +
  slippage), resting orders pay the maker fee. Stop is checked before tp in the same candle (worst case).
No LLM, no broker, no order. Pure arithmetic on public candles.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


def raw_signals(code_text: str, df: pd.DataFrame, pair: str) -> np.ndarray:
    """Entry triggers on CLOSED candles, from the exact code generated for the engine (body only)."""
    head, rest = code_text.split("        for code, df in data_map.items():", 1)
    body = rest.split("            raw = raw.fillna(0.0)", 1)[0]
    src = head + "        for code, df in data_map.items():" + body + \
        "            out[code] = raw.fillna(0.0)\n        return out\n"
    ns: dict = {}
    exec(compile(src, "<signal_raw>", "exec"), ns)  # our own generated code, no external input
    return ns["SignalEngine"]().generate({pair: df})[pair].to_numpy(float) > 0


def simulate(df: pd.DataFrame, sig: np.ndarray, ev0: int, P: dict, mode: str, rate: float = 100.0,
             seed: int = 1, ticks: float = 0.0, order_bars: int = 2) -> dict:
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    idx = pd.DatetimeIndex(df.index)
    loc = (idx.tz_localize("UTC") if idx.tz is None else idx).tz_convert(P["tz"])
    hrs = np.asarray(loc.hour + loc.minute / 60.0, float)
    days = np.asarray(loc.strftime("%Y-%m-%d"))
    wd = np.asarray(loc.weekday)
    s0, s1 = P["sess"]
    exit_h, sl, tp = P["exit_hour"], P["sl"] / 100.0, P["tp"] / 100.0
    trail = float(P.get("trail") or 0.0) / 100.0
    tstart = float(P.get("trail_start") or 0.0) / 100.0
    mf, ms, tf_, ts = P["maker_fee"], P["maker_slip"], P["taker_fee"], P["taker_slip"]
    thr = ticks / 10000.0
    rng = np.random.default_rng(seed)
    cash = float(P["cash"])
    pos = None      # open position
    pend = None     # resting entry order
    busy_day = None
    n = len(c)
    trades, orders = [], []
    eq = np.empty(n - ev0)

    def buy(j, px, maker, why_j):
        nonlocal cash, pos
        f, s = (mf, ms) if maker else (tf_, ts)
        pe = px * (1 + s)
        q = cash / (pe * (1 + f))
        fee = q * pe * f
        cash -= q * pe + fee
        pos = {"q": q, "e": pe, "e_raw": px, "peak": pe, "day": days[why_j], "j": j, "fee_in": fee, "maker_in": maker,
               "tp_ok": (mode != "rate") or (rng.random() * 100 < rate), "cost_in": q * pe + fee}

    def sell(j, px, maker, reason):
        nonlocal cash, pos
        f, s = (mf, ms) if maker else (tf_, ts)
        pe = px * (1 - s)
        gross = pos["q"] * pe
        fee = gross * f
        cash += gross - fee
        net = gross - fee - pos["cost_in"]
        trades.append({"entry": str(idx[pos["j"]]), "exit": str(idx[j]), "entry_px": pos["e"], "exit_px": pe,
                       "reason": reason, "exit_maker": maker, "fees": pos["fee_in"] + fee,
                       "net": net, "net_pct": net / pos["cost_in"] * 100})
        pos = None

    for j in range(ev0, n):
        hr, day = hrs[j], days[j]
        time_up = exit_h >= 0 and (hr >= exit_h)
        # 1. time exit at the open (market)
        if pos is not None and exit_h >= 0 and (time_up or day != pos["day"]):
            sell(j, o[j], False, "time_exit")
        if busy_day is not None and (time_up or day != busy_day):
            busy_day = None
        # 2. pending limit expires (validity window, exit hour, day change)
        if pend is not None and (j - pend["j0"] >= order_bars or time_up or day != pend["day"]):
            orders.append({**pend, "filled": False}); pend = None
        # 3. new signal on the previous closed candle -> place an order
        if pos is None and pend is None and busy_day is None and j - 1 >= 0 and sig[j - 1] \
                and (s0 < 0 or s0 <= hr < s1) and not (P["weekdays"] and wd[j] >= 5):
            busy_day = day
            if mode == "touch":
                pend = {"j0": j, "day": day, "limit": float(c[j - 1]) * (1 - P.get("offset", 0.0)), "t": str(idx[j - 1])}
            elif mode == "rate":
                ok = rng.random() * 100 < rate
                orders.append({"j0": j, "day": day, "limit": float(o[j]), "t": str(idx[j - 1]), "filled": ok})
                if ok:
                    buy(j, o[j], True, j)
            else:  # "all" replica of the engine (market at open, costs as configured for the engine)
                orders.append({"j0": j, "day": day, "limit": float(o[j]), "t": str(idx[j - 1]), "filled": True})
                buy(j, o[j], P.get("all_maker", True), j)
        # 4. resting entry fill check (touch): low strictly below limit (minus ticks)
        fill_bar = False
        if pend is not None and l[j] < pend["limit"] * (1 - thr):
            orders.append({**pend, "filled": True, "j_fill": j})
            buy(j, pend["limit"], True, j); pend = None; fill_bar = True
        # 5. stop (market) / take-profit (resting limit) on this candle
        if pos is not None:
            first = pos["j"] == j
            st, tk = pos["e"] * (1 - sl), pos["e"] * (1 + tp)
            why = "stop_loss"
            if trail > 0:
                tst = pos["peak"] * (1 - trail)
                if tstart > 0:
                    tst = max(tst, pos["e"]) if pos["peak"] >= pos["e"] * (1 + tstart) else -1.0
                if tst > st:
                    st, why = tst, "trailing_stop"
            if trail > 0 and not fill_bar:  # (touch fill candle: its high may come before the fill)
                pos["peak"] = max(pos["peak"], h[j])  # counts from the next candle
            if sl > 0 and l[j] <= st:
                sell(j, st if (first or fill_bar) else min(o[j], st), False, why)
            elif tp > 0 and not fill_bar and pos["tp_ok"]:
                if mode == "touch":
                    if h[j] > tk * (1 + thr):
                        sell(j, tk, True, "take_profit")
                elif h[j] >= tk:
                    sell(j, tk if first else max(o[j], tk), True, "take_profit")
        eq[j - ev0] = cash + (pos["q"] * c[j] * (1 - ts) * (1 - tf_) if pos is not None else 0.0)
    if pend is not None:
        orders.append({**pend, "filled": False})
    if pos is not None:
        sell(n - 1, c[n - 1], False, "end")
        eq[-1] = cash
    return {"final": cash, "trades": trades, "orders": orders, "equity": eq}


def stats(res: dict, cash0: float) -> dict:
    t, od = res["trades"], res["orders"]
    eq = res["equity"]
    peak = np.maximum.accumulate(np.r_[cash0, eq])
    mdd = float((np.r_[cash0, eq] / peak - 1).min())
    wins = [x for x in t if x["net"] > 0]
    gl = -sum(x["net"] for x in t if x["net"] <= 0)
    placed = len(od)
    filled = sum(1 for x in od if x["filled"])
    tp_hits = sum(1 for x in t if x["reason"] == "take_profit")
    return {
        "entry_orders_placed": placed, "entry_orders_filled": filled, "entry_orders_not_filled": placed - filled,
        "entry_filled_pct": round(filled / placed * 100, 1) if placed else None,
        "entry_not_filled_pct": round((placed - filled) / placed * 100, 1) if placed else None,
        "trades": len(t), "exit_reasons": dict(Counter(x["reason"] for x in t)),
        "exits_maker_tp": tp_hits, "exits_taker": len(t) - tp_hits,
        "final_value": round(res["final"], 2), "total_return_pct": round((res["final"] / cash0 - 1) * 100, 2),
        "win_rate_pct": round(len(wins) / len(t) * 100, 1) if t else None,
        "profit_factor": round(sum(x["net"] for x in wins) / gl, 3) if gl > 0 else None,
        "avg_net_per_trade": round(float(np.mean([x["net"] for x in t])), 2) if t else 0.0,
        "avg_net_pct_per_trade": round(float(np.mean([x["net_pct"] for x in t])), 3) if t else None,
        "fees_paid": round(sum(x["fees"] for x in t), 2), "max_drawdown_pct": round(mdd * 100, 2),
    }


def run_fill(a, s: dict, code_text: str, taker: tuple[float, float]) -> dict:
    """s = engine summary (baseline, all filled). Returns the fill-model block and writes files."""
    run = Path(s["run_dir"])
    cfg = json.loads((run / "config.json").read_text())
    px = pd.read_csv(run / "artifacts" / f"ohlcv_{a.pair}.csv", parse_dates=["trade_date"]).set_index("trade_date")
    px = px[["open", "high", "low", "close"] + [c for c in ("volume",) if c in px.columns]].astype(float)
    ev0 = int(np.searchsorted(px.index, pd.Timestamp(cfg["evaluation_start_date"])))
    sig = raw_signals(code_text, px, a.pair)
    P = {"tz": a.tz, "sess": a.sess, "weekdays": bool(a.weekdays), "exit_hour": float(a.exit_hour),
         "sl": a.sl, "tp": a.tp, "trail": float(getattr(a, "trail", 0.0) or 0.0),
         "trail_start": float(getattr(a, "trail_start", 0.0) or 0.0), "cash": a.cash, "maker_fee": a.fee, "maker_slip": a.slippage,
         "taker_fee": taker[0], "taker_slip": taker[1], "offset": a.limit_offset / 10000.0}
    # replica of the old model (all filled, every leg at the engine's costs) = check vs the engine
    P_all = {**P, "taker_fee": a.fee, "taker_slip": a.slippage}
    rep = stats(simulate(px, sig, ev0, P_all, "all"), a.cash)
    # old model but stop / time exits taker (isolates the fee effect from the non-fill effect)
    rep_tk = stats(simulate(px, sig, ev0, P, "all"), a.cash)
    if a.fill == "touch":
        res = simulate(px, sig, ev0, P, "touch", ticks=a.fill_ticks, order_bars=a.order_bars)
        st = stats(res, a.cash)
        spread = None
    else:
        res = simulate(px, sig, ev0, P, "rate", rate=a.fill_rate, seed=a.seed)
        st = stats(res, a.cash)
        runs = [stats(simulate(px, sig, ev0, P, "rate", rate=a.fill_rate, seed=a.seed + k), a.cash)
                for k in range(a.fill_seeds)]
        r = np.array([x["total_return_pct"] for x in runs])
        spread = {"seeds": [a.seed, a.seed + a.fill_seeds - 1], "n": len(runs),
                  "return_pct_min": round(float(r.min()), 2), "return_pct_median": round(float(np.median(r)), 2),
                  "return_pct_max": round(float(r.max()), 2),
                  "share_seeds_profitable": round(float((r > 0).mean()), 3),
                  "share_seeds_beating_hold": round(float((r > s["buy_hold_return_pct"]).mean()), 3)}
    bh = s["buy_hold_return_pct"]
    block = {
        "mode": a.fill, "fill_rate_pct": a.fill_rate if a.fill == "rate" else None,
        "seed": a.seed if a.fill == "rate" else None,
        "fill_ticks_bps": a.fill_ticks if a.fill == "touch" else None,
        "order_valid_bars": a.order_bars if a.fill == "touch" else None,
        "limit_offset_bps": a.limit_offset if a.fill == "touch" else None,
        "fees": {"resting_limit_maker": a.fee, "maker_slippage": a.slippage,
                 "market_taker_stop_time_end": taker[0], "taker_slippage": taker[1]},
        "result": st,
        "seed_spread": spread,
        "old_all_filled_engine": {k: s[k] for k in ("trades", "total_return_pct", "final_value", "win_rate_pct",
                                                     "profit_factor", "fees_paid", "max_drawdown_pct", "exit_reasons")},
        "old_all_filled_replica_check": {"total_return_pct": rep["total_return_pct"], "trades": rep["trades"],
                                         "matches_engine": abs(rep["final_value"] - s["final_value"]) < 0.5
                                         and rep["trades"] == s["trades"]},
        "all_filled_but_stop_time_taker": {k: rep_tk[k] for k in ("trades", "total_return_pct", "fees_paid")},
        "buy_hold_return_pct": bh,
        "verdict_vs_keeping_coins": "MIEUX que garder" if st["total_return_pct"] > bh else "MOINS BIEN que garder",
        "profitable_after_costs": st["total_return_pct"] > 0,
    }
    pd.DataFrame(res["trades"]).to_csv(run / "artifacts" / f"fill_{a.fill}_trades.csv", index=False)
    pd.DataFrame(res["orders"]).to_csv(run / "artifacts" / f"fill_{a.fill}_orders.csv", index=False)
    (run / f"fill_{a.fill}_summary.json").write_text(json.dumps(block, indent=1, default=str), encoding="utf-8")
    return block
