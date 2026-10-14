#!/usr/bin/env python3
"""Heure limite (deadline) per position — RAPPEL seulement (Quentin 8 oct 23h).
Default config (guardian/config.json deadline.close_enabled=false): at the deadline the watcher writes
state/deadline_reminder.json (+ one line per position in state/deadline_reminders.jsonl) and closes nothing;
only stop / target close. close_enabled=true (set in the COPIED tree only) restores the old close.
Copied tree + FAKE revx, time mocked with PMB_FAKE_NOW (ignored by the real repo). Never places a real order."""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tests as rt
from run_live_tests import Tree, ENTRY, fake_now, sells

BUY = {"pair": "ETH-EUR", "side": "buy", "type": "limit", "price": 2170, "amount_eur": 10, "stop_price": 2000,
       "idea_type": "hausse", "decision_id": "D-DL-1", "post_only": True}
SHORT = {"pair": "ETH-EUR", "side": "sell", "type": "limit", "price": 2170, "qty": 0.004, "amount_eur": 8.68,
         "idea_type": "baisse", "kind": "baisse", "decision_id": "D-DL-2", "stop_price": 2300, "target_price": 2000,
         "post_only": True}
REMINDER, REMINDERS = "state/deadline_reminder.json", "state/deadline_reminders.jsonl"


def at(T, hhmm, days=0):
    T.env["PMB_FAKE_NOW"] = fake_now(hhmm, days)
    T.env["WATCH_STOPS_NO_AUTOSTART"] = "1"
    T.env["PAPER_FILL_NO_WATCH"] = "1"
    return T


def close_enabled(T, value=True):
    """Turn deadline.close_enabled on in the COPIED tree's config only."""
    p = T.L / "guardian/config.json"
    cfg = json.loads(p.read_text()); cfg.setdefault("deadline", {})["close_enabled"] = value
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    return T


def paper_fill(T, order):
    p = subprocess.run([sys.executable, str(T.L / "guardian/scripts/paper_fill.py")], input=json.dumps(order),
                       text=True, capture_output=True, env=T.env, timeout=60)
    try:
        return json.loads(p.stdout), p.returncode
    except json.JSONDecodeError:
        return {"raw": p.stdout, "err": p.stderr}, p.returncode


def positions(T):
    return json.loads((T.L / "guardian/state.json").read_text())["positions"]


def jsonl(T, rel):
    p = T.L / rel
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def last_event(T):
    ev = jsonl(T, "state/auto_stop_events.jsonl")
    return ev[-1] if ev else {}


def reminder(T):
    p = T.L / REMINDER
    return json.loads(p.read_text()) if p.exists() else {}


def no_heure_limite(T):
    """No close / journal / event / alert / wake mentions heure_limite."""
    blobs = [T.L / "state/auto_stop_events.jsonl", T.L / "state/trades_log.jsonl", T.L / "state/live_orders.jsonl",
             T.L / "state/auto_stop_wake.json", T.L / "state/alerts_last.json", T.L / "guardian/state.json"]
    return not any(p.exists() and "heure_limite" in p.read_text() and "rappel_heure_limite" not in p.read_text() for p in blobs) \
        and not any(p.exists() and '"close_reason": "heure_limite"' in p.read_text() for p in blobs)


def watch_row(lines, pid):
    return next((w for w in (lines[-1].get("watching") or []) if str(w.get("id")) == str(pid)), {}) if lines else {}


