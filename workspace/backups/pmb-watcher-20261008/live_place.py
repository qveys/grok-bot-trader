#!/usr/bin/env python3
"""Place a validated Revolut X limit post-only order (live).

Arming (one of):
  - file LIVE_ONCE at repo root (preferred: one trade then auto-clears)
  - MODE file contents = live

Always: validate_order OK, no STOP/HALTED, limit + post-only only.
Mechanical gates (before place):
  - max 1 live/day via revx order history / trade (primary) + live_day.json (secondary)
  - expectancy: expected_gain_eur >= 3 * (costs_eur + expected_loss_eur)
  - min ticket MIN_LIVE_EUR

  python3 live_place.py --order order.json
  python3 live_place.py --order order.json --dry-run
  python3 live_place.py --order order.json --dry-run --skip-expectancy
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = GUARDIAN.parent
MODE_PATH = ROOT / "MODE"
LIVE_ONCE = ROOT / "LIVE_ONCE"
STOP_PATH = ROOT / "STOP"
HALTED_PATH = GUARDIAN / "HALTED"
LOG_PATH = ROOT / "state" / "live_orders.jsonl"
LIVE_DAY_PATH = ROOT / "state" / "live_day.json"  # {"date": "YYYY-MM-DD", "count": 1}
VALIDATE = Path(__file__).resolve().parent / "validate_order.py"
MAX_LIVE_PER_DAY = 1
MIN_LIVE_EUR = 8  # aligned Risk 2026-10-07: ~5% of ~165€ cash.0
EXPECTANCY_MULTIPLE = 3.0
# Round-trip fee estimate when costs_eur omitted (10 bps of notional)
FEE_ESTIMATE_BPS = 10.0
WHITELIST_PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
SUCCESS_ORDER_STATES = frozenset(
    {"filled", "partially_filled", "partially-filled", "done", "closed", "completed"}
)
TZ = ZoneInfo("Europe/Brussels")
REVX_BIN = os.environ.get("REVX_BIN", "revx")
PROXY = "http://127.0.0.1:8791"


def now_brussels() -> datetime:
    return datetime.now(TZ)


def today_local() -> str:
    return now_brussels().date().isoformat()


def revx_env() -> dict:
    env = os.environ.copy()
    env["HTTPS_PROXY"] = PROXY
    env["HTTP_PROXY"] = PROXY
    env["ALL_PROXY"] = PROXY
    # Prefer wrapper on PATH; ensure local bin is visible
    local_bin = "/home/box/.local/bin"
    path = env.get("PATH", "")
    if local_bin not in path.split(":"):
        env["PATH"] = f"{local_bin}:{path}" if path else local_bin
    return env


def load_order(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text())
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("No order JSON")
    return json.loads(raw)


def live_count_today() -> int:
    if not LIVE_DAY_PATH.exists():
        return 0
    try:
        data = json.loads(LIVE_DAY_PATH.read_text())
    except Exception:
        return 0
    if data.get("date") != today_local():
        return 0
    return int(data.get("count") or 0)


def record_live_success() -> None:
    LIVE_DAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIVE_DAY_PATH.write_text(
        json.dumps({"date": today_local(), "count": live_count_today() + 1}) + "\n"
    )


def armed() -> tuple[bool, str]:
    mode = MODE_PATH.read_text().strip() if MODE_PATH.exists() else ""
    if LIVE_ONCE.exists():
        return True, "LIVE_ONCE"
    if mode == "live":
        return True, "MODE=live"
    return False, f"not armed (MODE={mode!r}, no LIVE_ONCE)"


def _parse_json_stdout(stdout: str) -> object:
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some CLIs print banners before JSON
        start = text.find("{")
        start_arr = text.find("[")
        if start < 0 and start_arr < 0:
            return None
        if start < 0:
            start = start_arr
        elif start_arr >= 0:
            start = min(start, start_arr)
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            return None


def _as_list(payload: object) -> list:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "orders", "trades", "results", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
        return [payload]
    return []


def _item_looks_success(item: dict) -> bool:
    state = str(
        item.get("order_state")
        or item.get("state")
        or item.get("status")
        or item.get("orderState")
        or ""
    ).lower().replace(" ", "_")
    if state in SUCCESS_ORDER_STATES:
        return True
    # Trades / fills without explicit state count as successful live activity
    if item.get("trade_id") or item.get("tradeId") or item.get("id"):
        if "order" in item or "price" in item or "qty" in item or "quantity" in item:
            if state in ("", "filled", "partially_filled", "executed", "completed"):
                return True
    filled = item.get("filled_qty") or item.get("filledQty") or item.get("executed_qty")
    try:
        if filled is not None and float(filled) > 0:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _pair_of(item: dict) -> str:
    return str(
        item.get("symbol")
        or item.get("pair")
        or item.get("trading_pair")
        or item.get("market")
        or ""
    ).upper()


def query_revx_live_today() -> dict:
    """Primary max-1/day guard: any successful BTC/ETH/SOL live order or trade today."""
    env = revx_env()
    today = today_local()
    symbols = ",".join(WHITELIST_PAIRS)
    hits: list[dict] = []
    errors: list[str] = []

    # Order history for all whitelist pairs today
    cmd_hist = [
        REVX_BIN,
        "order",
        "history",
        "--symbols",
        symbols,
        "--start-date",
        "today",
        "--json",
        "--limit",
        "50",
    ]
    try:
        proc = subprocess.run(cmd_hist, capture_output=True, text=True, env=env, timeout=60)
        if proc.returncode != 0:
            errors.append(
                f"order history rc={proc.returncode}: {(proc.stderr or proc.stdout or '')[:300]}"
            )
        else:
            for item in _as_list(_parse_json_stdout(proc.stdout)):
                if not isinstance(item, dict):
                    continue
                pair = _pair_of(item)
                if pair and pair not in WHITELIST_PAIRS:
                    continue
                if _item_looks_success(item) or (
                    # With --order-states unset, include any non-cancelled/rejected row as caution
                    str(item.get("order_state") or item.get("state") or item.get("status") or "")
                    .lower()
                    .replace(" ", "_")
                    not in ("cancelled", "canceled", "rejected", "expired")
                    and pair in WHITELIST_PAIRS
                    and item
                ):
                    # Count only clearly successful fills; cancelled alone do not block
                    if _item_looks_success(item):
                        hits.append({"source": "order_history", "pair": pair or "?", "item": item})
    except (OSError, subprocess.TimeoutExpired) as e:
        errors.append(f"order history failed: {e}")

    # Also probe private trades per pair (covers wiped live_day.json)
    for pair in WHITELIST_PAIRS:
        cmd_tr = [
            REVX_BIN,
            "trade",
            "private",
            pair,
            "--start-date",
            "today",
            "--json",
            "--limit",
            "20",
        ]
        try:
            proc = subprocess.run(cmd_tr, capture_output=True, text=True, env=env, timeout=60)
            if proc.returncode != 0:
                errors.append(
                    f"trade {pair} rc={proc.returncode}: {(proc.stderr or proc.stdout or '')[:200]}"
                )
                continue
            for item in _as_list(_parse_json_stdout(proc.stdout)):
                if isinstance(item, dict):
                    # Any private trade row today is a successful live fill
                    hits.append({"source": "trade_private", "pair": pair, "item": item})
        except (OSError, subprocess.TimeoutExpired) as e:
            errors.append(f"trade {pair} failed: {e}")

    # Deduplicate by id if present
    seen: set[str] = set()
    unique: list[dict] = []
    for h in hits:
        item = h.get("item") or {}
        key = str(item.get("id") or item.get("order_id") or item.get("trade_id") or id(item))
        if key in seen:
            continue
        seen.add(key)
        unique.append(h)

    return {
        "date": today,
        "count": len(unique),
        "hits": unique[:10],  # cap payload
        "errors": errors or None,
        "queried_at": now_brussels().isoformat(),
    }


def estimate_costs_eur(amount_eur: float) -> float:
    return max(0.01, amount_eur * (FEE_ESTIMATE_BPS / 10_000.0))


def check_expectancy(order: dict, skip: bool) -> dict:
    """Return {ok, error?, details} for expectancy gate."""
    if skip:
        return {"ok": True, "skipped": True}

    missing = [
        k
        for k in ("expected_gain_eur", "expected_loss_eur")
        if order.get(k) is None
    ]
    if missing:
        return {
            "ok": False,
            "error": (
                f"expectancy fields missing: {missing}. "
                "Provide expected_gain_eur, expected_loss_eur, and optionally costs_eur "
                "(or rely on fee estimate). "
                "Gate: expected_gain_eur >= 3 * (costs_eur + expected_loss_eur). "
                "For dry-run tests only: pass --skip-expectancy with --dry-run."
            ),
        }

    try:
        expected_gain = float(order["expected_gain_eur"])
        expected_loss = float(order["expected_loss_eur"])
    except (TypeError, ValueError) as e:
        return {"ok": False, "error": f"invalid expectancy numbers: {e}"}

    if order.get("costs_eur") is not None:
        try:
            costs = float(order["costs_eur"])
            costs_source = "order.costs_eur"
        except (TypeError, ValueError) as e:
            return {"ok": False, "error": f"invalid costs_eur: {e}"}
    else:
        amount_eur = float(order.get("amount_eur") or 0)
        costs = estimate_costs_eur(amount_eur)
        costs_source = f"fee_estimate_{FEE_ESTIMATE_BPS}bps"

    threshold = EXPECTANCY_MULTIPLE * (costs + expected_loss)
    ok = expected_gain >= threshold
    details = {
        "expected_gain_eur": expected_gain,
        "expected_loss_eur": expected_loss,
        "costs_eur": costs,
        "costs_source": costs_source,
        "multiple": EXPECTANCY_MULTIPLE,
        "threshold": threshold,
        "formula": "expected_gain_eur >= 3 * (costs_eur + expected_loss_eur)",
    }
    if not ok:
        return {
            "ok": False,
            "error": (
                f"expectancy gate failed: gain {expected_gain} < "
                f"{EXPECTANCY_MULTIPLE}*(costs {costs} + loss {expected_loss}) = {threshold}"
            ),
            "details": details,
        }
    return {"ok": True, "details": details}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", help="order JSON path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--skip-expectancy",
        action="store_true",
        help="Skip expectancy gate (only allowed with --dry-run, for tests)",
    )
    args = ap.parse_args()

    if args.skip_expectancy and not args.dry_run:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "--skip-expectancy only allowed with --dry-run",
                }
            )
        )
        return 2

    if STOP_PATH.exists() or HALTED_PATH.exists():
        print(json.dumps({"ok": False, "error": "STOP or HALTED present"}))
        return 2

    # Primary: Revolut today (survives wiped live_day.json)
    revx_today = query_revx_live_today()
    file_count = live_count_today()
    effective_count = max(int(revx_today.get("count") or 0), file_count)

    if effective_count >= MAX_LIVE_PER_DAY and not args.dry_run:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": (
                        f"mechanical guard: already {effective_count} live today "
                        f"(max {MAX_LIVE_PER_DAY}); revx={revx_today.get('count')} "
                        f"live_day.json={file_count}"
                    ),
                    "date": today_local(),
                    "revx_today": {
                        "count": revx_today.get("count"),
                        "errors": revx_today.get("errors"),
                        "queried_at": revx_today.get("queried_at"),
                    },
                    "live_day_count": file_count,
                },
                ensure_ascii=False,
            )
        )
        return 7

    ok_arm, arm_reason = armed()
    if not ok_arm and not args.dry_run:
        print(
            json.dumps(
                {"ok": False, "error": arm_reason, "hint": "touch LIVE_ONCE or set MODE=live"}
            )
        )
        return 3

    order = load_order(args.order)

    # Min ticket
    try:
        amount_eur = float(order.get("amount_eur"))
    except (TypeError, ValueError):
        print(json.dumps({"ok": False, "error": "invalid or missing amount_eur"}))
        return 5
    if amount_eur < MIN_LIVE_EUR:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": (
                        f"min ticket gate: amount_eur {amount_eur} < MIN_LIVE_EUR {MIN_LIVE_EUR}"
                    ),
                    "MIN_LIVE_EUR": MIN_LIVE_EUR,
                }
            )
        )
        return 8

    # Expectancy gate
    exp = check_expectancy(order, skip=bool(args.skip_expectancy))
    if not exp.get("ok"):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": exp.get("error"),
                    "expectancy": exp.get("details"),
                },
                ensure_ascii=False,
            )
        )
        return 9

    if args.order:
        proc = subprocess.run(
            [sys.executable, str(VALIDATE), "--order", args.order], capture_output=True
        )
    else:
        proc = subprocess.run(
            [sys.executable, str(VALIDATE)],
            input=json.dumps(order).encode(),
            capture_output=True,
        )
    out = (proc.stdout or b"").decode()
    err = (proc.stderr or b"").decode()
    try:
        val = json.loads(out) if out.strip() else {"raw": err, "returncode": proc.returncode}
    except json.JSONDecodeError:
        val = {"raw": out + err, "returncode": proc.returncode}
    if proc.returncode != 0 or (isinstance(val, dict) and val.get("ok") is False):
        payload = {"ok": False, "error": "validate failed", "validate": val}
        if args.dry_run:
            payload["gates"] = {
                "min_ticket": {"amount_eur": amount_eur, "MIN_LIVE_EUR": MIN_LIVE_EUR},
                "expectancy": exp,
                "max_live_per_day": {
                    "max": MAX_LIVE_PER_DAY,
                    "revx_count": revx_today.get("count"),
                    "live_day_count": file_count,
                    "effective_count": effective_count,
                    "would_refuse": effective_count >= MAX_LIVE_PER_DAY,
                    "revx_errors": revx_today.get("errors"),
                    "queried_at": revx_today.get("queried_at"),
                },
            }
            payload["at"] = now_brussels().isoformat()
        print(json.dumps(payload, ensure_ascii=False))
        return 4

    pair = str(order["pair"]).upper()
    side = str(order["side"]).lower()
    price = float(order["price"])
    if str(order.get("type", "limit")).lower() != "limit":
        print(json.dumps({"ok": False, "error": "only limit orders allowed"}))
        return 5

    env = revx_env()

    cmd = [
        REVX_BIN,
        "order",
        "place",
        pair,
        side,
        "--quote",
        f"{amount_eur}",
        "--limit",
        f"{price}",
        "--post-only",
        "--json",
        "--client-order-id",
        str(uuid.uuid4()),
    ]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": True,
                    "armed": arm_reason,
                    "cmd": cmd,
                    "validate": val,
                    "gates": {
                        "min_ticket": {"amount_eur": amount_eur, "MIN_LIVE_EUR": MIN_LIVE_EUR},
                        "expectancy": exp,
                        "max_live_per_day": {
                            "max": MAX_LIVE_PER_DAY,
                            "revx_count": revx_today.get("count"),
                            "live_day_count": file_count,
                            "effective_count": effective_count,
                            "would_refuse": effective_count >= MAX_LIVE_PER_DAY,
                            "revx_errors": revx_today.get("errors"),
                            "queried_at": revx_today.get("queried_at"),
                        },
                    },
                    "at": now_brussels().isoformat(),
                },
                ensure_ascii=False,
            )
        )
        return 0

    # Final refuse if revx already has a live today (belt after validate)
    if effective_count >= MAX_LIVE_PER_DAY:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"mechanical guard: already {effective_count} live today",
                    "revx_today": revx_today,
                },
                ensure_ascii=False,
            )
        )
        return 7

    placed = subprocess.run(cmd, capture_output=True, text=True, env=env)
    result = {
        "ok": placed.returncode == 0,
        "armed": arm_reason,
        "at": now_brussels().isoformat(),
        "cmd": cmd,
        "stdout": placed.stdout,
        "stderr": placed.stderr,
        "returncode": placed.returncode,
        "order": order,
        "gates": {
            "expectancy": exp,
            "min_ticket": {"amount_eur": amount_eur, "MIN_LIVE_EUR": MIN_LIVE_EUR},
            "revx_today_count": revx_today.get("count"),
            "live_day_count": file_count,
        },
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    if placed.returncode == 0:
        record_live_success()
        if LIVE_ONCE.exists():
            LIVE_ONCE.unlink(missing_ok=True)

    print(json.dumps(result, ensure_ascii=False))
    return 0 if placed.returncode == 0 else 6


if __name__ == "__main__":
    raise SystemExit(main())
