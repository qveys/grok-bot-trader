"""Unit-style checks of the D-018 sell_rebuy simulator on small synthetic price series.
Run: /workspace/tools/vibe-trading/.venv/bin/python checks/test_sell_rebuy.py   (no network, no pytest needed)"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vt_sellrebuy as SR  # noqa: E402

T0 = pd.Timestamp("2026-10-05 00:00")  # Monday, UTC
TF, TS = 0.0009, 0.0005               # Revolut X market order: fee + slippage


def P(**kw):
    base = dict(rise=3.0, rise_hours=3, trend_ma=0, dip=3.0, stop=1.5, max_hours=0, chunk=100.0, sell_fill="open",
                sess=(-1, -1), weekdays=False, tz="Europe/Brussels", tf_hours=1.0,
                maker_fee=0.0, maker_slip=0.0, taker_fee=TF, taker_slip=TS)
    base.update(kw)
    return base


def bars(rows):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], dtype=float)
    df.index = pd.date_range(T0, periods=len(df), freq="h")
    return df


def sim(rows, sig_at, **kw):
    df = bars(rows)
    sig = np.zeros(len(df), dtype=bool)
    sig[list(sig_at)] = True
    p = P(**kw)
    return SR.simulate(*(df[k].to_numpy() for k in ("open", "high", "low", "close")), sig, 0, 1.0, p), df, p, sig


def close(a, b, tol=1e-12):
    assert abs(a - b) <= tol * max(1, abs(b)), (a, b)


FLAT = (100, 100, 100, 100)
results = []


def check(name):
    def deco(f):
        f()
        results.append(name)
        print(f"OK  {name}")
        return f
    return deco


@check("signal fires on +3% in 24h below the trend average, not above it; --trend-ma 0 disables")
def _():
    closes = list(np.linspace(160, 100, 30)) + [101, 102.5, 103.2]   # fall, then +3.2% in 3 bars
    df = bars([(c, c, c, c) for c in closes])
    s, _ = SR.signals(df, P(trend_ma=10))
    assert s[-1] and not s[:-1].any(), np.where(s)
    s0, _ = SR.signals(df, P(trend_ma=0))
    assert s0[-1] and not s0[:-2].any()
    up = list(np.linspace(80, 100, 30)) + [101, 102.5, 103.2]        # same rise but ABOVE the average
    s2, _ = SR.signals(bars([(c, c, c, c) for c in up]), P(trend_ma=10))
    assert not s2.any()
    s3, _ = SR.signals(df, P(trend_ma=10, rise=3.5))                   # rise below threshold
    assert not s3.any()


@check("session 15-17 Brussels + weekdays filter uses the decision time (candle close)")
def _():
    df = bars([FLAT] * (24 * 6))                                        # Mon 00:00 UTC .. Sat
    ok = SR.time_filter(df.index, 1.0, (15, 17), True, "Europe/Brussels")
    hrs = sorted(set(df.index[ok].hour))
    assert hrs == [12, 13], hrs                                         # 12:00 UTC candle closes 15:00 CEST
    assert all(d < 5 for d in df.index[ok].weekday)
    assert ok.sum() == 2 * 5


@check("target rebuy: limit at sell*(1-3%), maker 0%, coins = sold*100/97")
def _():
    r, *_ = sim([FLAT, (100, 100.5, 99, 99.5), (99, 99.5, 96.9, 97.5), FLAT], [0])
    cy = r["cycles"]
    assert len(cy) == 1 and cy[0]["reason"] == "target" and cy[0]["j_sell"] == 1 and cy[0]["j_buy"] == 2
    close(cy[0]["buy_px"], 97.0)
    close(r["coins_end"], 100 / 97)
    close(cy[0]["fees_eur"], 0.0)
    assert cy[0]["coin_gain"] > 0


@check("safety rebuy: price +1.5% above the sell -> market buy at 101.5 with fee 0.09% + slippage 0.05%")
def _():
    r, *_ = sim([FLAT, (100, 100.5, 99, 99.5), (99.5, 101.6, 99, 101), FLAT], [0])
    cy = r["cycles"][0]
    assert cy["reason"] == "safety"
    close(cy["buy_px"], 101.5)
    close(r["coins_end"], 100 / (101.5 * (1 + TS) * (1 + TF)))
    close(cy["fees_eur"], r["coins_end"] * 101.5 * (1 + TS) * TF)
    assert cy["coin_gain"] < 0


@check("same candle touches target AND safety -> safety (worse case)")
def _():
    r, *_ = sim([FLAT, (100, 101.6, 96.5, 98), FLAT], [0])
    assert r["cycles"][0]["reason"] == "safety"
    close(r["cycles"][0]["buy_px"], 101.5)


@check("gap up through the safety level -> bought at the (worse) open")
def _():
    r, *_ = sim([FLAT, (100, 100.2, 99.8, 100), (103, 104, 102.5, 103.5)], [0])
    close(r["cycles"][0]["buy_px"], 103.0)


@check("gap down through the target -> resting limit filled at the target price")
def _():
    r, *_ = sim([FLAT, (100, 100.2, 99.8, 100), (95, 95.5, 94, 95)], [0])
    assert r["cycles"][0]["reason"] == "target"
    close(r["cycles"][0]["buy_px"], 97.0)


@check("fees: flat01 limit fee 0.1% on the sell and on the target rebuy")
def _():
    r, *_ = sim([FLAT, (100, 100.5, 96.9, 97.5)], [0], maker_fee=0.001, taker_fee=0.001)
    cy = r["cycles"][0]
    close(cy["eur"], 99.9)
    qb = 99.9 / (97 * 1.001)
    close(r["coins_end"], qb)
    close(cy["fees_eur"], 0.1 + qb * 97 * 0.001)
    close(cy["cost_pct"], cy["fees_eur"] / 100 * 100)


@check("time-out: --max-hours 2 -> market rebuy at the open 2 hours after the sell")
def _():
    r, *_ = sim([FLAT, (100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (99, 99.5, 98.5, 99)], [0], max_hours=2)
    cy = r["cycles"][0]
    assert cy["reason"] == "timeout" and cy["j_buy"] == 3 and cy["hours"] == 2
    close(r["coins_end"], 100 / (99 * (1 + TS) * (1 + TF)))


@check("--sell-fill close: limit at the signal close; unfilled if the next candle never reaches it; no target on the fill candle")
def _():
    rows = [FLAT, (99.6, 99.8, 99.0, 99.5), (99.4, 100, 96, 97), (97, 97.5, 96, 96.5)]
    r, *_ = sim(rows, [0, 1], sell_fill="close")
    assert r["unfilled_sells"] == 1                       # signal at bar0 close=100, bar1 high 99.8 < 100
    cy = r["cycles"][0]
    assert cy["j_sell"] == 2 and cy["sell_px"] == 99.5    # signal at bar1 close=99.5, bar2 high 100 >= 99.5
    assert cy["j_buy"] == 3 and cy["reason"] == "target"  # bar2 low 96 < target but not credited on fill candle
    close(cy["buy_px"], 99.5 * 0.97)


@check("one cycle at a time; open cycle at the end closed at the last close (market)")
def _():
    r, *_ = sim([FLAT, (100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 100.5, 99.5, 99.8)], [0, 1, 2])
    assert len(r["cycles"]) == 1 and r["signals_ignored_in_cycle"] == 2
    cy = r["cycles"][0]
    assert cy["reason"] == "end" and cy["j_buy"] == 3
    close(r["coins_end"], 100 / (99.8 * (1 + TS) * (1 + TF)))


@check("--chunk 50 sells half the coins; the other half stays held")
def _():
    r, *_ = sim([FLAT, (100, 100.5, 96.9, 97.5)], [0], chunk=50)
    close(r["coins_end"], 0.5 + 0.5 * 100 / 97)


@check("wallet swap costs (uniswap-like): 0.05 % on BOTH legs + 0.03 EUR network fee per swap")
def _():
    sw = dict(maker_fee=0.0005, taker_fee=0.0005, maker_slip=0.0, taker_slip=0.0, fixed_fee_eur=0.03)
    r, *_ = sim([FLAT, (100, 100.5, 96.9, 97.5)], [0], **sw)          # 1 coin sold at 100, target 97
    cy = r["cycles"][0]
    eur = 100 * (1 - 0.0005) - 0.03
    close(cy["eur"], eur)
    qb = (eur - 0.03) / (97 * 1.0005)
    close(r["coins_end"], qb)
    close(cy["fees_eur"], 100 * 0.0005 + 0.03 + qb * 97 * 0.0005 + 0.03)
    r2, *_ = sim([FLAT, (100, 101.6, 99, 101)], [0], **sw)              # safety: same % fee (no taker premium)
    close(r2["coins_end"], (eur - 0.03) / (101.5 * 1.0005))


@check("vt_tools presets: --costs uniswap / metamask-swap / --fee-pct + --fixed-fee-eur map to swap params")
def _():
    import argparse
    import vt_tools as V
    def parse(extra):
        ap = argparse.ArgumentParser(); V.add_run_args(ap)
        return SR.params_from_args(V.finalize(ap.parse_args(["--strategy", "sell_rebuy"] + extra), ap))
    u = parse(["--costs", "uniswap"])
    assert (u["maker_fee"], u["taker_fee"], u["maker_slip"], u["taker_slip"], u["fixed_fee_eur"]) == (0.0005, 0.0005, 0, 0, 0.03)
    m = parse(["--costs", "metamask-swap"])
    assert (m["maker_fee"], m["taker_fee"], m["fixed_fee_eur"]) == (0.00875, 0.00875, 0.03)
    c = parse(["--fee-pct", "0.3", "--fixed-fee-eur", "0.1", "--slippage", "0.001"])
    assert (c["maker_fee"], c["taker_fee"], c["maker_slip"], c["taker_slip"], c["fixed_fee_eur"]) == (0.003, 0.003, 0.001, 0.001, 0.1)
    d = parse([])                                                        # default revolutx: maker 0 %, taker 0.09 % + 0.05 %
    assert (d["maker_fee"], d["taker_fee"], d["taker_slip"], d["fixed_fee_eur"], d["swap_mode"]) == (0.0, 0.0009, 0.0005, 0.0, False)


@check("coin accounting on a random 2000-candle series: coins_end = start + sum(cycle gains); cycles never overlap; EUR consistent")
def _():
    rng = np.random.default_rng(7)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, 2000)))
    o = np.r_[100, c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.01, 2000))
    l = np.minimum(o, c) * (1 - rng.uniform(0, 0.01, 2000))
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=pd.date_range(T0, periods=2000, freq="h"))
    p = P(rise=2, rise_hours=24, trend_ma=50, max_hours=36)
    sig, _ = SR.signals(df, p)
    start = 60
    r = SR.simulate(o, h, l, c, sig, start, 0.5, p)
    cy = r["cycles"]
    assert len(cy) >= 10, len(cy)
    close(r["coins_end"], 0.5 + sum(x["coin_gain"] for x in cy), 1e-10)
    close(r["path"][-1], r["coins_end"], 1e-10)
    for a_, b_ in zip(cy, cy[1:]):
        assert a_["j_sell"] <= a_["j_buy"] < b_["j_sell"]
    for x in cy:   # every target rebuy is >= dip below, every safety/timeout is a loss before costs or a market fill
        if x["reason"] == "target":
            close(x["buy_px"], x["sell_px"] * 0.97)
        if x["reason"] == "safety":
            assert x["buy_px"] >= x["sell_px"] * 1.015 - 1e-9
    s = SR.summarize(df, start, 0.5, r, p, sig)
    close(s["eur_end_strategy"], round(r["coins_end"] * c[-1], 4), 1e-9)
    close(s["eur_end_hold"], round(0.5 * c[-1], 4), 1e-9)
    assert s["wins"] + s["losses"] == s["cycles"] == len(cy)
    assert sum(s["rebuy_reasons"].values()) == len(cy)
    # independent re-count of the fees
    close(s["fees_paid_eur"], round(sum(x["fee_sell"] + x["fee_buy"] for x in cy), 4), 1e-9)


print(f"\nall {len(results)} checks passed")
