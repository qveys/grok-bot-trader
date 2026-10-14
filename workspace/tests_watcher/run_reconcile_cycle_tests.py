#!/usr/bin/env python3
"""Rapprochement Revolut + cycle_id (9 oct). Paper temp dirs + copied live tree with FAKE revx.
Never places a real order, never touches the real state."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt
from run_live_tests import Tree, ENTRY, sells

G = rt.G
BUY = {"pair": "BTC-EUR", "side": "buy", "type": "limit", "price": 74120, "amount_eur": 20, "stop_price": 73379,
       "target_price": 75232, "idea_type": "hausse", "decision_id": "D-C1", "post_only": True}


def close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def reco_cli(env, cwd_script, *args):
    p = subprocess.run([sys.executable, str(cwd_script), *args], text=True, capture_output=True, env=env, timeout=120)
    return json.loads(p.stdout.strip().splitlines()[-1]), p.returncode


def test_sim_block():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, BUY)
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 74200)
    lines, rc, err = rt.watch_once(env)
    b = rt.state_of(T).get("rapprochement_revolut") or {}
    rt.check("sim: watcher summary refresh writes the block when missing", rc == 0 and b.get("mode") == "simulation"
             and b.get("gain_revolut_eur") == "sans objet" and b.get("ecart_eur") == "sans objet"
             and b.get("gain_equipe_eur") == 0 and b.get("note") == "simulation : pas d'ordre réel"
             and str(b.get("controle_at", "")).endswith(("+02:00", "+01:00")), json.dumps(b) + err[-200:])
    r, rc = reco_cli(env, G / "reconcile_revolut.py")
    calls = (T / "revx_calls.log").read_text() if (T / "revx_calls.log").exists() else ""
    rt.check("sim: reconcile_revolut.py writes 'sans objet', no revx order call", rc == 0 and r["rapprochement_revolut"]["mode"] == "simulation"
             and "order" not in calls and rt.state_of(T)["rapprochement_revolut"]["ecart_eur"] == "sans objet", calls[-200:])
    s = rt.state_of(T)
    rt.check("sim: positions / cash untouched by the reconciliation", len(s["positions"]) == 1 and s["positions"][0]["status"] == "open"
             and close(s["cash_eur"], 500 - 20.01))


def test_live_reconcile():
    T = Tree(); T.env["WATCH_STOPS_NO_AUTOSTART"] = "1"
    T.tick(2170)
    r, rc = T.live_place(dict(ENTRY, target_price=2250))
    T.tick(2260, bid=2259, ask=2261)
    lines, rc2 = T.watch_once()
    ax = [x for x in T.rows() if x.get("kind") == "auto_exit"]
    team = ax[0]["realized_pnl_eur"] if ax else None
    n_before = len(T.calls())
    out, rc3 = reco_cli(T.env, T.L / "guardian/scripts/reconcile_revolut.py")
    b = out.get("rapprochement_revolut") or {}
    new_calls = T.calls()[n_before:]
    rt.check("live: gain_equipe = net realized of live_orders; gain_revolut from Revolut fills; écart ≈ 0", rc == 0 and rc3 == 0
             and b.get("mode") == "live" and close(b.get("gain_equipe_eur"), team) and close(b.get("gain_revolut_eur"), team, 1e-5)
             and close(b.get("ecart_eur"), 0, 1e-5) and b.get("cycles_controles") == 1, json.dumps(b)[:400])
    rt.check("live: only read-only revx calls (order history / order get), never place/cancel",
             new_calls and all(c.startswith(("order history", "order get")) for c in new_calls), str(new_calls))
    rt.check("live: block saved in guardian/state.json", T.read("guardian/state.json").get("rapprochement_revolut", {}).get("mode") == "live")
    # Revolut reports a worse exit fill (−0.50 €) → écart = équipe − revolut ≈ +0.50025
    d = T.fake(); ex = [o for o in d["orders"].values() if o["side"] == "sell"][0]
    ex["filled_amount"] = str(float(ex["filled_amount"]) - 0.5); ex["fee"] = "0.0011"; T.fs.write_text(json.dumps(d))
    out, rc4 = reco_cli(T.env, T.L / "guardian/scripts/reconcile_revolut.py")
    b = out["rapprochement_revolut"]
    rt.check("live: écart shows a Revolut fill difference (équipe − revolut)", rc4 == 0 and b["ecart_eur"] > 0.49
             and b["ecart_eur"] < 0.52 and close(b["gain_equipe_eur"] - b["gain_revolut_eur"], b["ecart_eur"]), json.dumps(b)[:300])
    # watcher helper: live trade today → runs (5-min cadence) with network
    code = ("import sys,json;sys.argv=['x'];import watch_stops as w;b=w.maybe_reconcile();b2=w.maybe_reconcile();"
            "print(json.dumps([b and b.get('mode'), b2]))")
    p = subprocess.run([sys.executable, "-c", code], cwd=str(T.L / "guardian/scripts"), text=True, capture_output=True, env=T.env, timeout=120)
    res = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else None
    rt.check("watcher maybe_reconcile: live trade today → reconciles, then waits ~5 min (2nd call skipped)",
             res == ["live", None], (p.stdout + p.stderr)[-300:])


def test_watcher_sim_daily_once():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    code = ("import sys,json;sys.argv=['x'];import watch_stops as w;a=w.maybe_reconcile();b=w.maybe_reconcile();"
            "print(json.dumps([a and a.get('mode'), b]))")
    p = subprocess.run([sys.executable, "-c", code], cwd=str(G), text=True, capture_output=True, env=env, timeout=60)
    res = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else None
    rt.check("watcher sim: writes 'sans objet' once a day (2nd call same day skipped)", res == ["simulation", None]
             and rt.state_of(T)["rapprochement_revolut"]["gain_revolut_eur"] == "sans objet", (p.stdout + p.stderr)[-300:])


def test_cycle_ids():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    r1, _ = rt.paper_fill(env, rt.SELL_SOL)
    pid = rt.state_of(T)["positions"][0]["id"]
    r2, _ = rt.paper_fill(env, {"pair": "SOL-EUR", "side": "buy", "type": "limit", "price": 95, "amount_eur": 9.5, "qty": 0.1,
                                "idea_type": "baisse", "rebuy_reason": "target", "linked_position_id": pid, "post_only": True})
    log = [json.loads(l) for l in (T / "state/trades_log.jsonl").read_text().splitlines()]
    rt.check("baisse: open sale line + return carry cycle_id = short position id; rebuy same cycle_id",
             r1["fill"].get("cycle_id") == pid and log[0].get("cycle_id") == pid and log[1].get("cycle_id") == pid
             and r2["fill"].get("cycle_id") == pid, json.dumps([l.get("cycle_id") for l in log]))
    rt.paper_fill(env, BUY)
    rt.paper_fill(env, dict(BUY, amount_eur=4, price=74100))
    s = rt.state_of(T); lp = [p for p in s["positions"] if p.get("decision_id") == "D-C1"][0]
    rt.write_tick(T / "state/price_ticks", "BTC-EUR", 75300)
    lines, rc, err = rt.watch_once(env)
    log = [json.loads(l) for l in (T / "state/trades_log.jsonl").read_text().splitlines()]
    longs = [l for l in log if l.get("pair") == "BTC-EUR"]
    rt.check("hausse: buy, merged buy and watcher sale all carry cycle_id = long position id",
             len(longs) == 3 and all(l.get("cycle_id") == lp["id"] for l in longs) and longs[-1]["side"] == "sell"
             and rc == 10, json.dumps([(l["side"], l.get("cycle_id")) for l in longs]) + err[-200:])


def test_full_qty_close_no_residue():
    FEE = 0.0005
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    A = {"pair": "SOL-EUR", "side": "buy", "type": "limit", "price": 98.5, "amount_eur": 15, "stop_price": 97.30,
         "target_price": 100.09, "idea_type": "hausse", "decision_id": "D-024a", "post_only": True}
    rt.paper_fill(env, A)
    p0 = rt.state_of(T)["positions"][0]
    sell = {"pair": "SOL-EUR", "side": "sell", "type": "limit", "price": 97.74, "qty": p0["qty"], "idea_type": "hausse",
            "decision_id": "D-024a", "close_reason": "idee_morte"}
    r, rc = rt.paper_fill(env, sell)
    s = rt.state_of(T); p = s["positions"][0]
    proceeds = p0["qty"] * 97.74; sf = round(proceeds * FEE, 6)
    rt.check("D-024a replica: sell of full qty BELOW entry closes fully (no residue)", rc == 0 and p["status"] == "closed"
             and p["qty"] == 0 and p["cost_eur"] == 0 and len(s["positions"]) == 1 and close(s.get("exposure_eur"), 0),
             json.dumps(p)[:300] + str(r.get("reasons")))
    rt.check("full-qty sell: cash = 500 − cost − buy fee + proceeds − sell fee; realized net",
             close(s["cash_eur"], 500 - 15.0075 + proceeds - sf, 2e-6)
             and close(r["fill"].get("realized_pnl_eur"), proceeds - 15 - 0.0075 - sf, 2e-6), f"cash={s['cash_eur']}")
    # full qty ABOVE entry (amount > cost) is allowed by validate and closes fully
    T2 = rt.new_root(); env2 = rt.make_env(T2, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env2, A); q = rt.state_of(T2)["positions"][0]["qty"]
    r2, rc2 = rt.paper_fill(env2, dict(sell, price=99.9, qty=q))
    rt.check("sell of full qty ABOVE entry accepted and fully closes", rc2 == 0
             and rt.state_of(T2)["positions"][0]["status"] == "closed", str(r2.get("reasons")))
    # partial sell leaving < 1 centime → dust closed too
    T3 = rt.new_root(); env3 = rt.make_env(T3, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env3, A); q = rt.state_of(T3)["positions"][0]["qty"]
    r3, rc3 = rt.paper_fill(env3, dict(sell, qty=q - 0.00005))  # reste 0.00005 × 97.74 ≈ 0.005 €
    p3 = rt.state_of(T3)["positions"][0]
    rt.check("sell leaving a residue < 0.01 € closes the whole position", rc3 == 0 and p3["status"] == "closed" and p3["qty"] == 0,
             json.dumps(p3)[:200])
    r4, rc4 = rt.paper_fill(env3, dict(sell, qty=0.001))
    rt.check("nothing left to sell afterwards (refused)", rc4 != 0)
    # real partial still partial
    T4 = rt.new_root(); env4 = rt.make_env(T4, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env4, A); q = rt.state_of(T4)["positions"][0]["qty"]
    rt.paper_fill(env4, dict(sell, qty=q / 2))
    p4 = rt.state_of(T4)["positions"][0]
    rt.check("a real half sell stays a partial (half qty, half cost, half fee left)", p4["status"] == "open"
             and close(p4["qty"], q / 2) and close(p4["cost_eur"], 7.5) and close(p4["fee_eur"], 0.00375), json.dumps(p4)[:200])
    # watcher close below entry: full close, cash = proceeds
    T5 = rt.new_root(); env5 = rt.make_env(T5, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env5, A); q = rt.state_of(T5)["positions"][0]["qty"]
    rt.write_tick(T5 / "state/price_ticks", "SOL-EUR", 97.2)
    lines, rc5, err = rt.watch_once(env5)
    s5 = rt.state_of(T5); p5 = s5["positions"][0]
    pr = q * 97.2; sf5 = round(pr * FEE, 6)
    rt.check("watcher stop close below entry: closed fully, qty 0, cash = proceeds − fees (no double count)",
             rc5 == 10 and p5["status"] == "closed" and p5["qty"] == 0 and close(s5["cash_eur"], 500 - 15.0075 + pr - sf5, 2e-6)
             and close(p5.get("realized_pnl_eur"), pr - 15 - 0.0075 - sf5, 2e-6), f"cash={s5['cash_eur']} {err[-200:]}")


def test_short_rebuy_no_residue():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env, rt.SELL_SOL)
    pid = rt.state_of(T)["positions"][0]["id"]
    rb = {"pair": "SOL-EUR", "side": "buy", "type": "limit", "price": 95, "qty": 0.1 - 0.00005, "idea_type": "baisse",
          "rebuy_reason": "target", "linked_position_id": pid, "post_only": True}
    r, rc = rt.paper_fill(env, rb)
    s = rt.state_of(T); p = s["positions"][0]
    rt.check("short rebuy leaving < 0.01 € closes fully; inventory gets the full 0.1 back", rc == 0 and p["status"] == "closed"
             and p["qty"] == 0 and close(r["fill"]["qty"], 0.1) and close(s["paper_inventory"]["SOL"], 0.241308, 1e-9),
             json.dumps(p)[:200] + json.dumps(s["paper_inventory"]))
    T2 = rt.new_root(); env2 = rt.make_env(T2, {"PAPER_FILL_NO_WATCH": "1"})
    rt.paper_fill(env2, rt.SELL_SOL); pid2 = rt.state_of(T2)["positions"][0]["id"]
    r2, rc2 = rt.paper_fill(env2, dict(rb, qty=0.05, linked_position_id=pid2))
    p2 = rt.state_of(T2)["positions"][0]
    rt.check("short half rebuy stays partial", rc2 == 0 and p2["status"] == "open" and close(p2["qty"], 0.05))


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_sim_block, test_live_reconcile, test_watcher_sim_daily_once, test_cycle_ids,
                  test_full_qty_close_no_residue, test_short_rebuy_no_residue):
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
