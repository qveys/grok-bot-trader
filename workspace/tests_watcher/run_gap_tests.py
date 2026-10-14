#!/usr/bin/env python3
"""Rattrapage des trous de prix (10 oct): mock candles (WATCH_STOPS_CANDLES_FILE), never network,
never a real order, never the real state. Paper temp dirs + copied live tree with FAKE revx."""
from __future__ import annotations
import json, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt
from run_live_tests import Tree, ENTRY, sells

BTC = {"pair": "BTC-EUR", "side": "buy", "type": "limit", "price": 74000, "amount_eur": 20, "stop_price": 73000,
       "target_price": 75000, "idea_type": "hausse", "decision_id": "D-G1", "post_only": True}


def log(T):
    return [json.loads(l) for l in (T / "state/trades_log.jsonl").read_text().splitlines()]


def gaps(T):
    p = T / "state/price_gaps.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def candles(T, pair, rows, ref=None):
    """rows: [(minutes_ago, low, high)] relative to ref (default real now)."""
    ref = ref or datetime.now(rt.TZ)
    out = [[int((ref - timedelta(minutes=m)).timestamp()), lo, hi, lo, hi, 1.0] for m, lo, hi in rows]
    out.sort(reverse=True)  # Coinbase: newest first
    (T / "candles.json").write_text(json.dumps({pair: out}))


def set_pos(T, **kw):
    s = rt.state_of(T)
    for p in s["positions"]:
        if p.get("status", "open") == "open":
            p.update(kw)
    (T / "guardian_state.json").write_text(json.dumps(s, indent=2))


def paper_tree(order=BTC, ago_min=30, field="last_checked_at"):
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    r, rc = rt.paper_fill(env, order)
    assert rc == 0, r
    set_pos(T, **{field: rt.now_iso(ago_min * 60)})
    return T, env


def flat(lo, hi, n=28, skip=()):
    return [(m, lo, hi) for m in range(1, n + 1) if m not in skip]


def test_stop_crossed():
    T, env = paper_tree()
    candles(T, "BTC-EUR", flat(73800, 74200, skip=(15,)) + [(15, 72900, 73900)])
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)  # current price fine: only the gap saw the stop
    lines, rc, err = rt.watch_once(env)
    last = log(T)[-1]; p = rt.state_of(T)["positions"][0]; g = gaps(T)
    rg = last.get("rattrapage_trou") or {}
    rt.check("gap: stop crossed in gap → closed AT the stop (73000), not at the current price", rc == 10
             and last.get("close_reason") == "stop_hit" and last.get("price") == 73000 and last.get("trigger_price") == 73000
             and p["status"] == "closed", json.dumps(last)[:300] + err[-300:])
    rt.check("gap: rattrapage_trou {debut, fin, source, plus_haut, plus_bas} on line + position",
             all(k in rg for k in ("debut", "fin", "source", "plus_haut", "plus_bas")) and rg["plus_bas"] == 72900
             and rg["plus_haut"] == 74200 and rg["source"] == "mock" and p.get("rattrapage_trou", {}).get("plus_bas") == 72900,
             json.dumps(rg))
    rt.check("gap: price_gaps.jsonl line complet, franchi stop_hit", len(g) == 1 and g[0]["statut"] == "complet"
             and g[0]["plus_bas"] == 72900 and g[0]["franchi"][0]["close_reason"] == "stop_hit", json.dumps(g)[:300])
    ev = json.loads((T / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
    wake = json.loads((T / "state/auto_stop_wake.json").read_text())
    rt.check("gap: event + wake carry rattrapage_trou, message mentions the gap", "rattrapage_trou" in ev
             and "Trou de prix" in wake.get("message_fr", ""), wake.get("message_fr", "")[:200])
    gross = p["qty"] * 73000
    rt.check("gap: P&L computed at the stop level", abs(p.get("close_price_eur", 0) - 73000) < 1e-9
             and p.get("realized_pnl_eur") is not None and p["realized_pnl_eur"] < 0, json.dumps(p)[:300])


def test_target_crossed():
    T, env = paper_tree()
    candles(T, "BTC-EUR", flat(73800, 74200, skip=(10,)) + [(10, 74000, 75100)])
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)
    lines, rc, err = rt.watch_once(env)
    last = log(T)[-1]
    rt.check("gap: target crossed → target_hit at 75000, trigger_price 75000", rc == 10
             and last.get("close_reason") == "target_hit" and last.get("price") == 75000 and last.get("trigger_price") == 75000
             and last.get("rattrapage_trou", {}).get("plus_haut") == 75100, json.dumps(last)[:300] + err[-200:])


def test_both_same_candle():
    T, env = paper_tree()
    candles(T, "BTC-EUR", flat(73800, 74200, skip=(12,)) + [(12, 72900, 75100)])
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)
    lines, rc, err = rt.watch_once(env)
    last = log(T)[-1]
    rt.check("gap: stop AND target in the same candle → stop first (73000)", rc == 10
             and last.get("close_reason") == "stop_hit" and last.get("price") == 73000
             and last.get("rattrapage_trou", {}).get("stop_et_objectif_meme_bougie") is True, json.dumps(last)[:300])
    T, env = paper_tree()
    candles(T, "BTC-EUR", flat(73800, 74200, skip=(20, 8)) + [(20, 74000, 75100), (8, 72900, 74000)])
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)
    rt.watch_once(env)
    rt.check("gap: target candle BEFORE the stop candle → target_hit (chronological)",
             log(T)[-1].get("close_reason") == "target_hit")