# (a) default config: paper long / short past deadline stay open, one reminder per position
def test_paper_reminder_default():
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    r, rc = paper_fill(T, dict(BUY, deadline=fake_now("18:00")[:16]))  # naive local "YYYY-MM-DDTHH:MM"
    pos = positions(T)[0]; pid = pos["id"]
    rt.check("paper long open stores deadline (Brussels offset)", rc == 0 and pos.get("deadline", "").endswith("+02:00")
             and pos["deadline"].startswith(fake_now("18:00")[:16]) and not r.get("warnings"), pos.get("deadline"))
    at(T, "17:59:30"); T.tick(2171)
    lines, rc = T.watch_once()
    rt.check("paper long before deadline → open, no reminder yet", rc == 0 and positions(T)[0]["status"] == "open"
             and not (T.L / REMINDER).exists() and not (T.L / REMINDERS).exists())
    at(T, "18:00:30")
    lines, rc = T.watch_once()
    rem, w = reminder(T), watch_row(lines, pid)
    rt.check("paper long past deadline → still OPEN (rc 0, action watch, reminder_only)", rc == 0
             and lines[-1].get("action") == "watch" and positions(T)[0]["status"] == "open"
             and w.get("deadline_reminder_only") is True, str(lines[-1])[:200])
    rt.check("paper long reminder file written with position id", rem.get("position_id") == str(pid)
             and rem.get("action") == "rappel_heure_limite" and rem.get("decision_id") == "D-DL-1"
             and str(rem.get("deadline", "")).startswith(fake_now("18:00")[:16]), json.dumps(rem)[:200])
    for hhmm, days in (("18:05", 0), ("19:00", 0), ("10:00", 1)):
        at(T, hhmm, days); T.tick(2172)
        lines, rc = T.watch_once()
    rows = jsonl(T, REMINDERS)
    rt.check("paper long after 4 cycles: still open, jsonl exactly 1 line for the position", rc == 0
             and positions(T)[0]["status"] == "open" and len(rows) == 1 and rows[0]["position_id"] == str(pid), f"lines={len(rows)}")
    tl = jsonl(T, "state/trades_log.jsonl")
    rt.check("paper long: no close, no heure_limite in events/journal, no wake", no_heure_limite(T)
             and not (T.L / "state/auto_stop_events.jsonl").exists() and not (T.L / "state/auto_stop_wake.json").exists()
             and all(x.get("side") != "sell" for x in tl), f"journal={len(tl)}")
    rt.check("paper reminder used no revx order", not [c for c in T.calls() if c.startswith("order place")])

    # short (idée à la baisse) — alias deadline_at
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    r, rc = paper_fill(T, dict(SHORT, deadline_at=fake_now("18:00")))
    pos = positions(T)[0]; sid = pos["id"]
    rt.check("paper short open with alias deadline_at → stored as deadline", rc == 0
             and pos.get("deadline", "").startswith(fake_now("18:00")[:16]), str(r.get("reasons") or pos.get("deadline")))
    for hhmm in ("18:00:30", "18:01", "18:30"):
        at(T, hhmm); T.tick(2150)
        lines, rc = T.watch_once()
    rows = jsonl(T, REMINDERS)
    rt.check("paper short past deadline → still OPEN, no rebuy, reminder (1 line, its id)", rc == 0
             and positions(T)[0]["status"] == "open" and not positions(T)[0].get("rebuy_reason")
             and reminder(T).get("position_id") == str(sid) and len(rows) == 1 and rows[0]["position_id"] == str(sid)
             and no_heure_limite(T), f"lines={len(rows)} rem={reminder(T).get('position_id')}")


