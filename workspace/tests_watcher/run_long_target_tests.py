#!/usr/bin/env python3
"""Idée à la hausse : objectif (target_price) — 9 oct. Paper (temp dirs) + live (copied tree, FAKE revx).
Never places a real order, never touches the real state."""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt
from run_live_tests import Tree, ENTRY, sells

G = rt.G
BUY = {"pair": "BTC-EUR", "side": "buy", "type": "limit", "price": 74120, "amount_eur": 25, "stop_price": 73379,
       "target_price": 75232, "idea_type": "hausse", "decision_id": "T-D023", "post_only": True}
FEE = 0.0005


def close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def test_paper_open_and_merge():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    r, rc = rt.paper_fill(env, BUY)
    s = rt.state_of(T); p = s["positions"][0]
    rt.check("paper long open stores target_price, stop_price + stop_price_eur, fee_eur 0.05 %",
             rc == 0 and p.get("target_price") == 75232 and p.get("stop_price") == 73379 and p.get("stop_price_eur") == 73379
             and close(p.get("fee_eur"), 0.0125) and close(s["cash_eur"], 500 - 25.0125)
             and r["fill"].get("target_price") == 75232 and close(r["fill"].get("fee_eur"), 0.0125), json.dumps(p)[:300])
    rt.check("paper long open: unrealized = −fee, equity = cash + mark", close(s.get("unrealized_pnl_eur"), -0.0125)
             and close(s.get("equity_eur"), 500 - 0.0125))
    r2, rc2 = rt.paper_fill(env, dict(BUY, amount_eur=5, price=74200, target_price=76000, stop_price=73500))
    p = rt.state_of(T)["positions"][0]
    rt.check("merge: latest target/stop apply, fee accumulates", rc2 == 0 and p.get("target_price") == 76000
             and p.get("stop_price") == 73500 and p.get("stop_price_eur") == 73500 and close(p.get("fee_eur"), 0.0125 + 0.0025)
             and close(p.get("cost_eur"), 30), json.dumps(p)[:300])
    r3, rc3 = rt.paper_fill(env, dict(BUY, target_price=74000))
    rt.check("paper long: target ≤ price refused", rc3 == 1 and any("AU-DESSUS" in x for x in r3.get("reasons", [])), str(r3.get("reasons")))
    r4, rc4 = rt.paper_fill(env, dict(BUY, target_price=74120))
    rt.check("paper long: target = price refused", rc4 == 1, str(r4.get("reasons")))


def test_validate_targets():
    T = rt.new_root(); env = rt.make_env(T)
    def v(order, *a):
        p = subprocess.run([sys.executable, str(G / "validate_order.py"), *a], input=json.dumps(order), text=True,
                           capture_output=True, env=env, timeout=30)
        return json.loads(p.stdout), p.returncode
    r, rc = v(dict(BUY, target_price=74000))
    rt.check("validate_order: long target below price → refused", rc == 1 and any("AU-DESSUS" in x for x in r["reasons"]), str(r["reasons"]))
    r, rc = v(dict(BUY, target_price=74000), "--live")
    rt.check("validate_order --live: long target below price → refused", rc == 1)
    r, rc = v(BUY)
    rt.check("validate_order: long target above price → ok", rc == 0, str(r["reasons"]))
    r, rc = v(dict(rt.SELL_SOL, target_price=97))
    rt.check("validate_order: baisse target above sell price → refused (same rule)", rc == 1, str(r["reasons"]))


