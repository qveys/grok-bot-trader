#!/usr/bin/env python3
"""Shared detached launcher for watch_stops.py (used by paper_fill + live_place).

ensure_watcher() starts `watch_stops.py --interval N` in the background, detached
(start_new_session=True, stdout/stderr appended to state/watch_stops.log), only if no
live watcher already owns state/watch_stops.pid. watch_stops itself also refuses a
2nd instance, so a race between two launchers is harmless.

Env:
  PAPER_FILL_NO_WATCH=1 / WATCH_STOPS_NO_AUTOSTART=1  → never start (tests)
  WATCH_STOPS_INTERVAL   → poll interval passed to the watcher (default 30 s)
  WATCH_STOPS_PID / WATCH_STOPS_LOG / PREDICT_BOT_ROOT → paths (isolated tests)
The child inherits the caller's environment (so test env vars keep it isolated).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

GUARDIAN = Path(__file__).resolve().parent.parent
WATCH_SCRIPT = GUARDIAN / "scripts" / "watch_stops.py"
DEFAULT_INTERVAL_S = 30.0
TZ = ZoneInfo("Europe/Brussels")


def _root() -> Path:
    return Path(os.environ.get("PREDICT_BOT_ROOT", str(GUARDIAN.parent)))


def pid_path() -> Path:
    return Path(os.environ.get("WATCH_STOPS_PID", str(_root() / "state" / "watch_stops.pid")))


def log_path() -> Path:
    return Path(os.environ.get("WATCH_STOPS_LOG", str(_root() / "state" / "watch_stops.log")))


def autostart_disabled() -> bool:
    for key in ("PAPER_FILL_NO_WATCH", "WATCH_STOPS_NO_AUTOSTART"):
        if str(os.environ.get(key, "")).strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # Guard against a recycled pid: on Linux check it is really watch_stops
    cmdline = Path(f"/proc/{pid}/cmdline")
    if cmdline.exists():
        try:
            if b"watch_stops" not in cmdline.read_bytes():
                return False
        except OSError:
            pass
    return True


def running_pid() -> int | None:
    p = pid_path()
    if not p.exists():
        return None
    try:
        pid = int(p.read_text().strip().split()[0])
    except (ValueError, OSError, IndexError):
        return None
    return pid if pid_alive(pid) else None


def ensure_watcher(reason: str = "", wait_s: float = 3.0) -> dict:
    """Start the detached watcher if none is running. Returns status fields for JSON output."""
    if autostart_disabled():
        return {"watcher_started": False, "watcher_already_running": False, "watcher_disabled": True}
    pid = running_pid()
    if pid:
        return {"watcher_started": False, "watcher_already_running": True, "watcher_pid": pid}
    if not WATCH_SCRIPT.exists():
        return {
            "watcher_started": False,
            "watcher_already_running": False,
            "watcher_error": f"missing {WATCH_SCRIPT}",
        }
    try:
        interval = float(os.environ.get("WATCH_STOPS_INTERVAL", DEFAULT_INTERVAL_S))
    except ValueError:
        interval = DEFAULT_INTERVAL_S
    log = log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log.open("ab") as lf:
            lf.write(
                f"[launcher] {datetime.now(TZ).isoformat()} start watch_stops "
                f"interval={interval:g} reason={reason or '-'} caller_pid={os.getpid()}\n".encode()
            )
            lf.flush()
            proc = subprocess.Popen(
                [sys.executable, str(WATCH_SCRIPT), "--interval", f"{interval:g}"],
                cwd=str(_root()) if _root().exists() else None,
                stdin=subprocess.DEVNULL,
                stdout=lf,
                stderr=lf,
                start_new_session=True,
                close_fds=True,
                env=os.environ.copy(),
            )
    except OSError as e:
        return {"watcher_started": False, "watcher_already_running": False, "watcher_error": str(e)}

    deadline = time.monotonic() + max(0.2, wait_s)
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            break
        if running_pid() == proc.pid:
            return {
                "watcher_started": True,
                "watcher_already_running": False,
                "watcher_pid": proc.pid,
                "watcher_log": str(log),
            }
        time.sleep(0.05)
    rc = proc.poll()
    if rc is None:
        # Still alive but pid file not seen yet (slow start) — count as started
        return {
            "watcher_started": True,
            "watcher_already_running": False,
            "watcher_pid": proc.pid,
            "watcher_log": str(log),
        }
    other = running_pid()
    if other:  # lost a race against another launcher
        return {"watcher_started": False, "watcher_already_running": True, "watcher_pid": other}
    return {
        "watcher_started": False,
        "watcher_already_running": False,
        "watcher_exit_code": rc,
        "watcher_log": str(log),
    }
