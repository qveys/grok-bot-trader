#!/usr/bin/env python3
"""Champs tableau (9 oct) + plafond simulation 50 € + max_live_per_day + résultat net des sorties live.
Temp dirs / copied trees + FAKE revx only. Never places a real order, never touches the real state."""
from __future__ import annotations
import fcntl, json, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt
from run_live_tests import Tree, ENTRY, QTY, entry_row_via_fake

G = rt.G
REAL_CONFIG = rt.REPO / "guardian/config.json"


def close(a, b, tol=1e-6):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def d021_state():
    st = rt.base_state()
    st["cash_eur"] = 513.966374
    st["paper_inventory"]["SOL"] = 0.091308
    st["positions"] = [{
        "id": "rx-paper-test-d021", "pair": "SOL-EUR", "side": "short", "idea_type": "baisse", "kind": "baisse",
        "qty": 0.15, "avg_price": 98.0, "cost_eur": 14.7, "mark_eur": 14.7, "stop_price": 99.47,
        "stop_price_eur": 99.47, "safety_price": 99.47, "target_price": 96.53, "decision_id": "D-021",
        "venue": "revolut_x", "fee_eur": 0.00735, "status": "open"}]
    return st


# ---------------------------------------------------------------- watcher marks / summary
def test_watcher_marks_short_and_long():
    st = d021_state()
    st["cash_eur"] = 513.966374 - 20.0
    st["positions"].append({"id": "rx-paper-test-eth-long", "pair": "ETH-EUR", "side": "long", "idea_type": "hausse",
                            "qty": 0.01, "avg_price": 2000.0, "cost_eur": 20.0, "mark_eur": 20.0,
                            "stop_price_eur": 1900.0, "status": "open"})
    T = rt.new_root(st); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 99.125)
    rt.write_tick(T / "state/price_ticks", "ETH-EUR", 2100.0)
    lines, rc, err = rt.watch_once(env)
    s = rt.state_of(T)
    sol = next(p for p in s["positions"] if p["pair"] == "SOL-EUR")
    eth = next(p for p in s["positions"] if p["pair"] == "ETH-EUR")
    rt.check("watch: D-021 short marked (mid 99.125 → mark 14.86875, P&L −0.1761 / −1.198 %)",
             rc == 0 and sol.get("last_mid_eur") == 99.125 and close(sol.get("mark_eur"), 14.86875)
             and close(sol.get("unrealized_pnl_eur"), -0.1761, 1e-9) and close(sol.get("unrealized_pnl_pct"), -1.198, 1e-9)
             and str(sol.get("mark_ts", "")).endswith(("+02:00", "+01:00")),
             json.dumps({k: sol.get(k) for k in rt.DASHBOARD_POS_FIELDS}) + err[-200:])
    rt.check("watch: long marked (qty×mid − cost − fee = +1.0 / +5 %)",
             close(eth.get("mark_eur"), 21.0) and close(eth.get("unrealized_pnl_eur"), 1.0) and close(eth.get("unrealized_pnl_pct"), 5.0),
             json.dumps({k: eth.get(k) for k in rt.DASHBOARD_POS_FIELDS}))
    eq = 513.966374 - 20.0 - 14.86875 + 21.0
    rt.check("watch: top-level equity / exposure / unrealized / total / drawdown",
             close(s.get("equity_eur"), eq) and close(s.get("exposure_eur"), 34.7) and close(s.get("exposure_pct"), 0.0694)
             and close(s.get("unrealized_pnl_eur"), -0.1761 + 1.0, 1e-4) and close(s.get("total_pnl_eur"), eq - 500, 1e-4)
             and close(s.get("peak_equity_eur"), max(500, eq)) and close(s.get("drawdown_pct"), round(max(0.0, (max(500, eq) - eq) / max(500, eq)), 6))
             and s.get("summary_updated_at"),
             json.dumps({k: s.get(k) for k in rt.DASHBOARD_TOP_FIELDS}))
    rt.check("watch: other state fields untouched (cash, inventory, stops)",
             s["cash_eur"] == st["cash_eur"] and s["paper_inventory"] == st["paper_inventory"]
             and sol["stop_price"] == 99.47 and sol["status"] == "open" and sol["cost_eur"] == 14.7)
    # exact replica of the hand-written D-021 figures (only D-021 open)
    T2 = rt.new_root(d021_state()); env2 = rt.make_env(T2, {"PAPER_FILL_NO_WATCH": "1"})
    rt.write_tick(T2 / "state/price_ticks", "SOL-EUR", 99.125)
    rt.watch_once(env2)
    s2 = rt.state_of(T2)
    rt.check("watch: same numbers as the hand-written D-021 state (equity 499.097624, exposure 14.7 / 0.0294, total −0.9024, DD 0.001805)",
             close(s2.get("equity_eur"), 499.097624) and close(s2.get("exposure_eur"), 14.7) and close(s2.get("exposure_pct"), 0.0294)
             and close(s2.get("unrealized_pnl_eur"), -0.1761, 1e-9) and close(s2.get("total_pnl_eur"), -0.9024, 1e-9)
             and close(s2.get("drawdown_pct"), 0.001805),
             json.dumps({k: s2.get(k) for k in rt.DASHBOARD_TOP_FIELDS}))


