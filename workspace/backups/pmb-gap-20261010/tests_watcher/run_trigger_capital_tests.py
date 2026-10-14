#!/usr/bin/env python3
"""trigger_price on every close line + capital_reel_depart kept (10 oct).
Paper temp dirs + copied live tree with FAKE revx. Never a real order, never the real state."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt
from run_live_tests import Tree, ENTRY

G = rt.G
BTC = {"pair": "BTC-EUR", "side": "buy", "type": "limit", "price": 74000, "amount_eur": 20, "stop_price": 73000,
       "target_price": 75000, "idea_type": "hausse", "decision_id": "D-T1", "post_only": True}
CAP = {"eur": 165.71, "date": "2026-10-09T02:17:59+02:00", "source": "test", "note": "test"}


def close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def log(T):
    return [json.loads(l) for l in (T / "state/trades_log.jsonl").read_text().splitlines()]


def test_manual_closes():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BTC)
    q = rt.state_of(T)["positions"][0]["qty"]
    sell = {"pair": "BTC-EUR", "side": "sell", "type": "limit", "price": 73586.385, "idea_type": "hausse",
            "decision_id": "D-T1", "close_reason": "idee_morte"}
    r, rc = rt.paper_fill(env, dict(sell, qty=q / 2, trigger_price=73590.1))
    rt.check("manual partial sell keeps the order's trigger_price", rc == 0 and r["fill"].get("trigger_price") == 73590.1
             and log(T)[-1].get("trigger_price") == 73590.1, json.dumps(r.get("fill"))[:200])
    r, rc = rt.paper_fill(env, dict(sell, qty=q / 2))
    p = rt.state_of(T)["positions"][0]
    rt.check("manual close without trigger_price → order price; closed position carries it too", rc == 0
             and r["fill"].get("trigger_price") == 73586.385 and p["status"] == "closed" and p.get("trigger_price") == 73586.385,
             json.dumps(r.get("fill"))[:200])
    rt.paper_fill(env, BTC); q = [p for p in rt.state_of(T)["positions"] if p["status"] == "open"][0]["qty"]
    r, rc = rt.paper_fill(env, dict(sell, qty=q - 1e-8, trigger_price=73500))  # leaves < 0.01 € → residue closed
    rt.check("residue close carries trigger_price", rc == 0 and r["fill"].get("trigger_price") == 73500
             and all(x["status"] == "closed" for x in rt.state_of(T)["positions"]))
    rt.paper_fill(env, rt.SELL_SOL)
    pid = [p for p in rt.state_of(T)["positions"] if p["status"] == "open"][0]["id"]
    rb = {"pair": "SOL-EUR", "side": "buy", "type": "limit", "price": 95, "qty": 0.1, "idea_type": "baisse",
          "rebuy_reason": "target", "linked_position_id": pid, "post_only": True, "trigger_price": 94.8}
    r, rc = rt.paper_fill(env, rb)
    rt.check("manual short rebuy keeps trigger_price", rc == 0 and r["fill"].get("trigger_price") == 94.8
             and log(T)[-1].get("trigger_price") == 94.8)
    rt.paper_fill(env, rt.SELL_SOL)
    pid = [p for p in rt.state_of(T)["positions"] if p["status"] == "open"][0]["id"]
    r, rc = rt.paper_fill(env, {k: v for k, v in dict(rb, linked_position_id=pid).items() if k != "trigger_price"})
    rt.check("manual short rebuy without trigger_price → order price", rc == 0 and r["fill"].get("trigger_price") == 95)
    opens = [l for l in log(T) if not l.get("linked_position_id")]
    rt.check("opening lines carry no trigger_price", all("trigger_price" not in l for l in opens))


def test_watcher_closes():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BTC)
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 72950.5)
    lines, rc, err = rt.watch_once(env)
    last = log(T)[-1]; p = rt.state_of(T)["positions"][0]
    ev = json.loads((T / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
    rt.check("watcher long stop close: trigger_price = breaching mid (line + position + event)", rc == 10
             and last.get("trigger_price") == 72950.5 and last.get("close_reason") == "stop_hit"
             and p.get("trigger_price") == 72950.5 and ev.get("trigger_price") == 72950.5, json.dumps(last)[:250] + err[-200:])
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BTC)
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 75010.25)
    lines, rc, err = rt.watch_once(env)
    rt.check("watcher long target close: trigger_price = mid", rc == 10 and log(T)[-1].get("trigger_price") == 75010.25
             and log(T)[-1].get("close_reason") == "target_hit")
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, rt.SELL_SOL)
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 100.37)
    lines, rc, err = rt.watch_once(env)
    rt.check("watcher short safety rebuy: trigger_price = mid", rc == 10 and log(T)[-1].get("trigger_price") == 100.37
             and log(T)[-1].get("rebuy_reason") == "safety")


def test_live_exit_trigger():
    T = Tree(); T.env["WATCH_STOPS_NO_AUTOSTART"] = "1"
    T.tick(2170)
    r, rc = T.live_place(ENTRY)
    T.tick(2095.5, bid=2095, ask=2096)
    lines, rc2 = T.watch_once()
    ax = [x for x in T.rows() if x.get("kind") == "auto_exit"]
    o = ax[0]["order"] if ax else {}
    rt.check("live exit row carries trigger_price = breaching mid", rc == 0 and rc2 == 10 and o.get("trigger_price") == 2095.5
             and ax[0].get("trigger_price") == 2095.5 and o.get("close_reason") == "stop_hit", json.dumps(o)[:250])


def test_capital_block_survives():
    st = rt.base_state(); st["capital_reel_depart"] = dict(CAP)
    T = rt.new_root(st); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BTC)
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74100)
    rt.watch_once(env)
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 72000)
    lines, rc, err = rt.watch_once(env)  # close path (enrich + refresh)
    subprocess.run([sys.executable, str(G / "reconcile_revolut.py")], env=env, capture_output=True, timeout=60)
    s = rt.state_of(T)
    rt.check("capital_reel_depart untouched by paper_fill, watcher marks/close, reconcile", rc == 10
             and s.get("capital_reel_depart") == CAP and s.get("rapprochement_revolut"), json.dumps(s.get("capital_reel_depart")))


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_manual_closes, test_watcher_closes, test_live_exit_trigger, test_capital_block_survives):
            try:
                t()
            except Exception as e:  # noqa: BLE001
                import traceback; traceback.print_exc()
                rt.check(t.__name__ + " crashed", False, str(e))
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
