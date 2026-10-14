#!/usr/bin/env python3
"""Horaires live (8 oct) — entry window, announcements, extra session, 22h force-close, heartbeat.
Copied guardian tree in /tmp + FAKE revx; time mocked with PMB_FAKE_NOW (ignored by the real repo).
Never places a real order."""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt
import run_live_tests as lt
from run_live_tests import Tree, ENTRY, fake_now, sells

TODAY = datetime.now(rt.TZ).date().isoformat()
YDAY = (datetime.now(rt.TZ) - timedelta(days=1)).date().isoformat()


def at(T, hhmm, days=0):
    T.env["PMB_FAKE_NOW"] = fake_now(hhmm, days)
    T.env["WATCH_STOPS_NO_AUTOSTART"] = "1"
    return T


def places(T):
    return [c for c in T.calls() if c.startswith("order place")]


def test_entry_window():
    for hhmm in ("14:00", "15:35", "17:10", "15:30", "15:44", "22:05"):
        T = at(Tree(), hhmm)
        T.tick(2170)
        r, rc = T.live_place(ENTRY)
        rt.check(f"entry refused at {hhmm} (rc 12, French msg, no order, LIVE_ONCE kept)",
                 rc == 12 and "Live refusé" in str(r.get("error")) and not places(T) and (T.L / "LIVE_ONCE").exists()
                 and not (T.L / "state/live_day.json").exists(), str(r.get("error"))[:110])
    for hhmm in ("15:10", "16:00", "15:45", "16:59"):
        T = at(Tree(), hhmm)
        T.tick(2170)
        r, rc = T.live_place(ENTRY)
        rt.check(f"entry allowed at {hhmm} (fake order placed)", rc == 0 and r.get("ok") and len(places(T)) == 1
                 and (r.get("gates") or {}).get("live_window", {}).get("ok") is True, f"rc={rc} {r.get('error')}")
    # dry-run reports, behaviour otherwise unchanged (rc 0, no order)
    T = at(Tree(), "14:00"); T.tick(2170)
    r, rc = T.live_place(ENTRY, "--dry-run")
    lw = (r.get("gates") or {}).get("live_window") or {}
    rt.check("dry-run at 14:00: rc 0, no order, gates.live_window.would_refuse + reason", rc == 0 and r.get("dry_run")
             and lw.get("would_refuse") is True and lw.get("reason") == "outside_window" and not places(T), lw.get("reason_fr", "")[:90])
    T = at(Tree(), "16:00")
    r, rc = T.live_place(ENTRY, "--dry-run")
    rt.check("dry-run at 16:00: would_refuse false", rc == 0 and (r.get("gates") or {}).get("live_window", {}).get("would_refuse") is False)
    # --exit is never time-gated
    T = at(Tree(), "14:00")
    pid = lt.entry_row_via_fake(T)
    r, rc = T.exit_spec({"position_id": pid, "pair": "ETH-EUR", "side": "long", "cost_eur": 10, "avg_price": 2170, "trigger_price": 2095})
    rt.check("--exit at 14:00 not blocked by the window (done)", rc == 0 and r.get("status") == "done", str(r.get("status")))


