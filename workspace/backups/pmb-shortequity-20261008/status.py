#!/usr/bin/env python3
"""Print guardian status summary — no secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = GUARDIAN.parent
CONFIG_PATH = GUARDIAN / "config.json"
STATE_PATH = GUARDIAN / "state.json"
MODE_PATH = ROOT / "MODE"
STOP_PATH = ROOT / "STOP"
HALTED_PATH = GUARDIAN / "HALTED"



def _today_brussels():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d")


def _daily_pnl_today(state):
    """Daily P&L resets each day (Brussels): stale value from a previous day counts as 0."""
    if state.get("daily_pnl_date") != _today_brussels():
        return 0.0
    return float(state.get("daily_pnl_eur", 0) or 0)

def main() -> int:
    cfg = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    mode = MODE_PATH.read_text().strip() if MODE_PATH.exists() else "(missing)"
    stop = STOP_PATH.exists()
    halted_file = HALTED_PATH.exists()
    halted_state = bool(state.get("halted"))

    positions = state.get("positions") or []
    opens = [p for p in positions if p.get("status", "open") == "open"]
    exposure = sum(float(p.get("cost_eur", 0) or 0) for p in opens)
    cash = float(state.get("cash_eur", 0) or 0)
    bankroll = float(state.get("bankroll_eur", 0) or 0)
    equity = cash + sum(float(p.get("mark_eur", 0) or 0) for p in opens)
    peak = float(state.get("peak_equity_eur", 0) or 0)
    dd = ((peak - equity) / peak) if peak > 0 else 0.0
    daily = _daily_pnl_today(state)

    summary = {
        "mode": mode,
        "stop_file": stop,
        "halted_file": halted_file,
        "halted_state": halted_state,
        "trading_blocked": stop or halted_file or halted_state,
        "bankroll_eur": bankroll,
        "cash_eur": cash,
        "equity_eur": round(equity, 4),
        "peak_equity_eur": peak,
        "drawdown_pct": round(dd, 6),
        "daily_pnl_eur": daily,
        "open_positions": len(opens),
        "exposure_eur": round(exposure, 4),
        "pairs_whitelist": cfg.get("pairs_whitelist", []),
        "limits": {
            "kelly_fraction": cfg.get("kelly_fraction"),
            "max_position_pct": cfg.get("max_position_pct"),
            "max_exposure_pct": cfg.get("max_exposure_pct"),
            "max_drawdown_pct": cfg.get("max_drawdown_pct"),
            "max_daily_loss_pct": cfg.get("max_daily_loss_pct"),
            "max_concurrent": cfg.get("max_concurrent"),
            "order_types": cfg.get("order_types"),
            "post_only": cfg.get("post_only"),
            "leverage": cfg.get("leverage"),
            "market_orders": cfg.get("market_orders"),
        },
        "positions_open": [
            {
                "pair": p.get("pair"),
                "qty": p.get("qty"),
                "avg_price": p.get("avg_price"),
                "cost_eur": p.get("cost_eur"),
            }
            for p in opens
        ],
        "updated_at": state.get("updated_at"),
        "guardian_path": str(GUARDIAN),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