# (b) live position past deadline: no exit order, reminder, LIVE_ONCE / live_day untouched
def test_live_reminder_default():
    T = at(Tree(), "16:00"); T.tick(2170)
    r, rc = T.live_place(dict(ENTRY, deadline_at=fake_now("16:30")[:16]))
    row = [x for x in T.rows() if x.get("ok")][0]
    rt.check("live entry stores normalized deadline in live_orders.jsonl", rc == 0
             and row["order"].get("deadline", "").startswith(fake_now("16:30")[:16]) and row["order"]["deadline"].endswith("+02:00"),
             row["order"].get("deadline"))
    live_day = (T.L / "state/live_day.json").read_text()
    (T.L / "LIVE_ONCE").write_text("re-armed\n")
    n_calls = len([c for c in T.calls() if c.startswith("order place")])
    at(T, "16:29:30"); T.tick(2171)
    lines, rc = T.watch_once()
    rt.check("live before deadline → no exit, no reminder", rc == 0 and not sells(T.calls()) and not T.exits()
             and not (T.L / REMINDER).exists())
    for hhmm in ("16:30:30", "16:31", "17:00"):
        at(T, hhmm); T.tick(2171)
        lines, rc = T.watch_once()
    rows, rem = jsonl(T, REMINDERS), reminder(T)
    pid = str(rem.get("position_id"))
    rt.check("live past deadline → NO exit order via fake client, no exit lock, no auto_exit row", rc == 0
             and not sells(T.calls()) and len([c for c in T.calls() if c.startswith("order place")]) == n_calls
             and not T.exits() and not [x for x in T.rows() if x.get("kind") == "auto_exit"], str(sells(T.calls()))[:200])
    rt.check("live reminder written once (position id live-…), watcher still watching it", pid.startswith("live-ETH-EUR-")
             and len(rows) == 1 and rows[0]["position_id"] == pid and lines[-1].get("action") == "watch"
             and watch_row(lines, pid).get("deadline_reminder_only") is True, f"lines={len(rows)} pid={pid}")
    rt.check("live reminder: LIVE_ONCE untouched, live_day unchanged, Quentin's ETH intact, no heure_limite",
             (T.L / "LIVE_ONCE").read_text() == "re-armed\n" and (T.L / "state/live_day.json").read_text() == live_day
             and T.fake()["balances"]["ETH"]["total"] >= 0.0309 - 1e-12 and no_heure_limite(T)
             and not (T.L / "state/auto_stop_wake.json").exists())
    return T


# (c) stop and target still close after the deadline
def test_stop_target_after_deadline():
    # paper long: past deadline (reminder) then stop
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    paper_fill(T, dict(BUY, deadline=fake_now("17:00")))
    at(T, "17:30"); T.tick(2100); T.watch_once()
    at(T, "17:31"); T.tick(1990)
    lines, rc = T.watch_once()
    pos, ev = positions(T)[0], last_event(T)
    rt.check("paper long past deadline then stop → closed stop_hit (not heure_limite)", rc == 10 and pos["status"] == "closed"
             and ev.get("close_reason") == "stop_hit" and pos.get("close_reason") in (None, "stop_hit")
             and len(jsonl(T, REMINDERS)) == 1, f"{pos.get('close_reason')} / {ev.get('close_reason')}")
    # paper short: past deadline then target
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    paper_fill(T, dict(SHORT, deadline=fake_now("17:00")))
    at(T, "17:30"); T.tick(2100); T.watch_once()
    at(T, "17:31"); T.tick(1990)
    lines, rc = T.watch_once()
    pos, ev = positions(T)[0], last_event(T)
    rt.check("paper short past deadline then target → rebuy, target_hit", rc == 10 and pos["status"] == "closed"
             and pos.get("rebuy_reason") == "target" and ev.get("close_reason") == "target_hit",
             f"{pos.get('rebuy_reason')} / {ev.get('close_reason')}")
    # paper short: past deadline then safety stop
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    paper_fill(T, dict(SHORT, deadline=fake_now("17:00")))
    at(T, "17:30"); T.tick(2200); T.watch_once()
    at(T, "17:31"); T.tick(2310)
    lines, rc = T.watch_once()
    pos, ev = positions(T)[0], last_event(T)
    rt.check("paper short past deadline then stop → rebuy safety, stop_hit", rc == 10 and pos["status"] == "closed"
             and pos.get("rebuy_reason") == "safety" and ev.get("close_reason") == "stop_hit",
             f"{pos.get('rebuy_reason')} / {ev.get('close_reason')}")
    # live: past deadline (reminder, no exit) then stop → auto exit via fake
    T = test_live_reminder_quiet()
    live_day = (T.L / "state/live_day.json").read_text()
    at(T, "17:05"); T.tick(2095, bid=2094, ask=2096)
    lines, rc = T.watch_once()
    ex = list(T.exits().values()); ev = last_event(T)
    rt.check("live past deadline then stop → one fake exit sell, stop_hit, LIVE_ONCE/live_day kept", rc == 10
             and len(sells(T.calls())) == 1 and ex and ex[0].get("status") == "done" and ev.get("close_reason") == "stop_hit"
             and (T.L / "LIVE_ONCE").exists() and (T.L / "state/live_day.json").read_text() == live_day,
             f"sells={len(sells(T.calls()))} ev={ev.get('close_reason')}")