def test_announcements_and_extra():
    T = at(Tree(), "16:05"); T.tick(2170)
    (T.L / "state/annonces_du_jour.json").write_text(json.dumps({"date": TODAY, "times": ["16:00"]}))
    r, rc = T.live_place(ENTRY)
    lw = r.get("live_window") or {}
    rt.check("annonces_du_jour 16:00 blocks 16:05 (source annonces_du_jour)", rc == 12 and lw.get("reason") == "post_announcement"
             and lw.get("announcement_source") == "annonces_du_jour" and not places(T), str(r.get("error"))[:110])
    at(T, "16:15")
    r, rc = T.live_place(ENTRY)
    rt.check("annonces_du_jour 16:00 → allowed again at 16:15", rc == 0 and len(places(T)) == 1, f"rc={rc} {r.get('error')}")
    T = at(Tree(), "16:05"); T.tick(2170)
    (T.L / "state/annonces_du_jour.json").write_text(json.dumps({"date": YDAY, "times": ["16:00"]}))
    r, rc = T.live_place(ENTRY)
    rt.check("annonces_du_jour of another day ignored", rc == 0, f"rc={rc} {r.get('error')}")
    # extra session (Quentin's green light)
    T = at(Tree(), "20:10"); T.tick(2170)
    r, rc = T.live_place(ENTRY)
    rt.check("20:10 without extra session → refused", rc == 12)
    (T.L / "state/LIVE_EXTRA_SESSION.json").write_text(json.dumps({"date": YDAY, "start": "20:00", "end": "21:00"}))
    r, rc = T.live_place(ENTRY)
    rt.check("extra session dated yesterday → refused", rc == 12)
    (T.L / "state/annonces_du_jour.json").write_text(json.dumps({"date": TODAY, "times": ["20:00"]}))
    (T.L / "state/LIVE_EXTRA_SESSION.json").write_text(json.dumps({"date": TODAY, "window": {"start": "20:00", "end": "21:00"}}))
    r, rc = T.live_place(ENTRY)
    rt.check("extra session 20:00–21:00 but Fed 20:00 → refused at 20:10", rc == 12 and (r.get("live_window") or {}).get("reason") == "post_announcement")
    (T.L / "state/annonces_du_jour.json").unlink()
    r, rc = T.live_place(ENTRY)
    rt.check("extra session today 20:00–21:00 → allowed at 20:10", rc == 0 and (r.get("gates") or {}).get("live_window", {}).get("session") == "extra",
             f"rc={rc} {r.get('error')}")
    T = at(Tree(), "22:10")
    (T.L / "state/LIVE_EXTRA_SESSION.json").write_text(json.dumps({"date": TODAY, "start": "21:00", "end": "23:00"}))
    r, rc = T.live_place(ENTRY)
    rt.check("extra session never allows entries after 22:00", rc == 12 and (r.get("live_window") or {}).get("reason") == "after_force_close")


def paper_pos(stop=2000.0):
    return rt.pos_long("ETH-EUR", 2170, stop)


def live_plus_paper(now_entry="16:00", days=0, flag=None):
    T = at(Tree(), now_entry, days)
    if flag is not None:
        cfg = json.loads((T.L / "guardian/config.json").read_text())
        cfg["live_window"]["force_close_enabled"] = flag
        (T.L / "guardian/config.json").write_text(json.dumps(cfg))
    st = rt.base_state(); st["positions"] = [paper_pos()]
    (T.L / "guardian/state.json").write_text(json.dumps(st))
    T.tick(2170)
    r, rc = T.live_place(ENTRY)
    assert rc == 0, r
    (T.L / "LIVE_ONCE").write_text("re-armed\n")  # must NOT be consumed by the 22h exit
    return T


def hb(T):
    p = T.L / "state/watch_stops_heartbeat.json"
    return json.loads(p.read_text()) if p.exists() else {}


