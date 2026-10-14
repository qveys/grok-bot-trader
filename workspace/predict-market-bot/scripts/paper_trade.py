#!/usr/bin/env python3
"""Simulate paper fills. Never calls live execution APIs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
LEDGER_PATH = STATE / "paper_ledger.json"
POSITIONS_PATH = STATE / "positions.json"
TRADES_PATH = STATE / "trades_log.jsonl"
VALIDATE = ROOT / "scripts" / "validate_risk.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")


def existing_exposure(positions: dict) -> float:
    total = 0.0
    for p in positions.get("positions", []):
        if p.get("status", "open") == "open":
            total += float(p.get("size_eur", 0))
    return total


def open_count(positions: dict) -> int:
    return sum(1 for p in positions.get("positions", []) if p.get("status", "open") == "open")


def run_validate(trade: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(VALIDATE)],
        input=json.dumps(trade),
        text=True,
        capture_output=True,
    )
    try:
        result = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "reasons": [f"validate_risk bad output: {proc.stdout!r} {proc.stderr!r}"],
            "max_size_eur": 0.0,
        }
    result["_exit"] = proc.returncode
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Paper trade simulator")
    parser.add_argument("--side", choices=["yes", "no"], required=True)
    parser.add_argument("--market-id", required=True)
    parser.add_argument("--price", type=float, required=True)
    parser.add_argument("--size-eur", type=float, required=True)
    parser.add_argument("--p-model", type=float, required=True)
    parser.add_argument("--p-market", type=float, required=True)
    args = parser.parse_args()

    ledger = load_json(LEDGER_PATH)
    positions = load_json(POSITIONS_PATH)

    bankroll = float(ledger.get("bankroll_eur", ledger.get("equity_eur", 500)))
    cash = float(ledger.get("cash_eur", bankroll))

    # crude daily loss / drawdown from ledger fields if present
    peak = float(ledger.get("peak_equity_eur", ledger.get("equity_eur", bankroll)))
    equity = float(ledger.get("equity_eur", bankroll))
    dd = max(0.0, (peak - equity) / peak) if peak > 0 else 0.0
    daily_loss = float(ledger.get("daily_loss_pct", 0.0))

    trade_check = {
        "p_model": args.p_model,
        "p_market": args.p_market,
        "bankroll": bankroll,
        "proposed_size_eur": args.size_eur,
        "existing_exposure_eur": existing_exposure(positions),
        "current_drawdown_pct": dd,
        "daily_loss_pct": daily_loss,
        "open_positions_count": open_count(positions),
    }

    validation = run_validate(trade_check)
    if not validation.get("ok"):
        print(json.dumps({"filled": False, "validation": validation}))
        return 1

    if args.size_eur > cash + 1e-9:
        print(
            json.dumps(
                {
                    "filled": False,
                    "validation": {
                        "ok": False,
                        "reasons": [f"insufficient cash {cash} for size {args.size_eur}"],
                        "max_size_eur": cash,
                    },
                }
            )
        )
        return 1

    ts = now_iso()
    trade_id = f"paper-{ts.replace(':', '').replace('-', '')}-{args.market_id}"[:64]
    contracts = args.size_eur / args.price if args.price > 0 else 0.0

    trade_row = {
        "id": trade_id,
        "ts": ts,
        "mode": "paper",
        "side": args.side,
        "market_id": args.market_id,
        "price": args.price,
        "size_eur": args.size_eur,
        "contracts": round(contracts, 6),
        "p_model": args.p_model,
        "p_market": args.p_market,
        "edge": round(args.p_model - args.p_market, 6),
        "status": "filled",
    }
    append_jsonl(TRADES_PATH, trade_row)

    pos = {
        "id": trade_id,
        "market_id": args.market_id,
        "side": args.side,
        "entry_price": args.price,
        "size_eur": args.size_eur,
        "contracts": round(contracts, 6),
        "p_model": args.p_model,
        "p_market": args.p_market,
        "opened_at": ts,
        "status": "open",
    }
    positions.setdefault("positions", []).append(pos)
    positions["updated_at"] = ts
    save_json(POSITIONS_PATH, positions)

    ledger["cash_eur"] = round(cash - args.size_eur, 4)
    # equity: cash + mark of open positions at entry (flat until mark-to-market)
    open_sz = existing_exposure(positions)
    ledger["equity_eur"] = round(ledger["cash_eur"] + open_sz, 4)
    ledger["peak_equity_eur"] = max(
        float(ledger.get("peak_equity_eur", ledger["equity_eur"])),
        ledger["equity_eur"],
    )
    ledger["updated_at"] = ts
    save_json(LEDGER_PATH, ledger)

    print(
        json.dumps(
            {
                "filled": True,
                "trade": trade_row,
                "ledger": {
                    "cash_eur": ledger["cash_eur"],
                    "equity_eur": ledger["equity_eur"],
                },
                "validation": {
                    "ok": True,
                    "reasons": [],
                    "max_size_eur": validation.get("max_size_eur"),
                },
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