def test_live_reminder_quiet():
    """Live entry with a deadline in the past (no checks) — for the stop-after-deadline case."""
    T = at(Tree(), "16:00"); T.tick(2170)
    T.live_place(dict(ENTRY, deadline=fake_now("16:30")))
    (T.L / "LIVE_ONCE").write_text("re-armed\n")
    at(T, "16:45"); T.tick(2171); T.watch_once()
    return T


# (d) validate_order: past / unreadable → ok + warning; missing → warning (paper and live)
def test_validate_warnings():
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    r, rc = paper_fill(T, dict(BUY, deadline=fake_now("15:00")))
    w = r.get("warnings") or []
    rt.check("paper: past deadline → accepted (ok, rc 0) with warning 'déjà passée'", rc == 0 and r.get("ok") is not False
             and any("déjà passée" in x for x in w) and len(positions(T)) == 1, str(w))
    lines, rc2 = T.watch_once()
    rt.check("paper: position opened with a past deadline → reminder at once, stays open", rc2 == 0
             and positions(T)[0]["status"] == "open" and reminder(T).get("position_id") == str(positions(T)[0]["id"]))
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    r, rc = paper_fill(T, dict(BUY, deadline="demain soir"))
    w = r.get("warnings") or []
    rt.check("paper: unreadable deadline → accepted with warning 'illisible', no deadline stored", rc == 0
             and any("illisible" in x for x in w) and len(positions(T)) == 1 and not positions(T)[0].get("deadline"), str(w))
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    r, rc = paper_fill(T, BUY)
    w = r.get("warnings") or []
    rt.check("paper: missing deadline → accepted with warning 'absente — pas de rappel'", rc == 0
             and any("absente" in x and "pas de rappel" in x for x in w), str(w))
    # live (fake client): --dry-run shows validate ok + warning, no order
    for raw, word in ((fake_now("15:30"), "déjà passée"), ("demain soir", "illisible")):
        T = at(Tree(), "16:00"); T.tick(2170)
        r, rc = T.live_place(dict(ENTRY, deadline=raw), "--dry-run")
        val = r.get("validate") or {}
        rt.check(f"live --dry-run: {word} deadline → validate ok + warning, no order", rc == 0 and r.get("ok") is True
                 and val.get("ok") is True and any(word in x for x in val.get("warnings") or [])
                 and not [c for c in T.calls() if c.startswith("order place")], str(val.get("warnings") or val.get("reasons")))
    # live real path (fake client): past deadline no longer refused
    T = at(Tree(), "16:00"); T.tick(2170)
    r, rc = T.live_place(dict(ENTRY, deadline=fake_now("15:30")))
    rt.check("live: past deadline → entry placed via fake client (rc 0, 1 buy)", rc == 0
             and len([c for c in T.calls() if c.startswith("order place ETH-EUR buy")]) == 1,
             str(r.get("error") or (r.get("validate") or {}).get("reasons")))