def test_force_close():
    # force_close_enabled defaults to false (retirée Quentin 8 oct) — opt in for this test
    T = live_plus_paper(flag=True)
    live_day = (T.L / "state/live_day.json").read_text()
    T.tick(2170)
    at(T, "21:59:30")
    lines, rc = T.watch_once()
    rt.check("21:59:30 → no force-close yet (watch, no sell)", rc == 0 and lines[-1].get("action") == "watch" and not sells(T.calls()))
    h = hb(T)
    rt.check("heartbeat written: ts/pid/open_live=1/open_paper=1", h.get("open_live") == 1 and h.get("open_paper") == 1
             and h.get("pid") and h.get("ts", "").startswith(TODAY), json.dumps(h))
    at(T, "22:00:30")
    lines, rc = T.watch_once()
    ex = list(T.exits().values())
    ax = [x for x in T.rows() if x.get("kind") == "auto_exit"]
    ev = json.loads((T.L / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
    rt.check("22:00:30 → live force-closed via live_place --exit (fake sell, lock done)", rc == 10 and len(sells(T.calls())) == 1
             and len(ex) == 1 and ex[0].get("status") == "done" and "--post-only" not in sells(T.calls())[0], sells(T.calls())[:1])
    rt.check("reason fermeture_22h in journal row + event + log", ax and ax[0]["order"]["close_reason"] == "fermeture_22h"
             and ev.get("close_reason") == "fermeture_22h" and ev.get("urgent") is False
             and any(l.get("action") == "live_auto_exit" and l.get("reason") == "fermeture_22h" for l in lines), ev.get("message_fr", "")[:120])
    rt.check("22h exit: LIVE_ONCE kept, live_day.json unchanged, Quentin's ETH intact",
             (T.L / "LIVE_ONCE").exists() and (T.L / "state/live_day.json").read_text() == live_day
             and T.fake()["balances"]["ETH"]["total"] >= 0.0309 - 1e-12, repr(T.fake()["balances"]["ETH"]))
    paper = json.loads((T.L / "guardian/state.json").read_text())["positions"][0]
    rt.check("paper position NOT force-closed at 22h", paper["status"] == "open")
    h = hb(T)
    rt.check("heartbeat after close: open_live=0, open_paper=1", h.get("open_live") == 0 and h.get("open_paper") == 1, json.dumps(h))
    at(T, "23:30")
    lines, rc = T.watch_once()
    paper = json.loads((T.L / "guardian/state.json").read_text())["positions"][0]
    rt.check("23:30 paper-only → still watched, not closed, no new order", rc == 0 and lines[-1].get("action") == "watch"
             and paper["status"] == "open" and len(sells(T.calls())) == 1)


def test_watcher_loop_past_22h():
    T = live_plus_paper(flag=True)
    at(T, "22:00:30")
    log = (T.L / "state/loop.log").open("w")
    proc = subprocess.Popen([sys.executable, str(T.L / "guardian/scripts/watch_stops.py"), "--interval", "1"],
                            stdout=log, stderr=subprocess.STDOUT, env=T.env, cwd=str(T.L))
    try:
        rows = lambda: [json.loads(l) for l in (T.L / "state/loop.log").read_text().splitlines() if l.startswith("{")]
        cont = rt.wait_for(lambda: next((x for x in rows() if x.get("action") == "continue_after_close"), None), timeout=40)
        time.sleep(2.5)
        h1 = hb(T); time.sleep(1.5); h2 = hb(T)
        rt.check("loop: live closed at 22h, watcher keeps running for paper (continue_after_close)",
                 cont and cont.get("remaining") == 1 and proc.poll() is None, json.dumps(cont))
        rt.check("loop: heartbeat refreshed each cycle (pid, open_live 0, open_paper 1)", h1.get("pid") == proc.pid
                 and h2.get("ts", "") > h1.get("ts", "") and h2.get("open_live") == 0 and h2.get("open_paper") == 1, f"{h1.get('ts')} → {h2.get('ts')}")
        rt.check("loop: exactly one exit order", len(sells(T.calls())) == 1)
        T.tick(1990)  # paper stop hit → nothing left → clean exit 10
        try:
            rc = proc.wait(timeout=40)
        except subprocess.TimeoutExpired:
            rc = None
        paper = json.loads((T.L / "guardian/state.json").read_text())["positions"][0]
        rt.check("loop: paper closed by its own stop, watcher exits cleanly (rc 10, pid released)", rc == 10
                 and paper["status"] == "closed" and not (T.L / "state/watch_stops.pid").exists(), f"rc={rc}")
        lines, rc2 = T.watch_once()
        h = hb(T)
        rt.check("nothing open → idle exit 0, heartbeat 0/0", rc2 == 0 and lines[-1].get("action") == "idle"
                 and h.get("open_live") == 0 and h.get("open_paper") == 0, json.dumps(h))
    finally:
        if proc.poll() is None:
            proc.kill()
        log.close()


def test_flag_and_overnight():
    # default config (force_close_enabled=false) — no close at 22h
    T = live_plus_paper()  # uses config as copied (= false)
    at(T, "22:00:30")
    lines, rc = T.watch_once()
    rt.check("default force_close_enabled=false → no 22h close (watch, no sell)", rc == 0 and lines[-1].get("action") == "watch"
             and not sells(T.calls()) and not T.exits())
    # overnight still closes WHEN the flag is true
    T2 = live_plus_paper("16:00", days=-1, flag=True)
    at(T2, "09:00")
    lines, rc = T2.watch_once()
    ex = list(T2.exits().values())
    rt.check("flag=true: live opened yesterday still open at 09:00 → force-closed", rc == 10 and ex and ex[0].get("status") == "done"
             and (ex[0].get("spec") or {}).get("close_reason") == "fermeture_22h")



def rhb(T):
    p = T.L / "state/revolut_heartbeat.json"
    return json.loads(p.read_text()) if p.exists() else {}


def test_revolut_heartbeat():
    """While a position is open, the long-running watcher probes Revolut ~every REVOLUT_HB_INTERVAL_S."""
    T = at(Tree(), "16:00")
    st = rt.base_state(); st["positions"] = [paper_pos()]
    (T.L / "guardian/state.json").write_text(json.dumps(st))
    T.tick(2170)
    T.env["REVOLUT_HB_INTERVAL_S"] = "1"
    T.env["WATCH_STOPS_NO_REVX_OPEN"] = "1"
    log = (T.L / "state/loop.log").open("w")
    proc = subprocess.Popen([sys.executable, str(T.L / "guardian/scripts/watch_stops.py"), "--interval", "1"],
                            stdout=log, stderr=subprocess.STDOUT, env=T.env, cwd=str(T.L))
    try:
        rows = lambda: [json.loads(l) for l in (T.L / "state/loop.log").read_text().splitlines() if l.startswith("{")]
        def wait_rhb(pred, timeout=25):
            return rt.wait_for(lambda: (lambda h: h if pred(h) else None)(rhb(T)), timeout=timeout)

        h1 = wait_rhb(lambda h: h.get("ok") is True and h.get("consecutive_failures") == 0)
        w1 = hb(T)
        rt.check("revolut_heartbeat ok (fake ticker) + watch_stops_heartbeat also present",
                 h1 and h1.get("ok") is True and h1.get("error") is None
                 and h1.get("open_paper") == 1 and w1.get("open_paper") == 1 and w1.get("pid") == proc.pid,
                 f"rhb={h1} whb={w1}")
        ts_ok = h1["ts"]
        # break Revolut: empty ticker + fail balances
        T.fs.write_text(json.dumps({**T.fake(), "ticker": {}, "fail_balances": True}))
        h2 = wait_rhb(lambda h: h.get("ok") is False and (h.get("consecutive_failures") or 0) >= 1 and h.get("ts", "") > ts_ok)
        rt.check("revolut_heartbeat failure recorded (ok=false, consecutive_failures>=1, error set)",
                 h2 and h2.get("ok") is False and h2.get("error"), f"rhb={h2}")
        ts_fail = h2["ts"]
        # recover
        d = T.fake(); d["fail_balances"] = False; d["ticker"] = {"ETH-EUR": {"bid": 2169, "ask": 2171}}
        T.fs.write_text(json.dumps(d)); T.tick(2170)
        h3 = wait_rhb(lambda h: h.get("ok") is True and h.get("consecutive_failures") == 0 and h.get("ts", "") > ts_fail)
        rt.check("revolut_heartbeat recovers (ok=true, consecutive_failures=0)",
                 h3 and h3.get("ok") is True and h3.get("consecutive_failures") == 0, f"rhb={h3}")
        # --once must NOT write revolut_heartbeat (short check only)
        before = rhb(T).get("ts")
        time.sleep(0.2)
        T.watch_once()
        rt.check("--once does not rewrite revolut_heartbeat", rhb(T).get("ts") == before)
        # no orders placed by the probe
        places = [c for c in T.calls() if c.startswith("order place")]
        tickers = [c for c in T.calls() if c.startswith("market ticker")]
        rt.check("probe is read-only (ticker/balances only, never order place)", not places and len(tickers) >= 1,
                 f"places={places} tickers={len(tickers)}")
    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=3)
            except Exception:
                pass
        log.close()
        rt.kill_all(str(T.L))


def test_fake_clock_ignored_in_real_repo():
    env = {**os.environ, "PMB_FAKE_NOW": fake_now("16:00"), "TEST_MARKER": "x"}
    code = "import sys;sys.argv=['x'];import live_place as l, watch_stops as w;print(l._fake_now(), w._fake_now())"
    p = subprocess.run([sys.executable, "-c", code], cwd=str(rt.G), text=True, capture_output=True, env=env)
    rt.check("PMB_FAKE_NOW ignored by the real repo scripts", p.stdout.strip() == "None None", p.stdout.strip() + p.stderr[-200:])


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_entry_window, test_announcements_and_extra, test_force_close, test_watcher_loop_past_22h,
                  test_flag_and_overnight, test_revolut_heartbeat, test_fake_clock_ignored_in_real_repo):
            try:
                t()
            except Exception as e:  # noqa: BLE001
                import traceback; traceback.print_exc()
                rt.check(t.__name__ + " crashed", False, str(e))
    finally:
        for T in rt.TMPS:
            rt.kill_all(str(T))
        after = rt.real_hashes()
        ignore = ("live_equity.json", "price_ticks", "watch_stops_heartbeat.json", "revolut_heartbeat.json")
        diff = {k: (before[k], after.get(k)) for k in before
                if before[k] != after.get(k) and not any(x in k for x in ignore)}
        rt.check("real state untouched", not diff, json.dumps(diff))
        left = [pid for T in rt.TMPS for pid in rt.watcher_pids_for(str(T))]
        rt.check("no test watcher left running", not left, str(left))
        n_ok = sum(1 for _, ok, _ in rt.RESULTS if ok)
        print(f"\n{n_ok}/{len(rt.RESULTS)} passed.")
        sys.exit(0 if n_ok == len(rt.RESULTS) else 1)
