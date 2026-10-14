#!/usr/bin/env python3
"""D-018 'vendre haut, racheter plus bas' (sell first, rebuy lower) - own candle-by-candle spot simulator.

Used by vt_tools.py (`backtest.sh run|robust --strategy sell_rebuy`). The Vibe-Trading crypto engine is
long-only, so this mode does NOT use it: it is a small, self-contained loop over OHLC candles.

Rules (spot, no borrowing: we only ever sell coins we hold):
  - start holding N coins (--coins, or --eur converted at the first evaluated candle open)
  - SELL signal on a CLOSED candle: close rose >= --rise % vs the close --rise-hours ago AND close is below
    its --trend-ma hour average (0 = no trend filter); optional --session / --weekdays filter on the
    decision time (= candle close = next candle open), same convention as the other strategies
  - the sell is a limit order (maker fee): --sell-fill open  -> filled at the next candle open (default)
                                           --sell-fill close -> limit at the signal close, filled only if
                                              the next candle trades at or above it (conservative)
  - target rebuy: resting limit at sell * (1 - dip) (maker fee), filled at that price when low <= it
  - safety rebuy: market buy when high >= sell * (1 + stop) (taker fee + slippage), at max(open, stop)
  - optional --trail N (mirror of a trailing stop, 0 = off): the safety level is
    min(sell * (1 + stop), lowest low since the sell * (1 + trail)) and never goes up; the lowest low only
    counts COMPLETED candles (the current candle's low is added after its high was checked) - conservative.
    Rebuy reason "trailing" when the lowered level (below the fixed safety level) is hit.
  - optional --trail-start N (with --trail): the lowered level only counts once the lowest low reaches
    sell * (1 - N%); from then the safety level is never above the sell price (breakeven-then-trail mirror)
  - --dip 0 = no target rebuy: the cycle ends only at the safety / trailing level (or --max-hours, end of data)
  - optional --max-hours: market rebuy at the open of the first candle >= N hours after the sell (taker)
  - same candle touches target AND safety -> safety assumed (worse case). In --sell-fill close mode the
    target is never credited on the fill candle itself (order of events unknown).
  - one cycle at a time; an open cycle at the end of the data is closed by a market rebuy at the last close
No LLM, no broker, no order. Results are measured in coins (vs simply holding) and in EUR.
"""
from __future__ import annotations

import copy
import datetime as dt
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

# Limit (maker) fee per preset; market (taker) fee + slippage come from vt_tools.COSTS.
MAKER_FEE = {"revolutx": 0.0, "revolutx-maker": 0.0, "flat01": 0.001}
# Wallet swaps (MetaMask on Arbitrum, measured by PM-Risk 2026-10-08): (fee per swap, network fee EUR per swap).
# Every leg (sell and rebuy) is a swap at that cost; no maker/taker difference; price = market price.
SWAP_COSTS = {"uniswap": (0.0005, 0.03), "metamask-swap": (0.00875, 0.03)}
DEFAULT_GRID = "rise=2,3,5;dip=2,3,5;stop=1,1.5,3"
REASON_FR = {"target": "achat au prix visé", "safety": "achat de sécurité", "trailing": "achat de sécurité (seuil suiveur)", "timeout": "achat après le délai",
             "end": "achat forcé (fin des données)"}
TZ_REPORT = "Europe/Brussels"