def test_api_failure():
    T, env = paper_tree()
    before = rt.state_of(T)["positions"][0]["last_checked_at"]
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)  # no candles.json → API failure
    lines, rc, err = rt.watch_once(env)
    p = rt.state_of(T)["positions"][0]; g = gaps(T)
    rt.check("gap: API failure → no close, loop continues (rc 0)", rc == 0 and p["status"] == "open"
             and len(log(T)) == 1, err[-300:])
    rt.check("gap: API failure → price_gaps line statut incomplet with error", len(g) == 1 and g[0]["statut"] == "incomplet"
             and g[0].get("erreur"), json.dumps(g)[:300])
    rt.check("gap: incomplet → last_checked_at kept (retried next loop)", p.get("last_checked_at") == before)
    (T / "candles.json").write_text(json.dumps({"fail": True}))
    lines, rc, err = rt.watch_once(env)
    rt.check("gap: explicit API error → still no close, 2nd incomplet line", rc == 0 and rt.state_of(T)["positions"][0]["status"] == "open"
             and len(gaps(T)) == 2 and gaps(T)[-1]["statut"] == "incomplet")
    # then the API comes back: the same window is re-scanned and the stop found
    candles(T, "BTC-EUR", flat(73800, 74200, skip=(15,)) + [(15, 72900, 73900)])
    lines, rc, err = rt.watch_once(env)
    rt.check("gap: API back → same window re-scanned, stop closes at 73000", rc == 10 and log(T)[-1].get("price") == 73000)


def test_no_cross_logged():
    T, env = paper_tree()
    candles(T, "BTC-EUR", flat(73800, 74200))
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)
    lines, rc, err = rt.watch_once(env)
    p = rt.state_of(T)["positions"][0]; g = gaps(T)
    rt.check("gap: nothing crossed → no close, gap still logged (max/min)", rc == 0 and p["status"] == "open" and len(g) == 1
             and g[0]["plus_haut"] == 74200 and g[0]["plus_bas"] == 73800 and g[0]["franchi"] == [] and g[0]["n_bougies"] == 28,
             json.dumps(g)[:300])
    lc = datetime.fromisoformat(p["last_checked_at"])
    rt.check("gap: last_checked_at advanced to the tick time", abs((datetime.now(rt.TZ) - lc).total_seconds()) < 60, p["last_checked_at"])
    lines, rc, err = rt.watch_once(env)
    rt.check("gap: next loop (no gap) → no new gap line", rc == 0 and len(gaps(T)) == 1)


