#!/usr/bin/env python3
"""30-second mid-price tick collector for PM pipeline scoring (D-007/008/009).

Writes one JSONL line per pair per cycle to:
  state/price_ticks/YYYY-MM-DD.jsonl  (Europe/Brussels date)

Public tickers only (Binance → Coinbase → Kraken) via scan_crypto helpers.
No Revolut order API. No secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import scan_crypto  # noqa: E402  — installs proxy opener + fetch helpers

TICKS_DIR = ROOT / "state" / "price_ticks"
PID_PATH = TICKS_DIR / "collector.pid"
DEFAULT_PAIRS = ["BTC-EUR", "ETH-EUR", "SOL-EUR"]
INTERVAL_S = 30.0


def brussels_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Europe/Brussels"))
    except Exception:
        return datetime.now(timezone.utc)


def day_file(d: datetime | None = None) -> Path:
    now = d or brussels_now()
    return TICKS_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"


def tick_from_row(pair: str, row: dict, ts: str) -> dict:
    """Build tick record: prefer mid=(bid+ask)/2, else last price as mid."""
    bid = row.get("bid")
    ask = row.get("ask")
    last = row.get("price_eur")
    mid = None
    if bid is not None and ask is not None and bid > 0 and ask > 0:
        mid = (float(bid) + float(ask)) / 2.0
    elif last is not None:
        mid = float(last)
    out: dict = {
        "ts": ts,
        "pair": pair,
        "mid": mid,
        "source": row.get("source") or "unknown",
    }
    if bid is not None:
        out["bid"] = float(bid)
    if ask is not None:
        out["ask"] = float(ask)
    if last is not None and mid is not None and abs(float(last) - mid) > 1e-12:
        out["last"] = float(last)
    return out


def fetch_tick(pair: str, ts: str | None = None) -> dict | None:
    """Fetch one pair; return tick dict or None on failure."""
    ts = ts or brussels_now().isoformat()
    row, errors = scan_crypto.fetch_pair(pair)
    if not row:
        msg = errors if errors else ["no data"]
        print(f"[price_ticks] skip {pair}: {msg}", file=sys.stderr)
        return None
    tick = tick_from_row(pair, row, ts)
    if tick.get("mid") is None:
        print(f"[price_ticks] skip {pair}: no mid/price", file=sys.stderr)
        return None
    return tick


def append_ticks(ticks: list[dict], path: Path | None = None) -> Path:
    path = path or day_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for t in ticks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    return path


def collect_cycle(pairs: list[str] | None = None) -> list[dict]:
    pairs = pairs or DEFAULT_PAIRS
    ts = brussels_now().isoformat()
    ticks: list[dict] = []
    for pair in pairs:
        try:
            tick = fetch_tick(pair, ts=ts)
            if tick:
                ticks.append(tick)
        except Exception as e:  # noqa: BLE001 — skip pair, retry next cycle
            print(f"[price_ticks] error {pair}: {e}", file=sys.stderr)
    if ticks:
        path = append_ticks(ticks)
        print(
            f"[price_ticks] wrote {len(ticks)} tick(s) → {path.name} @ {ts}",
            flush=True,
        )
    else:
        print(f"[price_ticks] no ticks written @ {ts}", file=sys.stderr, flush=True)
    return ticks


def write_pid() -> None:
    TICKS_DIR.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()) + "\n")


def clear_pid() -> None:
    try:
        if PID_PATH.exists() and PID_PATH.read_text().strip() == str(os.getpid()):
            PID_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def run_daemon(interval: float = INTERVAL_S, pairs: list[str] | None = None) -> None:
    write_pid()
    print(
        f"[price_ticks] daemon pid={os.getpid()} interval={interval}s pairs={pairs or DEFAULT_PAIRS}",
        flush=True,
    )
    try:
        while True:
            t0 = time.monotonic()
            collect_cycle(pairs)
            elapsed = time.monotonic() - t0
            sleep_for = max(0.5, interval - elapsed)
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        print("[price_ticks] stopped (KeyboardInterrupt)", flush=True)
    finally:
        clear_pid()


def main() -> int:
    ap = argparse.ArgumentParser(description="PM mid-price tick collector (30s)")
    ap.add_argument(
        "--once",
        action="store_true",
        help="Collect one cycle for all pairs and exit",
    )
    ap.add_argument(
        "--interval",
        type=float,
        default=INTERVAL_S,
        help=f"Seconds between cycles (default {INTERVAL_S})",
    )
    ap.add_argument(
        "--pairs",
        nargs="+",
        default=None,
        help="Override pairs (default BTC-EUR ETH-EUR SOL-EUR)",
    )
    args = ap.parse_args()
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        os.environ.setdefault(key, "http://127.0.0.1:8791")

    if args.once:
        ticks = collect_cycle(args.pairs)
        return 0 if ticks else 1
    run_daemon(interval=args.interval, pairs=args.pairs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
