#!/usr/bin/env python3
"""Isolated tests for watcher autostart + tick price source. Never touches the real state."""
from __future__ import annotations
import hashlib, json, os, shutil, signal, subprocess, sys, tempfile, time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path("/workspace/predict-market-bot")
G = REPO / "guardian" / "scripts"
TZ = ZoneInfo("Europe/Brussels")
RESULTS: list[tuple[str, bool, str]] = []
TMPS: list[Path] = []


def check(name, cond, info=""):
    RESULTS.append((name, bool(cond), info))
    print(("PASS " if cond else "FAIL ") + name + (f" — {info}" if info else ""), flush=True)


def real_hashes():
    out = {}
    for p in [REPO / "guardian/state.json", *sorted((REPO / "state").glob("*.json")),
              *sorted((REPO / "state").glob("*.jsonl")), REPO / "MODE"]:
        if p.name in ("watch_stops_heartbeat.json", "revolut_heartbeat.json", "routine_runs.jsonl",
                      "deadline_reminder.json", "deadline_reminders.jsonl"):
            continue  # rewritten by a real watcher / other bots' routines (shared log), not by tests

        out[str(p)] = hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None
    for p in [REPO / "state/watch_stops.pid", REPO / "state/watch_stops.log", REPO / "LIVE_ONCE",
              REPO / "state/live_orders.jsonl"]:
        out[str(p)] = p.exists()
    return out


def watcher_pids_for(marker: str) -> list[int]:
    pids = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            cmd = (d / "cmdline").read_bytes()
            if b"watch_stops" not in cmd:
                continue
            env = (d / "environ").read_bytes()
            cwd = os.readlink(d / "cwd")
        except OSError:
            continue
        if marker.encode() in cmd or marker.encode() in env or cwd.startswith(marker):
            pids.append(int(d.name))
    return pids


def kill_all(marker):
    for pid in watcher_pids_for(marker):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(0.5)
    for pid in watcher_pids_for(marker):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def now_iso(delta_s=0.0):
    return (datetime.now(TZ) - timedelta(seconds=delta_s)).isoformat()


def write_tick(ticks_dir: Path, pair, mid, age_s=0.0, day=None):
    ticks_dir.mkdir(parents=True, exist_ok=True)
    day = day or datetime.now(TZ).strftime("%Y-%m-%d")
    row = {"ts": now_iso(age_s), "pair": pair, "mid": mid, "source": "test",
           "bid": mid - 0.01, "ask": mid + 0.01}
    with (ticks_dir / f"{day}.jsonl").open("a") as f:
        f.write(json.dumps(row) + "\n")


def base_state():
    return {"bankroll_eur": 500, "cash_eur": 500, "positions": [], "daily_pnl_eur": 0,
            "peak_equity_eur": 500, "halted": False,
            "paper_inventory": {"ETH": 0.02085589, "SOL": 0.241308, "metamask_arbitrum": {"ETH": 0.0387}}}


def fake_revx(path: Path, ticker_file: Path, calls_log: Path):
    path.write_text(f"""#!/usr/bin/env bash
echo "$@" >> {calls_log}
case "$1 $2" in
  "market ticker")
     if [ -f {ticker_file} ]; then python3 -c "import json,sys;d=json.load(open('{ticker_file}'));p=d.get(sys.argv[1]);print(json.dumps({{'symbol':sys.argv[1],'last':p}})) if p else sys.exit(1)" "$3"; else exit 1; fi ;;
  "order open"|"order history") echo "[]" ;;
  "trade private") echo "[]" ;;
  "order place") echo '{{"id":"fake-order-1","state":"new"}}' ;;
  *) exit 2 ;;
esac
""")
    path.chmod(0o755)