# (e) config deadline.close_enabled=true (copied tree only) → old close behaviour
def test_close_enabled_true():
    T = close_enabled(at(Tree(live_once=False), "16:00")); T.tick(2170)
    paper_fill(T, dict(BUY, deadline=fake_now("18:00")))
    at(T, "17:59:30"); T.tick(2171)
    lines, rc = T.watch_once()
    rt.check("[close on] paper long before deadline → open", rc == 0 and positions(T)[0]["status"] == "open")
    at(T, "18:00:30")
    lines, rc = T.watch_once()
    pos, ev = positions(T)[0], last_event(T)
    tl = jsonl(T, "state/trades_log.jsonl")
    rt.check("[close on] paper long closed at deadline: heure_limite (state, event, journal), no reminder",
             rc == 10 and pos["status"] == "closed" and pos.get("close_reason") == "heure_limite"
             and ev.get("close_reason") == "heure_limite" and tl[-1].get("side") == "sell"
             and tl[-1].get("close_reason") == "heure_limite" and not (T.L / REMINDERS).exists(), ev.get("message_fr", ""))
    T = close_enabled(at(Tree(live_once=False), "16:00")); T.tick(2170)
    paper_fill(T, dict(SHORT, deadline_at=fake_now("18:00")))
    at(T, "18:00:30"); T.tick(2150)
    lines, rc = T.watch_once()
    pos, ev = positions(T)[0], last_event(T)
    rt.check("[close on] paper short rebuy at deadline: heure_limite, rebuy_reason time", rc == 10 and pos["status"] == "closed"
             and pos.get("close_reason") == "heure_limite" and pos.get("rebuy_reason") == "time"
             and ev.get("close_reason") == "heure_limite")
    T = close_enabled(at(Tree(), "16:00")); T.tick(2170)
    T.live_place(dict(ENTRY, deadline_at=fake_now("16:30")[:16]))
    live_day = (T.L / "state/live_day.json").read_text()
    (T.L / "LIVE_ONCE").write_text("re-armed\n")
    at(T, "16:30:30"); T.tick(2171)
    lines, rc = T.watch_once()
    ex = list(T.exits().values()); ax = [x for x in T.rows() if x.get("kind") == "auto_exit"]; ev = last_event(T)
    rt.check("[close on] live closed at deadline via fake sell (not post-only), heure_limite, not urgent", rc == 10
             and len(sells(T.calls())) == 1 and "--post-only" not in sells(T.calls())[0] and ex and ex[0].get("status") == "done"
             and ax and ax[0]["order"]["close_reason"] == "heure_limite" and ev.get("close_reason") == "heure_limite"
             and ev.get("urgent") is False, sells(T.calls())[:1])
    rt.check("[close on] live: LIVE_ONCE kept, live_day unchanged, ETH intact", (T.L / "LIVE_ONCE").exists()
             and (T.L / "state/live_day.json").read_text() == live_day and T.fake()["balances"]["ETH"]["total"] >= 0.0309 - 1e-12)
    n = len(sells(T.calls()))
    lines, rc = T.watch_once()
    rt.check("[close on] live after deadline exit: no second order (lock), idle", len(sells(T.calls())) == n
             and lines[-1].get("action") == "idle")


# (f) a running watcher stays alive past the deadline while the position is open
def test_watcher_alive_past_deadline():
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    paper_fill(T, dict(BUY, deadline=fake_now("18:00")))
    pid = positions(T)[0]["id"]
    at(T, "17:59:57")
    log = (T.L / "state/loop.log").open("w")
    proc = subprocess.Popen([sys.executable, str(T.L / "guardian/scripts/watch_stops.py"), "--interval", "1"],
                            stdout=log, stderr=subprocess.STDOUT, env=T.env, cwd=str(T.L))
    try:
        for _ in range(9):
            T.tick(2170); time.sleep(1)
            if proc.poll() is not None:
                break
        rows = jsonl(T, REMINDERS)
        alive = proc.poll() is None
        rt.check("running watcher alive ~6 s past the deadline, position open, 1 reminder line", alive
                 and positions(T)[0]["status"] == "open" and len(rows) == 1 and rows[0]["position_id"] == str(pid)
                 and no_heure_limite(T), f"alive={alive} rc={proc.poll()} lines={len(rows)}")
        T.tick(1990)  # stop still closes in the running watcher
        try:
            rc = proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            rc = None
        rt.check("running watcher: stop after deadline closes (stop_hit) and exits 10", rc == 10
                 and positions(T)[0]["status"] == "closed" and last_event(T).get("close_reason") == "stop_hit",
                 f"rc={rc} {positions(T)[0].get('close_reason')}")
    finally:
        if proc.poll() is None:
            proc.kill()
        log.close()