# ───────────────────────── signal ─────────────────────────
def time_filter(index, tf_hours: float, sess=(-1.0, -1.0), weekdays: bool = False, tz: str = TZ_REPORT) -> np.ndarray:
    """True where the decision time (candle close = next open, local tz) passes --session / --weekdays."""
    idx = pd.DatetimeIndex(index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    t = (idx + pd.Timedelta(minutes=int(round(tf_hours * 60)))).tz_convert(tz)
    hours = np.asarray(t.hour + t.minute / 60.0, dtype=float)
    ok = np.ones(len(idx), dtype=bool)
    if sess[0] >= 0:
        ok &= (hours >= sess[0]) & (hours < sess[1])
    if weekdays:
        ok &= np.asarray(t.weekday) < 5
    return ok


def signals(df: pd.DataFrame, P: dict) -> tuple[np.ndarray, np.ndarray]:
    """(sell signal on candle close, time-eligible mask)."""
    c = df["close"].astype(float)
    rb = max(1, int(round(P["rise_hours"] / P["tf_hours"])))
    chg = c / c.shift(rb) - 1.0
    raw = (chg >= P["rise"] / 100.0 - 1e-12) & chg.notna()
    if P["trend_ma"] > 0:
        tb = max(2, int(round(P["trend_ma"] / P["tf_hours"])))
        ma = c.rolling(tb, min_periods=tb).mean()
        raw &= ma.notna() & (c < ma)
    if P.get("min_range24", 0.0) > 0:  # --min-range24: sell signal only when last-24h range / close > N %
        rb24 = max(1, int(round(24 / P["tf_hours"])))
        rng = (df["high"].astype(float).rolling(rb24, min_periods=rb24).max()
               - df["low"].astype(float).rolling(rb24, min_periods=rb24).min()) / c
        raw &= rng.notna() & (rng > P["min_range24"] / 100.0)
    elig = time_filter(df.index, P["tf_hours"], P["sess"], P["weekdays"], P["tz"])
    return raw.to_numpy(dtype=bool) & elig, elig


# ───────────────────────── simulator ─────────────────────────
def simulate(o, h, l, c, sig, start: int, coins0: float, P: dict, keep_path: bool = True) -> dict:
    """Candle-by-candle loop. Returns final coins, cycles (dicts with bar indices) and coin-equivalent path."""
    n = len(c)
    coins, cyc, cycles, unfilled, sig_ignored = float(coins0), None, [], 0, 0
    path = np.empty(n - start) if keep_path else None
    dip, stp, mh, tfh = P["dip"] / 100.0, P["stop"] / 100.0, float(P["max_hours"] or 0), P["tf_hours"]
    trail = float(P.get("trail") or 0.0) / 100.0
    tstart = float(P.get("trail_start") or 0.0) / 100.0
    mf, ms, tf_, ts = P["maker_fee"], P["maker_slip"], P["taker_fee"], P["taker_slip"]
    fx = float(P.get("fixed_fee_eur") or 0.0)  # fixed network fee per swap (EUR), on every leg
    chunk, close_mode = P["chunk"] / 100.0, P["sell_fill"] == "close"
    # --fill touch: a resting limit fills only if price trades strictly THROUGH it (by fill_ticks bp)
    touch = P.get("fill") == "touch"
    thr = float(P.get("fill_ticks") or 0.0) / 10000.0

    def rebuy(j, px, taker, reason):
        nonlocal coins, cyc
        ff, ss = (tf_, ts) if taker else (mf, ms)
        pe = px * (1 + ss)
        spend = max(0.0, cyc["eur"] - fx)
        qb = spend / (pe * (1 + ff))
        rec = dict(cyc)
        rec.update(j_buy=j, buy_px=float(px), buy_px_eff=float(pe), q_bought=qb, reason=reason, taker_buy=taker,
                   fee_buy=qb * pe * ff + min(fx, cyc["eur"]), slip_buy=qb * px * ss)
        rec["coin_gain"] = qb - rec["q"]
        rec["coin_gain_pct"] = (qb / rec["q"] - 1) * 100
        notional = rec["q"] * rec["sell_px"]
        rec["fees_eur"] = rec["fee_sell"] + rec["fee_buy"]
        rec["slip_eur"] = rec["slip_sell"] + rec["slip_buy"]
        rec["cost_pct"] = (rec["fees_eur"] + rec["slip_eur"]) / notional * 100
        rec["gross_pct"] = (rec["sell_px"] / px - 1) * 100
        rec["eur_gain"] = rec["coin_gain"] * px
        rec["hours"] = (j - rec["j_sell"]) * tfh
        coins += qb
        cycles.append(rec)
        cyc = None

    for j in range(start, n):
        if j - 1 >= start and sig[j - 1]:
            if cyc is not None:
                sig_ignored += 1
            elif coins > 0:
                q = coins * chunk
                px = c[j - 1] if close_mode else o[j]
                if (not close_mode) or (h[j] > px * (1 + thr) if touch else h[j] >= px):
                    gross = q * px * (1 - ms)
                    fee = gross * mf
                    cyc = dict(j_sell=j, sell_px=float(px), q=q, eur=max(0.0, gross - fee - fx), fee_sell=fee + min(fx, gross - fee),
                               slip_sell=q * px * ms,
                               target=px * (1 - dip), stop=px * (1 + stp), trough=float(px))
                    coins -= q
                else:
                    unfilled += 1
        if cyc is not None:
            first = cyc["j_sell"] == j
            if (not first) and mh > 0 and (j - cyc["j_sell"]) * tfh >= mh - 1e-9:
                rebuy(j, o[j], True, "timeout")
            else:
                stop_lvl, why = cyc["stop"], "safety"
                if trail > 0:
                    tl = cyc["trough"] * (1 + trail)
                    if tstart > 0:
                        tl = min(tl, cyc["sell_px"]) if cyc["trough"] <= cyc["sell_px"] * (1 - tstart) else float("inf")
                    if tl < stop_lvl:
                        stop_lvl, why = tl, "trailing"
                    if not (first and close_mode):  # close mode: the fill candle's low may come before the sell
                        cyc["trough"] = min(cyc["trough"], l[j])  # counts from the next candle
                hit_stop = h[j] >= stop_lvl
                hit_tgt = (l[j] < cyc["target"] * (1 - thr) if touch else l[j] <= cyc["target"]) \
                    and not (first and close_mode) and dip > 0
                if hit_stop:  # also when both are touched in the same candle: worse case first
                    rebuy(j, max(o[j], stop_lvl), True, why)
                elif hit_tgt:
                    rebuy(j, cyc["target"], False, "target")
        if keep_path:
            path[j - start] = coins + (max(0.0, cyc["eur"] - fx) / (c[j] * (1 + ts) * (1 + tf_)) if cyc is not None else 0.0)
    if cyc is not None:
        rebuy(n - 1, c[n - 1], True, "end")
        if keep_path:
            path[-1] = coins
    return {"coins_end": coins, "cycles": cycles, "path": path, "unfilled_sells": unfilled,
            "signals_ignored_in_cycle": sig_ignored}


# ───────────────────────── helpers ─────────────────────────
def params_from_args(a) -> dict:
    from vt_tools import TF_HOURS
    mf = MAKER_FEE.get(a.costs, a.fee) if a.maker_fee is None else a.maker_fee
    tf_, ts, ms = a.fee, a.slippage, 0.0  # market orders: --costs preset (or --fee / --slippage overrides)
    swap = SWAP_COSTS.get(a.costs)
    fixed = float(a.fixed_fee_eur) if getattr(a, "fixed_fee_eur", None) is not None else (swap[1] if swap else 0.0)
    if swap or getattr(a, "fee_pct", None) is not None:
        # wallet swap mode: same % fee on both legs (sell + rebuy), slippage only if --slippage was given
        mf = tf_ = (a.fee_pct / 100.0) if getattr(a, "fee_pct", None) is not None else swap[0]
        ms = ts = a.slippage if getattr(a, "slippage_given", False) else 0.0
    return {"rise": float(a.rise), "rise_hours": float(a.rise_hours), "trend_ma": float(a.trend_ma),
            "dip": float(a.dip), "stop": float(a.stop), "trail": float(getattr(a, "trail", 0.0) or 0.0),
            "trail_start": float(getattr(a, "trail_start", 0.0) or 0.0),
            "max_hours": float(a.max_hours or 0),
            "chunk": float(a.chunk), "sell_fill": a.sell_fill, "sess": tuple(a.sess), "weekdays": bool(a.weekdays),
            "tz": a.tz, "tf_hours": TF_HOURS[a.tf], "maker_fee": float(mf), "maker_slip": float(ms),
            "taker_fee": float(tf_), "taker_slip": float(ts), "fixed_fee_eur": fixed,
            "swap_mode": bool(swap or getattr(a, "fee_pct", None) is not None),
            "fill": getattr(a, "fill", "all"), "fill_ticks": float(getattr(a, "fill_ticks", 0.0) or 0.0),
            "min_range24": float(getattr(a, "min_range24", 0.0) or 0.0)}


def warmup_bars(a, tf_hours: float) -> int:
    return max(int(math.ceil(a.trend_ma / tf_hours)) if a.trend_ma > 0 else 0,
               int(math.ceil(a.rise_hours / tf_hours))) + 10


def ts_utc(index, j) -> str:
    return str(pd.Timestamp(index[j]))[:16]


def ts_local(index, j, tz=TZ_REPORT) -> str:
    return pd.Timestamp(index[j]).tz_localize("UTC").tz_convert(tz).strftime("%d/%m/%Y %Hh%M")


def worst_runs(cycles: list[dict]) -> dict:
    longest, best_bad, cur, cur_start = 0, None, [], None
    runs = []
    for k, cy in enumerate(cycles + [None]):
        if cy is not None and cy["coin_gain"] <= 0:
            cur.append(k)
        elif cur:
            runs.append(list(cur)); cur = []
    for r in runs:
        mult = float(np.prod([1 + cycles[k]["coin_gain_pct"] / 100 for k in r]))
        longest = max(longest, len(r))
        if best_bad is None or mult < best_bad[0]:
            best_bad = (mult, r)
    return {"longest_losing_streak": longest,
            "worst_streak": None if best_bad is None else {
                "losses_in_a_row": len(best_bad[1]), "coin_change_pct": round((best_bad[0] - 1) * 100, 3),
                "from_k": best_bad[1][0], "to_k": best_bad[1][-1]}}


def summarize(df: pd.DataFrame, start: int, coins0: float, res: dict, P: dict, sig: np.ndarray) -> dict:
    o, c, idx = df["open"].to_numpy(float), df["close"].to_numpy(float), df.index
    cy = res["cycles"]
    p0, plast = float(o[start]), float(c[-1])
    coins_end = res["coins_end"]
    gains = np.array([x["coin_gain_pct"] for x in cy])
    wins = [x for x in cy if x["coin_gain"] > 0]
    losses = [x for x in cy if x["coin_gain"] <= 0]
    costs = np.array([x["cost_pct"] for x in cy])
    fees = sum(x["fees_eur"] for x in cy)
    slip = sum(x["slip_eur"] for x in cy)
    path = res["path"]
    eq = np.concatenate([[coins0], path])
    mdd = float((eq / np.maximum.accumulate(eq) - 1).min())
    reasons = {}
    for x in cy:
        reasons[x["reason"]] = reasons.get(x["reason"], 0) + 1
    wr = worst_runs(cy)
    if wr["worst_streak"]:
        w = wr["worst_streak"]
        w["from"] = ts_utc(idx, cy[w.pop("from_k")]["j_sell"])
        w["to"] = ts_utc(idx, cy[w.pop("to_k")]["j_buy"])
    avg_net = float(gains.mean()) if len(cy) else None
    avg_cost = float(costs.mean()) if len(cy) else None
    fx_pct = float(P.get("fixed_fee_eur") or 0.0) / (coins0 * P["chunk"] / 100 * p0)  # per leg, vs first position
    rt_maker = 2 * (P["maker_fee"] + P["maker_slip"] + fx_pct)
    rt_safety = P["maker_fee"] + P["maker_slip"] + P["taker_fee"] + P["taker_slip"] + 2 * fx_pct
    g_t, l_s = P["dip"] - rt_maker * 100, P["stop"] + rt_safety * 100
    s = {
        "coins_start": coins0, "coins_end": coins_end,
        "coin_gain_vs_hold": coins_end - coins0, "coin_gain_vs_hold_pct": round((coins_end / coins0 - 1) * 100, 3),
        "first_price": p0, "last_price": plast,
        "eur_start": round(coins0 * p0, 4),
        "eur_end_strategy": round(coins_end * plast, 4), "eur_end_hold": round(coins0 * plast, 4),
        "eur_gain_vs_hold": round((coins_end - coins0) * plast, 4),
        "eur_return_strategy_pct": round((coins_end * plast / (coins0 * p0) - 1) * 100, 2),
        "eur_return_hold_pct": round((plast / p0 - 1) * 100, 2),
        "cycles": len(cy), "wins": len(wins), "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(cy) * 100, 1) if cy else None,
        "avg_net_coin_pct_per_cycle": None if avg_net is None else round(avg_net, 3),
        "avg_win_coin_pct": round(float(np.mean([x["coin_gain_pct"] for x in wins])), 3) if wins else None,
        "avg_loss_coin_pct": round(float(np.mean([x["coin_gain_pct"] for x in losses])), 3) if losses else None,
        "avg_win_eur": round(float(np.mean([x["eur_gain"] for x in wins])), 4) if wins else None,
        "avg_loss_eur": round(float(np.mean([x["eur_gain"] for x in losses])), 4) if losses else None,
        "best_cycle_coin_pct": round(float(gains.max()), 3) if cy else None,
        "worst_cycle_coin_pct": round(float(gains.min()), 3) if cy else None,
        "worst_run": wr,
        "max_drawdown_coins_pct": round(mdd * 100, 3),
        "rebuy_reasons": reasons,
        "avg_hours_out_of_market": round(float(np.mean([x["hours"] for x in cy])), 1) if cy else None,
        "fees_paid_eur": round(fees, 4), "slippage_cost_eur": round(slip, 4),
        "fees_paid_coins_approx": sum(x["fees_eur"] / x["buy_px_eff"] for x in cy),
        "avg_cost_pct_per_cycle": None if avg_cost is None else round(avg_cost, 4),
        "signals": int(sig[start:].sum()), "signals_ignored_in_cycle": res["signals_ignored_in_cycle"],
        "unfilled_sells": res["unfilled_sells"],
        "team_checks": {
            "expectancy_ex_ante": {"target_gain_pct": P["dip"], "target_cycle_cost_pct": round(rt_maker * 100, 3),
                                   "safety_cycle_cost_pct": round(rt_safety * 100, 3),
                                   "ok": P["dip"] / 100 >= 3 * rt_safety,
                                   "breakeven_win_rate_pct": round(l_s / (g_t + l_s) * 100, 1) if g_t + l_s > 0 else None},
            "realized_avg_net_vs_3x_cost": None if not cy else {
                "avg_net_pct": round(avg_net, 3), "three_x_avg_cost_pct": round(3 * avg_cost, 3),
                "ok": avg_net >= 3 * avg_cost and avg_net > 0},
            "avg_win_vs_3x_cost": None if not wins else {
                "avg_win_pct": round(float(np.mean([x["coin_gain_pct"] for x in wins])), 3),
                "three_x_avg_cost_pct": round(3 * avg_cost, 3),
                "ok": float(np.mean([x["coin_gain_pct"] for x in wins])) >= 3 * avg_cost},
            "beats_hold_in_coins": bool(coins_end > coins0),
            "enough_cycles_20": len(cy) >= 20,
        },
    }
    return s


def cycles_table(df, cycles) -> list[dict]:
    idx = df.index
    return [{"sell_time_utc": ts_utc(idx, x["j_sell"]), "sell_px": round(x["sell_px"], 6), "coins_sold": x["q"],
             "rebuy_time_utc": ts_utc(idx, x["j_buy"]), "rebuy_px": round(x["buy_px"], 6),
             "rebuy_px_with_slippage": round(x["buy_px_eff"], 6), "coins_bought": x["q_bought"],
             "reason": x["reason"], "coin_gain": x["coin_gain"], "coin_gain_pct": round(x["coin_gain_pct"], 4),
             "eur_gain": round(x["eur_gain"], 6), "fees_eur": round(x["fees_eur"], 6),
             "slippage_eur": round(x["slip_eur"], 6), "cost_pct": round(x["cost_pct"], 4),
             "hours": x["hours"]} for x in cycles]


# ───────────────────────── run ─────────────────────────
def prepare(a, df: pd.DataFrame, start_ts: pd.Timestamp):
    df = df[["open", "high", "low", "close"]].astype(float).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    start = int(np.searchsorted(df.index, start_ts))
    if start >= len(df) - 2:
        raise ValueError("not enough candles after the start date")
    P = params_from_args(a)
    coins0 = float(a.coins) if a.coins else float(a.eur if a.eur else 25.0) / float(df["open"].iloc[start])
    return df, start, P, coins0


def run_one(df, start, P, coins0) -> tuple[dict, dict, np.ndarray]:
    sig, elig = signals(df, P)
    res = simulate(df["open"].to_numpy(float), df["high"].to_numpy(float), df["low"].to_numpy(float),
                   df["close"].to_numpy(float), sig, start, coins0, P)
    return summarize(df, start, coins0, res, P, sig), res, elig


def new_run_dir(runs_dir: Path, a, tag: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    d = runs_dir / f"{stamp}_{a.pair}_{a.tf}_sell_rebuy{tag}"
    (d / "artifacts").mkdir(parents=True, exist_ok=False)
    return d


def header(a, df, start, P, coins0, end) -> dict:
    return {
        "status": "ok", "engine": "vt_sellrebuy.py own candle-by-candle simulator (not the Vibe-Trading engine)",
        "pair": a.pair, "coin": a.pair.split("-")[0], "timeframe": a.tf, "source": a.source, "strategy": "sell_rebuy",
        "idea": "D-018 vendre haut, racheter plus bas",
        "params": {k: P[k] for k in ("rise", "rise_hours", "trend_ma", "dip", "stop", "max_hours", "chunk", "sell_fill",
                                     "fill", "fill_ticks") + (("trail",) if P.get("trail") else ()) + (("trail_start",) if P.get("trail_start") else ())},
        "entries": {"session": a.session, "tz": a.tz if a.session else None, "weekdays_only": bool(a.weekdays),
                    **({"min_range24_pct": P["min_range24"]} if P.get("min_range24", 0.0) else {})},
        "period": [str(df.index[start]), str(df.index[-1])], "times": "UTC", "bars": int(len(df) - start),
        "costs": {"profile": a.costs + ("+custom" if (getattr(a, "fee_pct", None) is not None
                                                       or getattr(a, "fixed_fee_eur", None) is not None) else ""),
                  "limit_order_fee": P["maker_fee"], "limit_order_slippage": P["maker_slip"],
                  "market_order_fee": P["taker_fee"], "market_order_slippage": P["taker_slip"],
                  "fixed_fee_eur_per_swap": P["fixed_fee_eur"],
                  "note": ("wallet swap: every leg (sell, rebuy) pays the same % fee + the fixed network fee"
                           if P["swap_mode"] else
                           "sell + target rebuy = limit (maker); safety / time-out / end rebuy = market (taker)")},
        "start_holding": {"coins": coins0, "eur_at_first_price": round(coins0 * float(df["open"].iloc[start]), 4),
                          "given_as": "coins" if a.coins else "eur"},
    }


def warnings_for(df, start, start_ts, end, s) -> list[str]:
    w = []
    if df.index[start] > start_ts + dt.timedelta(days=2):
        w.append(f"data only starts {df.index[start]} (requested {start_ts.date()}); period shorter than asked")
    if end.date() >= dt.date.today():
        w.append("end date is today or later: last candle may be incomplete")
    gaps = int((pd.Series(df.index[start:]).diff().dt.total_seconds().dropna() > 3 * 3600 * 1.01).sum())
    if gaps:
        w.append(f"{gaps} gaps longer than 3 candles in the data")
    if s["cycles"] == 0:
        w.append("no cycle in period")
    if s.get("rebuy_reasons", {}).get("end"):
        w.append("last cycle was still open at the end: closed by a market rebuy at the last close")
    return w


def run(a, df_raw: pd.DataFrame, start_ts, end, runs_dir: Path, tag: str = "") -> dict:
    df, start, P, coins0 = prepare(a, df_raw, start_ts)
    s_core, res, _ = run_one(df, start, P, coins0)
    out = header(a, df, start, P, coins0, end)
    out.update(s_core)
    out["warnings"] = warnings_for(df, start, start_ts, end, s_core)
    d = new_run_dir(runs_dir, a, tag)
    cyc = cycles_table(df, res["cycles"])
    out["run_dir"] = str(d)
    out["report_fr"] = str(d / "rapport_fr.md")
    out["cycles_file"] = str(d / "artifacts" / "cycles.csv")
    out["last_cycles"] = cyc[-5:]
    (d / "config.json").write_text(json.dumps({"strategy": "sell_rebuy", "pair": a.pair, "tf": a.tf, "source": a.source,
                                               "start": str(start_ts.date()), "end": str(end.date()), "params": P,
                                               "coins0": coins0, "costs": a.costs}, indent=1, default=str))
    df.to_csv(d / "artifacts" / f"ohlcv_{a.pair}.csv", index_label="trade_date")
    pd.DataFrame(cyc).to_csv(d / "artifacts" / "cycles.csv", index=False)
    pd.DataFrame({"timestamp": df.index[start:], "coins_equivalent": res["path"],
                  "close": df["close"].to_numpy()[start:]}).to_csv(d / "artifacts" / "coins.csv", index=False)
    full = dict(out, cycles_list=cyc)
    (d / "summary.json").write_text(json.dumps(full, indent=1, default=str), encoding="utf-8")
    (d / "rapport_fr.md").write_text(report_fr(out), encoding="utf-8")
    return out


# ───────────────────────── robust ─────────────────────────
def _bar_returns(path: np.ndarray, coins0: float) -> np.ndarray:
    prev = np.concatenate([[coins0], path[:-1]])
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(prev > 0, path / np.where(prev > 0, prev, 1.0) - 1.0, 0.0)


def robust(a, df_raw, start_ts, end, runs_dir: Path, grid: dict, n_sims: int, wf_windows: int) -> dict:
    df, start, P, coins0 = prepare(a, df_raw, start_ts)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    base, res, elig = run_one(df, start, P, coins0)
    sig, _ = signals(df, P)
    idx = df.index
    nb = len(df) - start
    out = header(a, df, start, P, coins0, end)
    out["base_result"] = {k: base[k] for k in ("cycles", "win_rate_pct", "coin_gain_vs_hold_pct", "eur_gain_vs_hold",
                                               "avg_net_coin_pct_per_cycle", "max_drawdown_coins_pct", "fees_paid_eur",
                                               "eur_return_hold_pct")}
    gains = np.array([x["coin_gain_pct"] for x in res["cycles"]])
    rng = np.random.default_rng(42)

    # 1. bootstrap of the average result per cycle (coins %)
    if len(gains) >= 5:
        boots = np.array([rng.choice(gains, len(gains)).mean() for _ in range(n_sims)])
        out["bootstrap_avg_per_cycle"] = {"mean_coin_pct": round(float(gains.mean()), 3),
                                          "ci95": [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)],
                                          "prob_mean_positive": round(float((boots > 0).mean()), 3), "n_sims": n_sims}
    else:
        out["bootstrap_avg_per_cycle"] = {"skipped": f"moins de 5 tours ({len(gains)}) : pas de calcul"}

    # 2a. Monte Carlo: shuffle the order of the cycles -> how bad could the worst fall in coins get?
    if len(gains) >= 5:
        mdds = []
        for _ in range(n_sims):
            g = rng.permutation(gains)
            eq = np.concatenate([[1.0], np.cumprod(1 + g / 100)])
            mdds.append((eq / np.maximum.accumulate(eq) - 1).min() * 100)
        mdds = np.array(mdds)
        out["monte_carlo_order"] = {"actual_max_drop_coins_pct": base["max_drawdown_coins_pct"],
                                    "median_max_drop_coins_pct": round(float(np.median(mdds)), 3),
                                    "bad_case_5pct_max_drop_coins_pct": round(float(np.percentile(mdds, 5)), 3)}
    else:
        out["monte_carlo_order"] = {"skipped": "moins de 5 tours"}

    # 2b. Monte Carlo: random sell times (same number of sells as the rule, same hours filter, same rebuy rules)
    pool = np.where(elig[start:len(df) - 1])[0] + start
    k = len(res["cycles"])
    if k > 0 and len(pool) > k:
        rand = []
        for _ in range(n_sims):
            s2 = np.zeros(len(df), dtype=bool)
            s2[rng.choice(pool, k, replace=False)] = True
            rand.append((simulate(o, h, l, c, s2, start, coins0, P, keep_path=False)["coins_end"] / coins0 - 1) * 100)
        rand = np.array(rand)
        act = base["coin_gain_vs_hold_pct"]
        out["monte_carlo_random_timing"] = {
            "n_sims": n_sims, "random_sells_per_sim": k, "actual_coin_gain_pct": act,
            "random_median_coin_gain_pct": round(float(np.median(rand)), 3),
            "random_5_95_pct": [round(float(np.percentile(rand, 5)), 3), round(float(np.percentile(rand, 95)), 3)],
            "p_value": round(float((1 + (rand >= act - 1e-12).sum()) / (1 + n_sims)), 4)}
    else:
        out["monte_carlo_random_timing"] = {"skipped": "pas de signal de vente : rien à comparer"}

    # 3. walk-forward windows (fixed parameters)
    path = res["path"]
    cuts = np.linspace(0, nb, wf_windows + 1).astype(int)
    rows = []
    sells = np.array([x["j_sell"] - start for x in res["cycles"]], dtype=int)
    for w in range(wf_windows):
        a0, a1 = cuts[w], cuts[w + 1]
        v0 = coins0 if a0 == 0 else path[a0 - 1]
        r = path[a1 - 1] / v0 - 1
        n_c = int(((sells >= a0) & (sells < a1)).sum())
        rows.append({"start": str(idx[start + a0])[:10], "end": str(idx[start + a1 - 1])[:10],
                     "coin_change_pct": round(r * 100, 3), "cycles_started": n_c})
    out["walk_forward_windows"] = {"windows": rows,
                                   "windows_with_gain": sum(1 for r in rows if r["coin_change_pct"] > 0),
                                   "windows_with_loss": sum(1 for r in rows if r["coin_change_pct"] < 0),
                                   "windows_without_sell": sum(1 for r in rows if r["cycles_started"] == 0),
                                   "n_windows": wf_windows}

    # 4. parameter grid -> share profitable, walk-forward optimisation, PBO
    combos = []
    for vals in itertools.product(*grid.values()) if grid else []:
        b = copy.copy(a)
        for kk, v in zip(grid.keys(), vals):
            setattr(b, kk, v)
        combos.append((dict(zip(grid.keys(), vals)), params_from_args(b)))
    table, R = [], {}
    for cdict, P2 in combos:
        s2, _ = signals(df, P2)
        r2 = simulate(o, h, l, c, s2, start, coins0, P2)
        key = json.dumps(cdict, sort_keys=True)
        R[key] = _bar_returns(r2["path"], coins0)
        wins = sum(1 for x in r2["cycles"] if x["coin_gain"] > 0)
        table.append({"params": cdict, "coin_gain_pct": round((r2["coins_end"] / coins0 - 1) * 100, 3),
                      "cycles": len(r2["cycles"]),
                      "win_rate_pct": round(wins / len(r2["cycles"]) * 100, 1) if r2["cycles"] else None})
    table.sort(key=lambda x: -x["coin_gain_pct"])
    out["grid"] = {"params": grid, "n_trials": len(table), "results": table,
                   "share_of_variants_beating_hold": round(sum(1 for t in table if t["coin_gain_pct"] > 0) / len(table), 3) if table else None}
    if len(R) >= 2:
        Rdf = pd.DataFrame(R, index=idx[start:])
        blocks = np.array_split(np.arange(nb), wf_windows + 1)
        folds, oos, oos_base = [], [], []
        base_r = _bar_returns(path, coins0)
        for f in range(1, len(blocks)):
            tr = np.concatenate(blocks[:f]); te = blocks[f]
            score = {kk: float(np.prod(1 + Rdf[kk].to_numpy()[tr]) - 1) for kk in Rdf.columns}
            best = max(score, key=score.get)
            seg = Rdf[best].to_numpy()[te]
            oos.append(seg)
            oos_base.append(base_r[te])
            folds.append({"test_from": str(idx[start + te[0]])[:16], "test_to": str(idx[start + te[-1]])[:16],
                          "chosen_params": json.loads(best), "oos_coin_change_pct": round((np.prod(1 + seg) - 1) * 100, 3)})
        allo = np.concatenate(oos)
        out["walk_forward_optimisation"] = {
            "folds": folds, "oos_coin_change_pct": round((np.prod(1 + allo) - 1) * 100, 3),
            "default_params_same_period_pct": round((np.prod(1 + np.concatenate(oos_base)) - 1) * 100, 3) if oos_base else None,
            "hold_same_period_pct": 0.0,
            "note": "params chosen on the past blocks only (best coin gain), tested on the next block; no purge (approximation)"}
        try:
            import sys
            from vt_tools import ROOT
            sys.path.insert(0, str(ROOT / ".venv"))
            from src.quantlib.multipletesting import probability_of_backtest_overfitting
            keep = [kk for kk in Rdf.columns if Rdf[kk].std() > 0]
            n_splits = 16 if nb >= 16 * 20 else (8 if nb >= 8 * 4 else 4)
            pbo = probability_of_backtest_overfitting(Rdf[keep], n_splits=n_splits)
            out["pbo_cscv"] = {"pbo": round(float(pbo.pbo), 4), "n_splits": n_splits, "n_strategies": len(keep),
                               "n_combinations": int(len(pbo.logits))}
        except Exception as exc:  # noqa: BLE001
            out["pbo_cscv"] = {"error": str(exc)}
    out["skipped_checks"] = {
        "engine_validation_vibe_trading": "non fait : ce mode n'utilise pas le moteur Vibe-Trading (il n'achète que d'abord). "
                                          "Remplacé par le tirage au hasard des moments de vente et le mélange de l'ordre des tours.",
        "deflated_sharpe": "non fait : le résultat se compte en pièces gagnées, pas en euros ; ce calcul ne s'applique pas bien ici.",
        "cpcv": "non fait : le découpage par blocs (walk-forward) et le PBO suffisent pour ce mode simple."}
    out["verdict"] = verdict(base, out)
    d = new_run_dir(runs_dir, a, "_robust")
    out["run_dir"] = str(d)
    out["report_fr"] = str(d / "rapport_fr.md")
    df.to_csv(d / "artifacts" / f"ohlcv_{a.pair}.csv", index_label="trade_date")
    pd.DataFrame(cycles_table(df, res["cycles"])).to_csv(d / "artifacts" / "cycles.csv", index=False)
    pd.DataFrame({"timestamp": idx[start:], "coins_equivalent": path, "close": c[start:]}).to_csv(d / "artifacts" / "coins.csv", index=False)
    (d / "summary.json").write_text(json.dumps(dict(out, base_full=base), indent=1, default=str), encoding="utf-8")
    base_out = header(a, df, start, P, coins0, end); base_out.update(base)
    base_out["warnings"] = warnings_for(df, start, start_ts, end, base)
    base_out["run_dir"] = str(d)
    (d / "rapport_fr.md").write_text(report_fr(base_out, out), encoding="utf-8")
    return out


def verdict(base: dict, rb: dict) -> dict:
    bs = rb.get("bootstrap_avg_per_cycle", {})
    mc = rb.get("monte_carlo_random_timing", {})
    wfo = rb.get("walk_forward_optimisation", {})
    pbo = rb.get("pbo_cscv", {})
    wfw = rb.get("walk_forward_windows", {})
    checks = {
        "beats_hold_in_coins": bool(base["coin_gain_vs_hold"] > 0),
        "enough_cycles_20": base["cycles"] >= 20,
        "bootstrap_prob_mean_positive_ge_0_9": (bs.get("prob_mean_positive") or 0) >= 0.9 if "prob_mean_positive" in bs else None,
        "better_than_random_timing_p_lt_0_05": (mc["p_value"] < 0.05) if "p_value" in mc else None,
        "walk_forward_optimised_oos_positive": (wfo["oos_coin_change_pct"] > 0) if "oos_coin_change_pct" in wfo else None,
        "walk_forward_windows_majority_gain": (wfw["windows_with_gain"] > wfw["n_windows"] / 2) if wfw else None,
        "pbo_below_0_5": (pbo["pbo"] < 0.5) if "pbo" in pbo else None,
        "team_rule_avg_gain_ge_3x_costs": (base["team_checks"]["realized_avg_net_vs_3x_cost"] or {}).get("ok"),
    }
    checks = {k: (None if v is None else bool(v)) for k, v in checks.items()}
    done = [v for v in checks.values() if v is not None]
    if not checks["beats_hold_in_coins"]:
        word, fr = "NO", "NON : sur cette période, vendre d'abord a fini avec moins de pièces que simplement garder."
    elif all(done) and checks["enough_cycles_20"]:
        word, fr = "SOLID", "SOLIDE : toutes les vérifications sont bonnes (mais le passé ne garantit rien)."
    else:
        word, fr = "FRAGILE", (f"FRAGILE : plus de pièces qu'en gardant, mais seulement {sum(done)} vérifications bonnes sur {len(done)} ; "
                               "le gain peut venir de la chance.")
    return {"verdict": word, "verdict_fr": fr, "checks": checks, "passed": sum(done), "of": len(done)}


# ───────────────────────── French report ─────────────────────────
def fr(x, nd=2, sign=False) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    s = f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"
    return s.replace(",", " ").replace(".", ",")


def _local(ts: str) -> str:
    return pd.Timestamp(ts).tz_localize("UTC").tz_convert(TZ_REPORT).strftime("%d/%m/%Y %Hh")


def report_fr(s: dict, rb: dict | None = None) -> str:
    coin, p = s["coin"], s["params"]
    de = "d'" if coin[:1] in "AEIOUY" else "de "
    nd = 6 if s["coins_start"] < 1 else 4
    L = [f"# Vendre d'abord, racheter plus bas (idée D-018) : {s['pair']}, bougies de {s['timeframe']}", ""]
    L.append(f"Période : du {_local(s['period'][0])} au {_local(s['period'][1])} (heure de Bruxelles), prix publics {s['source']} (Binance).")
    L.append(f"Au départ : {fr(s['coins_start'], nd)} {coin} (= {fr(s['eur_start'])} € au premier prix, {fr(s['first_price'])} €).")
    L += ["", "## La règle testée"]
    tr = (f"ET qu'il reste sous sa moyenne des {p['trend_ma']:g} dernières heures" if p["trend_ma"] > 0 else "(sans condition de moyenne)")
    L.append(f"- Vente de {p['chunk']:g} % des {coin} quand le prix a monté d'au moins {fr(p['rise'], 1)} % en {p['rise_hours']:g} heures {tr}.")
    if p.get("fill") == "touch":
        L.append(f"- Ordres à prix fixé remplis seulement si le prix passe strictement au-delà"
                 f"{' de ' + fr(p['fill_ticks'] / 100, 2) + ' %' if p.get('fill_ticks') else ''} (`--fill touch`) ; juste toucher = pas rempli.")
    e = s["entries"]
    if e["session"]:
        L.append(f"- Vente seulement entre {e['session'].replace('-', 'h et ')}h (heure de Bruxelles){', du lundi au vendredi' if e['weekdays_only'] else ''}.")
    elif e["weekdays_only"]:
        L.append("- Vente seulement du lundi au vendredi.")
    L.append(f"- Prix de vente : {'le prix d’ouverture de l’heure suivante' if p['sell_fill'] == 'open' else 'le prix de fin de l’heure du signal (vente seulement si le prix y revient)'}.")
    L.append(f"- Ensuite, achat quand le prix est {fr(p['dip'], 1)} % plus bas que le prix de vente." if p["dip"] > 0
             else "- Pas de prix visé (`--dip 0`) : le rachat se fait seulement au seuil de sécurité (fixe ou suiveur) ou en fin de données.")
    if p.get("trail_start"):
        L.append(f"- Le seuil suiveur ne démarre qu'une fois le prix {fr(p['trail_start'], 1)} % sous le prix de vente ; ensuite il ne remonte jamais au-dessus du prix de vente.")
    L.append(f"- Si le prix monte de {fr(p['stop'], 1)} % au-dessus du prix de vente, achat quand même pour limiter la perte.")
    if p["max_hours"]:
        L.append(f"- Si rien ne s'est passé après {p['max_hours']:g} heures, achat au prix du moment.")
    L.append("- Une seule vente à la fois. Si les deux prix sont touchés dans la même heure, on compte le cas le pire.")
    c = s["costs"]
    if s["costs"]["note"].startswith("wallet swap"):
        L.append(f"- Frais (échange dans le portefeuille, profil {c['profile']}) : {fr(c['market_order_fee'] * 100, 3)} % à chaque vente et à chaque achat"
                 + (f", + {fr(c['market_order_slippage'] * 100, 3)} % d'écart de prix" if c["market_order_slippage"] else "")
                 + f", + {fr(c['fixed_fee_eur_per_swap'])} € de frais de réseau à chaque fois.")
    else:
        L.append(f"- Frais : {fr(c['limit_order_fee'] * 100)} % pour la vente et l'achat au prix visé ; "
                 f"{fr(c['market_order_fee'] * 100)} % + {fr(c['market_order_slippage'] * 100)} % d'écart de prix pour l'achat de sécurité"
                 + (f" ; + {fr(c['fixed_fee_eur_per_swap'])} € fixes à chaque vente et à chaque achat" if c["fixed_fee_eur_per_swap"] else "") + ".")
    L += ["", "## Résultat"]
    n = s["cycles"]
    if n == 0:
        L.append("- Aucune vente sur la période : le résultat est le même que garder.")
    else:
        L.append(f"- Nombre de ventes (chacune suivie d'un achat) : {n}.")
        L.append(f"- Ventes gagnantes (plus {de}{coin} après l'achat) : {s['wins']} sur {n} ({fr(s['win_rate_pct'], 0)} %).")
        rr = s["rebuy_reasons"]
        L.append(f"- Achats au prix visé : {rr.get('target', 0)} ; achats de sécurité : {rr.get('safety', 0)}"
                 + (f" ; achats de sécurité au seuil suiveur : {rr.get('trailing', 0)}" if rr.get("trailing") else "")
                 + (f" ; achats après le délai : {rr.get('timeout', 0)}" if rr.get("timeout") else "")
                 + (f" ; achat forcé à la fin : {rr.get('end', 0)}" if rr.get("end") else "") + ".")
        L.append(f"- Gain moyen quand c'est gagné : {fr(s['avg_win_coin_pct'], 2, True)} % {de}{coin}"
                 f" ; perte moyenne quand c'est perdu : {fr(s['avg_loss_coin_pct'], 2, True)} % {de}{coin}.")
        w = s["worst_run"]["worst_streak"]
        if w:
            L.append(f"- Pire série : {w['losses_in_a_row']} perte(s) de suite, soit {fr(w['coin_change_pct'], 2, True)} % {de}{coin} "
                     f"(du {_local(w['from'])} au {_local(w['to'])}).")
        L.append(f"- Plus forte baisse du nombre {de}{coin} depuis un sommet : {fr(s['max_drawdown_coins_pct'], 2)} %.")
        L.append(f"- Frais payés : {fr(s['fees_paid_eur'], 4)} € (+ {fr(s['slippage_cost_eur'], 4)} € d'écart de prix).")
    L.append("")
    L.append(f"**En {coin} :** {fr(s['coins_end'], nd)} {coin} à la fin, contre {fr(s['coins_start'], nd)} en gardant simplement "
             f"→ {'gain' if s['coin_gain_vs_hold'] > 0 else 'perte'} de {fr(abs(s['coin_gain_vs_hold']), nd)} {coin} "
             f"({fr(s['coin_gain_vs_hold_pct'], 2, True)} %).")
    L.append(f"**En euros :** {fr(s['eur_end_strategy'])} € à la fin, contre {fr(s['eur_end_hold'])} € en gardant "
             f"→ {'gain' if s['eur_gain_vs_hold'] > 0 else 'perte'} de {fr(abs(s['eur_gain_vs_hold']))} € par rapport à garder. "
             f"(En gardant, la valeur a fait {fr(s['eur_return_hold_pct'], 1, True)} % sur la période.)")
    tc = s["team_checks"]
    L += ["", "## Règle de l'équipe"]
    r = tc["realized_avg_net_vs_3x_cost"]
    if r:
        L.append(f"- Gain moyen par vente ({fr(r['avg_net_pct'], 2, True)} %) au moins 3 fois les frais ({fr(r['three_x_avg_cost_pct'], 2)} %) : "
                 f"{'OUI' if r['ok'] else 'NON'}.")
    ex = tc["expectancy_ex_ante"]
    if ex["breakeven_win_rate_pct"] is not None:
        L.append(f"- Pour ne pas perdre, il faut au moins {fr(ex['breakeven_win_rate_pct'], 0)} % de ventes gagnantes "
                 f"(ici : {fr(s['win_rate_pct'], 0) if n else '—'} %).")
    L.append(f"- Au moins 20 ventes pour juger : {'OUI' if tc['enough_cycles_20'] else 'NON'} ({n}).")
    if rb:
        v = rb["verdict"]
        L += ["", "## Est-ce de la chance ?"]
        mc = rb.get("monte_carlo_random_timing", {})
        if "p_value" in mc:
            L.append(f"- En vendant à des moments pris au hasard ({mc['n_sims']} essais), on obtient en général {fr(mc['random_median_coin_gain_pct'], 2, True)} % {de}{coin}. "
                     f"La règle fait mieux que ce hasard dans {fr((1 - mc['p_value']) * 100, 0)} % des essais (il faudrait au moins 95 %).")
        bs = rb.get("bootstrap_avg_per_cycle", {})
        if "prob_mean_positive" in bs:
            L.append(f"- En re-tirant au hasard parmi les {n} ventes ({bs['n_sims']} fois), "
                     f"le gain moyen reste positif dans {fr(bs['prob_mean_positive'] * 100, 0)} % des cas.")
        wfw = rb.get("walk_forward_windows")
        if wfw:
            L.append(f"- Période coupée en {wfw['n_windows']} morceaux : gain dans {wfw['windows_with_gain']}, perte dans {wfw['windows_with_loss']}, "
                     f"aucune vente dans {wfw['windows_without_sell']}.")
        wfo = rb.get("walk_forward_optimisation")
        if wfo:
            L.append(f"- Réglage choisi sur le passé puis testé sur la suite : {fr(wfo['oos_coin_change_pct'], 2, True)} % {de}{coin}"
                     + (f" (réglage de base sur la même période : {fr(wfo['default_params_same_period_pct'], 2, True)} %)."
                        if wfo.get("default_params_same_period_pct") is not None else "."))
        pb = rb.get("pbo_cscv", {})
        if "pbo" in pb:
            L.append(f"- Risque que « le meilleur réglage » soit de la chance : {fr(pb['pbo'] * 100, 0)} % (au-dessus de 50 % = mauvais signe).")
        g = rb.get("grid", {})
        if g.get("n_trials"):
            L.append(f"- Réglages voisins essayés : {g['n_trials']} ; plus {de}{coin} qu'en gardant dans {fr(g['share_of_variants_beating_hold'] * 100, 0)} % des cas.")
        L.append("- Certaines vérifications faites pour les autres règles ne s'appliquent pas ici (détail dans le fichier JSON, « skipped_checks »).")
        L.append(f"- **Verdict : {v['verdict_fr']}**")
    L += ["", "## En clair"]
    if n == 0:
        L.append("Aucune vente : rien à juger.")
    elif s["coin_gain_vs_hold"] > 0:
        L.append(f"Sur cette période, vendre d'abord puis racheter a donné PLUS {de}{coin} que simplement garder.")
    else:
        L.append(f"Sur cette période, vendre d'abord puis racheter a donné MOINS {de}{coin} que simplement garder.")
    L += ["", "## Attention",
          "- Un bon résultat sur le passé ne garantit rien pour demain. Ce n'est pas un conseil.",
          "- Une vente ou un achat à prix fixé peut ne pas se faire dans la réalité si peu de monde achète ou vend à ce prix.",
          "- Calcul fait heure par heure : ce qui se passe à l'intérieur d'une heure n'est pas connu (on prend alors le cas le pire).",
          "- Aucun ordre n'a été passé. Pas d'argent réel."]
    for w in s.get("warnings", []):
        L.append(f"- Note technique : {w}")
    L += ["", f"Détails : {s.get('run_dir', '')}"]
    return "\n".join(L) + "\n"
