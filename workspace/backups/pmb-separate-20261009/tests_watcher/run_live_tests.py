#!/usr/bin/env python3
"""LIVE auto-exit tests — copied guardian tree in /tmp + FAKE revx (no real order, no network)."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt  # helpers (check, write_tick, kill_all, real_hashes, ...)

FAKE = Path(__file__).resolve().parent / "fake_revx.py"
REPO, G = rt.REPO, rt.G


def base_fake():
    return {"ticker": {"ETH-EUR": {"bid": 2169.0, "ask": 2171.0}},
            "balances": {"ETH": {"total": 0.0309, "reserved": 0.0}, "EUR": {"total": 165.0, "reserved": 0.0}},
            "orders": {}, "entry_fill": "immediate", "fill_mode": "immediate"}


def fake_now(hhmm="16:00", days=0):
    """ISO local time today (± days) at HH:MM[:SS] — for PMB_FAKE_NOW (honoured only in copied trees)."""
    from datetime import datetime, timedelta
    d = (datetime.now(rt.TZ) + timedelta(days=days)).date()
    parts = [int(x) for x in hhmm.split(":")] + [0]
    return datetime(d.year, d.month, d.day, parts[0], parts[1], parts[2], tzinfo=rt.TZ).isoformat()


class Tree:
    def __init__(self, fake=None, live_once=True, now="16:00"):
        L = Path(tempfile.mkdtemp(prefix="pmb-live-test-")); rt.TMPS.append(L); self.L = L
        (L / "guardian/scripts").mkdir(parents=True)
        for f in ("live_place.py", "validate_order.py", "watch_stops.py", "watcher_launch.py", "paper_fill.py", "check_alerts.py",
                  "state_summary.py"):
            shutil.copy2(G / f, L / "guardian/scripts" / f)
        shutil.copy2(REPO / "guardian/config.json", L / "guardian/config.json")
        shutil.copy2(REPO / "config.json", L / "config.json")
        (L / "guardian/state.json").write_text(json.dumps(rt.base_state(), indent=2))
        (L / "state").mkdir(); (L / "MODE").write_text("paper\n")
        if live_once:
            (L / "LIVE_ONCE").write_text("test\n")
        self.fs = L / "fake_state.json"
        self.fs.write_text(json.dumps(fake or base_fake()))
        (L / "revx").write_text(f"#!/usr/bin/env bash\nexport FAKE_REVX_STATE={self.fs}\nexec {sys.executable} {FAKE} \"$@\"\n")
        (L / "revx").chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(
            ("PREDICT_BOT", "GUARDIAN_", "WATCH_STOPS", "PAPER_FILL", "PRICE_TICK", "MODE_FILE", "STOP_FILE", "TRADES_LOG", "LIVE_"))}
        self.env.update({"REVX_BIN": str(L / "revx"), "WATCH_STOPS_REVX_BIN": str(L / "revx"),
                         "WATCH_STOPS_INTERVAL": "1", "LIVE_EXIT_FILL_WAIT_S": "1", "LIVE_EXIT_POLL_S": "0.2",
                         "TEST_MARKER": str(L)})
        # Horaires live (8 oct): entries only 15:00–17:00 → existing tests run at a mocked 16:00
        if now:
            self.env["PMB_FAKE_NOW"] = fake_now(now)

    def fake(self):
        return json.loads(self.fs.read_text())

    def set_fake(self, **kw):
        d = self.fake(); d.update(kw); self.fs.write_text(json.dumps(d))

    def calls(self):
        p = Path(str(self.fs) + ".calls")
        return p.read_text().splitlines() if p.exists() else []

    def tick(self, mid, bid=None, ask=None):
        rt.write_tick(self.L / "state/price_ticks", "ETH-EUR", mid)
        d = self.fake(); d["ticker"]["ETH-EUR"] = {"bid": bid or mid - 1, "ask": ask or mid + 1}; self.fs.write_text(json.dumps(d))

    def live_place(self, order, *extra):
        (self.L / "order.json").write_text(json.dumps(order))
        p = subprocess.run([sys.executable, str(self.L / "guardian/scripts/live_place.py"), "--order", str(self.L / "order.json"), *extra],
                           text=True, capture_output=True, env=self.env, timeout=120)
        try:
            return json.loads(p.stdout.strip().splitlines()[-1]), p.returncode
        except (json.JSONDecodeError, IndexError):
            return {"raw": p.stdout, "err": p.stderr}, p.returncode

    def exit_spec(self, spec):
        p = subprocess.run([sys.executable, str(self.L / "guardian/scripts/live_place.py"), "--exit"], input=json.dumps(spec),
                           text=True, capture_output=True, env=self.env, timeout=120)
        return json.loads(p.stdout.strip().splitlines()[-1]), p.returncode

    def watch_once(self):
        p = subprocess.run([sys.executable, str(self.L / "guardian/scripts/watch_stops.py"), "--once"], text=True,
                           capture_output=True, env=self.env, timeout=120)
        return [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")], p.returncode

    def rows(self):
        p = self.L / "state/live_orders.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def exits(self):
        p = self.L / "state/live_exits.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def read(self, rel):
        return json.loads((self.L / rel).read_text())


ENTRY = {"pair": "ETH-EUR", "side": "buy", "type": "limit", "price": 2170, "amount_eur": 10, "stop_price": 2100,
         "idea_type": "hausse", "post_only": True, "expected_gain_eur": 3, "expected_loss_eur": 0.3, "decision_id": "T-L"}
QTY = 10 / 2170


def sells(calls):
    return [c for c in calls if c.startswith("order place ETH-EUR sell")]


def test_normal_exit_watcher_flow():
    T = Tree()
    # Quentin's own resting sell order (must never be cancelled)
    d = T.fake(); d["orders"]["manual-1"] = {"id": "manual-1", "client_order_id": "q-manual", "symbol": "ETH/EUR", "side": "sell",
        "quantity": "0.01", "price": "3000", "status": "new", "filled_quantity": "0", "filled_amount": "0"}
    d["balances"]["ETH"]["reserved"] = 0.01; T.fs.write_text(json.dumps(d))
    T.tick(2170)
    try:
        r, rc = T.live_place(ENTRY)
        rt.check("LIVE entry (fake) ok + watcher_started", rc == 0 and r.get("watcher_started") is True, f"rc={rc} {r.get('error')}")
        live_day_before = (T.L / "state/live_day.json").read_text()
        pid = r.get("watcher_pid")
        row = rt.wait_for(lambda: next((x for x in rt.log_rows(T.L) if x.get("action") == "watch"), None))
        pos_id = row["watching"][0]["id"]
        # bot target (objectif) order resting on Revolut + journal row
        T.set_fake(entry_fill="never")
        tp = subprocess.run([str(T.L / "revx"), "order", "place", "ETH-EUR", "sell", "--qty", f"{QTY:.8f}", "--limit", "2300",
                             "--post-only", "--json", "--client-order-id", "tgt-1"], text=True, capture_output=True, env=T.env)
        with (T.L / "state/live_orders.jsonl").open("a") as f:
            f.write(json.dumps({"ok": True, "at": rt.now_iso(), "cmd": ["revx", "order", "place", "--client-order-id", "tgt-1"],
                                "stdout": tp.stdout, "returncode": 0,
                                "order": {"pair": "ETH-EUR", "side": "sell", "amount_eur": round(QTY * 2300, 4), "price": 2300,
                                          "purpose": "target", "target_for": pos_id}}) + "\n")
        (T.L / "LIVE_ONCE").write_text("re-armed for check\n")
        time.sleep(1.5)
        still = [x for x in rt.log_rows(T.L) if x.get("action") == "watch"][-1]
        rt.check("target row does not close the position for the watcher", still.get("open") == 1)
        T.tick(2095, bid=2094, ask=2096)
        gone = rt.wait_for(lambda: not Path(f"/proc/{pid}").exists() or
                           Path(f"/proc/{pid}/stat").read_text().split()[2] == "Z", timeout=40)
        ex = T.exits().get(pos_id, {})
        res = ex.get("result", {})
        f = T.fake()
        place = [c for c in sells(T.calls()) if "tgt-1" not in c]
        rt.check("auto exit done: sold exactly the position qty", gone and ex.get("status") == "done"
                 and abs(res.get("sold_qty", 0) - round(QTY, 8)) < 1e-8, f"status={ex.get('status')} sold={res.get('sold_qty')} qty={QTY:.8f}")
        rt.check("exit order = executable limit bid−0.3 % (not post-only)", len(place) == 1 and "--limit 2087.71" in place[0]
                 and "--post-only" not in place[0], place[0] if place else "")
        rt.check("bot target order cancelled first", f["orders"]["fake-2"]["status"] == "cancelled")
        rt.check("Quentin's manual order untouched", f["orders"]["manual-1"]["status"] == "new")
        rt.check("Quentin's ETH intact (0.0309)", 0.0309 <= f["balances"]["ETH"]["total"] < 0.0309 + 1e-8, f"ETH total={f['balances']['ETH']['total']:.8f}")
        rt.check("LIVE_ONCE not consumed by exit", (T.L / "LIVE_ONCE").exists())
        rt.check("live_day.json unchanged by exit", (T.L / "state/live_day.json").read_text() == live_day_before, live_day_before.strip())
        wake = T.read("state/auto_stop_wake.json")
        rt.check("wake for Risk: mode live, auto_sell, NOT urgent", wake.get("mode") == "live" and wake.get("auto_sell") is True
                 and wake.get("urgent") is False, wake.get("message_fr", ""))
        ev = json.loads((T.L / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
        rt.check("event: close_reason stop_hit, urgent false, exit_result", ev.get("close_reason") == "stop_hit" and ev.get("urgent") is False
                 and ev.get("exit_result", {}).get("status") == "done")
        ax = [x for x in T.rows() if x.get("kind") == "auto_exit"]
        rt.check("live state: auto_exit row (amount_eur = cost basis) in live_orders.jsonl", len(ax) == 1 and abs(ax[0]["order"]["amount_eur"] - 10) < 1e-6,
                 f"pnl={ax[0]['order'].get('realized_pnl_eur') if ax else None}")
        lines, rc2 = T.watch_once()
        rt.check("position closed afterwards (watcher idle)", rc2 == 0 and lines[-1].get("action") == "idle")
        # duplicate attempt directly
        n_before = len(sells(T.calls()))
        r2, rc3 = T.exit_spec({"position_id": pos_id, "pair": "ETH-EUR", "side": "long", "cost_eur": 10, "avg_price": 2170})
        rt.check("no duplicate exit (lock) — 2nd call refused, no order", rc3 == 11 and r2.get("status") == "already_handled"
                 and len(sells(T.calls())) == n_before)
        return T
    finally:
        rt.kill_all(str(T.L))


def entry_row_via_fake(T: Tree, qty=QTY, fill="immediate", side="buy", extra_order=None):
    """Place an entry with the FAKE client and journal it like live_place would."""
    T.set_fake(entry_fill=fill)
    coid = f"entry-{side}-{time.time_ns()}"
    p = subprocess.run([str(T.L / "revx"), "order", "place", "ETH-EUR", side, "--quote", str(round(qty * 2170, 6)), "--limit", "2170",
                        "--post-only", "--json", "--client-order-id", coid], text=True, capture_output=True, env=T.env)
    at = rt.now_iso()
    order = {"pair": "ETH-EUR", "side": side, "type": "limit", "price": 2170, "amount_eur": round(qty * 2170, 6), "stop_price": 2100}
    order.update(extra_order or {})
    with (T.L / "state/live_orders.jsonl").open("a") as f:
        f.write(json.dumps({"ok": True, "at": at, "cmd": ["revx", "order", "place", "--client-order-id", coid], "stdout": p.stdout,
                            "returncode": 0, "order": order}) + "\n")
    return f"live-ETH-EUR-{at}"


def test_qty_limited_and_quentin_protected():
    # bot holds only 0.002 of the 0.0046 position → sells 0.002, partial → urgent
    T = Tree()
    pid = entry_row_via_fake(T)
    d = T.fake(); d["balances"]["ETH"]["total"] = 0.0309 + 0.002; T.fs.write_text(json.dumps(d))
    r, rc = T.exit_spec({"position_id": pid, "pair": "ETH-EUR", "side": "long", "cost_eur": 10, "avg_price": 2170, "trigger_price": 2095})
    f = T.fake()
    rt.check("qty limited to real bot balance (sold 0.002, partial, urgent)", rc == 11 and r.get("status") == "partial"
             and abs(r.get("sold_qty", 0) - 0.002) < 1e-9 and r.get("urgent") is True, f"sold={r.get('sold_qty')} status={r.get('status')}")
    rt.check("Quentin's ETH intact after partial", 0.0309 - 1e-12 <= f["balances"]["ETH"]["total"] < 0.0309 + 1e-8, repr(f["balances"]["ETH"]["total"]))
    # balance = only Quentin's coins → nothing sold, urgent
    T2 = Tree()
    pid2 = entry_row_via_fake(T2)
    d = T2.fake(); d["balances"]["ETH"]["total"] = 0.0309; T2.fs.write_text(json.dumps(d))
    r2, rc2 = T2.exit_spec({"position_id": pid2, "pair": "ETH-EUR", "side": "long", "cost_eur": 10, "avg_price": 2170, "trigger_price": 2095})
    rt.check("only Quentin's coins on account → NO sell order, failed + urgent", rc2 == 11 and r2.get("status") == "failed"
             and not sells(T2.calls()) and abs(T2.fake()["balances"]["ETH"]["total"] - 0.0309) < 1e-12, f"target_qty={r2.get('target_qty')}")
    r3, rc3 = T2.exit_spec({"position_id": pid2, "pair": "ETH-EUR", "side": "long", "cost_eur": 10, "avg_price": 2170})
    rt.check("no retry after a failure (lock kept)", r3.get("status") == "already_handled" and not sells(T2.calls()))
    # live_equity hors_bot larger than config → larger reserve used
    T3 = Tree()
    pid3 = entry_row_via_fake(T3)
    (T3.L / "state/live_equity.json").write_text(json.dumps({"hors_bot": {"ETH": {"qty": 0.0329}}}))
    r4, _ = T3.exit_spec({"position_id": pid3, "pair": "ETH-EUR", "side": "long", "cost_eur": 10, "avg_price": 2170, "trigger_price": 2095})
    rt.check("reserve = max(config, live_equity hors_bot)", (r4.get("balance") or {}).get("quentin_reserve") == 0.0329
             and 0.0329 <= T3.fake()["balances"]["ETH"]["total"] < 0.0329 + 1e-8, f"sold={r4.get('sold_qty')}")


def test_unfilled_three_tries_alert():
    T = Tree()
    T.tick(2170)
    r, rc = T.live_place(ENTRY)  # watcher auto-start (we stop it; use --once for determinism)
    rt.kill_all(str(T.L)); time.sleep(0.3)
    live_day_before = (T.L / "state/live_day.json").read_text()
    (T.L / "LIVE_ONCE").write_text("x\n")
    T.set_fake(fill_mode="never")
    T.tick(2095, bid=2094, ask=2096)
    lines, rc2 = T.watch_once()
    exit_sells = [c for c in sells(T.calls())]
    cancels = [c for c in T.calls() if c.startswith("order cancel")]
    ex = list(T.exits().values())[0]
    rt.check("unfilled → 3 tries (0.3 % then 0.5 %, 0.5 %) then stop", len(exit_sells) == 3 and "--limit 2087.71" in exit_sells[0]
             and "--limit 2083.53" in exit_sells[1] and "--limit 2083.53" in exit_sells[2] and len(cancels) == 3,
             " | ".join(c.split("--limit ")[1].split()[0] for c in exit_sells))
    wake = T.read("state/auto_stop_wake.json")
    ev = json.loads((T.L / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
    rt.check("failed exit → URGENT wake + event stop_hit_live_exit_failed", rc2 == 10 and ex.get("status") == "failed"
             and wake.get("urgent") is True and ev.get("close_reason") == "stop_hit_live_exit_failed", wake.get("message_fr", "")[:160])
    rt.check("LIVE_ONCE / live_day intact after failed exit", (T.L / "LIVE_ONCE").exists()
             and (T.L / "state/live_day.json").read_text() == live_day_before)
    n = len(sells(T.calls()))
    lines2, rc3 = T.watch_once()
    rt.check("next watcher cycle does not retry (lock)", len(sells(T.calls())) == n and lines2[-1].get("watching", [{}])[0].get("exit_status") == "failed")


def test_stop_file_and_short_and_nofill():
    # STOP: entries blocked, exits allowed
    T = Tree()
    pid = entry_row_via_fake(T)
    (T.L / "STOP").write_text("halt\n")
    r, rc = T.live_place(ENTRY)
    rt.check("STOP present → new live entry refused", rc == 2)
    r2, rc2 = T.exit_spec({"position_id": pid, "pair": "ETH-EUR", "side": "long", "cost_eur": 10, "avg_price": 2170, "trigger_price": 2095})
    rt.check("STOP present → exit still allowed (done)", rc2 == 0 and r2.get("status") == "done")
    # Live idée à la baisse: sell 0.004 then automatic rebuy above stop at ask+0.3 %
    T2 = Tree()
    sid = entry_row_via_fake(T2, qty=0.004, side="sell", extra_order={"idea_type": "baisse", "kind": "baisse", "qty": 0.004,
                                                                      "stop_price": 2250, "target_price": 2050, "decision_id": "T-S"})
    eth_after_sell = T2.fake()["balances"]["ETH"]["total"]
    T2.tick(2260, bid=2259, ask=2261)
    lines, rc3 = T2.watch_once()
    buys = [c for c in T2.calls() if c.startswith("order place ETH-EUR buy")]
    ex = T2.exits().get(sid.replace("live-", "live-"), {}) or list(T2.exits().values())[0]
    rt.check("live baisse: auto rebuy at ask+0.3 % (2267.79), qty 0.004, not post-only", rc3 == 10 and len(buys) == 1
             and "--limit 2267.79" in buys[0] and "--qty 0.004" in buys[0] and "--post-only" not in buys[0] and ex.get("status") == "done",
             buys[0] if buys else str(lines[-1])[:200])
    rt.check("live baisse: coins back (ETH +0.004)", abs(T2.fake()["balances"]["ETH"]["total"] - (eth_after_sell + 0.004)) < 1e-9)
    # Entry never filled → exit cancels our resting entry, nothing sold, not urgent
    T3 = Tree()
    pid3 = entry_row_via_fake(T3, fill="never")
    T3.tick(2095, bid=2094, ask=2096)
    lines, rc4 = T3.watch_once()
    f = T3.fake()
    ex3 = list(T3.exits().values())[0]
    wake = T3.read("state/auto_stop_wake.json")
    rt.check("entry unfilled → entry cancelled, no sell, status no_fill, not urgent", ex3.get("status") == "no_fill"
             and f["orders"]["fake-1"]["status"] == "cancelled" and not sells(T3.calls()) and wake.get("urgent") is False)


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_normal_exit_watcher_flow, test_qty_limited_and_quentin_protected, test_unfilled_three_tries_alert,
                  test_stop_file_and_short_and_nofill):
            try:
                t()
            except Exception as e:  # noqa: BLE001
                import traceback; traceback.print_exc()
                rt.check(t.__name__ + " crashed", False, str(e))
    finally:
        for T in rt.TMPS:
            rt.kill_all(str(T))
        after = rt.real_hashes()
        diff = {k: (before[k], after.get(k)) for k in before if before[k] != after.get(k)}
        rt.check("real state untouched", not diff, json.dumps(diff))
        left = [pid for T in rt.TMPS for pid in rt.watcher_pids_for(str(T))]
        rt.check("no test watcher left running", not left, str(left))
        real_calls = [c for T in rt.TMPS for c in (Path(str(T / "fake_state.json") + ".calls").read_text().splitlines()
                      if Path(str(T / "fake_state.json") + ".calls").exists() else [])]
        n_ok = sum(1 for _, ok, _ in rt.RESULTS if ok)
        print(f"\n{n_ok}/{len(rt.RESULTS)} passed. fake revx calls: {len(real_calls)}")
        sys.exit(0 if n_ok == len(rt.RESULTS) else 1)