# (c) 10 oct : Predict moves the deadline of an OPEN position → one new reminder for the new deadline;
#     the same deadline never re-reminds (dedupe key = position id + deadline string, across processes)
def test_new_deadline_re_reminds():
    T = at(Tree(live_once=False), "16:00"); T.tick(2170)
    r, rc = paper_fill(T, dict(BUY, deadline=fake_now("18:00")[:16]))
    pid = positions(T)[0]["id"]
    for hhmm in ("18:00:30", "18:05"):
        at(T, hhmm); T.tick(2171); T.watch_once()
    rows = jsonl(T, REMINDERS)
    rt.check("first deadline → exactly 1 reminder", rc == 0 and len(rows) == 1 and rows[0]["position_id"] == str(pid), f"lines={len(rows)}")
    new_dl = fake_now("14:00", 1)  # Predict gives a new deadline (next day 14:00), position stays open
    sp = T.L / "guardian/state.json"; st = json.loads(sp.read_text())
    st["positions"][0]["deadline"] = new_dl; sp.write_text(json.dumps(st, indent=2))
    at(T, "13:59", 1); T.tick(2172); T.watch_once()
    rt.check("new deadline not yet reached → no new reminder", len(jsonl(T, REMINDERS)) == 1)
    at(T, "15:08", 1); T.tick(2172)  # late cycle (box frozen over 14:00) still reminds once
    lines, rc = T.watch_once()
    rows = jsonl(T, REMINDERS)
    rt.check("new deadline passed → ONE new reminder (new deadline), reminder file updated", rc == 0 and len(rows) == 2
             and rows[1]["position_id"] == str(pid) and rows[1]["deadline"] == new_dl
             and reminder(T).get("deadline") == new_dl and positions(T)[0]["status"] == "open", f"lines={len(rows)}")
    for hhmm in ("15:10", "16:00", "20:00"):
        at(T, hhmm, 1); T.tick(2173); T.watch_once()
    rows = jsonl(T, REMINDERS)
    rt.check("same new deadline on later cycles / new processes → no duplicate (still 2 lines)", len(rows) == 2, f"lines={len(rows)}")


if __name__ == "__main__":
    before = rt.real_hashes()
    try:
        for t in (test_paper_reminder_default, test_live_reminder_default, test_stop_target_after_deadline,
                  test_validate_warnings, test_close_enabled_true, test_watcher_alive_past_deadline,
                  test_new_deadline_re_reminds):
            try:
                t()
            except Exception as e:  # noqa: BLE001
                import traceback; traceback.print_exc()
                rt.check(t.__name__ + " crashed", False, str(e))
    finally:
        for T in rt.TMPS:
            rt.kill_all(str(T))
        after = rt.real_hashes()
        # written by the REAL watcher / other routines, not by tests
        ignore = ("live_equity.json", "routine_runs.jsonl", "deadline_reminder.json", "deadline_reminders.jsonl")
        diff = {k: (before[k], after.get(k)) for k in before
                if before[k] != after.get(k) and not any(x in k for x in ignore)}
        rt.check("real state untouched", not diff, json.dumps(diff))
        left = [pid for T in rt.TMPS for pid in rt.watcher_pids_for(str(T))]
        rt.check("no test watcher left running", not left, str(left))
        n_ok = sum(1 for _, ok, _ in rt.RESULTS if ok)
        print(f"\n{n_ok}/{len(rt.RESULTS)} passed.")
        sys.exit(0 if n_ok == len(rt.RESULTS) else 1)
