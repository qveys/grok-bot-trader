#!/usr/bin/env python3
"""Read latest mid-price tick for a pair; emergency refresh if stale.

Prints one JSON object to stdout for Predict to consume.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import collect_price_ticks as cpt  # noqa: E402

DEFAULT_STALE_S = 75.0


def parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        # Support +02:00 and Z
        s = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def read_latest_for_pair(pair: str, path: Path) -> dict | None:
    if not path.exists():
        return None
    last: dict | None = None
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("pair") == pair:
                last = row
    return last


def age_seconds(tick: dict, now: datetime | None = None) -> float | None:
    now = now or cpt.brussels_now()
    dt = parse_ts(tick.get("ts") or "")
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds()


def get_latest(
    pair: str,
    date_str: str | None = None,
    stale_s: float = DEFAULT_STALE_S,
    refresh: bool = True,
) -> dict:
    """Return latest tick for pair; emergency fetch+append if missing/stale."""
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        os.environ.setdefault(key, "http://127.0.0.1:8791")

    if date_str:
        path = cpt.TICKS_DIR / f"{date_str}.jsonl"
        now = cpt.brussels_now()
    else:
        now = cpt.brussels_now()
        path = cpt.day_file(now)

    tick = read_latest_for_pair(pair, path)
    need_refresh = False
    reason = None
    if tick is None:
        need_refresh = True
        reason = "missing"
    else:
        age = age_seconds(tick, now)
        if age is None or age > stale_s:
            need_refresh = True
            reason = f"stale_age={age}"

    if need_refresh and refresh:
        fresh = cpt.fetch_tick(pair)
        if fresh:
            cpt.append_ticks([fresh], path=path)
            fresh["_refreshed"] = True
            fresh["_refresh_reason"] = reason
            return fresh
        # Fall through: return stale tick if we have one
        if tick is not None:
            tick = dict(tick)
            tick["_refreshed"] = False
            tick["_refresh_failed"] = True
            tick["_refresh_reason"] = reason
            return tick
        return {
            "error": "no_tick",
            "pair": pair,
            "reason": reason or "fetch_failed",
        }

    if tick is None:
        return {"error": "no_tick", "pair": pair, "reason": "missing"}
    out = dict(tick)
    out["_refreshed"] = False
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Read latest PM price tick for a pair")
    ap.add_argument("pair", help="e.g. ETH-EUR")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: today Brussels)")
    ap.add_argument(
        "--stale-seconds",
        type=float,
        default=DEFAULT_STALE_S,
        help=f"Max age before emergency refresh (default {DEFAULT_STALE_S})",
    )
    ap.add_argument(
        "--no-refresh",
        action="store_true",
        help="Do not emergency-fetch if missing/stale",
    )
    args = ap.parse_args()
    result = get_latest(
        args.pair.upper() if "-" in args.pair.upper() else args.pair,
        date_str=args.date,
        stale_s=args.stale_seconds,
        refresh=not args.no_refresh,
    )
    # Normalize pair casing for common form
    if "pair" in result and isinstance(result["pair"], str):
        pass
    print(json.dumps(result, ensure_ascii=False))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