def test_dry_run_no_write_and_idle_summary():
    T = rt.new_root(d021_state()); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 99.125)
    before = (T / "guardian_state.json").read_bytes()
    lines, rc, err = rt.watch_once(env, "--dry-run")
    rt.check("--dry-run: guardian state not written", (T / "guardian_state.json").read_bytes() == before and rc == 0)
    # no open position: top-level fields still right (stale values replaced)
    st = rt.base_state(); st["cash_eur"] = 500.101124
    st["positions"] = [{"id": "x-closed", "pair": "SOL-EUR", "side": "short", "idea_type": "baisse", "qty": 0.0,
                        "cost_eur": 0.0, "mark_eur": 0.0, "status": "closed"}]
    st.update({"exposure_eur": 14.7, "exposure_pct": 0.0294, "unrealized_pnl_eur": -0.17, "total_pnl_eur": -0.9, "equity_eur": 499.0})
    T2 = rt.new_root(st); env2 = rt.make_env(T2, {"PAPER_FILL_NO_WATCH": "1"})
    lines, rc, err = rt.watch_once(env2)
    s = rt.state_of(T2)
    rt.check("idle: exposure 0, unrealized 0, equity = cash, total = equity − bankroll",
             rc == 0 and lines[-1].get("action") == "idle" and s.get("exposure_eur") == 0 and s.get("exposure_pct") == 0
             and s.get("unrealized_pnl_eur") == 0 and close(s.get("equity_eur"), 500.101124)
             and close(s.get("total_pnl_eur"), 0.1011, 1e-9) and s.get("summary_updated_at"),
             json.dumps({k: s.get(k) for k in rt.DASHBOARD_TOP_FIELDS}))
    m1 = (T2 / "guardian_state.json").stat().st_mtime_ns
    time.sleep(0.05)
    rt.watch_once(env2)
    rt.check("idle again with unchanged values: no rewrite", (T2 / "guardian_state.json").stat().st_mtime_ns == m1)


def test_paper_fill_refreshes_summary():
    T = rt.new_root(); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    r, rc = rt.paper_fill(env, rt.SELL_SOL)
    s = rt.state_of(T)
    p = s["positions"][0]
    rt.check("paper_fill open: exposure 9.6 / 0.0192, unrealized −fee, total = equity − bankroll",
             rc == 0 and close(s.get("exposure_eur"), 9.6) and close(s.get("exposure_pct"), 0.0192)
             and close(s.get("unrealized_pnl_eur"), -0.0048) and close(s.get("equity_eur"), 499.9952)
             and close(s.get("total_pnl_eur"), -0.0048) and s.get("summary_updated_at")
             and p.get("last_mid_eur") == 96 and p.get("mark_ts"),
             json.dumps({k: s.get(k) for k in rt.DASHBOARD_TOP_FIELDS}) + str(r.get("reasons")))
    rebuy = {"pair": "SOL-EUR", "side": "buy", "type": "limit", "price": 95, "qty": 0.1, "amount_eur": 9.5,
             "idea_type": "baisse", "linked_position_id": p["id"], "rebuy_reason": "target", "post_only": True}
    r2, rc2 = rt.paper_fill(env, rebuy)
    s = rt.state_of(T)
    realized = (96 - 95) * 0.1 - 0.0048 - 0.00475
    rt.check("paper_fill close: exposure 0, unrealized 0, total = realized",
             rc2 == 0 and s.get("exposure_eur") == 0 and s.get("unrealized_pnl_eur") == 0
             and close(s.get("total_pnl_eur"), realized, 1e-4) and close(s.get("equity_eur"), 500 + realized),
             json.dumps({k: s.get(k) for k in rt.DASHBOARD_TOP_FIELDS}))


