#!/usr/bin/env python3
"""Stop-loss watcher for ALL open positions (paper + live).

Poll mid prices while any watchable position is open (guardian/state.json,
state/positions.json crypto rows, live_orders.jsonl fills, revx open orders
best-effort).

On stop / target breach:
  - paper/sim long → sell via paper_fill; short (idée à la baisse) → rebuy
    (safety if mid≥stop, target if mid≤target_price); wake + events, exit 10
  - live → do NOT auto market-dump; write urgent wake (mode=live) so Risk
    can arm and sell; exit 10. live_place has no documented stop-close path
    (LIVE_ONCE + expectancy + max-1/day); prefer wake+alert over auto live sell.
  ALLOW_LIVE_AUTO_SELL stays False.

Paper path never places live Revolut orders.
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

TZ = ZoneInfo("Europe/Brussels")
SCAN_MIN_INTERVAL_S = 60.0
REVX_BIN = os.path.expanduser("~/.local/bin/revx")
WHITELIST_PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
# live_place has no stop-close path; never auto-sell live from this watcher
ALLOW_LIVE_AUTO_SELL = False

_pid_written = False
_last_scan_run_monotonic = 0.0



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
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None
    for key in ("last", "lastPrice", "price", "mid", "markPrice"):
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


def resolve_prices(pairs: list[str]) -> tuple[dict[str, float], str]:
    """Return (prices, source_label). Prefer scan (throttled), then last_scan, then revx."""
    prices = try_run_scan()
    source = "scan" if prices else "none"
    if not prices:
        prices = scan_price_map(load_json(SCAN_PATH))
        if prices:
            source = "last_scan"

    missing = [p for p in pairs if p not in prices]
    if missing:
        for pair in missing:
            mid = revx_ticker_mid(pair)
            if mid is not None:
                prices[pair] = mid
                source = f"{source}+revx" if source != "none" else "revx"
    return prices, source


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


def load_live_orders_open() -> list[dict]:
    """Reconstruct open live positions from successful live_orders.jsonl buys without close."""
    if not LIVE_ORDERS_PATH.exists():
        return []
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
        order = row.get("order") if isinstance(row.get("order"), dict) else row
        pair = str(order.get("pair") or "").upper()
        side = str(order.get("side") or "").lower()
        if not pair:
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
                "stop_price_eur": order.get("stop_price_eur"),
                "status": "open",
                "mode": "live",
                "source": "live_orders",
                "opened_at": row.get("at") or now_utc_iso(),
            }
        elif side == "sell" and amount > 0:
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
    return open_buys


def load_revx_open_orders(timeout_s: float = 15.0) -> list[dict]:
    """Best-effort list of revx open orders (no place/cancel)."""
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
        pos_val += float(p.get("mark_eur", p.get("cost_eur", 0)) or 0)
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
            "close_reason": "stop_hit" if c.get("mode") != "live" else "stop_hit_live_pending",
            "pnl_eur": c.get("pnl_eur"),
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
    if CHECK_ALERTS.exists():
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


def estimate_pnl(pos: dict, mid: float) -> float:
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
            if c.get("idea_type") == "baisse" or c.get("side") in ("short", "sell"):
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
        if len(live_breached) == 1:
            message_fr = (
                f"Stop touché en LIVE — vente à faire sur {c['pair']}: "
                f"prix {c['price']:.4f} ≤ stop {c['stop']:.4f}. "
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
                "live_pending": live_breached,
                "auto_sell": False,
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
            parts_fr.append(
                "Stop touché en LIVE — vente à faire: "
                + ", ".join(c["pair"] for c in live_breached)
            )
        primary = live_breached[0] if live_breached else paper_closed[0]
        wake.update(
            {
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

    save_json(WAKE_PATH, wake)
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a") as f:
        for c in paper_closed:
            event = {
                "ts": ts,
                "mode": "paper",
                "pair": c["pair"],
                "stop": c["stop"],
                "price": c["price"],
                "pnl_eur": c["pnl_eur"],
                "position_id": c.get("id"),
                "close_reason": "stop_hit",
                "message_fr": (
                    f"Stop paper touché sur {c['pair']}: prix {c['price']:.4f} ≤ stop "
                    f"{c['stop']:.4f}, PnL {c['pnl_eur']:+.4f} EUR."
                ),
            }
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        for c in live_breached:
            event = {
                "ts": ts,
                "mode": "live",
                "pair": c["pair"],
                "stop": c["stop"],
                "price": c["price"],
                "pnl_eur": c.get("pnl_eur"),
                "position_id": c.get("id"),
                "close_reason": "stop_hit_live_pending",
                "auto_sell": False,
                "message_fr": (
                    f"Stop touché en LIVE — vente à faire sur {c['pair']}: "
                    f"prix {c['price']:.4f} ≤ stop {c['stop']:.4f}."
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
            }
        )
    return closed_out


def handle_live_breached(breached: list[dict], dry_run: bool) -> list[dict]:
    """Live stop: wake+alert only (no auto sell unless ALLOW_LIVE_AUTO_SELL)."""
    out: list[dict] = []
    for item in breached:
        pos = item["pos"]
        mid = item["mid"]
        stop = item["stop"]
        pair = str(pos.get("pair") or "").upper()
        entry = {
            "id": pos.get("id"),
            "pair": pair,
            "side": str(pos.get("side") or "long").lower(),
            "mode": "live",
            "stop": stop,
            "price": mid,
            "pnl_eur": estimate_pnl(pos, mid),
            "auto_sell": False,
            "track_source": pos.get("_track_source"),
            "dry_run": dry_run,
            "message_fr": "Stop touché en LIVE — vente à faire",
        }
        if ALLOW_LIVE_AUTO_SELL:
            # Reserved: playbook currently has no stop-close path on live_place.
            entry["auto_sell_attempted"] = False
            entry["auto_sell_reason"] = "disabled_no_playbook_stop_close"
        out.append(entry)
        if not dry_run:
            log_json(
                {
                    "ok": True,
                    "action": "live_stop_wake_only",
                    "pair": pair,
                    "stop": stop,
                    "price": mid,
                    "hint": "arm LIVE_ONCE then live_place limit sell — no silent dump",
                }
            )
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
    prices, source = resolve_prices(pairs)

    paper_breached: list[dict] = []
    live_breached: list[dict] = []
    watching: list[dict] = []
    for pos in opens:
        pair = str(pos.get("pair") or "").upper()
        mid = prices.get(pair)
        if mid is None:
            mid_fallback = pos.get("last_mid_eur")
            try:
                mid = float(mid_fallback) if mid_fallback is not None else None
            except (TypeError, ValueError):
                mid = None
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
        }
        # For shorts, stop may be set while target drives take-profit; expose both
        entry["target_price"] = pos.get("target_price")
        entry["idea_type"] = pos.get("idea_type") or pos.get("kind")
        watching.append(entry)
        if mid is None:
            continue
        # Longs need a stop; shorts can breach on target without stop (rare)
        side_l = str(pos.get("side") or "long").lower()
        idea_l = str(pos.get("idea_type") or "").lower()
        is_short = side_l in ("short", "sell") or idea_l == "baisse"
        if stop is None and not is_short:
            continue
        if stop is None and is_short and pos.get("target_price") is None:
            continue
        breach = position_breach(pos, float(mid))
        if breach:
            item = {
                "pos": pos,
                "mid": breach["mid"],
                "stop": breach["stop"],
                "rebuy_reason": breach.get("rebuy_reason"),
                "close_reason": breach.get("close_reason"),
            }
            if mode == "live":
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
            "close_reason": "stop_hit_live_pending",
            "pnl_eur": c.get("pnl_eur"),
            "message_fr": "Stop touché en LIVE — vente à faire",
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
        "ts": now_utc_iso(),
    }
    return action, 10, payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Watch ALL open positions (paper+live); paper-close on stop, "
            "live → urgent wake only (no silent dump)"
        )
    )
    parser.add_argument("--interval", type=float, default=15.0, help="Poll interval seconds")
    parser.add_argument("--once", action="store_true", help="Single check then exit")
    parser.add_argument(
        "--dry-run", action="store_true", help="Detect breaches only; do not close"
    )
    parser.add_argument(
        "--force", action="store_true", help="Ignore existing watch_stops.pid"
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

    while True:
        try:
            action, code, payload = one_cycle(dry_run=args.dry_run)
        except Exception as e:
            log_json({"ok": False, "action": "error", "error": str(e), "ts": now_utc_iso()})
            release_pid()
            return 1

        log_json(payload)

        if action == "idle":
            release_pid()
            return 0
        if action in ("stop_closed", "live_stop_wake", "stop_mixed"):
            release_pid()
            return 10
        if action == "close_failed":
            release_pid()
            return 1
        if args.once:
            release_pid()
            return 0

        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