def test_restart_catch_up():
    # never checked (e.g. watcher was down since open): window starts at opened_at
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BTC)
    s = rt.state_of(T); s["positions"][0]["opened_at"] = rt.now_iso(40 * 60); s["positions"][0].pop("last_checked_at", None)
    (T / "guardian_state.json").write_text(json.dumps(s, indent=2))
    candles(T, "BTC-EUR", [(50, 72000, 74000)] + flat(73800, 74200, n=38, skip=(20,)) + [(20, 72950, 74000)])
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)
    lines, rc, err = rt.watch_once(env)
    last = log(T)[-1]
    rt.check("restart: never checked → window from opened_at, stop found → closed at 73000", rc == 10
             and last.get("price") == 73000 and last["rattrapage_trou"].get("depuis") == "opened_at"
             and last["rattrapage_trou"]["plus_bas"] == 72950, json.dumps(last)[:300] + err[-200:])
    # a candle BEFORE opened_at must not count
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BTC)
    set_pos(T, opened_at=rt.now_iso(40 * 60))
    candles(T, "BTC-EUR", [(50, 72000, 74000)] + flat(73800, 74200, n=38))
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)
    lines, rc, err = rt.watch_once(env)
    rt.check("restart: candle before opened_at ignored → no close", rc == 0 and rt.state_of(T)["positions"][0]["status"] == "open")
    lc1 = rt.state_of(T)["positions"][0].get("last_checked_at")
    rt.check("restart: last_checked_at persisted in state after a loop", bool(lc1))
    # simulate the watcher down 30 min: persisted last_checked is old → next start catches up
    set_pos(T, last_checked_at=rt.now_iso(30 * 60))
    candles(T, "BTC-EUR", flat(73800, 74200, skip=(5,)) + [(5, 72990, 74000)])
    lines, rc, err = rt.watch_once(env)
    rt.check("restart: persisted old last_checked → catch-up closes at the stop", rc == 10 and log(T)[-1].get("price") == 73000
             and log(T)[-1]["rattrapage_trou"].get("depuis") == "last_checked_at")


def test_short_gap():
    T, env = paper_tree(rt.SELL_SOL)
    candles(T, "SOL-EUR", flat(95, 97, skip=(9,)) + [(9, 96, 100.5)])
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 96.2)
    lines, rc, err = rt.watch_once(env)
    last = log(T)[-1]
    rt.check("gap short: high ≥ stop 100 → safety rebuy AT 100, trigger 100, cycle closed", rc == 10
             and last.get("side") == "buy" and last.get("price") == 100 and last.get("trigger_price") == 100
             and last.get("rebuy_reason") == "safety" and last.get("close_reason") == "stop_hit"
             and last.get("rattrapage_trou", {}).get("plus_haut") == 100.5, json.dumps(last)[:300] + err[-200:])
    T, env = paper_tree(rt.SELL_SOL)
    candles(T, "SOL-EUR", flat(95, 97, skip=(9,)) + [(9, 89.5, 96)])
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 96.2)
    rt.watch_once(env)
    last = log(T)[-1]
    rt.check("gap short: low ≤ target 90 → target rebuy AT 90", last.get("price") == 90 and last.get("close_reason") == "target_hit"
             and last.get("rebuy_reason") == "target", json.dumps(last)[:300])