def test_lock_and_no_clobber():
    T = rt.new_root(d021_state()); env = rt.make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    rt.write_tick(T / "state/price_ticks", "SOL-EUR", 99.0)
    sp = T / "guardian_state.json"
    before = sp.read_bytes()
    with open(str(sp) + ".lock", "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        proc = subprocess.Popen([sys.executable, str(G / "watch_stops.py"), "--once"], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(2.5)
        waiting = proc.poll() is None and sp.read_bytes() == before
        fcntl.flock(fh, fcntl.LOCK_UN)
    proc.wait(timeout=60)
    s = rt.state_of(T)
    rt.check("watcher waits for the state lock (held by a paper_fill) before writing", waiting
             and s["positions"][0].get("last_mid_eur") == 99.0)
    # live watcher every 1 s + 6 paper fills in a row: no fill lost
    proc = subprocess.Popen([sys.executable, str(G / "watch_stops.py"), "--interval", "1"], env=env,
                            stdout=open(T / "state/watch_stops.log", "a"), stderr=subprocess.STDOUT)
    try:
        time.sleep(1.5)
        oks = 0
        for i in range(6):
            rt.write_tick(T / "state/price_ticks", "SOL-EUR", 99.0 + i * 0.01)
            rt.write_tick(T / "state/price_ticks", "BTC-EUR", 72000 + i)
            r, rc = rt.paper_fill(env, dict(rt.BUY_BTC, amount_eur=2, decision_id=f"T-C{i}"))
            oks += rc == 0
            time.sleep(0.4)
        time.sleep(2.5)
    finally:
        proc.terminate(); proc.wait(timeout=10)
    s = rt.state_of(T)
    btc = [p for p in s["positions"] if p["pair"] == "BTC-EUR" and p["status"] == "open"]
    n_trades = len((T / "state/trades_log.jsonl").read_text().splitlines())
    rt.check("concurrent watcher + 6 paper fills: nothing clobbered (cash, BTC cost, trades)",
             oks == 6 and n_trades == 6 and close(s["cash_eur"], 513.966374 - 12 - 6 * 0.001)  # 0,05 % buy fee per 2 € fill (9 oct) and btc and close(btc[0]["cost_eur"], 12)
             and close(s.get("exposure_eur"), 26.7) and btc[0].get("mark_ts"),
             f"oks={oks} trades={n_trades} cash={s['cash_eur']} btc={btc[0]['cost_eur'] if btc else None} exp={s.get('exposure_eur')}")
    rt.check("no stray tmp files next to the state", not list(T.glob("guardian_state.json.*.tmp")))


# ---------------------------------------------------------------- simulation cap 50 € / live 25 €
def validate(state, order, live=False, cfg=None):
    T = rt.new_root(state)
    env = rt.make_env(T, {"GUARDIAN_CONFIG": str(cfg or REAL_CONFIG)})
    args = [sys.executable, str(G / "validate_order.py")] + (["--live"] if live else [])
    p = subprocess.run(args, input=json.dumps(order), text=True, capture_output=True, env=env, timeout=30)
    return json.loads(p.stdout), p.returncode


def open_paper(costs):
    st = rt.base_state()
    st["positions"] = [rt.pos_long("ETH-EUR", 2000, 1900, cost=c) for c in costs]
    for i, p in enumerate(st["positions"]):
        p["id"] += f"-{i}"
    st["cash_eur"] = 500 - sum(costs)
    return st


def buy(amount):
    return {"pair": "BTC-EUR", "side": "buy", "type": "limit", "price": 72000, "amount_eur": amount,
            "stop_price": 70000, "idea_type": "hausse", "decision_id": "T-CAP", "post_only": True}


def test_paper_cap_50():
    cfg = json.loads(REAL_CONFIG.read_text())
    rt.check("config: paper_max_exposure_pct 0.10, max_exposure_pct 0.05, max_position_pct 0.05, max_live_per_day 1",
             cfg.get("paper_max_exposure_pct") == 0.10 and cfg.get("max_exposure_pct") == 0.05
             and cfg.get("max_position_pct") == 0.05 and cfg.get("max_live_per_day") == 1)
    r, rc = validate(open_paper([25, 20]), buy(5))
    rt.check("paper: exposure 45 € + 5 € → allowed (total 50 €)", rc == 0 and r["ok"], str(r.get("reasons")))
    r, rc = validate(open_paper([25, 25]), buy(1))
    rt.check("paper: exposure 50 € + 1 € → refused", rc == 1 and any("exposure" in x for x in r["reasons"]), str(r.get("reasons")))
    r, rc = validate(open_paper([]), buy(26))
    rt.check("paper: single trade 26 € → refused (≤ 25 € per trade)", rc == 1 and any("max_position_pct" in x for x in r["reasons"]),
             str(r.get("reasons")))
    r, rc = validate(open_paper([20]), buy(10))
    rt.check("paper: 20 € + 10 € = 30 € → allowed (was refused at 25 €)", rc == 0 and r["ok"], str(r.get("reasons")))
    sell = {"pair": "SOL-EUR", "side": "sell", "type": "limit", "price": 96, "amount_eur": 9.6, "qty": 0.1,
            "idea_type": "baisse", "decision_id": "T-S", "stop_price": 100, "post_only": True}
    r, rc = validate(open_paper([25, 20]), sell)
    rt.check("paper: baisse 9.6 € on top of 45 € → refused (shorts count too)", rc == 1, str(r.get("reasons")))
    # live (validate_order --live, as live_place calls it) keeps 25 € total
    r, rc = validate(open_paper([20]), buy(10), live=True)
    rt.check("live (--live): 20 € + 10 € = 30 € → refused (live cap 25 € unchanged)", rc == 1
             and any("max_exposure 25.0000" in x for x in r["reasons"]), str(r.get("reasons")))
    r, rc = validate(open_paper([15]), buy(10), live=True)
    rt.check("live (--live): 15 € + 10 € = 25 € → allowed", rc == 0 and r["ok"], str(r.get("reasons")))
    r, rc = validate(open_paper([]), buy(26), live=True)
    rt.check("live (--live): single 26 € → refused", rc == 1, str(r.get("reasons")))
    # config without the new key → paper falls back to max_exposure_pct (old behaviour)
    T = rt.new_root(); c2 = T / "cfg.json"
    cfg.pop("paper_max_exposure_pct", None); c2.write_text(json.dumps(cfg))
    r, rc = validate(open_paper([20]), buy(10), cfg=c2)
    rt.check("config without paper_max_exposure_pct → paper back to 25 € total", rc == 1, str(r.get("reasons")))
    # real paper_fill path: 45 € open + 5 € fill ok
    Tp = rt.new_root(open_paper([25, 20])); envp = rt.make_env(Tp, {"PAPER_FILL_NO_WATCH": "1"})
    r, rc = rt.paper_fill(envp, buy(5))
    s = rt.state_of(Tp)
    rt.check("paper_fill: 45 € + 5 € filled, exposure_eur 50 / 0.1", rc == 0 and close(s.get("exposure_eur"), 50)
             and close(s.get("exposure_pct"), 0.1), str(r.get("reasons")))


def test_live_place_cap_and_per_day():
    # live_place (copied tree, fake revx) with 20 € of paper exposure: live 10 € refused by validate (--live)
    T = Tree(); T.env["WATCH_STOPS_NO_AUTOSTART"] = "1"
    (T.L / "guardian/state.json").write_text(json.dumps(open_paper([20])))
    T.tick(2170)
    r, rc = T.live_place(ENTRY)
    places = [c for c in T.calls() if c.startswith("order place")]
    rt.check("live_place: 20 € open + 10 € live → refused (rc 4, exposure), no order", rc == 4 and not places
             and "exposure" in json.dumps(r.get("validate")), str(r)[:200])
    # max_live_per_day from config (default 1 / absent → 1 / 2 → two)
    for val, expect_second in (("absent", 7), (1, 7), (2, 0)):
        T = Tree(); T.env["WATCH_STOPS_NO_AUTOSTART"] = "1"
        cp = T.L / "guardian/config.json"; cfg = json.loads(cp.read_text())
        if val == "absent":
            cfg.pop("max_live_per_day", None)
        else:
            cfg["max_live_per_day"] = val
        cp.write_text(json.dumps(cfg))
        T.tick(2170)
        r1, rc1 = T.live_place(ENTRY)
        (T.L / "LIVE_ONCE").write_text("re-arm\n")
        r2, rc2 = T.live_place(ENTRY)
        rt.check(f"max_live_per_day={val}: 1st live ok, 2nd rc {expect_second}", rc1 == 0 and rc2 == expect_second,
                 f"rc1={rc1} rc2={rc2} {str(r2.get('error'))[:100]}")
        rt.kill_all(str(T.L))
    T = Tree(); T.tick(2170)
    r, rc = T.live_place(ENTRY, "--dry-run")
    rt.check("dry-run gate shows max from config (1)", rc == 0 and r.get("gates", {}).get("max_live_per_day", {}).get("max") == 1)


# ---------------------------------------------------------------- live exit realized net of fees
def test_live_exit_realized_net():
    T = Tree()
    pid = entry_row_via_fake(T)
    T.tick(2095, bid=2094, ask=2096)
    r, rc = T.exit_spec({"position_id": pid, "pair": "ETH-EUR", "side": "long", "cost_eur": 10, "avg_price": 2170,
                         "trigger_price": 2095})
    ax = [x for x in T.rows() if x.get("kind") == "auto_exit"]
    o = ax[0]["order"] if ax else {}
    sold = float(o.get("qty") or 0)
    quote = sold * 2087.71
    gross = quote - 2170 * sold
    fees = 0.0005 * (2170 * sold + quote)
    rt.check("live exit (long): realized_pnl_eur net of fees in live_orders.jsonl",
             rc == 0 and len(ax) == 1 and close(o.get("realized_pnl_eur"), gross - fees, 2e-6)
             and close(o.get("realized_pnl_gross_eur"), gross, 2e-6) and close(o.get("fees_eur"), fees, 2e-6)
             and close(ax[0].get("realized_pnl_eur"), gross - fees, 2e-6),
             f"net={o.get('realized_pnl_eur')} expected={gross - fees:.6f} gross={o.get('realized_pnl_gross_eur')} fees={o.get('fees_eur')}")
    rt.check("live exit: existing fields kept (amount_eur, qty, price, quote_eur, exit_for, close_reason, status)",
             close(o.get("amount_eur"), 10) and o.get("price") == 2087.71 and close(o.get("quote_eur"), quote, 1e-6)
             and o.get("exit_for") == pid and o.get("linked_position_id") == pid and o.get("close_reason") == "stop_hit"
             and ax[0].get("status") == "done" and o.get("idea_type") == "hausse" and o.get("entry_price") == 2170)
    rt.check("live exit result JSON carries the same net value", close(r.get("realized_pnl_eur"), gross - fees, 2e-6))
    # short (idée à la baisse) live: rebuy at ask+0.3 %
    T2 = Tree()
    sid = entry_row_via_fake(T2, qty=0.004, side="sell", extra_order={"idea_type": "baisse", "kind": "baisse", "qty": 0.004,
                                                                       "stop_price": 2250, "target_price": 2050, "decision_id": "T-S"})
    T2.tick(2260, bid=2259, ask=2261)
    r2, rc2 = T2.exit_spec({"position_id": sid, "pair": "ETH-EUR", "side": "short", "cost_eur": 8.68, "avg_price": 2170,
                            "trigger_price": 2260})
    ax2 = [x for x in T2.rows() if x.get("kind") == "auto_exit"]
    o2 = ax2[0]["order"] if ax2 else {}
    exp2 = (2170 - 2267.79) * 0.004 - 0.0005 * (2170 * 0.004 + 2267.79 * 0.004)
    rt.check("live exit (short): realized = (entry − rebuy)×qty − fees", rc2 == 0 and close(o2.get("realized_pnl_eur"), exp2, 2e-6),
             f"net={o2.get('realized_pnl_eur')} expected={exp2:.6f}")


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_watcher_marks_short_and_long, test_dry_run_no_write_and_idle_summary, test_paper_fill_refreshes_summary,
                  test_lock_and_no_clobber, test_paper_cap_50, test_live_place_cap_and_per_day, test_live_exit_realized_net):
            try:
                t()
            except Exception as e:  # noqa: BLE001
                import traceback; traceback.print_exc()
                rt.check(t.__name__ + " crashed", False, str(e))
    finally:
        for T in rt.TMPS:
            rt.kill_all(str(T))
        after = rt.real_hashes()
        ignore = ("price_ticks",)
        diff = {k: (before[k], after.get(k)) for k in before
                if before[k] != after.get(k) and not any(x in k for x in ignore)}
        rt.check("real state untouched", not diff, json.dumps(diff))
        left = [pid for T in rt.TMPS for pid in rt.watcher_pids_for(str(T))]
        rt.check("no test watcher left running", not left, str(left))
        n_ok = sum(1 for _, ok, _ in rt.RESULTS if ok)
        print(f"\n{n_ok}/{len(rt.RESULTS)} passed.")
        sys.exit(0 if n_ok == len(rt.RESULTS) else 1)