def make_env(T: Path, extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PREDICT_BOT", "GUARDIAN_", "WATCH_STOPS", "PAPER_FILL", "PRICE_TICK"))}
    env.update({
        "PREDICT_BOT_ROOT": str(T),
        "GUARDIAN_STATE": str(T / "guardian_state.json"),
        "TRADES_LOG": str(T / "state/trades_log.jsonl"),
        "MODE_FILE": str(T / "MODE"),
        "STOP_FILE": str(T / "STOP"),
        "WATCH_STOPS_REVX_BIN": str(T / "fake_revx"),
        "WATCH_STOPS_NO_REVX_OPEN": "1",
        "WATCH_STOPS_INTERVAL": "1",
        "TEST_MARKER": str(T),
    })
    env.update(extra or {})
    return env


def new_root(state=None) -> Path:
    T = Path(tempfile.mkdtemp(prefix="pmb-watch-test-"))
    TMPS.append(T)
    (T / "state").mkdir()
    (T / "MODE").write_text("paper\n")
    (T / "guardian_state.json").write_text(json.dumps(state or base_state(), indent=2))
    fake_revx(T / "fake_revx", T / "fake_ticker.json", T / "revx_calls.log")
    return T


def paper_fill(env, order):
    p = subprocess.run([sys.executable, str(G / "paper_fill.py")], input=json.dumps(order),
                       text=True, capture_output=True, env=env, timeout=60)
    try:
        return json.loads(p.stdout), p.returncode
    except json.JSONDecodeError:
        return {"raw": p.stdout, "err": p.stderr}, p.returncode


def watch_once(env, *args):
    p = subprocess.run([sys.executable, str(G / "watch_stops.py"), "--once", *args], text=True,
                       capture_output=True, env=env, timeout=90)
    lines = [json.loads(l) for l in p.stdout.splitlines() if l.strip().startswith("{")]
    return lines, p.returncode, p.stderr


def log_rows(T):
    out = []
    lp = T / "state/watch_stops.log"
    if lp.exists():
        for l in lp.read_text().splitlines():
            if l.startswith("{"):
                try:
                    out.append(json.loads(l))
                except json.JSONDecodeError:
                    pass
    return out


def wait_for(fn, timeout=20.0, step=0.25):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return None


def state_of(T):
    return json.loads((T / "guardian_state.json").read_text())


BUY_BTC = {"pair": "BTC-EUR", "side": "buy", "type": "limit", "price": 72000, "amount_eur": 10,
           "stop_price": 70000, "idea_type": "hausse", "decision_id": "T-1", "post_only": True}
SELL_SOL = {"pair": "SOL-EUR", "side": "sell", "type": "limit", "price": 96, "amount_eur": 9.6, "qty": 0.1,
            "idea_type": "baisse", "kind": "baisse", "decision_id": "T-2", "stop_price": 100,
            "target_price": 90, "post_only": True}


def test_autostart_flow():
    T = new_root()
    env = make_env(T)
    ticks = T / "state/price_ticks"
    write_tick(ticks, "BTC-EUR", 72000); write_tick(ticks, "SOL-EUR", 96)
    try:
        # 1) open paper → watcher started
        r, rc = paper_fill(env, BUY_BTC)
        check("open paper hausse → watcher_started", rc == 0 and r.get("watcher_started") is True,
              f"rc={rc} watcher_started={r.get('watcher_started')} pid={r.get('watcher_pid')}")
        pid = r.get("watcher_pid")
        pidfile = T / "state/watch_stops.pid"
        check("pid file in temp root matches", pidfile.exists() and int(pidfile.read_text().split()[0]) == pid)
        envb = Path(f"/proc/{pid}/environ").read_bytes() if pid else b""
        check("detached watcher uses temp state (env inherited)",
              f"GUARDIAN_STATE={T}/guardian_state.json".encode() in envb)
        check("detached watcher own session", pid and os.getsid(pid) == pid)
        # fresh tick used
        row = wait_for(lambda: next((x for x in log_rows(T) if x.get("action") == "watch"), None))
        pm = (row or {}).get("prices", {}).get("BTC-EUR", {})
        check("fresh tick used (source=ticks, age logged)",
              pm.get("source") == "ticks" and pm.get("age_s") is not None and pm["age_s"] < 120,
              json.dumps(pm))
        # 2) second open → already running, no duplicate
        r2, rc2 = paper_fill(env, SELL_SOL)
        check("2nd open (baisse) → watcher_already_running", rc2 == 0 and r2.get("watcher_already_running") is True
              and r2.get("watcher_started") is False, f"{ {k: r2.get(k) for k in ('watcher_started','watcher_already_running','watcher_pid')} }")
        lines, rcx, _ = watch_once(env)
        check("manual 2nd watch_stops refuses (already_running)", rcx == 0 and lines and lines[0].get("action") == "already_running")
        check("exactly one watcher process for temp root", watcher_pids_for(str(T)) == [pid], str(watcher_pids_for(str(T))))
        # 3) SOL safety breach (short, mid >= stop) while BTC still open → close + continue
        write_tick(ticks, "BTC-EUR", 72100); write_tick(ticks, "SOL-EUR", 101)
        cont = wait_for(lambda: next((x for x in log_rows(T) if x.get("action") == "continue_after_close"), None))
        closed_row = next((x for x in log_rows(T) if x.get("action") == "stop_closed"), {})
        c0 = (closed_row.get("closed") or [{}])[0]
        check("short safety close (mid≥stop) via detached watcher", c0.get("pair") == "SOL-EUR"
              and c0.get("close_reason") == "stop_hit" and c0.get("rebuy_reason") == "safety", json.dumps(c0)[:300])
        check("closed item logs price source ticks", c0.get("price_source") == "ticks")
        check("continue_after_close with 1 remaining", cont and cont.get("remaining") == 1, json.dumps(cont))
        time.sleep(1.5)
        check("watcher still alive after close", Path(f"/proc/{pid}").exists())
        wake = json.loads((T / "state/auto_stop_wake.json").read_text())
        check("wake file written (paper, SOL)", wake.get("mode") == "paper" and wake.get("pair") == "SOL-EUR", wake.get("message_fr", ""))
        ev = [json.loads(l) for l in (T / "state/auto_stop_events.jsonl").read_text().splitlines()]
        check("event written with rebuy safety + source", ev and ev[-1]["pair"] == "SOL-EUR"
              and ev[-1]["rebuy_reason"] == "safety" and ev[-1]["price_source"] == "ticks", ev[-1]["message_fr"] if ev else "")
        st = state_of(T)
        sol = [p for p in st["positions"] if p["pair"] == "SOL-EUR"][0]
        check("SOL position closed in temp state", sol["status"] == "closed")
        later = wait_for(lambda: [x for x in log_rows(T) if x.get("action") == "watch"
                                  and x.get("open") == 1 and x.get("ts", "") >= cont.get("ts", "")])
        check("watch continues on BTC after close", bool(later))
        # 4) BTC long stop (mid <= stop) → close, nothing left → exit 10
        write_tick(ticks, "BTC-EUR", 69900)
        gone = wait_for(lambda: not Path(f"/proc/{pid}").exists() or
                        Path(f"/proc/{pid}/stat").read_text().split()[2] == "Z", timeout=20)
        btc = [p for p in state_of(T)["positions"] if p["pair"] == "BTC-EUR"][0]
        check("long stop close (mid≤stop) then watcher exits", gone and btc["status"] == "closed"
              and btc.get("close_reason") == "stop_hit", f"status={btc['status']}")
        check("pid file released", not pidfile.exists())
        launcher = [l for l in (T / "state/watch_stops.log").read_text().splitlines() if l.startswith("[launcher]")]
        check("log appended to state/watch_stops.log with launcher line", len(launcher) == 1, launcher[0] if launcher else "")
    finally:
        kill_all(str(T))


def test_disabled_and_preopen():
    T = new_root()
    write_tick(T / "state/price_ticks", "BTC-EUR", 72000)
    env = make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    try:
        r, rc = paper_fill(env, BUY_BTC)
        check("PAPER_FILL_NO_WATCH=1 → no watcher", rc == 0 and r.get("watcher_started") is False
              and r.get("watcher_disabled") is True and not watcher_pids_for(str(T)))
        # pre-open: open position exists, no watcher → next open starts it before opening
        env2 = make_env(T)
        r2, rc2 = paper_fill(env2, dict(BUY_BTC, amount_eur=5))
        pre = r2.get("watcher_preopen") or {}
        check("pre-open: unwatched positions → watcher started before open", rc2 == 0 and pre.get("watcher_started") is True
              and r2.get("watcher_already_running") is True, json.dumps({k: r2.get(k) for k in ('watcher_started','watcher_already_running','watcher_preopen')}))
        # rejected open still triggers pre-open check (kill first)
        kill_all(str(T)); time.sleep(0.3)
        r3, rc3 = paper_fill(env2, dict(BUY_BTC, amount_eur=50))
        check("pre-open check also on a rejected open", rc3 == 1 and (r3.get("watcher_preopen") or {}).get("watcher_started") is True,
              str(r3.get("reasons"))[:120])
    finally:
        kill_all(str(T))


def pos_long(pair, avg, stop, cost=10.0):
    return {"id": f"rx-paper-test-{pair}", "pair": pair, "side": "long", "idea_type": "hausse", "qty": cost / avg,
            "avg_price": avg, "cost_eur": cost, "mark_eur": cost, "stop_price_eur": stop, "status": "open"}


def pos_short(pair, avg, stop, target, qty=0.1):
    return {"id": f"rx-paper-test-short-{pair}", "pair": pair, "side": "short", "idea_type": "baisse", "kind": "baisse",
            "qty": qty, "avg_price": avg, "cost_eur": qty * avg, "mark_eur": qty * avg, "stop_price": stop,
            "stop_price_eur": stop, "safety_price": stop, "target_price": target, "decision_id": "T-9",
            "venue": "revolut_x", "fee_eur": 0.0048, "status": "open"}


def test_price_sources():
    st = base_state(); st["positions"] = [pos_long("ETH-EUR", 2170, 2000)]
    # stale tick → revolut
    T = new_root(st); env = make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    write_tick(T / "state/price_ticks", "ETH-EUR", 2171, age_s=180)
    (T / "fake_ticker.json").write_text(json.dumps({"ETH-EUR": 2180.5}))
    lines, rc, err = watch_once(env)
    pm = lines[-1].get("prices", {}).get("ETH-EUR", {}) if lines else {}
    check("tick >2 min → fallback revolut", pm.get("source") == "revolut" and pm.get("mid") == 2180.5
          and pm.get("fallback_reason") == "tick_stale" and pm.get("tick_age_s", 0) >= 180, json.dumps(pm))
    # revolut fails → scan
    (T / "fake_ticker.json").unlink()
    (T / "state/last_scan.json").write_text(json.dumps({"scanned_at": now_iso(10), "pairs": [{"pair": "ETH-EUR", "price_eur": 2175.0}]}))
    lines, rc, err = watch_once(env)
    pm = lines[-1].get("prices", {}).get("ETH-EUR", {}) if lines else {}
    check("tick stale + revolut down → scan", pm.get("source") == "scan" and pm.get("mid") == 2175.0 and pm.get("age_s") is not None, json.dumps(pm))
    # missing tick file
    T2 = new_root(st); env2 = make_env(T2, {"PAPER_FILL_NO_WATCH": "1"})
    (T2 / "fake_ticker.json").write_text(json.dumps({"ETH-EUR": 2190.0}))
    lines, rc, err = watch_once(env2)
    pm = lines[-1].get("prices", {}).get("ETH-EUR", {}) if lines else {}
    check("no tick → revolut (tick_missing)", pm.get("source") == "revolut" and pm.get("fallback_reason") == "tick_missing", json.dumps(pm))
    # fresh tick wins over revolut
    write_tick(T2 / "state/price_ticks", "ETH-EUR", 2172.0, age_s=20)
    lines, rc, err = watch_once(env2)
    pm = lines[-1].get("prices", {}).get("ETH-EUR", {}) if lines else {}
    calls = (T2 / "revx_calls.log").read_text().splitlines()
    check("fresh tick (20 s) preferred, revolut not called", pm.get("source") == "ticks" and pm.get("mid") == 2172.0
          and len(calls) == 1, f"{json.dumps(pm)} revx_calls={len(calls)}")
    # yesterday file just after midnight
    T3 = new_root(st); env3 = make_env(T3, {"PAPER_FILL_NO_WATCH": "1"})
    yday = (datetime.now(TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
    write_tick(T3 / "state/price_ticks", "ETH-EUR", 2173.0, age_s=5, day=yday)
    lines, rc, err = watch_once(env3)
    pm = lines[-1].get("prices", {}).get("ETH-EUR", {}) if lines else {}
    check("tick from yesterday's file (midnight) still read", pm.get("source") == "ticks", json.dumps(pm))
    # efficient tail on a big file
    T4 = new_root(st)
    td = T4 / "state/price_ticks"; td.mkdir(parents=True)
    day = datetime.now(TZ).strftime("%Y-%m-%d")
    with (td / f"{day}.jsonl").open("w") as f:
        line = json.dumps({"ts": now_iso(3600), "pair": "BTC-EUR", "mid": 1.0, "source": "x"}) + "\n"
        f.write(line * 200000)
    write_tick(td, "ETH-EUR", 2174.0)
    code = ("import sys,time;sys.argv=['x'];import watch_stops as w;t=time.perf_counter();"
            "r=w.read_latest_ticks(['ETH-EUR','SOL-EUR']);print(round((time.perf_counter()-t)*1000,1),r.get('ETH-EUR',{}).get('mid'))")
    p = subprocess.run([sys.executable, "-c", code], cwd=str(G), text=True, capture_output=True,
                       env=make_env(T4))
    ms, mid = p.stdout.split()
    size_mb = (td / f"{day}.jsonl").stat().st_size / 1e6
    check("tail read fast on big file", float(ms) < 100 and mid == "2174.0", f"{size_mb:.1f} MB file, {ms} ms, mid={mid}")


def test_closes_once():
    # short target hit
    st = base_state(); st["positions"] = [pos_short("SOL-EUR", 96, 100, 90)]
    T = new_root(st); env = make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    write_tick(T / "state/price_ticks", "SOL-EUR", 89.5)
    lines, rc, err = watch_once(env)
    s = [p for p in state_of(T)["positions"]][0]
    ev = json.loads((T / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
    check("short target close (mid≤target) rc=10", rc == 10 and s["status"] == "closed" and s.get("close_reason") == "target_hit"
          and ev["rebuy_reason"] == "target" and ev["close_reason"] == "target_hit", f"rc={rc} pnl={s.get('realized_pnl_eur')} {ev['message_fr']}")
    # short safety
    st = base_state(); st["positions"] = [pos_short("SOL-EUR", 96, 100, 90)]
    T = new_root(st); env = make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    write_tick(T / "state/price_ticks", "SOL-EUR", 100.2)
    lines, rc, err = watch_once(env)
    s = state_of(T)["positions"][0]
    check("short safety close (mid≥stop) rc=10", rc == 10 and s["status"] == "closed" and s.get("rebuy_reason") == "safety", f"pnl={s.get('realized_pnl_eur')}")
    # long stop
    st = base_state(); st["positions"] = [pos_long("BTC-EUR", 72000, 70000)]; st["cash_eur"] = 490
    T = new_root(st); env = make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    write_tick(T / "state/price_ticks", "BTC-EUR", 69950)
    lines, rc, err = watch_once(env)
    s = state_of(T)["positions"][0]
    wake = json.loads((T / "state/auto_stop_wake.json").read_text())
    check("long stop close (mid≤stop) rc=10 + wake", rc == 10 and s["status"] == "closed" and wake.get("pair") == "BTC-EUR"
          and wake.get("price_sources", [{}])[0].get("price_source") == "ticks", f"pnl={s.get('realized_pnl_eur')}")
    # no breach / idle
    T = new_root(base_state()); env = make_env(T, {"PAPER_FILL_NO_WATCH": "1"})
    lines, rc, err = watch_once(env)
    check("idle when no position → exit 0", rc == 0 and lines[-1].get("action") == "idle")


def test_live_copy_tree():
    """live_place in a COPIED tree (all paths relative to the copy) with a fake revx client."""
    L = Path(tempfile.mkdtemp(prefix="pmb-live-test-")); TMPS.append(L)
    (L / "guardian/scripts").mkdir(parents=True)
    for f in ("live_place.py", "validate_order.py", "watch_stops.py", "watcher_launch.py", "paper_fill.py", "check_alerts.py"):
        shutil.copy2(G / f, L / "guardian/scripts" / f)
    shutil.copy2(REPO / "guardian/config.json", L / "guardian/config.json")
    shutil.copy2(REPO / "config.json", L / "config.json")
    (L / "guardian/state.json").write_text(json.dumps(base_state(), indent=2))
    (L / "state").mkdir(); (L / "MODE").write_text("paper\n"); (L / "LIVE_ONCE").write_text("test\n")
    fake_revx(L / "fake_revx", L / "fake_ticker.json", L / "revx_calls.log")
    write_tick(L / "state/price_ticks", "ETH-EUR", 2170.0)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PREDICT_BOT", "GUARDIAN_", "WATCH_STOPS", "PAPER_FILL", "PRICE_TICK", "MODE_FILE", "STOP_FILE", "TRADES_LOG"))}
    env.update({"REVX_BIN": str(L / "fake_revx"), "WATCH_STOPS_REVX_BIN": str(L / "fake_revx"),
                "WATCH_STOPS_INTERVAL": "1", "TEST_MARKER": str(L)})
    order = {"pair": "ETH-EUR", "side": "buy", "type": "limit", "price": 2170, "amount_eur": 10,
             "stop_price": 2100, "idea_type": "hausse", "post_only": True,
             "expected_gain_eur": 3, "expected_loss_eur": 0.3, "decision_id": "T-L"}
    (L / "order.json").write_text(json.dumps(order))
    try:
        p = subprocess.run([sys.executable, str(L / "guardian/scripts/live_place.py"), "--order", str(L / "order.json")],
                           text=True, capture_output=True, env=env, timeout=90)
        r = json.loads(p.stdout)
        check("live_place (fake client) ok + watcher_started", p.returncode == 0 and r.get("ok") and r.get("watcher_started") is True,
              f"rc={p.returncode} watcher={r.get('watcher_started')} err={r.get('error')}")
        check("live gates unchanged: LIVE_ONCE consumed + live_day.json written (copy)",
              not (L / "LIVE_ONCE").exists() and json.loads((L / "state/live_day.json").read_text()).get("count") == 1)
        pid = r.get("watcher_pid")
        row = wait_for(lambda: next((x for x in log_rows(L) if x.get("action") == "watch"), None))
        w = (row or {}).get("watching", [{}])
        check("watcher sees live position from live_orders.jsonl with stop", w and w[0].get("mode") == "live"
              and w[0].get("stop") == 2100 and w[0].get("price_source") == "ticks", json.dumps(w)[:250])
        write_tick(L / "state/price_ticks", "ETH-EUR", 2095.0)
        gone = wait_for(lambda: not Path(f"/proc/{pid}").exists() or
                        Path(f"/proc/{pid}/stat").read_text().split()[2] == "Z", timeout=20)
        wake = json.loads((L / "state/auto_stop_wake.json").read_text())
        ev = json.loads((L / "state/auto_stop_events.jsonl").read_text().splitlines()[-1])
        places = [c for c in (L / "revx_calls.log").read_text().splitlines() if c.startswith("order place")]
        check("live stop → urgent wake mode=live, auto_sell False, exit", gone and wake.get("mode") == "live"
              and wake.get("auto_sell") is False and ev.get("close_reason") == "stop_hit_live_pending", wake.get("message_fr", ""))
        check("no automatic live sell (only the 1 test buy hit fake client)", len(places) == 1 and " buy " in f" {places[0]} ", places[0][:80] if places else "")
        # 2nd live_place same day: refused by max-1/day (unchanged), no watcher dup
        p2 = subprocess.run([sys.executable, str(L / "guardian/scripts/live_place.py"), "--order", str(L / "order.json")],
                            text=True, capture_output=True, env=env, timeout=90)
        check("max 1 live/day still enforced (rc 7)", p2.returncode == 7)
    finally:
        kill_all(str(L))


if __name__ == "__main__":
    before = real_hashes()
    try:
        for t in (test_autostart_flow, test_disabled_and_preopen, test_price_sources, test_closes_once):
            try:
                t()
            except Exception as e:  # noqa: BLE001
                import traceback; traceback.print_exc()
                check(t.__name__ + " crashed", False, str(e))
    finally:
        for T in TMPS:
            kill_all(str(T))
        after = real_hashes()
        diff = {k: (before[k], after.get(k)) for k in before if before[k] != after.get(k)}
        # trades/price ticks may legitimately change from the real collector; only report
        check("real state untouched (guardian/state.json, state/*.json(l), pid/log/LIVE_ONCE)",
              not {k: v for k, v in diff.items() if "price_ticks" not in k}, json.dumps(diff))
        left = [pid for T in TMPS for pid in watcher_pids_for(str(T))]
        check("no test watcher left running", not left, str(left))
        n_ok = sum(1 for _, ok, _ in RESULTS if ok)
        print(f"\n{n_ok}/{len(RESULTS)} passed. tmp dirs: {[str(t) for t in TMPS]}")
        sys.exit(0 if n_ok == len(RESULTS) else 1)