def test_live_gap():
    T = Tree(); T.env["WATCH_STOPS_NO_AUTOSTART"] = "1"
    fnow = datetime.fromisoformat(T.env["PMB_FAKE_NOW"])

    def tick(mid):
        d = T.L / "state/price_ticks"; d.mkdir(parents=True, exist_ok=True)
        with (d / f"{fnow.strftime('%Y-%m-%d')}.jsonl").open("a") as f:
            f.write(json.dumps({"ts": fnow.isoformat(), "pair": "ETH-EUR", "mid": mid, "source": "test",
                                "bid": mid - 1, "ask": mid + 1}) + "\n")
        fk = T.fake(); fk["ticker"]["ETH-EUR"] = {"bid": mid - 1, "ask": mid + 1}; T.fs.write_text(json.dumps(fk))

    tick(2170)
    r, rc = T.live_place(dict(ENTRY))
    rt.check("live gap: entry (fake) ok", rc == 0, str(r)[:200])
    lines, rc1 = T.watch_once()
    st = T.read("guardian/state.json")
    lm = st.get("live_last_checked") or {}
    rt.check("live gap: live position last check persisted in state.json (live_last_checked)", rc1 == 0 and len(lm) == 1, json.dumps(lm))
    old = (fnow - timedelta(minutes=30)).isoformat()
    st["live_last_checked"] = {k: old for k in lm}
    (T.L / "guardian/state.json").write_text(json.dumps(st, indent=2))
    (T.L / "candles.json").write_text(json.dumps({"ETH-EUR": [[int((fnow - timedelta(minutes=m)).timestamp()),
                                                                2090 if m == 15 else 2160, 2180, 2170, 2170, 1] for m in range(1, 29)]}))
    tick(2165)
    lines, rc2 = T.watch_once()
    ax = [x for x in T.rows() if x.get("kind") == "auto_exit"]
    o = ax[0]["order"] if ax else {}
    pl = sells(T.calls())
    rt.check("live gap: stop crossed in gap → market exit at the CURRENT bid−0.3 % (no invented fill at 2100)",
             rc2 == 10 and len(pl) == 1 and "--limit 2157.5" in pl[0], (pl[0] if pl else json.dumps(lines[-1])[:300]))
    rt.check("live gap: auto_exit row has trigger_price 2100 + rattrapage_trou", o.get("trigger_price") == 2100
             and (ax[0].get("rattrapage_trou") or o.get("rattrapage_trou") or {}).get("plus_bas") == 2090, json.dumps(ax)[:400])
    wake = T.read("state/auto_stop_wake.json")
    ev = json.loads((T.L / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
    rt.check("live gap: wake URGENT, message mentions the gap; event stop_hit with rattrapage_trou",
             wake.get("urgent") is True and "trou de prix" in wake.get("message_fr", "") and ev.get("close_reason") == "stop_hit"
             and ev.get("rattrapage_trou"), wake.get("message_fr", "")[:250])
    g = gaps(T.L)
    rt.check("live gap: gap logged in price_gaps.jsonl", g and g[-1]["franchi"] and g[-1]["pair"] == "ETH-EUR")
    rt.check("Quentin's ETH intact (0.0309)", 0.0309 - 1e-12 <= T.fake()["balances"]["ETH"]["total"] < 0.0309 + 1e-8)
    rt.kill_all(str(T.L))


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_stop_crossed, test_target_crossed, test_both_same_candle, test_api_failure, test_no_cross_logged,
                  test_restart_catch_up, test_short_gap, test_live_gap):
            try:
                t()
            except Exception as e:  # noqa: BLE001
                import traceback; traceback.print_exc()
                rt.check(f"{t.__name__} crashed", False, repr(e))
    finally:
        for T in rt.TMPS:
            rt.kill_all(str(T))
        after = rt.real_hashes()
        diff = {k: (before[k], after.get(k)) for k in before if before[k] != after.get(k) and "price_ticks" not in k}
        rt.check("real state untouched", not diff, json.dumps(diff))
        left = [pid for T in rt.TMPS for pid in rt.watcher_pids_for(str(T))]
        rt.check("no test watcher left running", not left, str(left))
        n_ok = sum(1 for _, ok, _ in rt.RESULTS if ok)
        print(f"\n{n_ok}/{len(rt.RESULTS)} passed.")
        sys.exit(0 if n_ok == len(rt.RESULTS) else 1)
