#!/usr/bin/env python3
"""Une décision = une position (9 oct). Two paper longs (or shorts) on the same pair stay SEPARATE,
each with its own stop / target / risk_level; closes hit exactly the designated position.
Temp dirs only — never touches the real state, never places an order."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt

G = rt.G
FEE = 0.0005
A = {"pair": "SOL-EUR", "side": "buy", "type": "limit", "price": 98.5, "amount_eur": 15, "stop_price": 97.30,
     "target_price": 100.09, "idea_type": "hausse", "decision_id": "D-024a", "risk_level": "equilibree", "post_only": True}
B = dict(A, price=99.0, amount_eur=10, stop_price=98.60, target_price=101.60, decision_id="D-024b", risk_level="risquee")
BTC = {"pair": "BTC-EUR", "side": "buy", "type": "limit", "price": 74120, "amount_eur": 20, "stop_price": 73379,
       "target_price": 75232, "idea_type": "hausse", "decision_id": "D-023", "post_only": True}


def close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def by_did(s, did):
    return [p for p in s["positions"] if p.get("decision_id") == did]


def validate(env, order):
    p = subprocess.run([sys.executable, str(G / "validate_order.py")], input=json.dumps(order), text=True,
                       capture_output=True, env=env, timeout=30)
    return json.loads(p.stdout), p.returncode


def test_open_separate_and_same_decision_merge():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    ra, rca = rt.paper_fill(env, A)
    rb, rcb = rt.paper_fill(env, B)
    s = rt.state_of(T)
    pa, pb = by_did(s, "D-024a"), by_did(s, "D-024b")
    rt.check("two SOL longs, different decision_id → 2 separate open positions", rca == 0 and rcb == 0
             and len(pa) == 1 and len(pb) == 1 and pa[0]["id"] != pb[0]["id"]
             and pa[0]["status"] == pb[0]["status"] == "open", f"{rca} {rcb} {len(s['positions'])}")
    pa, pb = pa[0], pb[0]
    rt.check("each keeps its own stop / target / risk_level / qty / cost / fee",
             pa["stop_price"] == 97.30 and pa["target_price"] == 100.09 and pa["risk_level"] == "equilibree"
             and pb["stop_price"] == 98.60 and pb["stop_price_eur"] == 98.60 and pb["target_price"] == 101.60
             and pb["risk_level"] == "risquee" and close(pa["cost_eur"], 15) and close(pb["cost_eur"], 10)
             and close(pa["qty"], 15 / 98.5) and close(pb["qty"], 10 / 99.0)
             and close(pa["fee_eur"], 0.0075) and close(pb["fee_eur"], 0.005), json.dumps([pa, pb])[:400])
    rt.check("fill records: position_id, merged false, risk_level", rb["fill"].get("position_id") == pb["id"]
             and rb["fill"].get("merged") is False and rb["fill"].get("risk_level") == "risquee", json.dumps(rb["fill"])[:300])
    rt.check("cash / exposure summary over both", close(s["cash_eur"], 500 - 25.0125) and close(s.get("exposure_eur"), 25)
             and close(s.get("equity_eur"), 500 - 0.0125, 1e-4), f"cash={s['cash_eur']} exp={s.get('exposure_eur')}")
    rc_, rcc = rt.paper_fill(env, dict(A, amount_eur=5, price=98.0, stop_price=97.0, target_price=100.5, risk_level="prudente"))
    s = rt.state_of(T); pa2 = by_did(s, "D-024a"); pb2 = by_did(s, "D-024b")[0]
    rt.check("same decision_id → merges into its own position only (old behaviour)", rcc == 0 and len(pa2) == 1
             and close(pa2[0]["cost_eur"], 20) and pa2[0]["stop_price"] == 97.0 and pa2[0]["target_price"] == 100.5
             and pa2[0]["risk_level"] == "prudente" and rc_["fill"].get("merged") is True
             and close(pb2["cost_eur"], 10) and pb2["stop_price"] == 98.60 and pb2["target_price"] == 101.60,
             json.dumps(pa2)[:300])
    rn, rcn = rt.paper_fill(env, {k: v for k, v in dict(A, amount_eur=3).items() if k not in ("decision_id", "risk_level")})
    s = rt.state_of(T)
    rt.check("order without decision_id → new position (never merged into a decision)", rcn == 0
             and len([p for p in s["positions"] if p["status"] == "open" and p["pair"] == "SOL-EUR"]) == 3,
             str(rn.get("reasons")))


def test_manual_sells_target_one_position():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, A); rt.paper_fill(env, B)
    s = rt.state_of(T); pa, pb = by_did(s, "D-024a")[0], by_did(s, "D-024b")[0]
    sell = {"pair": "SOL-EUR", "side": "sell", "type": "limit", "price": 100.0, "amount_eur": 10, "idea_type": "hausse"}
    r0, rc0 = rt.paper_fill(env, sell)
    v0, vrc0 = validate(env, sell)
    rt.check("sell with 2 SOL longs and no id → refused (paper_fill + validate), nothing closed", rc0 != 0 and vrc0 == 1
             and any("préciser" in x for x in r0.get("reasons", []) + v0["reasons"])
             and all(p["status"] == "open" for p in rt.state_of(T)["positions"]), str(r0.get("reasons")))
    r1, rc1 = rt.paper_fill(env, dict(sell, decision_id="D-024b"))
    s = rt.state_of(T); pa1, pb1 = by_did(s, "D-024a")[0], by_did(s, "D-024b")[0]
    qb = 10 / 99.0; gross = qb * 100 - 10; fees = 0.005 + round(qb * 100 * FEE, 6)
    rt.check("sell with decision_id D-024b closes D-024b only; D-024a untouched", rc1 == 0 and pb1["status"] == "closed"
             and pa1["status"] == "open" and close(pa1["cost_eur"], 15) and close(pa1["qty"], pa["qty"])
             and r1["fill"].get("linked_position_id") == pb["id"] and r1["fill"].get("risk_level") == "risquee"
             and close(r1["fill"].get("realized_pnl_eur"), gross - fees, 2e-6), json.dumps(r1.get("fill"))[:300])
    rt.check("cash after manual close = sale proceeds − sell fee",
             close(s["cash_eur"], 500 - 25.0125 + qb * 100 - round(qb * 100 * FEE, 6)) and close(s.get("exposure_eur"), 15),
             f"cash={s['cash_eur']}")
    r2, rc2 = rt.paper_fill(env, dict(sell, linked_position_id=pb["id"]))
    rt.check("sell linked to an already-closed position → refused, D-024a not touched", rc2 != 0
             and by_did(rt.state_of(T), "D-024a")[0]["status"] == "open", str(r2.get("reasons")))
    r3, rc3 = rt.paper_fill(env, dict(sell, amount_eur=20, linked_position_id=pa["id"]))
    rt.check("sell bigger than the designated position → refused by validate", rc3 != 0
             and by_did(rt.state_of(T), "D-024a")[0]["status"] == "open", str(r3.get("reasons")))
    r4, rc4 = rt.paper_fill(env, dict(sell, amount_eur=15, position_id=pa["id"]))
    s = rt.state_of(T)
    rt.check("sell with position_id closes D-024a (now the only long)", rc4 == 0
             and by_did(s, "D-024a")[0]["status"] == "closed" and close(s.get("exposure_eur"), 0), str(r4.get("reasons")))


def test_watcher_closes_only_breached_long():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BTC); rt.paper_fill(env, A); rt.paper_fill(env, B)
    s0 = rt.state_of(T); pa0, pb0 = by_did(s0, "D-024a")[0], by_did(s0, "D-024b")[0]
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74200)
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 99.2)
    lines, rc, err = rt.watch_once(env)
    w = {x["id"]: x for x in (lines[-1].get("watching") or [])} if lines else {}
    rt.check("watcher watches 3 positions, each with its own stop/target", rc == 0 and len(w) == 3
             and w[pa0["id"]]["stop"] == 97.30 and w[pa0["id"]]["target_price"] == 100.09
             and w[pb0["id"]]["stop"] == 98.60 and w[pb0["id"]]["target_price"] == 101.60, err[-300:])
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 98.5)  # < 98.60 (B stop) but > 97.30 (A stop)
    lines, rc, err = rt.watch_once(env)
    s = rt.state_of(T); pa, pb = by_did(s, "D-024a")[0], by_did(s, "D-024b")[0]
    btc = by_did(s, "D-023")[0]
    qb = 10 / 99.0; sell_fee = round(qb * 98.5 * FEE, 6); gross = qb * 98.5 - 10
    rt.check("mid 98.5: only D-024b (stop 98.60) closes, stop_hit", rc == 10 and pb["status"] == "closed"
             and pb.get("close_reason") == "stop_hit" and pa["status"] == "open" and btc["status"] == "open", err[-300:])
    rt.check("D-024a intact: qty, cost, fee, stop, target, risk_level unchanged",
             close(pa["qty"], pa0["qty"]) and close(pa["cost_eur"], 15) and close(pa["fee_eur"], 0.0075)
             and pa["stop_price"] == 97.30 and pa["target_price"] == 100.09 and pa["risk_level"] == "equilibree"
             and not pa.get("close_reason"), json.dumps(pa)[:300])
    rt.check("D-024b realized net (buy + sell fee); cash = before + gross − sell fee",
             close(pb.get("realized_pnl_eur"), gross - 0.005 - sell_fee, 2e-6)
             and close(s["cash_eur"], s0["cash_eur"] + 10 + gross - sell_fee, 2e-6),
             f"realized={pb.get('realized_pnl_eur')} cash={s['cash_eur']} vs {s0['cash_eur'] + 10 + gross - sell_fee}")
    qa = pa0["qty"]; qbtc = btc["qty"]
    unreal = (qa * 98.5 - 15 - 0.0075) + (qbtc * 74200 - 20 - 0.01)
    rt.check("dashboard: exposure 35, unrealized over the 2 open, equity = cash + marks",
             close(s.get("exposure_eur"), 35) and close(s.get("unrealized_pnl_eur"), unreal, 2e-4)
             and close(s.get("equity_eur"), s["cash_eur"] + qa * 98.5 + qbtc * 74200, 2e-4),
             f"exp={s.get('exposure_eur')} unr={s.get('unrealized_pnl_eur')} vs {unreal:.4f}")
    trades = [json.loads(l) for l in (T / "state/trades_log.jsonl").read_text().splitlines()]
    last = trades[-1]
    rt.check("journal sell row linked to D-024b's id", last["side"] == "sell" and last.get("linked_position_id") == pb0["id"]
             and last.get("decision_id") == "D-024b", json.dumps(last)[:300])
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 100.10)
    lines, rc, err = rt.watch_once(env)
    s = rt.state_of(T); pa = by_did(s, "D-024a")[0]
    rt.check("mid 100.10 ≥ 100.09 → D-024a closes target_hit; BTC still open", rc == 10 and pa["status"] == "closed"
             and pa.get("close_reason") == "target_hit" and by_did(s, "D-023")[0]["status"] == "open"
             and close(s.get("exposure_eur"), 20), err[-300:])


def test_two_shorts_separate():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    s1 = dict(rt.SELL_SOL, risk_level="prudente")
    s2 = dict(rt.SELL_SOL, decision_id="T-3", stop_price=99, target_price=92, risk_level="risquee")
    r1, rc1 = rt.paper_fill(env, s1); r2, rc2 = rt.paper_fill(env, s2)
    s = rt.state_of(T); p1, p2 = by_did(s, "T-2")[0], by_did(s, "T-3")[0]
    inv0 = 0.241308
    rt.check("two SOL shorts: 2 positions, own stop/target/risk_level, inventory debited twice", rc1 == rc2 == 0
             and p1["id"] != p2["id"] and p1["risk_level"] == "prudente" and p2["risk_level"] == "risquee"
             and p1["stop_price"] == 100 and p2["stop_price"] == 99 and close(s["paper_inventory"]["SOL"], inv0 - 0.2, 1e-9),
             json.dumps(s["paper_inventory"]))
    rb = {"pair": "SOL-EUR", "side": "buy", "type": "limit", "price": 95, "amount_eur": 9.5, "qty": 0.1,
          "idea_type": "baisse", "rebuy_reason": "target", "post_only": True}
    r0, rc0 = rt.paper_fill(env, rb)
    rt.check("rebuy with 2 open SOL shorts and no id → refused", rc0 != 0
             and all(p["status"] == "open" for p in rt.state_of(T)["positions"]), str(r0.get("reasons")))
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 99.5)  # ≥ 99 (T-3 safety), < 100 (T-2)
    lines, rc, err = rt.watch_once(env)
    s = rt.state_of(T); p1, p2 = by_did(s, "T-2")[0], by_did(s, "T-3")[0]
    rt.check("mid 99.5: only T-3 bought back (safety); T-2 open; inventory credited 0.1 only", rc == 10
             and p2["status"] == "closed" and p2.get("close_reason") == "stop_hit" and p1["status"] == "open"
             and close(p1["qty"], 0.1) and close(s["paper_inventory"]["SOL"], inv0 - 0.1, 1e-9)
             and close(s.get("exposure_eur"), 9.6), err[-300:] + json.dumps(s["paper_inventory"]))
    r3, rc3 = rt.paper_fill(env, dict(rb, decision_id="T-2", linked_position_id=p2["id"]))
    rt.check("rebuy linked to the already-closed short → refused (no fallback to T-2)", rc3 != 0
             and by_did(rt.state_of(T), "T-2")[0]["status"] == "open", str(r3.get("reasons")))
    r4, rc4 = rt.paper_fill(env, dict(rb, decision_id="T-2"))
    s = rt.state_of(T)
    rt.check("rebuy by decision_id T-2 closes T-2; inventory back to start", rc4 == 0
             and by_did(s, "T-2")[0]["status"] == "closed" and close(s["paper_inventory"]["SOL"], inv0, 1e-9)
             and r4["fill"].get("risk_level") == "prudente" and close(s.get("exposure_eur"), 0), str(r4.get("reasons")))


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_open_separate_and_same_decision_merge, test_manual_sells_target_one_position,
                  test_watcher_closes_only_breached_long, test_two_shorts_separate):
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
