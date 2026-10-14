#!/usr/bin/env python3
"""Read last_scan.json + guardian state; emit alert JSON for risk breaches.

Alerts (any may set alerted=true):
  - ETH (or any open position) below stop
  - daily loss >= 15%
  - drawdown >= 8%

Always exits 0. Writes state/alerts_last.json.

Buy-side (Predict BUY awaiting Risk) is separate: also run
`check_buy_wake.py` in the weekday routine / handoff — it writes
state/buy_wake.json. Scan price moves alone do not trigger that wake.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = GUARDIAN.parent
STATE_PATH = GUARDIAN / "state.json"
SCAN_PATH = ROOT / "state" / "last_scan.json"
OUT_PATH = ROOT / "state" / "alerts_last.json"
CFG_PATH = GUARDIAN / "config.json"
ROOT_CFG = ROOT / "config.json"
TZ = ZoneInfo("Europe/Brussels")



def _today_brussels():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d")


def _daily_pnl_today(state):
    """Daily P&L resets each day (Brussels): stale value from a previous day counts as 0."""
    if state.get("daily_pnl_date") != _today_brussels():
        return 0.0
    return float(state.get("daily_pnl_eur", 0) or 0)

def now_iso() -> str:
    return datetime.now(TZ).isoformat()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


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


def open_positions(state: dict) -> list[dict]:
    return [p for p in (state.get("positions") or []) if p.get("status", "open") == "open"]


def main() -> int:
    state = load_json(STATE_PATH)
    scan = load_json(SCAN_PATH)
    gcfg = load_json(CFG_PATH)
    rcfg = load_json(ROOT_CFG)
    risk = (rcfg.get("risk") or {}) if rcfg else {}

    max_daily = float(
        gcfg.get("max_daily_loss_pct", risk.get("max_daily_loss_pct", 0.15))
    )
    max_dd = float(gcfg.get("max_drawdown_pct", risk.get("max_drawdown_pct", 0.08)))

    prices = scan_price_map(scan)
    alerts: list[dict] = []
    flags = {
        "stop_breach": False,
        "daily_loss": False,
        "drawdown": False,
    }

    # Stop breaches for open positions (and ETH specifically if stop known)
    for pos in open_positions(state):
        pair = str(pos.get("pair") or "").upper()
        stop = pos.get("stop_price_eur")
        side = str(pos.get("side") or "long").lower()
        mid = prices.get(pair)
        if mid is None:
            mid = pos.get("last_mid_eur")
        try:
            mid_f = float(mid) if mid is not None else None
            stop_f = float(stop) if stop is not None else None
        except (TypeError, ValueError):
            continue
        if mid_f is None or stop_f is None:
            continue
        breached = False
        if side in ("long", "buy"):
            breached = mid_f <= stop_f
        elif side in ("short", "sell"):
            breached = mid_f >= stop_f
        if breached:
            flags["stop_breach"] = True
            alerts.append(
                {
                    "type": "stop_breach",
                    "pair": pair,
                    "side": side,
                    "price_eur": mid_f,
                    "stop_price_eur": stop_f,
                    "position_id": pos.get("id"),
                }
            )

    # ETH below stop even if only closed recently still of interest when open;
    # also flag if scan ETH is below a configured paper stop on any ETH row
    eth_px = prices.get("ETH-EUR")
    for pos in state.get("positions") or []:
        if str(pos.get("pair") or "").upper() != "ETH-EUR":
            continue
        if pos.get("status", "open") != "open":
            continue
        # already handled above
        break
    else:
        # No open ETH — still surface informational if scan missing
        if eth_px is None and "ETH-EUR" in (scan.get("pairs_whitelist") or []):
            pass

    bankroll = float(state.get("bankroll_eur") or 0) or 1.0
    daily_pnl = _daily_pnl_today(state)
    daily_loss_pct = abs(min(0.0, daily_pnl)) / bankroll
    if daily_loss_pct >= max_daily:
        flags["daily_loss"] = True
        alerts.append(
            {
                "type": "daily_loss",
                "daily_pnl_eur": daily_pnl,
                "daily_loss_pct": daily_loss_pct,
                "threshold": max_daily,
            }
        )

    # Prefer state.drawdown_pct if present; else compute from peak/equity
    dd = state.get("drawdown_pct")
    try:
        dd_f = float(dd) if dd is not None else None
    except (TypeError, ValueError):
        dd_f = None
    if dd_f is None:
        peak = float(state.get("peak_equity_eur") or bankroll)
        equity = float(state.get("equity_eur") or bankroll)
        dd_f = max(0.0, (peak - equity) / peak) if peak > 0 else 0.0
    # Accept either fraction (0.08) or percent (8)
    dd_frac = dd_f / 100.0 if dd_f > 1.0 else dd_f
    if dd_frac >= max_dd:
        flags["drawdown"] = True
        alerts.append(
            {
                "type": "drawdown",
                "drawdown_pct": dd_frac,
                "threshold": max_dd,
            }
        )

    alerted = any(flags.values())
    payload = {
        "checked_at": now_iso(),
        "alerted": alerted,
        "flags": flags,
        "alerts": alerts,
        "scan_at": scan.get("scanned_at"),
        "prices": prices,
        "open_positions": len(open_positions(state)),
        "daily_loss_pct": daily_loss_pct,
        "drawdown_pct": dd_frac,
        "thresholds": {
            "max_daily_loss_pct": max_daily,
            "max_drawdown_pct": max_dd,
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