def test_watcher_long_target_close():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BUY)
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 75000)
    lines, rc, _ = rt.watch_once(env)
    p = rt.state_of(T)["positions"][0]
    w = lines[-1].get("watching", [{}])[0] if lines else {}
    rt.check("between stop and target → no close, watcher shows target_price", rc == 0 and p["status"] == "open"
             and w.get("target_price") == 75232)
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 75240)
    lines, rc, err = rt.watch_once(env)
    s = rt.state_of(T); p = s["positions"][0]
    qty = 25 / 74120
    gross = qty * 75240 - 25
    fees = 0.0125 + qty * 75240 * FEE
    ev = json.loads((T / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
    wake = json.loads((T / "state/auto_stop_wake.json").read_text())
    rt.check("mid ≥ target → paper long sold, close_reason target_hit, rc 10", rc == 10 and p["status"] == "closed"
             and p.get("close_reason") == "target_hit" and p.get("close_price_eur") == 75240, err[-200:])
    rt.check("realized net of buy+sell fees; cash = 500 + gross − fees", close(p.get("realized_pnl_eur"), gross - fees, 2e-6)
             and close(s["cash_eur"], 500 + gross - fees, 2e-6) and s.get("exposure_eur") == 0
             and close(s.get("total_pnl_eur"), gross - fees, 1e-4),
             f"realized={p.get('realized_pnl_eur')} exp={gross - fees:.6f} cash={s['cash_eur']}")
    rt.check("event + wake say target_hit / Objectif", ev.get("close_reason") == "target_hit" and "Objectif" in wake.get("message_fr", ""),
             wake.get("message_fr", ""))
    trades = [json.loads(l) for l in (T / "state/trades_log.jsonl").read_text().splitlines()]
    rt.check("journal sell row: realized net + gross + fees", trades[-1]["side"] == "sell" and close(trades[-1].get("realized_pnl_eur"), gross - fees, 2e-6)
             and close(trades[-1].get("realized_pnl_gross_eur"), gross, 2e-6))


def test_stop_priority_and_d023_replica():
    code = ("import sys,json;sys.argv=['x'];import watch_stops as w;"
            "p={'side':'long','stop_price_eur':73379,'target_price':73000,'avg_price':74120};"
            "print(json.dumps([w.position_breach(p,72900),w.position_breach(dict(p,target_price=75232),75232),"
            "w.position_breach(dict(p,target_price=75232),74000)]))")
    out = subprocess.run([sys.executable, "-c", code], cwd=str(G), text=True, capture_output=True, env=rt.make_env(rt.new_root()))
    a, b, c = json.loads(out.stdout)
    rt.check("stop has priority when both hit; target at exactly target; none in between",
             a["close_reason"] == "stop_hit" and b["close_reason"] == "target_hit" and c is None, out.stdout + out.stderr[-200:])
    st = rt.base_state(); st["cash_eur"] = 500 - 24.98
    st["positions"] = [{"id": "rx-paper-2026-10-09T123021Z-0f531d4f", "pair": "BTC-EUR", "side": "long", "idea_type": "hausse",
                        "qty": 0.000337, "avg_price": 74120.0, "cost_eur": 24.98, "mark_eur": 24.98, "stop_pct": None,
                        "status": "open", "stop_price_eur": 73379.0, "stop_price": 73379.0, "target_price": 75232.0,
                        "decision_id": "D-023", "deadline": "2026-10-09T17:00:00+02:00"}]
    T = rt.new_root(st); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 75232)
    lines, rc, err = rt.watch_once(env)
    p = rt.state_of(T)["positions"][0]
    gross = 0.000337 * 75232 - 24.98
    rt.check("D-023 replica (no fee_eur on entry): sold at target 75232, realized = gross − sell fee",
             rc == 10 and p["status"] == "closed" and p.get("close_reason") == "target_hit"
             and close(p.get("realized_pnl_eur"), gross - 0.000337 * 75232 * FEE, 2e-6), f"{p.get('realized_pnl_eur')} {err[-200:]}")


def test_live_long_target():
    T = Tree(); T.env["WATCH_STOPS_NO_AUTOSTART"] = "1"
    T.tick(2170)
    r0, rc0 = T.live_place(dict(ENTRY, target_price=2100))
    rt.check("live entry with target ≤ price → refused (rc 4), no order", rc0 == 4 and not [c for c in T.calls() if c.startswith("order place")],
             str(r0)[:160])
    r, rc = T.live_place(dict(ENTRY, target_price=2250))
    rt.check("live entry (fake) with target 2250 ok", rc == 0, str(r.get("error")))
    T.tick(2200, bid=2199, ask=2201)
    lines, rc1 = T.watch_once()
    w = lines[-1].get("watching", [{}])[0]
    rt.check("live long watched with target_price, no exit below target", rc1 == 0 and w.get("target_price") == 2250
             and not sells(T.calls()), json.dumps(w)[:200])
    T.tick(2260, bid=2259, ask=2261)
    lines, rc2 = T.watch_once()
    ex = list(T.exits().values())[0] if T.exits() else {}
    place = sells(T.calls())
    ax = [x for x in T.rows() if x.get("kind") == "auto_exit"]
    f = T.fake()
    rt.check("live long target → auto exit done, executable limit bid−0.3 % (2252.22), not post-only",
             rc2 == 10 and ex.get("status") == "done" and len(place) == 1 and "--limit 2252.22" in place[0]
             and "--post-only" not in place[0], place[0] if place else str(lines[-1])[:200])
    o = ax[0]["order"] if ax else {}
    sold = float(o.get("qty") or 0)
    net = sold * 2252.22 - 2170 * sold - FEE * (2170 * sold + 2252.22 * sold)
    rt.check("live exit row: close_reason target_hit, realized net > 0", o.get("close_reason") == "target_hit"
             and close(o.get("realized_pnl_eur"), net, 2e-6) and o["realized_pnl_eur"] > 0, f"{o.get('realized_pnl_eur')} vs {net:.6f}")
    rt.check("Quentin's ETH intact (0.0309)", 0.0309 - 1e-12 <= f["balances"]["ETH"]["total"] < 0.0309 + 1e-8)
    wake = T.read("state/auto_stop_wake.json")
    ev = json.loads((T.L / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
    rt.check("wake not urgent, message mentions objectif; event close_reason target_hit",
             wake.get("urgent") is False and "objectif" in wake.get("message_fr", "") and ev.get("close_reason") == "target_hit",
             wake.get("message_fr", "")[:160])
    n = len(sells(T.calls()))
    lines, rc3 = T.watch_once()
    rt.check("one exit per position: next cycle idle, no 2nd sell", rc3 == 0 and lines[-1].get("action") == "idle" and len(sells(T.calls())) == n)
    rt.kill_all(str(T.L))


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_paper_open_and_merge, test_validate_targets, test_watcher_long_target_close,
                  test_stop_priority_and_d023_replica, test_live_long_target):
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
