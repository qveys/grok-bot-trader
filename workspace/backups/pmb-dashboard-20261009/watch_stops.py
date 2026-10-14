#!/usr/bin/env python3
"""Stop-loss watcher for ALL open positions (paper + live).

Poll mid prices while any watchable position is open (guardian/state.json,
state/positions.json crypto rows, live_orders.jsonl fills, revx open orders
best-effort).

On stop / target breach:
  - paper/sim long → sell via paper_fill; short (idée à la baisse) → rebuy
    (safety if mid≥stop, target if mid≤target_price); wake + events, exit 10
  - live (8 oct, décision Quentin; guardian/config.json allow_live_auto_sell=true):
    positions tracked from state/live_orders.jsonl → automatic exit via
    `live_place.py --exit` (sells only the pipeline qty, never Quentin's coins,
    executable limit bid−0.3 %, 3 tries; lock state/live_exits.json = one exit per
    position). Wake for Risk (bilan/journal, urgent=false) + event; urgent wake only
    if the exit fails. Other live rows (revx open orders, positions.json) or
    allow_live_auto_sell=false → urgent wake only (no sale), as before.

Paper path never places live Revolut orders.

Price source (each cycle, per pair):
  1. last tick of the pair in state/price_ticks/YYYY-MM-DD.jsonl (shared 30 s collector,
     Brussels date; tail-read) if age <= 120 s (PRICE_TICK_MAX_AGE_S);
  2. else Revolut X ticker (`revx market ticker`, read-only);
  3. else last scan (state/last_scan.json, scan_crypto re-run at most every 60 s);
  4. else the stale tick, else the position's last_mid_eur.
  The cycle payload logs `prices[pair] = {mid, source, age_s}`.

Heure limite (Predict, 8 oct) = REMINDER ONLY (Quentin, 8 oct 23h): config
`deadline.close_enabled` defaults to false → when now >= `deadline` (alias `deadline_at`) nothing
is closed; the watcher writes state/deadline_reminder.json and one line per position in
state/deadline_reminders.jsonl. Only stop and target close a trade. close_enabled=true restores
the old close (paper via paper_fill, live via `live_place.py --exit`, reason "heure_limite").

Fermeture 22h (code kept, RETIRÉE Quentin 8 oct): `live_window.force_close_enabled` defaults
to false. When true, at `force_close` (22:00) every still-open LIVE position from
live_orders.jsonl is exited via `live_place.py --exit` (reason "fermeture_22h"). Paper never.
Heartbeat: state/watch_stops_heartbeat.json each loop; while any position is open, also
state/revolut_heartbeat.json every ~5 min (read-only revx ticker/balances, never an order).

Lifecycle: started detached by paper_fill / live_place (watcher_launch.py) or by
start_stop_watch.sh. After a close, if other positions stay open it keeps watching
(wake + event already written); it exits 10 only when nothing is left to watch
(or with --once / --exit-on-close). Exit 0 when idle. Live breaches are alerted
once per position per process (urgent wake), never auto-sold.
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("PREDICT_BOT_ROOT", str(GUARDIAN.parent)))
STATE_PATH = Path(os.environ.get("GUARDIAN_STATE", str(GUARDIAN / "state.json")))
ROOT_POSITIONS_PATH = Path(os.environ.get("ROOT_POSITIONS", str(ROOT / "state" / "positions.json")))
LIVE_ORDERS_PATH = Path(os.environ.get("LIVE_ORDERS", str(ROOT / "state" / "live_orders.jsonl")))
SCAN_PATH = Path(os.environ.get("SCAN_PATH", str(ROOT / "state" / "last_scan.json")))
SCAN_SCRIPT = ROOT / "scripts" / "scan_crypto.py"
PAPER_FILL = GUARDIAN / "scripts" / "paper_fill.py"
CHECK_ALERTS = GUARDIAN / "scripts" / "check_alerts.py"
WAKE_PATH = Path(os.environ.get("AUTO_STOP_WAKE", str(ROOT / "state" / "auto_stop_wake.json")))
EVENTS_PATH = Path(os.environ.get("AUTO_STOP_EVENTS", str(ROOT / "state" / "auto_stop_events.jsonl")))
PID_PATH = Path(os.environ.get("WATCH_STOPS_PID", str(ROOT / "state" / "watch_stops.pid")))
ALERTS_PATH = Path(os.environ.get("ALERTS_LAST", str(ROOT / "state" / "alerts_last.json")))
HEARTBEAT_PATH = Path(os.environ.get("WATCH_STOPS_HEARTBEAT", str(ROOT / "state" / "watch_stops_heartbeat.json")))
REVOLUT_HB_PATH = Path(os.environ.get("REVOLUT_HEARTBEAT", str(ROOT / "state" / "revolut_heartbeat.json")))
REVOLUT_HB_INTERVAL_S = float(os.environ.get("REVOLUT_HB_INTERVAL_S", "300"))  # ~5 min
_last_revolut_hb_monotonic = 0.0
_revolut_hb_failures = 0

TICKS_DIR = Path(os.environ.get("PRICE_TICKS_DIR", str(ROOT / "state" / "price_ticks")))

TZ = ZoneInfo("Europe/Brussels")
SCAN_MIN_INTERVAL_S = 60.0
TICK_MAX_AGE_S = float(os.environ.get("PRICE_TICK_MAX_AGE_S", "120"))
DEFAULT_INTERVAL_S = 30.0
MAX_CONSECUTIVE_ERRORS = 5
REVX_BIN = os.environ.get("WATCH_STOPS_REVX_BIN") or os.path.expanduser("~/.local/bin/revx")
# check_alerts.py has hard-coded real paths: only run it when we watch the real state
_REAL_PATHS = (
    STATE_PATH.resolve() == (GUARDIAN / "state.json").resolve()
    and ROOT.resolve() == GUARDIAN.parent.resolve()
)
WHITELIST_PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
LIVE_PLACE = GUARDIAN / "scripts" / "live_place.py"
LIVE_EXITS_PATH = Path(os.environ.get("LIVE_EXITS", str(ROOT / "state" / "live_exits.json")))
GUARDIAN_CONFIG = Path(os.environ.get("GUARDIAN_CONFIG", str(GUARDIAN / "config.json")))


def _load_cfg() -> dict:
    try:
        return json.loads(GUARDIAN_CONFIG.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


# 8 oct, décision Quentin: live stop exit is automatic (config allow_live_auto_sell)
ALLOW_LIVE_AUTO_SELL = bool(_load_cfg().get("allow_live_auto_sell", False))
FORCE_CLOSE_REASON = "fermeture_22h"
DEADLINE_REASON = "heure_limite"  # per-position deadline written by Predict
TIME_EXIT_LABELS = {FORCE_CLOSE_REASON: "Fermeture 22h", DEADLINE_REASON: "Heure limite"}
REAL_ROOT = Path("/workspace/predict-market-bot")
_PROC_START = time.time()


def _fake_now() -> datetime | None:
    """TEST ONLY: PMB_FAKE_NOW (ISO, Brussels if naive), advancing with real time since start.
    Honoured only when the script runs from a COPIED tree (never the real repo) with TEST_MARKER."""
    raw = os.environ.get("PMB_FAKE_NOW")
    if not raw or not os.environ.get("TEST_MARKER"):
        return None
    try:
        if GUARDIAN.parent.resolve() == REAL_ROOT.resolve() or ROOT.resolve() == REAL_ROOT.resolve():
            return None
        dt = datetime.fromisoformat(raw)
    except (OSError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    from datetime import timedelta
    return dt.astimezone(TZ) + timedelta(seconds=time.time() - _PROC_START)


def now_local() -> datetime:
    """Local Brussels time used for the 22h live force-close."""
    return _fake_now() or datetime.now(TZ)


def force_close_minutes() -> int:
    raw = str((_load_cfg().get("live_window") or {}).get("force_close") or "22:00")
    try:
        h, m = (int(x) for x in raw.strip().split(":")[:2])
        if 0 <= h <= 24 and 0 <= m < 60:
            return min(24 * 60, h * 60 + m)
    except ValueError:
        pass
    return 22 * 60


def force_close_enabled() -> bool:
    """config live_window.force_close_enabled (default false — retirée Quentin 8 oct). Set true to restore."""
    v = (_load_cfg().get("live_window") or {}).get("force_close_enabled", False)
    if isinstance(v, str):
        return v.strip().lower() not in ("false", "0", "no", "off", "")
    return bool(v)


def position_deadline(pos: dict) -> datetime | None:
    """Position deadline (`deadline` or alias `deadline_at`, ISO; naive = Europe/Brussels)."""
    raw = pos.get("deadline") or pos.get("deadline_at")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt


def deadline_close_enabled() -> bool:
    """config deadline.close_enabled (default false — Quentin 8 oct 23h: l'heure limite n'est qu'un rappel)."""
    v = (_load_cfg().get("deadline") or {}).get("close_enabled", False)
    if isinstance(v, str):
        return v.strip().lower() not in ("false", "0", "no", "off", "")
    return bool(v)


DEADLINE_REMINDER_PATH = ROOT / "state" / "deadline_reminder.json"
DEADLINE_REMINDER_LOG = ROOT / "state" / "deadline_reminders.jsonl"
_deadline_reminded: set = set()


def deadline_remind(pos: dict) -> None:
    """Heure limite atteinte, fermeture coupée : écrit un rappel (une fois par position), ne ferme rien."""
    pid = str(pos.get("id"))
    if pid in _deadline_reminded:
        return
    _deadline_reminded.add(pid)
    rec = {"ts": now_local().isoformat(), "position_id": pid, "pair": pos.get("pair"),
           "decision_id": pos.get("decision_id"), "deadline": pos.get("deadline") or pos.get("deadline_at"),
           "idea_type": pos.get("idea_type") or pos.get("kind"), "action": "rappel_heure_limite",
           "note": "Rappel seulement : Predict regarde le trade ; Risk décide. Rien n'est fermé."}
    try:
        if DEADLINE_REMINDER_LOG.exists():
            for line in DEADLINE_REMINDER_LOG.read_text().splitlines():
                try:
                    if str(json.loads(line).get("position_id")) == pid:
                        return  # déjà rappelé (process précédent)
                except (ValueError, AttributeError):
                    continue
        DEADLINE_REMINDER_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DEADLINE_REMINDER_LOG, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        _atomic_json(DEADLINE_REMINDER_PATH, rec)
    except OSError:
        pass


def deadline_due(pos: dict, now: datetime | None = None) -> bool:
    dl = position_deadline(pos)
    return dl is not None and (now or now_local()) >= dl


def live_force_close_due(pos: dict, now: datetime | None = None) -> bool:
    """True if a LIVE position is past its force-close deadline (opening day at force_close)."""
    from datetime import timedelta
    if not force_close_enabled():
        return False
    now = (now or now_local()).astimezone(TZ)
    fc = force_close_minutes()
    opened = _parse_ts(str(pos.get("opened_at") or ""))
    day = opened.astimezone(TZ).date() if opened else now.date()
    deadline = datetime(day.year, day.month, day.day, tzinfo=TZ) + timedelta(minutes=fc)
    return now >= deadline

_pid_written = False
_last_scan_run_monotonic = 0.0
_live_alerted: set[str] = set()  # live position ids already alerted by this process



def _today_brussels():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d")


def _daily_pnl_today(state):
    """Daily P&L resets each day (Brussels): stale value from a previous day counts as 0."""
    if state.get("daily_pnl_date") != _today_brussels():
        return 0.0
    return float(state.get("daily_pnl_eur", 0) or 0)

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_local_iso() -> str:
    return datetime.now(TZ).isoformat()


def log_json(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    cmdline = Path(f"/proc/{pid}/cmdline")
    if cmdline.exists():
        try:
            if b"watch_stops" not in cmdline.read_bytes():
                return False  # recycled pid, not a watcher
        except OSError:
            pass
    return True


def acquire_pid(force: bool) -> bool:
    """Return True if we own the pid file; False if another watcher is running."""
    global _pid_written
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PID_PATH.exists() and not force:
        try:
            old = int(PID_PATH.read_text().strip().split()[0])
        except (ValueError, OSError, IndexError):
            old = -1
        if old > 0 and old != os.getpid() and pid_alive(old):
            log_json(
                {
                    "ok": True,
                    "action": "already_running",
                    "pid": old,
                    "pid_file": str(PID_PATH),
                }
            )
            return False
    PID_PATH.write_text(f"{os.getpid()}\n")
    _pid_written = True
    return True


def release_pid() -> None:
    global _pid_written
    if not _pid_written:
        return
    try:
        if PID_PATH.exists():
            cur = int(PID_PATH.read_text().strip().split()[0])
            if cur == os.getpid():
                PID_PATH.unlink(missing_ok=True)
    except (ValueError, OSError, IndexError):
        pass
    _pid_written = False


def scan_price_map(scan: dict) -> dict[str, float]:
    prices: dict[str, float] = {}
    for row in scan.get("pairs") or scan.get("markets") or []:
        pair = str(row.get("pair") or "").upper()
        px = row.get("price_eur")
        if pair and px is not None:
            try:
                prices[pair] = float(px)
            except (TypeError, ValueError):
                pass
    return prices


def try_run_scan(timeout_s: float = 25.0) -> dict[str, float]:
    """Run scan_crypto at most every SCAN_MIN_INTERVAL_S; return price map (may be empty)."""
    global _last_scan_run_monotonic
    now_m = time.monotonic()
    age = now_m - _last_scan_run_monotonic
    if _last_scan_run_monotonic > 0 and age < SCAN_MIN_INTERVAL_S:
        return scan_price_map(load_json(SCAN_PATH))

    scan = load_json(SCAN_PATH)
    scanned_at = scan.get("scanned_at")
    if scanned_at:
        try:
            ts = scanned_at.replace("Z", "+00:00")
            scanned_dt = datetime.fromisoformat(ts)
            if scanned_dt.tzinfo is None:
                scanned_dt = scanned_dt.replace(tzinfo=timezone.utc)
            age_s = (datetime.now(timezone.utc) - scanned_dt.astimezone(timezone.utc)).total_seconds()
            if age_s < SCAN_MIN_INTERVAL_S:
                return scan_price_map(scan)
        except (TypeError, ValueError):
            pass

    if not SCAN_SCRIPT.exists():
        return scan_price_map(scan)

    _last_scan_run_monotonic = now_m
    try:
        proc = subprocess.run(
            [sys.executable, str(SCAN_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        log_json({"ok": True, "action": "scan_skip", "reason": str(e)})
        return scan_price_map(load_json(SCAN_PATH))

    if proc.returncode != 0:
        log_json(
            {
                "ok": True,
                "action": "scan_failed",
                "returncode": proc.returncode,
                "stderr": (proc.stderr or "")[:200],
            }
        )
        return scan_price_map(load_json(SCAN_PATH))

    return scan_price_map(load_json(SCAN_PATH))


def revx_ticker_mid(pair: str, timeout_s: float = 12.0) -> float | None:
    """Best-effort mid from `revx market ticker PAIR --json`. No orders."""
    bin_path = REVX_BIN if Path(REVX_BIN).exists() else "revx"
    try:
        proc = subprocess.run(
            [bin_path, "market", "ticker", pair, "--json"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ, "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", "")},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    raw = (proc.stdout or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        data = data["data"]  # real revx format: {"data": [{bid, ask, mid, last_price}]}
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None
    for key in ("mid", "last", "last_price", "lastPrice", "price", "markPrice"):
        if data.get(key) is not None:
            try:
                return float(data[key])
            except (TypeError, ValueError):
                pass
    bid = data.get("bid") or data.get("bestBid")
    ask = data.get("ask") or data.get("bestAsk")
    try:
        if bid is not None and ask is not None:
            return (float(bid) + float(ask)) / 2.0
        if bid is not None:
            return float(bid)
        if ask is not None:
            return float(ask)
    except (TypeError, ValueError):
        return None
    return None


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt


def _tick_mid(row: dict) -> float | None:
    for key in ("mid",):
        if row.get(key) is not None:
            try:
                v = float(row[key])
                if v > 0:
                    return v
            except (TypeError, ValueError):
                pass
    try:
        bid, ask = row.get("bid"), row.get("ask")
        if bid is not None and ask is not None and float(bid) > 0 and float(ask) > 0:
            return (float(bid) + float(ask)) / 2.0
        if row.get("last") is not None and float(row["last"]) > 0:
            return float(row["last"])
    except (TypeError, ValueError):
        pass
    return None


def _scan_file_tail(path: Path, wanted: set[str], found: dict[str, dict]) -> None:
    """Read the end of a JSONL tick file backwards (8 KB, then up to 256 KB)."""
    try:
        size = path.stat().st_size
    except OSError:
        return
    for chunk in (8192, 65536, 262144):
        start = max(0, size - chunk)
        try:
            with path.open("rb") as f:
                f.seek(start)
                data = f.read(size - start)
        except OSError:
            return
        lines = data.split(b"\n")
        if start > 0 and lines:
            lines = lines[1:]  # first line is partial
        for raw in reversed(lines):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            pair = str(row.get("pair") or "").upper()
            if pair in wanted and pair not in found and _tick_mid(row) is not None:
                found[pair] = row
        if wanted.issubset(found) or start == 0:
            return


def read_latest_ticks(pairs: list[str]) -> dict[str, dict]:
    """Latest tick per pair from today's (then yesterday's) Brussels tick file."""
    from datetime import timedelta

    wanted = {p.upper() for p in pairs}
    found: dict[str, dict] = {}
    now_local = datetime.now(TZ)
    for day in (now_local, now_local - timedelta(days=1)):
        if wanted.issubset(found):
            break
        _scan_file_tail(TICKS_DIR / f"{day.strftime('%Y-%m-%d')}.jsonl", wanted, found)
    return found


def _age_s(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return round(max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()), 1)


def _scan_age_s() -> float | None:
    return _age_s(_parse_ts(str(load_json(SCAN_PATH).get("scanned_at") or "")))


def resolve_prices(pairs: list[str]) -> tuple[dict[str, float], str, dict[str, dict]]:
    """Return (prices, source_summary, meta[pair] = {mid, source, age_s, ...}).

    Order: fresh tick (<= TICK_MAX_AGE_S) → revolut ticker → scan → stale tick.
    """
    uniq = list(dict.fromkeys(p.upper() for p in pairs if p))
    prices: dict[str, float] = {}
    meta: dict[str, dict] = {}
    ticks = read_latest_ticks(uniq)
    stale: dict[str, dict] = {}
    for pair in uniq:
        t = ticks.get(pair)
        if t is None:
            continue
        mid = _tick_mid(t)
        age = _age_s(_parse_ts(str(t.get("ts") or "")))
        if mid is not None and age is not None and age <= TICK_MAX_AGE_S:
            prices[pair] = mid
            meta[pair] = {
                "mid": mid,
                "source": "ticks",
                "age_s": age,
                "tick_ts": t.get("ts"),
                "feed": t.get("source"),
            }
        elif mid is not None:
            stale[pair] = {"mid": mid, "age_s": age, "tick_ts": t.get("ts")}

    missing = [p for p in uniq if p not in prices]
    for pair in missing:
        reason = "tick_stale" if pair in stale else "tick_missing"
        mid = revx_ticker_mid(pair)
        if mid is not None:
            prices[pair] = mid
            meta[pair] = {"mid": mid, "source": "revolut", "age_s": 0.0, "fallback_reason": reason}
            if pair in stale:
                meta[pair]["tick_age_s"] = stale[pair]["age_s"]

    missing = [p for p in uniq if p not in prices]
    if missing:
        scan_map = try_run_scan()
        scan_age = _scan_age_s()
        for pair in missing:
            reason = "tick_stale" if pair in stale else "tick_missing"
            if pair in scan_map:
                prices[pair] = scan_map[pair]
                meta[pair] = {
                    "mid": scan_map[pair],
                    "source": "scan",
                    "age_s": scan_age,
                    "fallback_reason": reason + "+revolut_failed",
                }
                if pair in stale:
                    meta[pair]["tick_age_s"] = stale[pair]["age_s"]
            elif pair in stale:
                prices[pair] = stale[pair]["mid"]
                meta[pair] = {
                    "mid": stale[pair]["mid"],
                    "source": "ticks_stale",
                    "age_s": stale[pair]["age_s"],
                    "tick_ts": stale[pair]["tick_ts"],
                    "fallback_reason": "revolut_and_scan_failed",
                }

    used = sorted({m["source"] for m in meta.values()})
    if not used:
        source = "none"
    elif len(used) == 1:
        source = used[0]
    else:
        source = "mixed:" + "+".join(used)
    return prices, source, meta


def derive_stop(pos: dict) -> float | None:
    stop = pos.get("stop_price_eur")
    if stop is not None:
        try:
            return float(stop)
        except (TypeError, ValueError):
            pass
    stop_pct = pos.get("stop_pct")
    avg = pos.get("avg_price") or pos.get("entry_price") or pos.get("price")
    if stop_pct is None or avg is None:
        return None
    try:
        sp = float(stop_pct)
        ap = float(avg)
    except (TypeError, ValueError):
        return None
    if ap <= 0:
        return None
    if sp > 0:
        sp = -sp
    return ap * (1.0 + sp / 100.0)


def is_long_stop_hit(side: str, price: float, stop: float) -> bool:
    s = (side or "long").lower()
    if s in ("long", "buy"):
        return price <= stop
    if s in ("short", "sell"):
        return price >= stop
    return False


def position_breach(pos: dict, mid: float) -> dict | None:
    """Return breach info for long stop or short safety/target, else None.

    Long (hausse): mid <= stop → close sell.
    Short (idée à la baisse): mid >= stop_price → rebuy safety;
      mid <= target_price → rebuy target.
    """
    side = str(pos.get("side") or "long").lower()
    idea = str(pos.get("idea_type") or pos.get("kind") or "").lower()
    is_short = side in ("short", "sell") or idea == "baisse"

    stop = derive_stop(pos)
    target = pos.get("target_price")
    try:
        target_f = float(target) if target is not None else None
    except (TypeError, ValueError):
        target_f = None

    if is_short:
        # Safety first if both hit (gap up): prefer safety
        if stop is not None and mid >= float(stop):
            return {
                "mid": float(mid),
                "stop": float(stop),
                "rebuy_reason": "safety",
                "close_reason": "stop_hit",
                "kind": "baisse",
            }
        if target_f is not None and mid <= target_f:
            return {
                "mid": float(mid),
                "stop": float(stop) if stop is not None else target_f,
                "target": target_f,
                "rebuy_reason": "target",
                "close_reason": "target_hit",
                "kind": "baisse",
            }
        return None

    if stop is None:
        return None
    if is_long_stop_hit("long", float(mid), float(stop)):
        return {
            "mid": float(mid),
            "stop": float(stop),
            "rebuy_reason": None,
            "close_reason": "stop_hit",
            "kind": "hausse",
        }
    return None


def classify_mode(pos: dict) -> str:
    """paper | live — default paper unless explicitly live-tagged."""
    for key in ("mode", "execution_mode"):
        m = str(pos.get(key) or "").strip().lower()
        if m in ("live", "paper", "sim", "simulation"):
            if m in ("sim", "simulation"):
                return "paper"
            return m
    src = str(pos.get("source") or "").lower()
    if "live" in src and "paper" not in src:
        return "live"
    pid = str(pos.get("id") or "").lower()
    if pid.startswith("rx-live") or "-live-" in pid or pid.startswith("live-"):
        return "live"
    if pid.startswith("rx-paper") or "paper" in pid:
        return "paper"
    # guardian state without mode → paper/sim book
    if pos.get("_track_source") == "guardian_state":
        return "paper"
    if pos.get("_track_source") in ("live_orders", "revx_open"):
        return "live"
    return "paper"


def is_watchable_crypto(pos: dict) -> bool:
    """Only crypto spot rows with a pair (PM yes/no rows without pair are ignored)."""
    pair = str(pos.get("pair") or pos.get("symbol") or "").upper()
    if not pair:
        return False
    if pair in WHITELIST_PAIRS:
        return True
    # Allow other *-EUR pairs if present
    return pair.endswith("-EUR") and "-" in pair


def normalize_position(raw: dict, track_source: str) -> dict | None:
    if not isinstance(raw, dict):
        return None
    status = str(raw.get("status") or "open").lower()
    if status not in ("open", "partial", "partially_filled", "new", "pending_new", ""):
        # closed / filled-and-done positions skipped; open orders keep active states
        if track_source != "revx_open":
            return None
        if status in ("cancelled", "canceled", "rejected", "expired", "closed", "filled"):
            return None
    pair = str(raw.get("pair") or raw.get("symbol") or raw.get("trading_pair") or "").upper()
    if not pair and track_source == "revx_open":
        return None
    pos = dict(raw)
    pos["pair"] = pair or str(pos.get("pair") or "").upper()
    if not is_watchable_crypto(pos):
        return None
    side_raw = str(pos.get("side") or "long").lower()
    idea = str(pos.get("idea_type") or pos.get("kind") or "").lower()
    if idea == "baisse" or side_raw in ("short",):
        pos["side"] = "short"
        pos["idea_type"] = pos.get("idea_type") or "baisse"
    elif side_raw in ("buy", "long"):
        pos["side"] = "long"
    elif side_raw in ("sell",):
        # Open sell orders are exits, not short positions we stop-watch as longs
        if track_source == "revx_open":
            pos["side"] = "long"  # treat resting sell as protecting a long; stop on mid<=stop if set
            pos["_open_order_side"] = "sell"
        else:
            pos["side"] = "short"
    else:
        pos["side"] = "long"
    if not pos.get("id"):
        oid = raw.get("order_id") or raw.get("client_order_id") or raw.get("id")
        pos["id"] = str(oid) if oid else f"{track_source}-{pos['pair']}-{pos.get('opened_at') or now_utc_iso()}"
    # cost / qty defaults for live order rows
    if pos.get("cost_eur") is None:
        for k in ("amount_eur", "quote_qty", "quoteQty", "filled_quote"):
            if raw.get(k) is not None:
                try:
                    pos["cost_eur"] = float(raw[k])
                    break
                except (TypeError, ValueError):
                    pass
    if pos.get("qty") is None:
        for k in ("qty", "quantity", "filled_qty", "filledQty", "base_qty"):
            if raw.get(k) is not None:
                try:
                    pos["qty"] = float(raw[k])
                    break
                except (TypeError, ValueError):
                    pass
    if pos.get("avg_price") is None:
        for k in ("price", "avg_price", "limit_price", "avgPrice", "entry_price"):
            if raw.get(k) is not None:
                try:
                    pos["avg_price"] = float(raw[k])
                    break
                except (TypeError, ValueError):
                    pass
    pos["_track_source"] = track_source
    pos["mode"] = classify_mode(pos)
    pos["status"] = "open"
    return pos


def _dedupe_key(pos: dict) -> str:
    pid = str(pos.get("id") or "")
    if pid:
        return f"id:{pid}"
    return f"{pos.get('mode')}:{pos.get('pair')}:{pos.get('_track_source')}"


def load_live_exits() -> dict:
    return load_json(LIVE_EXITS_PATH)


def load_live_orders_open() -> list[dict]:
    """Reconstruct open live positions from successful live_orders.jsonl rows.

    Longs = buys minus plain sells (EUR netting, as before). Rows kind=auto_exit are
    resolved through the exit lock (state/live_exits.json), not netted. Idée à la
    baisse live = sell with idea_type/kind baisse → short; closed by a linked rebuy.
    """
    if not LIVE_ORDERS_PATH.exists():
        return []
    exits = load_live_exits()
    closed_by_exit = {k for k, v in exits.items()
                      if str((v or {}).get("status")) in ("done", "no_fill", "closed_by_target")}
    shorts: dict[str, dict] = {}
    closed_shorts: set[str] = set()
    buys: dict[str, dict] = {}
    sells_by_pair: dict[str, float] = {}
    try:
        lines = LIVE_ORDERS_PATH.read_text().splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or not row.get("ok"):
            continue
        if row.get("dry_run"):
            continue
        if row.get("kind") == "auto_exit":
            continue  # handled via the exit lock
        order = row.get("order") if isinstance(row.get("order"), dict) else row
        pair = str(order.get("pair") or "").upper()
        side = str(order.get("side") or "").lower()
        if not pair:
            continue
        idea = str(order.get("idea_type") or order.get("kind") or "").lower()
        linked = order.get("linked_position_id") or order.get("cycle_id")
        if side == "sell" and idea == "baisse" and not linked:
            oid = str(order.get("id") or row.get("client_order_id") or f"live-{pair}-{row.get('at') or now_utc_iso()}")
            sid = oid if oid.startswith("rx-live") or oid.startswith("live-") else f"rx-live-{oid}"
            stop_v = order.get("stop_price") if order.get("stop_price") is not None else (
                order.get("safety_price") if order.get("safety_price") is not None else order.get("stop_price_eur"))
            try:
                amt = float(order.get("amount_eur") or 0)
                px = float(order.get("price") or 0)
            except (TypeError, ValueError):
                amt, px = 0.0, 0.0
            shorts[sid] = {
                "id": sid, "pair": pair, "side": "short", "idea_type": "baisse", "kind": "baisse",
                "qty": float(order.get("qty") or 0) or ((amt / px) if px else None),
                "avg_price": order.get("price"), "cost_eur": amt,
                "stop_price_eur": stop_v, "target_price": order.get("target_price"),
                "deadline": order.get("deadline") or order.get("deadline_at"),
                "status": "open", "mode": "live", "source": "live_orders", "opened_at": row.get("at") or now_utc_iso(),
            }
            continue
        if side == "buy" and linked and (idea == "baisse" or order.get("rebuy_reason")):
            closed_shorts.add(str(linked))
            continue
        try:
            amount = float(order.get("amount_eur") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if side == "buy" and amount > 0:
            oid = str(
                order.get("id")
                or row.get("client_order_id")
                or f"live-{pair}-{row.get('at') or now_utc_iso()}"
            )
            buys[oid] = {
                "id": oid if oid.startswith("rx-live") or oid.startswith("live-") else f"rx-live-{oid}",
                "pair": pair,
                "side": "long",
                "qty": float(order.get("qty") or 0) or None,
                "avg_price": order.get("price"),
                "cost_eur": amount,
                "stop_pct": order.get("stop_pct"),
                "stop_price_eur": (
                    order.get("stop_price_eur")
                    if order.get("stop_price_eur") is not None
                    else order.get("stop_price")
                    if order.get("stop_price") is not None
                    else order.get("safety_price")
                ),
                "target_price": order.get("target_price"),
                "deadline": order.get("deadline") or order.get("deadline_at"),
                "status": "open",
                "mode": "live",
                "source": "live_orders",
                "opened_at": row.get("at") or now_utc_iso(),
            }
        elif side == "sell" and amount > 0:
            if order.get("target_for") or str(order.get("purpose") or "").lower() in ("target", "objectif"):
                continue  # resting target (objectif) order of a bot position, not a close
            sells_by_pair[pair] = sells_by_pair.get(pair, 0.0) + amount

    # Net out sells against buys (FIFO by insertion order)
    remaining_sell = dict(sells_by_pair)
    open_buys: list[dict] = []
    for oid, buy in buys.items():
        pair = buy["pair"]
        cost = float(buy.get("cost_eur") or 0)
        left = remaining_sell.get(pair, 0.0)
        if left >= cost - 1e-9:
            remaining_sell[pair] = left - cost
            continue
        if left > 0:
            buy = dict(buy)
            buy["cost_eur"] = round(cost - left, 6)
            remaining_sell[pair] = 0.0
        open_buys.append(buy)
    open_buys = [b for b in open_buys if b["id"] not in closed_by_exit]
    open_buys += [sh for k, sh in shorts.items() if k not in closed_shorts and k not in closed_by_exit]
    return open_buys


def load_revx_open_orders(timeout_s: float = 15.0) -> list[dict]:
    """Best-effort list of revx open orders (no place/cancel)."""
    if str(os.environ.get("WATCH_STOPS_NO_REVX_OPEN", "")).lower() in ("1", "true", "yes"):
        return []
    bin_path = REVX_BIN if Path(REVX_BIN).exists() else "revx"
    symbols = ",".join(WHITELIST_PAIRS)
    env = {
        **os.environ,
        "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""),
        "HTTPS_PROXY": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:8791"),
        "HTTP_PROXY": os.environ.get("HTTP_PROXY", "http://127.0.0.1:8791"),
        "ALL_PROXY": os.environ.get("ALL_PROXY", "http://127.0.0.1:8791"),
    }
    try:
        proc = subprocess.run(
            [bin_path, "order", "open", "--symbols", symbols, "--json", "--limit", "50"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        log_json({"ok": True, "action": "revx_open_skip", "reason": str(e)})
        return []
    if proc.returncode != 0:
        log_json(
            {
                "ok": True,
                "action": "revx_open_skip",
                "returncode": proc.returncode,
                "stderr": (proc.stderr or "")[:200],
            }
        )
        return []
    raw = (proc.stdout or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        if start < 0:
            start = raw.find("{")
        if start < 0:
            return []
        try:
            data = json.loads(raw[start:])
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        for key in ("data", "orders", "results", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            data = [data]
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item = dict(item)
        item["mode"] = "live"
        item["source"] = "revx_open"
        out.append(item)
    return out


def collect_all_open_positions() -> list[dict]:
    """Merge watchable opens from guardian state, root positions, live fills, revx opens."""
    merged: dict[str, dict] = {}

    def add(raw: dict, track_source: str) -> None:
        pos = normalize_position(raw, track_source)
        if pos is None:
            return
        key = _dedupe_key(pos)
        # Prefer guardian_state / live_orders over revx_open for same id
        prev = merged.get(key)
        if prev is None:
            merged[key] = pos
            return
        rank = {"guardian_state": 3, "root_positions": 2, "live_orders": 3, "revx_open": 1}
        if rank.get(track_source, 0) >= rank.get(prev.get("_track_source"), 0):
            # keep richer stop fields
            for fld in ("stop_price_eur", "stop_pct", "avg_price", "cost_eur", "qty"):
                if pos.get(fld) is None and prev.get(fld) is not None:
                    pos[fld] = prev[fld]
            merged[key] = pos

    state = load_json(STATE_PATH)
    for p in state.get("positions") or []:
        if str(p.get("status") or "open").lower() == "open":
            add(p, "guardian_state")

    root_pos = load_json(ROOT_POSITIONS_PATH)
    for p in root_pos.get("positions") or []:
        if str(p.get("status") or "open").lower() == "open":
            add(p, "root_positions")

    for p in load_live_orders_open():
        add(p, "live_orders")

    for p in load_revx_open_orders():
        add(p, "revx_open")

    return list(merged.values())


def open_positions(state: dict) -> list[dict]:
    """Backward-compat: open rows from a single state dict."""
    return [p for p in (state.get("positions") or []) if p.get("status", "open") == "open"]


def run_paper_fill(order: dict) -> tuple[dict, int]:
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="stop_sell_",
        dir=str(ROOT / "state"),
        delete=False,
    ) as tf:
        json.dump(order, tf, indent=2)
        tf.write("\n")
        order_path = tf.name
    try:
        proc = subprocess.run(
            [sys.executable, str(PAPER_FILL), "--order", order_path],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "PAPER_FILL_NO_WATCH": "1"},
        )
        try:
            result = json.loads(proc.stdout.strip() or "{}")
        except json.JSONDecodeError:
            result = {
                "ok": False,
                "reasons": [
                    f"paper_fill bad stdout: {proc.stdout!r} {proc.stderr!r}"
                ],
            }
        return result, proc.returncode
    finally:
        try:
            os.unlink(order_path)
        except OSError:
            pass


def equity_from_state(state: dict) -> float:
    cash = float(state.get("cash_eur", 0) or 0)
    pos_val = 0.0
    for p in state.get("positions") or []:
        if p.get("status", "open") != "open":
            continue
        pos_val += (-1.0 if (str(p.get("side") or "").lower() in ("short","sell") or str(p.get("idea_type") or p.get("kind") or "").lower() == "baisse") else 1.0) * float(p.get("mark_eur", p.get("cost_eur", 0)) or 0)  # baisse = rachat dû
    return cash + pos_val


def enrich_closed_position(
    state: dict,
    position_id: str,
    *,
    mid: float,
    stop: float,
    original_cost: float,
    original_qty: float,
    close_reason: str = "stop_hit",
    realized_override: float | None = None,
    skip_cash_adjust: bool = False,
) -> dict | None:
    """Patch closed position + cash/daily_pnl/equity after paper_fill close."""
    target = None
    for p in state.get("positions") or []:
        if p.get("id") == position_id:
            target = p
            break
    if target is None:
        return None

    side = str(target.get("side") or "long").lower()
    idea = str(target.get("idea_type") or "").lower()
    is_short = side in ("short", "sell") or idea == "baisse"

    exit_value = original_qty * mid if original_qty > 0 else 0.0
    if exit_value <= 0 and original_cost > 0:
        avg = float(target.get("avg_price") or 0) or mid
        exit_value = original_cost * (mid / avg) if avg else original_cost

    if realized_override is not None:
        realized = round(float(realized_override), 6)
    elif is_short:
        # (sell_price - rebuy_price) * qty
        avg = float(target.get("avg_price") or 0) or mid
        realized = round((avg - mid) * original_qty if original_qty > 0 else original_cost - exit_value, 6)
    else:
        realized = round(exit_value - original_cost, 6)

    if not skip_cash_adjust:
        cash = float(state.get("cash_eur", 0) or 0)
        cash = round(cash + realized, 6)
        state["cash_eur"] = cash

    daily = _daily_pnl_today(state)
    state["daily_pnl_eur"] = round(daily + realized, 6)
    state["daily_pnl_date"] = _today_brussels()

    target["status"] = "closed"
    target["close_reason"] = close_reason
    target["close_price_eur"] = mid
    target["realized_pnl_eur"] = realized
    if original_cost > 0:
        target["realized_pnl_pct"] = round(100.0 * realized / original_cost, 4)
    target["last_mid_eur"] = mid
    target["stop_price_eur"] = stop
    target["mark_eur"] = round(exit_value, 6)
    if not target.get("closed_at"):
        target["closed_at"] = now_utc_iso()
    target["updated_at"] = now_utc_iso()

    eq = equity_from_state(state)
    state["equity_eur"] = round(eq, 6)
    peak = float(state.get("peak_equity_eur", 0) or 0)
    if peak <= 0:
        peak = float(state.get("bankroll_eur", 0) or 0) or eq
        state["peak_equity_eur"] = round(peak, 6)
    state["drawdown_pct"] = round(max(0.0, (peak - eq) / peak), 6) if peak > 0 else 0.0
    state["updated_at"] = now_utc_iso()
    return target


def mirror_alerts(closed: list[dict], *, live_alerts: list[dict] | None = None) -> None:
    """Update alerts_last.json and best-effort run check_alerts.py."""
    alerts = [
        {
            "type": "stop_breach",
            "mode": c.get("mode", "paper"),
            "pair": c["pair"],
            "side": c.get("side", "long"),
            "price_eur": c["price"],
            "stop_price_eur": c["stop"],
            "position_id": c.get("id"),
            "close_reason": (c.get("close_reason") or "stop_hit")
            if c.get("mode") != "live"
            else "stop_hit_live_pending",
            "pnl_eur": c.get("pnl_eur"),
            "price_source": c.get("price_source"),
            "price_age_s": c.get("price_age_s"),
        }
        for c in closed
    ]
    for a in live_alerts or []:
        alerts.append(a)
    opens = collect_all_open_positions()
    payload = {
        "checked_at": now_local_iso(),
        "alerted": True,
        "flags": {"stop_breach": True, "daily_loss": False, "drawdown": False},
        "alerts": alerts,
        "source": "watch_stops",
        "open_positions": len(opens),
    }
    save_json(ALERTS_PATH, payload)
    if CHECK_ALERTS.exists() and _REAL_PATHS:
        try:
            subprocess.run(
                [sys.executable, str(CHECK_ALERTS)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass


def estimate_pnl(pos: dict, mid: float | None) -> float:
    if mid is None:
        return 0.0
    original_cost = float(pos.get("cost_eur", 0) or 0)
    original_qty = float(pos.get("qty", 0) or 0)
    side = str(pos.get("side") or "long").lower()
    idea = str(pos.get("idea_type") or "").lower()
    is_short = side in ("short", "sell") or idea == "baisse"
    if is_short:
        avg = float(pos.get("avg_price") or 0) or mid
        if original_qty > 0:
            return round((avg - mid) * original_qty, 6)
        if original_cost > 0 and avg:
            return round(original_cost * (avg - mid) / avg, 6)
        return 0.0
    if original_qty > 0:
        return round(original_qty * mid - original_cost, 6)
    if original_cost > 0:
        avg = float(pos.get("avg_price") or 0) or mid
        exit_value = original_cost * (mid / avg) if avg else original_cost
        return round(exit_value - original_cost, 6)
    return 0.0


def write_wake_and_events(
    paper_closed: list[dict],
    live_breached: list[dict],
) -> None:
    ts = now_utc_iso()
    parts_fr: list[str] = []
    wake: dict = {
        "closed_at": ts,
        "closed_count": len(paper_closed),
        "live_pending_count": len(live_breached),
        "source": "watch_stops",
    }

    if paper_closed and not live_breached:
        if len(paper_closed) == 1:
            c = paper_closed[0]
            pnl = c["pnl_eur"]
            sign = "+" if pnl >= 0 else ""
            if c.get("close_reason") == DEADLINE_REASON:
                message_fr = (
                    f"Heure limite atteinte (paper) sur {c['pair']}: "
                    f"{'rachat' if c.get('idea_type') == 'baisse' or c.get('side') in ('short', 'sell') else 'vente'} "
                    f"à {c['price']:.4f}, PnL {sign}{pnl:.4f} EUR — position clôturée."
                )
            elif c.get("idea_type") == "baisse" or c.get("side") in ("short", "sell"):
                reason = c.get("rebuy_reason") or "safety"
                message_fr = (
                    f"Rachat auto (idée à la baisse, {reason}) sur {c['pair']}: "
                    f"prix {c['price']:.4f}, seuil {c['stop']:.4f}, "
                    f"PnL {sign}{pnl:.4f} EUR — position clôturée."
                )
            else:
                message_fr = (
                    f"Stop paper touché sur {c['pair']}: prix {c['price']:.4f} ≤ stop "
                    f"{c['stop']:.4f}, PnL {sign}{pnl:.4f} EUR — position clôturée."
                )
            wake.update(
                {
                    "mode": "paper",
                    "pair": c["pair"],
                    "stop": c["stop"],
                    "price": c["price"],
                    "pnl_eur": pnl,
                    "position_id": c.get("id"),
                    "message_fr": message_fr,
                }
            )
        else:
            pairs = ", ".join(c["pair"] for c in paper_closed)
            total_pnl = round(sum(c["pnl_eur"] for c in paper_closed), 6)
            sign = "+" if total_pnl >= 0 else ""
            message_fr = (
                f"Stops paper touchés ({len(paper_closed)}): {pairs}. "
                f"PnL total {sign}{total_pnl:.4f} EUR — positions clôturées."
            )
            wake.update(
                {
                    "mode": "paper",
                    "pair": paper_closed[0]["pair"],
                    "pairs": [c["pair"] for c in paper_closed],
                    "stop": paper_closed[0]["stop"],
                    "price": paper_closed[0]["price"],
                    "pnl_eur": total_pnl,
                    "closed": paper_closed,
                    "message_fr": message_fr,
                }
            )
    elif live_breached and not paper_closed:
        c = live_breached[0]
        pairs = ", ".join(x["pair"] for x in live_breached)
        pending = [x for x in live_breached if x.get("urgent", True)]
        done = [x for x in live_breached if not x.get("urgent", True)]
        if any(x.get("auto_sell") or x.get("close_reason") in TIME_EXIT_LABELS for x in live_breached):
            message_fr = " | ".join(x.get("message_fr") or "" for x in live_breached)
        elif len(live_breached) == 1:
            if c.get("close_reason") in TIME_EXIT_LABELS:
                message_fr = c.get("message_fr") or f"{TIME_EXIT_LABELS[c['close_reason']]} LIVE — {c['pair']}"
            else:
                px = c.get("price"); st = c.get("stop")
                message_fr = (
                    f"Stop touché en LIVE — vente à faire sur {c['pair']}: "
                    f"prix {px if px is None else f'{px:.4f}'} ≤ stop "
                    f"{st if st is None else f'{st:.4f}'}. "
                    f"Pas de vente auto (armer LIVE_ONCE + live_place)."
                )
        else:
            message_fr = (
                f"Stop touché en LIVE — vente à faire ({len(live_breached)}): {pairs}. "
                f"Pas de vente auto (armer LIVE_ONCE + live_place)."
            )
        wake.update(
            {
                "mode": "live",
                "pair": c["pair"],
                "pairs": [x["pair"] for x in live_breached],
                "stop": c["stop"],
                "price": c["price"],
                "pnl_eur": c.get("pnl_eur"),
                "position_id": c.get("id"),
                "live_pending": pending or None,
                "live_closed": done or None,
                "auto_sell": any(x.get("auto_sell") for x in live_breached),
                "urgent": bool(pending),
                "message_fr": message_fr,
            }
        )
    else:
        # mixed
        if paper_closed:
            parts_fr.append(
                f"{len(paper_closed)} paper clôturé(s): "
                + ", ".join(c["pair"] for c in paper_closed)
            )
        if live_breached:
            parts_fr.append(" | ".join(c.get("message_fr") or f"LIVE {c['pair']}" for c in live_breached))
        primary = live_breached[0] if live_breached else paper_closed[0]
        wake.update(
            {
                "urgent": any(x.get("urgent", True) for x in live_breached),
                "mode": "mixed",
                "pair": primary["pair"],
                "stop": primary["stop"],
                "price": primary["price"],
                "closed": paper_closed or None,
                "live_pending": live_breached or None,
                "auto_sell": False,
                "message_fr": " | ".join(parts_fr),
            }
        )

    srcs = [
        {"pair": c["pair"], "price_source": c.get("price_source"), "price_age_s": c.get("price_age_s")}
        for c in list(paper_closed) + list(live_breached)
    ]
    wake["price_sources"] = srcs
    save_json(WAKE_PATH, wake)
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a") as f:
        for c in paper_closed:
            if c.get("close_reason") == DEADLINE_REASON:
                msg = (f"Heure limite atteinte (paper) sur {c['pair']}: prix {c['price']:.4f}, "
                       f"PnL {c['pnl_eur']:+.4f} EUR.")
            elif c.get("idea_type") == "baisse" or c.get("side") in ("short", "sell"):
                msg = (
                    f"Rachat auto (idée à la baisse, {c.get('rebuy_reason') or 'safety'}) sur "
                    f"{c['pair']}: prix {c['price']:.4f}, seuil {c['stop']:.4f}, "
                    f"PnL {c['pnl_eur']:+.4f} EUR."
                )
            else:
                msg = (
                    f"Stop paper touché sur {c['pair']}: prix {c['price']:.4f} ≤ stop "
                    f"{c['stop']:.4f}, PnL {c['pnl_eur']:+.4f} EUR."
                )
            event = {
                "ts": ts,
                "mode": "paper",
                "pair": c["pair"],
                "stop": c["stop"],
                "price": c["price"],
                "pnl_eur": c["pnl_eur"],
                "position_id": c.get("id"),
                "close_reason": c.get("close_reason") or "stop_hit",
                "rebuy_reason": c.get("rebuy_reason"),
                "price_source": c.get("price_source"),
                "price_age_s": c.get("price_age_s"),
                "message_fr": msg,
            }
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        for c in live_breached:
            if c.get("auto_sell") and not c.get("urgent", True):
                reason_live = c.get("close_reason") or "stop_hit"  # closed automatically
            elif c.get("auto_sell"):
                reason_live = (f"{c['close_reason']}_exit_failed" if c.get("close_reason") in TIME_EXIT_LABELS
                               else "stop_hit_live_exit_failed")
            else:
                reason_live = "stop_hit_live_pending"
            event = {
                "ts": ts,
                "mode": "live",
                "pair": c["pair"],
                "stop": c["stop"],
                "price": c["price"],
                "pnl_eur": c.get("pnl_eur"),
                "position_id": c.get("id"),
                "close_reason": reason_live,
                "auto_sell": bool(c.get("auto_sell")),
                "urgent": bool(c.get("urgent", True)),
                "exit_result": c.get("exit_result"),
                "price_source": c.get("price_source"),
                "price_age_s": c.get("price_age_s"),
                "message_fr": c.get("message_fr") if (c.get("auto_sell") or c.get("close_reason") in TIME_EXIT_LABELS) else (
                    f"Stop touché en LIVE — vente à faire sur {c['pair']}: "
                    f"prix {c['price'] if c.get('price') is None else f'{c["price"]:.4f}'} ≤ stop "
                    f"{c['stop'] if c.get('stop') is None else f'{c["stop"]:.4f}'}."
                ),
            }
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def close_paper_breached(breached: list[dict], dry_run: bool) -> list[dict]:
    """Close paper/sim breached positions via paper_fill."""
    closed_out: list[dict] = []
    for item in breached:
        pos = item["pos"]
        mid = item["mid"]
        stop = item["stop"]
        pair = str(pos.get("pair") or "").upper()
        pid = pos.get("id")
        original_cost = float(pos.get("cost_eur", 0) or 0)
        original_qty = float(pos.get("qty", 0) or 0)
        side = str(pos.get("side") or "long").lower()
        mode = "paper"

        if dry_run:
            closed_out.append(
                {
                    "id": pid,
                    "pair": pair,
                    "side": side,
                    "mode": mode,
                    "stop": stop,
                    "price": mid,
                    "pnl_eur": estimate_pnl(pos, mid),
                    "dry_run": True,
                    "close_reason": item.get("close_reason"),
                    "price_source": item.get("price_source"),
                    "price_age_s": item.get("price_age_s"),
                }
            )
            continue

        # Only guardian_state / root paper positions can be closed via paper_fill
        # into guardian state — skip if cost ~0
        if original_cost <= 1e-9 and pos.get("_track_source") not in ("guardian_state",):
            # Still mark as closed-out for wake if we have pnl estimate
            closed_out.append(
                {
                    "id": pid,
                    "pair": pair,
                    "side": side,
                    "mode": mode,
                    "stop": stop,
                    "price": mid,
                    "pnl_eur": estimate_pnl(pos, mid),
                    "dry_run": False,
                    "note": "no_cost_skip_paper_fill",
                }
            )
            continue

        if original_cost <= 1e-9:
            log_json(
                {
                    "ok": False,
                    "action": "skip_close",
                    "pair": pair,
                    "reason": "cost_eur ~ 0",
                }
            )
            continue

        is_short = side in ("short", "sell") or str(pos.get("idea_type") or "").lower() == "baisse"
        rebuy_reason = item.get("rebuy_reason")
        close_reason = item.get("close_reason") or "stop_hit"
        if is_short:
            amount = original_qty * mid if original_qty > 0 else original_cost
            order = {
                "pair": pair,
                "side": "buy",
                "type": "limit",
                "price": mid,
                "amount_eur": amount,
                "qty": original_qty if original_qty > 0 else None,
                "idea_type": "baisse",
                "kind": "baisse",
                "linked_position_id": pid,
                "cycle_id": pid,
                "rebuy_reason": rebuy_reason or "safety",
                "close_reason": close_reason,
                "decision_id": pos.get("decision_id") or "auto-stop",
                "venue": pos.get("venue") or "revolut_x",
                "post_only": True,
            }
            if order.get("qty") is None:
                del order["qty"]
        else:
            order = {
                "pair": pair,
                "side": "sell",
                "type": "limit",
                "price": mid,
                "amount_eur": original_cost,
                "idea_type": "hausse",
                "close_reason": close_reason,
                "post_only": True,
            }
        result, rc = run_paper_fill(order)
        if not result.get("ok") or rc != 0:
            log_json(
                {
                    "ok": False,
                    "action": "paper_fill_failed",
                    "pair": pair,
                    "reasons": result.get("reasons", []),
                    "returncode": rc,
                }
            )
            continue

        state = load_json(STATE_PATH)
        fill = result.get("fill") or {}
        realized_from_fill = fill.get("realized_pnl_eur")
        # paper_fill already adjusted cash for baisse rebuy; only adjust daily_pnl / marks
        enriched = enrich_closed_position(
            state,
            pid,
            mid=mid,
            stop=stop,
            original_cost=original_cost,
            original_qty=original_qty,
            close_reason=close_reason,
            realized_override=float(realized_from_fill) if realized_from_fill is not None else None,
            skip_cash_adjust=is_short,
        )
        if enriched is None:
            for p in state.get("positions") or []:
                if (
                    str(p.get("pair") or "").upper() == pair
                    and p.get("status") == "closed"
                    and p.get("close_reason") is None
                ):
                    enriched = enrich_closed_position(
                        state,
                        p.get("id"),
                        mid=mid,
                        stop=stop,
                        original_cost=original_cost,
                        original_qty=original_qty,
                        close_reason=close_reason,
                        realized_override=float(realized_from_fill) if realized_from_fill is not None else None,
                        skip_cash_adjust=is_short,
                    )
                    break
        # If paper_fill already closed the short, still refresh daily_pnl from fill
        if enriched is None and is_short and realized_from_fill is not None:
            daily = _daily_pnl_today(state)
            state["daily_pnl_eur"] = round(daily + float(realized_from_fill), 6)
            state["daily_pnl_date"] = _today_brussels()
            state["updated_at"] = now_utc_iso()
            for p in state.get("positions") or []:
                if p.get("id") == pid:
                    enriched = p
                    break
        save_json(STATE_PATH, state)
        pnl = float(
            (enriched or {}).get("realized_pnl_eur")
            or (realized_from_fill if realized_from_fill is not None else estimate_pnl(pos, mid))
        )
        closed_out.append(
            {
                "id": pid,
                "pair": pair,
                "side": side,
                "mode": mode,
                "stop": stop,
                "price": mid,
                "pnl_eur": pnl,
                "dry_run": False,
                "rebuy_reason": rebuy_reason,
                "close_reason": close_reason,
                "idea_type": "baisse" if is_short else "hausse",
                "price_source": item.get("price_source"),
                "price_age_s": item.get("price_age_s"),
            }
        )
    return closed_out


def run_live_exit(pos: dict, item: dict) -> dict:
    """Call `live_place.py --exit` for one pipeline live position. Returns its JSON."""
    side = "short" if str(pos.get("side") or "").lower() in ("short", "sell") or \
        str(pos.get("idea_type") or "").lower() == "baisse" else "long"
    spec = {
        "position_id": pos.get("id"),
        "pair": str(pos.get("pair") or "").upper(),
        "side": side,
        "stop": item.get("stop"),
        "trigger_price": item.get("mid") if item.get("mid") is not None else pos.get("avg_price"),
        "close_reason": item.get("close_reason") or "stop_hit",
        "rebuy_reason": item.get("rebuy_reason"),
        "qty_hint": pos.get("qty"),
        "cost_eur": pos.get("cost_eur"),
        "avg_price": pos.get("avg_price"),
        "price_source": item.get("price_source"),
        "price_age_s": item.get("price_age_s"),
    }
    try:
        cfg = (_load_cfg().get("live_exit") or {})
        attempts = int(cfg.get("max_attempts", 3))
        wait = float(os.environ.get("LIVE_EXIT_FILL_WAIT_S") or cfg.get("fill_wait_s", 60))
    except (TypeError, ValueError):
        attempts, wait = 3, 60.0
    timeout = attempts * (wait + 60) + 120
    try:
        proc = subprocess.run(
            [sys.executable, str(LIVE_PLACE), "--exit"],
            input=json.dumps(spec),
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "status": "error", "error": f"live_place --exit: {e}", "urgent": True}
    try:
        return json.loads((proc.stdout or "").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"ok": False, "status": "error", "urgent": True,
                "error": f"live_place --exit bad stdout rc={proc.returncode}: {(proc.stdout or '')[:200]} {(proc.stderr or '')[:200]}"}


def handle_live_breached(breached: list[dict], dry_run: bool) -> list[dict]:
    """Live stop: automatic exit (allow_live_auto_sell, live_orders rows) else urgent wake only."""
    out: list[dict] = []
    for item in breached:
        pos = item["pos"]
        mid = item["mid"]
        stop = item["stop"]
        pair = str(pos.get("pair") or "").upper()
        is_short = str(pos.get("side") or "").lower() in ("short", "sell")
        entry = {
            "id": pos.get("id"),
            "pair": pair,
            "side": str(pos.get("side") or "long").lower(),
            "idea_type": "baisse" if is_short else "hausse",
            "mode": "live",
            "stop": stop,
            "price": mid,
            "pnl_eur": estimate_pnl(pos, mid) if mid is not None else None,
            "auto_sell": False,
            "urgent": True,
            "close_reason": item.get("close_reason") or "stop_hit",
            "track_source": pos.get("_track_source"),
            "dry_run": dry_run,
            "price_source": item.get("price_source"),
            "price_age_s": item.get("price_age_s"),
            "message_fr": "Stop touché en LIVE — vente à faire",
        }
        is_fc = item.get("close_reason") in TIME_EXIT_LABELS
        label = TIME_EXIT_LABELS.get(item.get("close_reason"), "")
        fstop = f"{stop:.4f}" if stop is not None else "?"
        fmid = f"{mid:.4f}" if mid is not None else "?"
        if is_fc:
            entry["message_fr"] = (f"{label} LIVE sur {pair} — "
                                   f"{'rachat' if is_short else 'vente'} à faire (pas de sortie auto).")
        can_auto = ALLOW_LIVE_AUTO_SELL and pos.get("_track_source") == "live_orders"
        if can_auto and dry_run:
            entry["auto_sell_would_attempt"] = True
        elif can_auto:
            res = run_live_exit(pos, item)
            ok = bool(res.get("ok"))
            entry.update({
                "auto_sell": True,
                "urgent": not ok,
                "exit_status": res.get("status"),
                "exit_result": {k: res.get(k) for k in (
                    "status", "sold_qty", "avg_price", "quote_eur", "realized_pnl_eur", "unsold_qty",
                    "target_qty", "position_qty", "balance", "cancelled_target_orders", "error", "note")
                    if res.get(k) is not None},
            })
            if res.get("realized_pnl_eur") is not None:
                entry["pnl_eur"] = res["realized_pnl_eur"]
            verb = "Rachat" if is_short else "Vente"
            if ok and is_fc:
                if res.get("status") == "no_fill":
                    entry["message_fr"] = (f"{label} LIVE sur {pair}: l'ordre d'entrée n'était pas rempli — "
                                           f"reste annulé, rien à vendre.")
                else:
                    entry["message_fr"] = (
                        f"{label} LIVE sur {pair} (prix {fmid}): {verb.lower()} auto "
                        f"{res.get('sold_qty')} à {float(res.get('avg_price') or 0):.4f}, "
                        f"PnL {float(res.get('realized_pnl_eur') or 0):+.4f} EUR — position clôturée."
                    )
            elif not ok and is_fc:
                entry["message_fr"] = (
                    f"URGENT — {label.lower()} LIVE ÉCHOUÉE sur {pair} ({res.get('status')}): prix {fmid}, "
                    f"exécuté {res.get('sold_qty') or 0} / {res.get('position_qty') or '?'} — "
                    f"{verb.lower()} à faire à la main. {res.get('error') or ''}".strip()
                )
            elif ok:
                if res.get("status") == "no_fill":
                    entry["message_fr"] = (f"Stop LIVE sur {pair}: l'ordre d'entrée n'était pas rempli — "
                                           f"reste annulé, rien à vendre.")
                else:
                    entry["message_fr"] = (
                        f"{verb} auto LIVE sur {pair} (stop {fstop}, prix {fmid}): "
                        f"{res.get('sold_qty')} à {float(res.get('avg_price') or 0):.4f}, "
                        f"PnL {float(res.get('realized_pnl_eur') or 0):+.4f} EUR — position clôturée."
                    )
            else:
                entry["message_fr"] = (
                    f"URGENT — {verb.lower()} auto LIVE ÉCHOUÉE sur {pair} ({res.get('status')}): "
                    f"stop {fstop}, prix {fmid}, exécuté {res.get('sold_qty') or 0} / "
                    f"{res.get('position_qty') or '?'} — {verb.lower()} à faire à la main. "
                    f"{res.get('error') or ''}".strip()
                )
            log_json({"ok": ok, "action": "live_auto_exit", "pair": pair, "position_id": pos.get("id"),
                      "reason": entry["close_reason"], "exit": entry["exit_result"], "urgent": not ok})
        elif not dry_run:
            log_json(
                {
                    "ok": True,
                    "action": "live_stop_wake_only",
                    "pair": pair,
                    "stop": stop,
                    "price": mid,
                    "hint": "auto exit only for live_orders rows with allow_live_auto_sell=true",
                }
            )
        out.append(entry)
    return out


def one_cycle(dry_run: bool) -> tuple[str, int, dict]:
    """
    Returns (action, exit_hint, payload).
    exit_hint: 0 continue/idle, 10 stop closed or live wake, 1 error
    """
    opens = collect_all_open_positions()
    if not opens:
        payload = {"ok": True, "action": "idle", "open": 0, "ts": now_utc_iso()}
        return "idle", 0, payload

    pairs = [str(p.get("pair") or "").upper() for p in opens]
    prices, source, price_meta = resolve_prices(pairs)
    live_exits = load_live_exits()

    paper_breached: list[dict] = []
    live_breached: list[dict] = []
    watching: list[dict] = []
    for pos in opens:
        pair = str(pos.get("pair") or "").upper()
        mid = prices.get(pair)
        pmeta = price_meta.get(pair) or {}
        price_source = pmeta.get("source")
        price_age = pmeta.get("age_s")
        if mid is None:
            mid_fallback = pos.get("last_mid_eur")
            try:
                mid = float(mid_fallback) if mid_fallback is not None else None
            except (TypeError, ValueError):
                mid = None
            if mid is not None:
                price_source, price_age = "position_last_mid", None
        stop = derive_stop(pos)
        mode = classify_mode(pos)
        entry = {
            "pair": pair,
            "id": pos.get("id"),
            "mode": mode,
            "mid": mid,
            "stop": stop,
            "cost_eur": pos.get("cost_eur"),
            "track_source": pos.get("_track_source"),
            "price_source": price_source,
            "price_age_s": price_age,
        }
        # For shorts, stop may be set while target drives take-profit; expose both
        entry["target_price"] = pos.get("target_price")
        entry["idea_type"] = pos.get("idea_type") or pos.get("kind")
        watching.append(entry)
        # Fermeture 22h: live pipeline positions only (paper never force-closed)
        fc_due = (mode == "live" and pos.get("_track_source") == "live_orders"
                  and live_force_close_due(pos))
        if fc_due:
            entry["force_close_due"] = True
        side_l = str(pos.get("side") or "long").lower()
        idea_l = str(pos.get("idea_type") or "").lower()
        is_short = side_l in ("short", "sell") or idea_l == "baisse"
        breach = None
        if mid is not None and not (stop is None and not is_short) and \
                not (stop is None and is_short and pos.get("target_price") is None):
            breach = position_breach(pos, float(mid))
        # Heure limite (deadline) — paper and live, after stop/target
        dl_due = deadline_due(pos)
        if dl_due:
            entry["deadline_due"] = True
            if not deadline_close_enabled():
                entry["deadline_reminder_only"] = True
                if not dry_run:
                    deadline_remind(pos)
                dl_due = False  # rappel seulement — seuls stop et prix visé ferment (Quentin 8 oct 23h)
        entry["deadline"] = pos.get("deadline") or pos.get("deadline_at")
        time_reason = DEADLINE_REASON if dl_due else (FORCE_CLOSE_REASON if fc_due else None)
        if mode != "live" and mid is None:
            time_reason = None  # paper close needs a price; retry next cycle
        if time_reason and not breach:
            ref = mid if mid is not None else (pos.get("avg_price") or pos.get("last_mid_eur"))
            try:
                ref = float(ref) if ref is not None else None
            except (TypeError, ValueError):
                ref = None
            breach = {"mid": ref, "stop": stop if stop is not None else ref,
                      "rebuy_reason": "time" if is_short else None,
                      "close_reason": time_reason}
        if mid is None and not time_reason:
            continue
        # Longs need a stop; shorts can breach on target without stop (rare)
        if breach:
            item = {
                "pos": pos,
                "mid": breach["mid"],
                "stop": breach["stop"],
                "rebuy_reason": breach.get("rebuy_reason"),
                "close_reason": breach.get("close_reason"),
                "price_source": price_source,
                "price_age_s": price_age,
            }
            if mode == "live":
                lock = live_exits.get(str(pos.get("id")))
                if lock:
                    entry["exit_status"] = lock.get("status")  # one exit per position, no retry
                    continue
                if str(pos.get("id")) in _live_alerted:
                    entry["live_alerted"] = True  # urgent wake already sent by this process
                    continue
                live_breached.append(item)
            else:
                paper_breached.append(item)

    if not paper_breached and not live_breached:
        payload = {
            "ok": True,
            "action": "watch",
            "open": len(opens),
            "paper": sum(1 for p in opens if classify_mode(p) != "live"),
            "live": sum(1 for p in opens if classify_mode(p) == "live"),
            "source": source,
            "prices": price_meta,
            "watching": watching,
            "ts": now_utc_iso(),
        }
        return "watch", 0, payload

    paper_closed = close_paper_breached(paper_breached, dry_run=dry_run) if paper_breached else []
    live_out = handle_live_breached(live_breached, dry_run=dry_run) if live_breached else []

    if dry_run:
        payload = {
            "ok": True,
            "action": "dry_run_breach",
            "open": len(opens),
            "source": source,
            "prices": price_meta,
            "breached_paper": paper_closed,
            "breached_live": live_out,
            "ts": now_utc_iso(),
        }
        return "dry_run_breach", 0, payload

    if not paper_closed and not live_out:
        payload = {
            "ok": False,
            "action": "close_failed",
            "open": len(opens),
            "source": source,
            "ts": now_utc_iso(),
        }
        return "close_failed", 1, payload

    for c in live_out:
        _live_alerted.add(str(c.get("id")))
    write_wake_and_events(paper_closed, live_out)
    mirror_alerts(paper_closed, live_alerts=[
        {
            "type": "stop_breach",
            "mode": "live",
            "pair": c["pair"],
            "side": c.get("side", "long"),
            "price_eur": c["price"],
            "stop_price_eur": c["stop"],
            "position_id": c.get("id"),
            "close_reason": ((c["close_reason"] + ("" if not c.get("urgent", True) else
                                                   "_exit_failed" if c.get("auto_sell") else "_pending"))
                             if c.get("close_reason") in TIME_EXIT_LABELS else
                             "stop_hit_live_auto_exit" if not c.get("urgent", True) else
                             "stop_hit_live_exit_failed" if c.get("auto_sell") else "stop_hit_live_pending"),
            "type_detail": c.get("close_reason"),
            "urgent": bool(c.get("urgent", True)),
            "auto_sell": bool(c.get("auto_sell")),
            "pnl_eur": c.get("pnl_eur"),
            "message_fr": c.get("message_fr") or "Stop touché en LIVE — vente à faire",
        }
        for c in live_out
    ])

    action = "stop_closed" if paper_closed and not live_out else (
        "live_stop_wake" if live_out and not paper_closed else "stop_mixed"
    )
    payload = {
        "ok": True,
        "action": action,
        "closed": paper_closed,
        "live_pending": live_out,
        "wake": str(WAKE_PATH),
        "source": source,
        "prices": price_meta,
        "ts": now_utc_iso(),
    }
    return action, 10, payload


def _cheap_open_count() -> int:
    """Open watchable rows in local files only (no revx call)."""
    n = 0
    for path in (STATE_PATH, ROOT_POSITIONS_PATH):
        for p in load_json(path).get("positions") or []:
            if str(p.get("status") or "open").lower() == "open":
                if normalize_position(p, "guardian_state" if path == STATE_PATH else "root_positions"):
                    n += 1
    return n + len(load_live_orders_open())


def remaining_to_watch() -> int:
    """Open positions still needing a watch (live ones already alerted excluded)."""
    exits = load_live_exits()
    return sum(
        1
        for p in collect_all_open_positions()
        if not (classify_mode(p) == "live" and (str(p.get("id")) in _live_alerted or str(p.get("id")) in exits))
    )


def _local_open_counts() -> tuple[int, int]:
    """(open_live, open_paper) from local files only (state.json, positions.json, live_orders.jsonl)."""
    live = paper = 0
    for path, src in ((STATE_PATH, "guardian_state"), (ROOT_POSITIONS_PATH, "root_positions")):
        for p in load_json(path).get("positions") or []:
            if str(p.get("status") or "open").lower() != "open":
                continue
            pos = normalize_position(p, src)
            if pos is None:
                continue
            if classify_mode(pos) == "live":
                live += 1
            else:
                paper += 1
    live += len(load_live_orders_open())
    return live, paper


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False) + "\n")
    tmp.replace(path)


def revolut_probe(timeout_s: float = 12.0) -> tuple[bool, str | None]:
    """Read-only Revolut access check (ticker, never an order). Returns (ok, error)."""
    pair = "BTC-EUR"
    try:  # pair of an open position (local files only, no extra revx call)
        rows = [p for p in (load_json(STATE_PATH).get("positions") or [])
                if str(p.get("status") or "open").lower() == "open"] + load_live_orders_open()
        for r in rows:
            cand = str(r.get("pair") or "").upper()
            if cand in WHITELIST_PAIRS:
                pair = cand
                break
    except Exception:  # noqa: BLE001
        pass
    mid = revx_ticker_mid(pair, timeout_s=timeout_s)
    if mid is not None and mid > 0:
        return True, None
    # ticker failed: try balances as a second read-only probe
    bin_path = REVX_BIN if Path(REVX_BIN).exists() else "revx"
    env = {
        **os.environ,
        "PATH": os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""),
        "HTTPS_PROXY": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:8791"),
        "HTTP_PROXY": os.environ.get("HTTP_PROXY", "http://127.0.0.1:8791"),
        "ALL_PROXY": os.environ.get("ALL_PROXY", "http://127.0.0.1:8791"),
    }
    try:
        proc = subprocess.run(
            [bin_path, "account", "balances", "--currencies", "EUR", "--json"],
            capture_output=True, text=True, timeout=timeout_s, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"ticker+balances: {e}"
    if proc.returncode == 0 and (proc.stdout or "").strip():
        return True, None
    err = (proc.stderr or proc.stdout or f"rc={proc.returncode}")[:200]
    return False, f"ticker failed; balances: {err}"


def maybe_write_revolut_heartbeat(force: bool = False) -> None:
    """While any position is open: every ~5 min, probe Revolut (read-only) → state/revolut_heartbeat.json.
    Idle (nothing open): leave the last file alone (doorbell uses watch_stops_heartbeat for idle)."""
    global _last_revolut_hb_monotonic, _revolut_hb_failures
    try:
        live, paper = _local_open_counts()
    except Exception:  # noqa: BLE001
        live = paper = 0
    open_n = (live or 0) + (paper or 0)
    if open_n <= 0 and not force:
        return
    now_m = time.monotonic()
    if not force and _last_revolut_hb_monotonic > 0 and (now_m - _last_revolut_hb_monotonic) < REVOLUT_HB_INTERVAL_S:
        return
    _last_revolut_hb_monotonic = now_m
    ok, err = revolut_probe()
    if ok:
        _revolut_hb_failures = 0
    else:
        _revolut_hb_failures += 1
    payload = {
        "ts": now_local_iso(),
        "ok": ok,
        "error": err,
        "consecutive_failures": _revolut_hb_failures,
        "open_live": live,
        "open_paper": paper,
        "pid": os.getpid(),
    }
    if _fake_now() is not None:
        payload["fake_now"] = now_local().isoformat()
    try:
        _atomic_json(REVOLUT_HB_PATH, payload)
    except OSError:
        pass
    log_json({"ok": True, "action": "revolut_heartbeat", "revolut_ok": ok,
              "consecutive_failures": _revolut_hb_failures, "error": err, "ts": now_utc_iso()})


def write_heartbeat(action: str) -> None:
    """state/watch_stops_heartbeat.json, rewritten after every loop (best effort, atomic)."""
    try:
        live, paper = _local_open_counts()
    except Exception:  # noqa: BLE001
        live = paper = None  # type: ignore[assignment]
    hb = {"ts": now_local_iso(), "pid": os.getpid(), "open_live": live, "open_paper": paper,
          "action": action}
    if _fake_now() is not None:
        hb["fake_now"] = now_local().isoformat()
    try:
        _atomic_json(HEARTBEAT_PATH, hb)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Watch ALL open positions (paper+live); paper-close on stop, "
            "live → urgent wake only (no silent dump)"
        )
    )
    parser.add_argument(
        "--interval", type=float, default=DEFAULT_INTERVAL_S,
        help=f"Poll interval seconds (default {DEFAULT_INTERVAL_S:g})",
    )
    parser.add_argument("--once", action="store_true", help="Single check then exit")
    parser.add_argument(
        "--dry-run", action="store_true", help="Detect breaches only; do not close"
    )
    parser.add_argument(
        "--force", action="store_true", help="Ignore existing watch_stops.pid"
    )
    parser.add_argument(
        "--exit-on-close", action="store_true",
        help="Legacy: exit 10 after any close even if other positions stay open",
    )
    args = parser.parse_args()

    if not acquire_pid(force=args.force):
        return 0

    atexit.register(release_pid)

    def _sig_handler(_signum, _frame):
        release_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    interval = max(1.0, float(args.interval))
    log_json({"ok": True, "action": "start", "pid": os.getpid(), "interval_s": interval,
              "state": str(STATE_PATH), "ticks_dir": str(TICKS_DIR), "ts": now_utc_iso()})
    errors = 0

    while True:
        try:
            action, code, payload = one_cycle(dry_run=args.dry_run)
        except Exception as e:  # noqa: BLE001
            errors += 1
            log_json({"ok": False, "action": "error", "error": str(e), "consecutive": errors,
                      "ts": now_utc_iso()})
            write_heartbeat("error")
            if args.once or errors >= MAX_CONSECUTIVE_ERRORS:
                release_pid()
                return 1
            time.sleep(interval)
            continue

        log_json(payload)
        write_heartbeat(action)
        if action != "idle" and not args.once:  # long-running watcher only (--once = one-shot check)
            maybe_write_revolut_heartbeat()

        if action == "idle":
            release_pid()
            # Race guard: a position opened while we were deciding to stop
            if not args.once and _cheap_open_count() > 0 and acquire_pid(force=False):
                log_json({"ok": True, "action": "resume_after_idle", "ts": now_utc_iso()})
                time.sleep(min(interval, 2.0))
                continue
            return 0
        if action in ("stop_closed", "live_stop_wake", "stop_mixed"):
            errors = 0
            if args.once or args.exit_on_close:
                release_pid()
                return 10
            try:
                left = remaining_to_watch()
            except Exception:  # noqa: BLE001
                left = _cheap_open_count()
            if left <= 0:
                release_pid()
                return 10
            log_json({"ok": True, "action": "continue_after_close", "remaining": left,
                      "wake": str(WAKE_PATH), "ts": now_utc_iso()})
            time.sleep(interval)
            continue
        if action == "close_failed":
            errors += 1
            if args.once or errors >= MAX_CONSECUTIVE_ERRORS:
                release_pid()
                return 1
            time.sleep(interval)
            continue
        errors = 0
        if args.once:
            release_pid()
            return 0

        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
